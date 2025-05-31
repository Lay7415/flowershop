# catalog/admin.py
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncMonth
import plotly.express as px
import plotly.graph_objects as go
from django.template.response import TemplateResponse

from .models import (
    Flower, Ribbon, Wrapper,
    BouquetFlower, BouquetRibbon, BouquetWrapper,
    StockFlower, StockRibbon, StockWrapper,
    Bouquet
)

class BouquetStatisticsMixin:
    change_list_template = 'admin/catalog/bouquet_changelist.html'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        my_urls = [
            path('statistics/', self.statistics_view, name='bouquet_statistics'),
        ]
        return my_urls + urls

    def statistics_view(self, request):
        try:
            # Try the first approach - assuming direct cart->order relationship
            popular_bouquets = Bouquet.objects.annotate(
                orders_count=Count('cartitem__order', distinct=True),
                total_revenue=Sum(
                    F('cartitem__quantity') * F('price'),
                    filter=Q(cartitem__order__isnull=False)
                ),
                avg_price=Avg('price')
            ).filter(cartitem__order__isnull=False).order_by('-orders_count')
        except Exception:
            try:
                # Try second approach - assuming orderitem relationship
                popular_bouquets = Bouquet.objects.annotate(
                    orders_count=Count('orderitem__order', distinct=True),
                    total_revenue=Sum(
                        F('orderitem__quantity') * F('price'),
                        filter=Q(orderitem__order__isnull=False)
                    ),
                    avg_price=Avg('price')
                ).filter(orderitem__order__isnull=False).order_by('-orders_count')
            except Exception:
                # Fallback - just get all bouquets without order statistics
                popular_bouquets = Bouquet.objects.annotate(
                    orders_count=Count('id'),
                    total_revenue=Sum('price'),
                    avg_price=Avg('price')
                ).order_by('-orders_count')

        # График популярности букетов
        bouquets_data = [
            {'name': b.name, 'orders_count': b.orders_count} 
            for b in popular_bouquets[:10]
        ]
        
        if bouquets_data:
            bouquets_fig = px.bar(
                bouquets_data,
                x='name',
                y='orders_count',
                title="Топ-10 самых популярных букетов",
                labels={'name': 'Букет', 'orders_count': 'Количество заказов'}
            )
        else:
            # Create empty chart if no data
            bouquets_fig = go.Figure()
            bouquets_fig.update_layout(
                title="Топ-10 самых популярных букетов",
                annotations=[dict(text="Нет данных для отображения", 
                                x=0.5, y=0.5, showarrow=False)]
            )

        # Статистика по компонентам
        try:
            # Try different relationship patterns for components
            popular_flowers = Flower.objects.annotate(
                usage_count=Count('bouquet_items__bouquet__cartitem__order', distinct=True)
            ).filter(usage_count__gt=0).order_by('-usage_count')
        except Exception:
            try:
                popular_flowers = Flower.objects.annotate(
                    usage_count=Count('bouquet_items__bouquet__orderitem__order', distinct=True)
                ).filter(usage_count__gt=0).order_by('-usage_count')
            except Exception:
                popular_flowers = Flower.objects.annotate(
                    usage_count=Count('bouquet_items', distinct=True)
                ).filter(usage_count__gt=0).order_by('-usage_count')

        try:
            popular_ribbons = Ribbon.objects.annotate(
                usage_count=Count('bouquet_items__bouquet__cartitem__order', distinct=True)
            ).filter(usage_count__gt=0).order_by('-usage_count')
        except Exception:
            try:
                popular_ribbons = Ribbon.objects.annotate(
                    usage_count=Count('bouquet_items__bouquet__orderitem__order', distinct=True)
                ).filter(usage_count__gt=0).order_by('-usage_count')
            except Exception:
                popular_ribbons = Ribbon.objects.annotate(
                    usage_count=Count('bouquet_items', distinct=True)
                ).filter(usage_count__gt=0).order_by('-usage_count')

        try:
            popular_wrappers = Wrapper.objects.annotate(
                usage_count=Count('bouquet_items__bouquet__cartitem__order', distinct=True)
            ).filter(usage_count__gt=0).order_by('-usage_count')
        except Exception:
            try:
                popular_wrappers = Wrapper.objects.annotate(
                    usage_count=Count('bouquet_items__bouquet__orderitem__order', distinct=True)
                ).filter(usage_count__gt=0).order_by('-usage_count')
            except Exception:
                popular_wrappers = Wrapper.objects.annotate(
                    usage_count=Count('bouquet_items', distinct=True)
                ).filter(usage_count__gt=0).order_by('-usage_count')

        # График популярности компонентов
        components_data = []
        for flower in popular_flowers[:5]:
            components_data.append({'name': flower.name, 'count': flower.usage_count, 'type': 'Цветы'})
        for ribbon in popular_ribbons[:5]:
            components_data.append({'name': ribbon.name, 'count': ribbon.usage_count, 'type': 'Ленты'})
        for wrapper in popular_wrappers[:5]:
            components_data.append({'name': wrapper.name, 'count': wrapper.usage_count, 'type': 'Упаковка'})

        if components_data:
            components_fig = px.bar(
                components_data,
                x='name',
                y='count',
                color='type',
                title="Популярные компоненты букетов",
                barmode='group',
                labels={'name': 'Компонент', 'count': 'Количество использований', 'type': 'Тип'}
            )
        else:
            # Create empty chart if no data
            components_fig = go.Figure()
            components_fig.update_layout(
                title="Популярные компоненты букетов",
                annotations=[dict(text="Нет данных для отображения", 
                                x=0.5, y=0.5, showarrow=False)]
            )

        # Статистика по месяцам
        try:
            # Try different approaches for monthly stats
            monthly_stats = Bouquet.objects.annotate(
                month=TruncMonth('cartitem__order__created_at')
            ).values('month').annotate(
                total_orders=Count('cartitem__order', distinct=True),
                total_revenue=Sum('cartitem__price_per_item')
            ).filter(month__isnull=False).order_by('month')
        except Exception:
            try:
                monthly_stats = Bouquet.objects.annotate(
                    month=TruncMonth('orderitem__order__created_at')
                ).values('month').annotate(
                    total_orders=Count('orderitem__order', distinct=True),
                    total_revenue=Sum('orderitem__price')
                ).filter(month__isnull=False).order_by('month')
            except Exception:
                # Fallback to creation date if no order relationship works
                monthly_stats = Bouquet.objects.annotate(
                    month=TruncMonth('created_at')
                ).values('month').annotate(
                    total_orders=Count('id'),
                    total_revenue=Sum('price')
                ).filter(month__isnull=False).order_by('month') if hasattr(Bouquet, 'created_at') else []

        # График продаж по месяцам
        if monthly_stats:
            monthly_fig = go.Figure()
            monthly_fig.add_trace(go.Scatter(
                x=[stat['month'] for stat in monthly_stats],
                y=[stat['total_orders'] for stat in monthly_stats],
                name='Количество заказов',
                mode='lines+markers'
            ))
            monthly_fig.add_trace(go.Scatter(
                x=[stat['month'] for stat in monthly_stats],
                y=[float(stat['total_revenue'] or 0) for stat in monthly_stats],
                name='Выручка',
                mode='lines+markers',
                yaxis='y2'
            ))
            monthly_fig.update_layout(
                title='Динамика продаж букетов по месяцам',
                yaxis=dict(title='Количество заказов'),
                yaxis2=dict(title='Выручка', overlaying='y', side='right')
            )
        else:
            # Create empty chart if no data
            monthly_fig = go.Figure()
            monthly_fig.update_layout(
                title='Динамика продаж букетов по месяцам',
                annotations=[dict(text="Нет данных для отображения", 
                                x=0.5, y=0.5, showarrow=False)]
            )

        context = {
            'popular_bouquets': popular_bouquets[:10],
            'popular_flowers': popular_flowers[:10],
            'popular_ribbons': popular_ribbons[:10],
            'popular_wrappers': popular_wrappers[:10],
            'bouquets_chart': bouquets_fig.to_html(full_html=False),
            'components_chart': components_fig.to_html(full_html=False),
            'monthly_chart': monthly_fig.to_html(full_html=False),
            'title': 'Статистика букетов',
            'opts': self.model._meta,
        }

        return TemplateResponse(request, 'admin/catalog/statistics.html', context)

# Инлайны для управления складом
class StockFlowerInline(admin.TabularInline):
    model = StockFlower
    extra = 1

class StockRibbonInline(admin.TabularInline):
    model = StockRibbon
    extra = 1

class StockWrapperInline(admin.TabularInline):
    model = StockWrapper
    extra = 1

# Инлайны для букетов
class BouquetFlowerInline(admin.TabularInline):
    model = BouquetFlower
    extra = 1

class BouquetRibbonInline(admin.TabularInline):
    model = BouquetRibbon
    extra = 1

class BouquetWrapperInline(admin.TabularInline):
    model = BouquetWrapper
    extra = 1

@admin.register(Bouquet)
class BouquetAdmin(BouquetStatisticsMixin, admin.ModelAdmin):
    list_display = ('name', 'price', 'tag', 'is_active', 'display_image', 'admin_actions')
    list_filter = ('is_active', 'tag')
    search_fields = ('name', 'description', 'tag')
    list_editable = ('price', 'is_active')
    inlines = [BouquetFlowerInline, BouquetRibbonInline, BouquetWrapperInline]
    list_per_page = 15
    
    fieldsets = (
        (None, {
            'fields': ('name', 'price', 'description', 'photo', 'tag', 'is_active')
        }),
    )
    
    def display_image(self, obj):
        if obj and obj.photo:
            try:
                return format_html(
                    '<img src="{}" style="width:100px; height:100px; object-fit:cover; border-radius:8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />',
                    obj.photo.url
                )
            except Exception as e:
                return format_html('<span class="error">Ошибка загрузки фото: {}</span>', str(e))
        return format_html('<span style="color: #999;">Нет фото</span>')
    display_image.short_description = 'Фото'
    display_image.allow_tags = True

    def save_model(self, request, obj, form, change):
        if not change:  # This is a new object
            super().save_model(request, obj, form, change)
        else:
            if 'photo' in form.changed_data and obj.photo:
                # Save without commit to get the model instance
                obj.save(update_fields=['photo'])
            super().save_model(request, obj, form, change)

    class Media:
        css = {
            'all': ('admin/css/custom.css',)
        }

    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" href="{}">Delete</a>',
            f'/admin/catalog/bouquet/{obj.pk}/change/',
            f'/admin/catalog/bouquet/{obj.pk}/delete/'
        )
    admin_actions.short_description = 'Actions'

@admin.register(Flower)
class FlowerAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'display_photo', 'admin_actions')
    search_fields = ('name', 'description')
    list_editable = ('price',)
    inlines = [StockFlowerInline]
    list_per_page = 20

    def display_photo(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-width: 100px; height: auto; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />',
                obj.photo.url
            )
        return format_html('<span class="text-muted">Нет фото</span>')
    display_photo.short_description = 'Фото'

    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" href="{}">Delete</a>',
            f'/admin/catalog/flower/{obj.pk}/change/',
            f'/admin/catalog/flower/{obj.pk}/delete/'
        )
    admin_actions.short_description = 'Actions'

@admin.register(Ribbon)
class RibbonAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'display_photo', 'admin_actions')
    search_fields = ('name', 'description')
    list_editable = ('price',)
    inlines = [StockRibbonInline]
    list_per_page = 20

    def display_photo(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-width: 100px; height: auto; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />',
                obj.photo.url
            )
        return format_html('<span class="text-muted">Нет фото</span>')
    display_photo.short_description = 'Фото'

    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" href="{}">Delete</a>',
            f'/admin/catalog/ribbon/{obj.pk}/change/',
            f'/admin/catalog/ribbon/{obj.pk}/delete/'
        )
    admin_actions.short_description = 'Actions'

@admin.register(Wrapper)
class WrapperAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'display_photo', 'admin_actions')
    search_fields = ('name', 'description')
    list_editable = ('price',)
    inlines = [StockWrapperInline]
    list_per_page = 20

    def display_photo(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-width: 100px; height: auto; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />',
                obj.photo.url
            )
        return format_html('<span class="text-muted">Нет фото</span>')
    display_photo.short_description = 'Фото'

    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" href="{}">Delete</a>',
            f'/admin/catalog/wrapper/{obj.pk}/change/',
            f'/admin/catalog/wrapper/{obj.pk}/delete/'
        )
    admin_actions.short_description = 'Actions'

@admin.register(StockFlower)
class StockFlowerAdmin(admin.ModelAdmin):
    list_display = ('flower', 'delivery_date', 'quantity', 'number', 'status', 'admin_actions')
    list_filter = ('status', 'delivery_date')
    search_fields = ('flower__name', 'number')
    raw_id_fields = ('flower',)
    list_per_page = 20

    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" href="{}">Delete</a>',
            f'/admin/catalog/stockflower/{obj.pk}/change/',
            f'/admin/catalog/stockflower/{obj.pk}/delete/'
        )
    admin_actions.short_description = 'Actions'

@admin.register(StockRibbon)
class StockRibbonAdmin(admin.ModelAdmin):
    list_display = ('ribbon', 'delivery_date', 'length', 'status', 'admin_actions')
    list_filter = ('status', 'delivery_date')
    search_fields = ('ribbon__name',)
    raw_id_fields = ('ribbon',)
    list_per_page = 20

    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" href="{}">Delete</a>',
            f'/admin/catalog/stockribbon/{obj.pk}/change/',
            f'/admin/catalog/stockribbon/{obj.pk}/delete/'
        )
    admin_actions.short_description = 'Actions'

@admin.register(StockWrapper)
class StockWrapperAdmin(admin.ModelAdmin):
    list_display = ('wrapper', 'delivery_date', 'length', 'status', 'admin_actions')
    list_filter = ('status', 'delivery_date')
    search_fields = ('wrapper__name',)
    raw_id_fields = ('wrapper',)
    list_per_page = 20

    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" href="{}">Delete</a>',
            f'/admin/catalog/stockwrapper/{obj.pk}/change/',
            f'/admin/catalog/stockwrapper/{obj.pk}/delete/'
        )
    admin_actions.short_description = 'Actions'