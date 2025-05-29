# cart/context_processors.py
from .cart import Cart

def cart_context(request):
    cart = Cart(request)
    return {
        'cart_items': cart, # Объект Cart для итерации в шаблонах
        'cart_total_items': len(cart),
        'cart_total_price': cart.get_total_price()
    }