from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

def role_required(allowed_roles):
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Для доступа необходимо войти в систему.")
                return redirect(f"{reverse('users:login')}?next={request.path}")
            if request.user.role not in allowed_roles:
                messages.error(request, "Доступ запрещен. Эта страница не пользователя с этой ролью.")
                return redirect('catalog:bouquet_list')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def deny_roles(denied_roles):
    if isinstance(denied_roles, str):
        denied_roles = [denied_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.role in denied_roles:
                messages.error(request, "Доступ запрещен для вашей роли.")
                # Перенаправляем на соответствующую панель вместо каталога
                if request.user.role == 'florist':
                    return redirect('orders:florist_dashboard')
                elif request.user.role == 'courier':
                    return redirect('orders:courier_dashboard')
                else:
                    return redirect('catalog:bouquet_list')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
