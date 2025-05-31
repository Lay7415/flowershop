# orders/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from django.utils import timezone
from rangefilter.filters import DateRangeFilter
import plotly.express as px
import plotly.graph_objects as go
from django.http import JsonResponse
from django.template.response import TemplateResponse

from .models import (
    CourierLocation, UserStatus, WorkRecord,
    Order, OrderItem, Payment, Cart, CartItem
)

class OrderStatisticsMixin:
    change_list_template = 'admin/orders/order_changelist.html'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        my_urls = [
            path('statistics/', self.statistics_view, name='order_statistics'),
        ]
        return my_urls + urls

    def statistics_view(self, request):
        # Статистика по дням
        daily_stats = Order.objects.filter(
            status__in=['completed', 'delivered']
        ).annotate(
            date=TruncDay('created_at')
        ).values('date').annotate(
            total_sales=Count('id'),
            total_revenue=Sum('total_cost'),
            total_delivery=Sum('delivery_cost'),
            net_revenue=Sum('total_cost') - Sum('delivery_cost')
        ).order_by('date')

        # Создаем графики
        dates = [stat['date'] for stat in daily_stats]
        sales = [stat['total_sales'] for stat in daily_stats]
        revenue = [float(stat['total_revenue']) for stat in daily_stats]
        net_revenue = [float(stat['net_revenue']) for stat in daily_stats]

        # График продаж
        sales_fig = go.Figure()
        sales_fig.add_trace(go.Scatter(x=dates, y=sales, mode='lines+markers', name='Количество заказов'))
        sales_fig.update_layout(title='Динамика продаж по дням', xaxis_title='Дата', yaxis_title='Количество заказов')
        
        # График выручки
        revenue_fig = go.Figure()
        revenue_fig.add_trace(go.Scatter(x=dates, y=revenue, mode='lines+markers', name='Общая выручка'))
        revenue_fig.add_trace(go.Scatter(x=dates, y=net_revenue, mode='lines+markers', name='Чистая прибыль'))
        revenue_fig.update_layout(title='Динамика выручки по дням', xaxis_title='Дата', yaxis_title='Сумма (сом)')

        # Месячная статистика
        monthly_stats = Order.objects.filter(
            status__in=['completed', 'delivered']
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total_sales=Count('id'),
            total_revenue=Sum('total_cost'),
            net_revenue=Sum('total_cost') - Sum('delivery_cost')
        ).order_by('month')

        # Годовая статистика
        yearly_stats = Order.objects.filter(
            status__in=['completed', 'delivered']
        ).annotate(
            year=TruncYear('created_at')
        ).values('year').annotate(
            total_sales=Count('id'),
            total_revenue=Sum('total_cost'),
            net_revenue=Sum('total_cost') - Sum('delivery_cost')
        ).order_by('year')

        context = {
            'daily_stats': daily_stats,
            'monthly_stats': monthly_stats,
            'yearly_stats': yearly_stats,
            'sales_chart': sales_fig.to_html(full_html=False),
            'revenue_chart': revenue_fig.to_html(full_html=False),
            'title': 'Статистика продаж',
            'opts': self.model._meta,
        }

        return TemplateResponse(request, 'admin/orders/statistics.html', context)

# Inline для отображения позиций прямо в заказе
class OrderItemInline(admin.TabularInline): # или admin.StackedInline
    model = OrderItem
    fields = ('bouquet', 'quantity', 'price_per_item', 'get_total')
    readonly_fields = ('price_per_item', 'get_total') # Запрещаем менять детали заказа
    extra = 0 # Не показывать пустые формы для добавления
    can_delete = False # Запретить удаление позиций из админки заказа

    def get_total(self, obj):
        return obj.get_total() if obj.id else 0
    get_total.short_description = 'Total Amount'

# Inline для отображения оплаты прямо в заказе
class PaymentInline(admin.StackedInline):
    model = Payment
    fields = ('amount', 'status', 'payment_method', 'paid_at', 'error_message')
    readonly_fields = ('amount', 'paid_at') # Сумму и время не меняем тут
    extra = 0
    can_delete = False # Нельзя удалить оплату отдельно от заказа

@admin.register(CourierLocation)
class CourierLocationAdmin(admin.ModelAdmin):
    list_display = ('user', 'latitude', 'longitude', 'last_update', 'admin_actions')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('last_update',)
    list_per_page = 20

    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" href="{}">Delete</a>',
            f'/admin/orders/courierlocation/{obj.pk}/change/',
            f'/admin/orders/courierlocation/{obj.pk}/delete/'
        )
    admin_actions.short_description = 'Actions'

@admin.register(UserStatus)
class UserStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'admin_actions')
    list_filter = ('status',)
    search_fields = ('user__email', 'user__username')
    list_per_page = 20

    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" href="{}">Delete</a>',
            f'/admin/orders/userstatus/{obj.pk}/change/',
            f'/admin/orders/userstatus/{obj.pk}/delete/'
        )
    admin_actions.short_description = 'Actions'

@admin.register(WorkRecord)
class WorkRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'start_time', 'end_time', 'admin_actions')
    list_filter = ('start_time',)
    search_fields = ('user__email', 'user__username')
    list_per_page = 20

    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" href="{}">Delete</a>',
            f'/admin/orders/workrecord/{obj.pk}/change/',
            f'/admin/orders/workrecord/{obj.pk}/delete/'
        )
    admin_actions.short_description = 'Actions'

@admin.register(Order)
class OrderAdmin(OrderStatisticsMixin, admin.ModelAdmin):
    list_display = (
        'id', 'customer', 'status', 'delivery_datetime',
        'florist', 'courier', 'calculated_total', 'admin_actions'
    )
    list_filter = (
        ('created_at', DateRangeFilter),
        'status', 'delivery_datetime', 'florist', 'courier'
    )
    search_fields = ('id', 'customer__email', 'customer__username', 'recipient_name', 'recipient_phone')
    readonly_fields = ('created_at', 'updated_at', 'total_cost') # Не даем менять вычисляемые/авто поля
    list_select_related = ('customer', 'florist', 'courier') # Оптимизация запросов для списка
    list_per_page = 15

    fieldsets = (
        ('Main Information', {
            'fields': ('id', 'customer', 'status', 'total_cost', 'created_at', 'updated_at')
        }),
        ('Executors', {
            'fields': ('florist', 'courier')
        }),
        ('Delivery Details', {
            'fields': ('delivery_address_name', 'delivery_lat', 'delivery_lon', 
                      'delivery_datetime', 'delivery_cost', 'delivery_distance')
        }),
        ('Recipient', {
            'fields': ('recipient_name', 'recipient_phone')
        }),
    )
    # Добавляем инлайны для позиций и оплаты
    inlines = [OrderItemInline, PaymentInline]

    # Добавляем ID в readonly_fields, чтобы оно отображалось, но не редактировалось
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj: # При редактировании существующего объекта
            readonly_fields.append('id')
            readonly_fields.append('customer') # Не даем менять клиента после создания
        return readonly_fields

    def calculated_total(self, obj):
        items = OrderItem.objects.filter(order=obj)
        total = sum(item.get_total() for item in items)
        return f"{total:.2f} сом"
    calculated_total.short_description = "Total Amount"

    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" href="{}">Delete</a>',
            f'/admin/orders/order/{obj.pk}/change/',
            f'/admin/orders/order/{obj.pk}/delete/'
        )
    admin_actions.short_description = 'Actions'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_link', 'amount', 'status', 'payment_method', 'paid_at', 'admin_actions')
    list_filter = ('status', 'payment_method')
    search_fields = ('order__id', 'order__customer__email')
    readonly_fields = ('paid_at',)
    list_select_related = ('order', 'order__customer') # Оптимизация
    list_per_page = 20

    # Ссылка на связанный заказ
    def order_link(self, obj):
        link = reverse("admin:orders_order_change", args=[obj.order.id])
        return format_html('<a href="{}">Order #{}</a>', link, obj.order.id)
    order_link.short_description = 'Order'

    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" href="{}">Delete</a>',
            f'/admin/orders/payment/{obj.pk}/change/',
            f'/admin/orders/payment/{obj.pk}/delete/'
        )
    admin_actions.short_description = 'Actions'

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_at', 'admin_actions')
    list_filter = ('status',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at',)
    inlines = [CartItemInline]
    list_per_page = 20

    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" href="{}">Delete</a>',
            f'/admin/orders/cart/{obj.pk}/change/',
            f'/admin/orders/cart/{obj.pk}/delete/'
        )
    admin_actions.short_description = 'Actions'

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'bouquet', 'quantity', 'admin_actions')
    search_fields = ('cart__user__username', 'bouquet__name')
    list_per_page = 20

    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" href="{}">Delete</a>',
            f'/admin/orders/cartitem/{obj.pk}/change/',
            f'/admin/orders/cartitem/{obj.pk}/delete/'
        )
    admin_actions.short_description = 'Actions'
