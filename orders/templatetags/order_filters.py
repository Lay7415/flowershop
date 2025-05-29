from django import template

register = template.Library()

@register.filter
def sub(value, arg):
    """Вычитает arg из value"""
    try:
        return value - arg
    except (ValueError, TypeError):
        return value