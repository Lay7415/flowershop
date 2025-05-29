# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm
from .models import User
from .forms import CustomAuthenticationForm

# Регистрируем нашу форму аутентификации для админки
admin.site.login_form = CustomAuthenticationForm

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Используем стандартные поля BaseUserAdmin и добавляем свои
    list_display = ('email', 'username', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active', 'groups')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    # Добавляем редактирование роли в детальном просмотре
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Дополнительная информация', {'fields': ('role', 'phone', 'first_name', 'last_name')}),
    )
    # Поле для логина - email
    ordering = ('email',)