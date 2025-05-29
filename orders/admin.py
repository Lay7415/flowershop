# orders/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    CourierLocation, UserStatus, WorkRecord,
    Order, OrderItem, Payment, Cart, CartItem
)

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
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'customer', 'status', 'delivery_datetime',
        'florist', 'courier', 'calculated_total', 'admin_actions'
    )
    list_filter = ('status', 'delivery_datetime', 'florist', 'courier')
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
            'fields': ('delivery_address', 'delivery_lat', 'delivery_lon', 
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
    