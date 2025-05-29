# catalog/admin.py
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from .models import (
    Flower, Ribbon, Wrapper,
    BouquetFlower, BouquetRibbon, BouquetWrapper,
    StockFlower, StockRibbon, StockWrapper,
    Bouquet
)

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
class BouquetAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'tag', 'is_active', 'display_image', 'admin_actions')
    list_filter = ('is_active', 'tag')
    search_fields = ('name', 'description', 'tag')
    list_editable = ('price', 'is_active')
    inlines = [BouquetFlowerInline, BouquetRibbonInline, BouquetWrapperInline]
    list_per_page = 15

    def display_image(self, obj):
        if obj.photo:
            return mark_safe(f'<img src="{obj.photo.url}" width="50" height="auto" />')
        return "Нет фото"
    display_image.short_description = 'Фото'

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
    inlines = [StockFlowerInline]  # Добавляем инлайн для управления складом
    list_per_page = 20

    def display_photo(self, obj):
        if obj.photo:
            return mark_safe(f'<img src="{obj.photo.url}" width="50" height="auto" />')
        return "Нет фото"
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
    inlines = [StockRibbonInline]  # Добавляем инлайн для управления складом
    list_per_page = 20

    def display_photo(self, obj):
        if obj.photo:
            return mark_safe(f'<img src="{obj.photo.url}" width="50" height="auto" />')
        return "Нет фото"
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
    inlines = [StockWrapperInline]  # Добавляем инлайн для управления складом
    list_per_page = 20

    def display_photo(self, obj):
        if obj.photo:
            return mark_safe(f'<img src="{obj.photo.url}" width="50" height="auto" />')
        return "Нет фото"
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