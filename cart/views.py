# cart/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from catalog.models import Bouquet
from .cart import Cart
from core.decorators import role_required


@role_required('client')
@require_POST
def add_to_cart(request, bouquet_id):
    cart = Cart(request)
    bouquet = get_object_or_404(Bouquet, id=bouquet_id, is_active=True)
    quantity = int(request.POST.get('quantity', 1)) # Получаем количество из формы
    cart.add(bouquet=bouquet, quantity=quantity, update_quantity=False)
    messages.success(request, f'"{bouquet.name}" добавлен в корзину.')
    return redirect('cart:cart_detail') # Или redirect(request.META.get('HTTP_REFERER', 'catalog:bouquet_list'))

@role_required('client')
@require_POST
def update_cart(request, bouquet_id):
    cart = Cart(request)
    bouquet = get_object_or_404(Bouquet, id=bouquet_id) # Не обязательно активный, чтобы можно было убрать
    quantity = int(request.POST.get('quantity', 0))
    if quantity > 0:
         cart.add(bouquet=bouquet, quantity=quantity, update_quantity=True)
         messages.info(request, f'Количество "{bouquet.name}" обновлено.')
    else:
         cart.remove(bouquet)
         messages.info(request, f'"{bouquet.name}" удален из корзины.')
    return redirect('cart:cart_detail')

@role_required('client')
@require_POST
def remove_from_cart(request, bouquet_id):
    cart = Cart(request)
    bouquet = get_object_or_404(Bouquet, id=bouquet_id)
    cart.remove(bouquet)
    messages.info(request, f'"{bouquet.name}" удален из корзины.')
    return redirect('cart:cart_detail')

@role_required('client')
def cart_detail(request):
    cart = Cart(request)
    # Проверяем, есть ли неактивные товары в корзине и удаляем их
    # (лучше делать это при итерации, как в __iter__)
    active_bouquet_ids = list(Bouquet.objects.filter(id__in=cart.cart.keys(), is_active=True).values_list('id', flat=True))
    removed_count = 0
    for bouquet_id in list(cart.cart.keys()): # Итерируемся по копии ключей
        if int(bouquet_id) not in active_bouquet_ids:
            del cart.cart[bouquet_id]
            removed_count += 1
    if removed_count > 0:
        cart.save()
        messages.warning(request, f"Некоторые товары были удалены из корзины, так как стали недоступны.")

    return render(request, 'cart/cart_detail.html', {'cart': cart}) # Передаем сам объект cart