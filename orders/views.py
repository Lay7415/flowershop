# orders/views.py
import time
import random
from decimal import Decimal
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.conf import settings
from django.http import JsonResponse, HttpResponseNotAllowed
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied, ValidationError
from cart.cart import Cart
from core.decorators import role_required
from .models import CourierLocation, Order, OrderItem, Payment
from .forms import OrderCreateForm, PaymentForm


@role_required('client')
def order_create(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.warning(request, "Ваша корзина пуста.")
        return redirect('cart:cart_detail')

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    order = form.save(commit=False)
                    order.customer = request.user
                    order.delivery_distance = form.cleaned_data['delivery_distance']
                    
                    delivery_cost = Decimal(str(order.delivery_distance * float(settings.BASE_DELIVERY_PRICE_PER_METER)))
                    order.delivery_cost = delivery_cost
                    
                    cart_total = Decimal(str(cart.get_total_price()))
                    order.total_cost = cart_total + delivery_cost
                    
                    order.save()

                    order_items = []
                    for item in cart:
                        bouquet_obj = item['bouquet']
                        item_data = {
                            'quantity': item['quantity'],
                            'price': item['price'],
                        }
                        order_items.append(
                            OrderItem(
                                order=order,
                                bouquet=bouquet_obj,
                                price_per_item=item_data['price'],
                                quantity=item_data['quantity'],
                            )
                        )
                    OrderItem.objects.bulk_create(order_items)

                    Payment.objects.create(
                        order=order,
                        amount=order.total_cost,
                        status="new"
                    )

                cart.clear()
                messages.success(request, "Заказ успешно создан. Перенаправляем на страницу оплаты.")
                return redirect(reverse('orders:order_pay', kwargs={'order_id': order.id}))

            except Exception as e:
                messages.error(request, f"Ошибка при создании заказа: {str(e)}")
        context = {
            'form': form,
            'cart': cart,
            'settings': settings
        }
        return render(request, 'orders/order_form.html', context)
    else: 
        form = OrderCreateForm()
        context = {
            'form': form,
            'cart': cart,
            'settings': settings
        }
        return render(request, 'orders/order_form.html', context)


@role_required('client')
def order_pay(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    payment = order.payment 

    if order.status != "new" or payment.status != "new":
        messages.info(request, "Этот заказ уже обрабатывается или оплачен.")
        return redirect("orders:order_detail", pk=order.id)

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment.status = "pending"
            payment.save()

            payment_successful = random.choices([True, False], weights=[85, 15], k=1)[0]

            try:
                with transaction.atomic():
                    if payment_successful:
                        payment.status = "success"
                        payment.paid_at = timezone.now()
                        payment.error_message = None
                        order.status = "paid"
                        messages.success(request, f"Оплата заказа №{order.id} прошла успешно!")
                    else:
                        payment.status = "failed"
                        payment.error_message = random.choice([
                            "Недостаточно средств", "Ошибка шлюза банка",
                            "Карта заблокирована", "Неверные данные карты",
                        ])
                        messages.error(request, f"Оплата заказа №{order.id} не удалась: {payment.error_message}")
                    
                    payment.save()
                    order.save()

            except Exception as e:
                payment.status = "failed"
                payment.error_message = f"Внутренняя ошибка системы: {e}"
                payment.save()
                messages.error(request, "Произошла системная ошибка при обработке платежа. Попробуйте позже или свяжитесь с поддержкой.")
                return redirect("orders:order_detail", pk=order.id)

            if payment.status == "success":
                return redirect("orders:order_detail", pk=order.id)
            else:
                context = {"order": order, "payment": payment, "form": form}
                return render(request, "orders/order_pay.html", context)
        else: 
            context = {"order": order, "payment": payment, "form": form}
            messages.error(request, "Пожалуйста, проверьте правильность введенных данных карты.")
            return render(request, "orders/order_pay.html", context)
    else: 
        form = PaymentForm()
        context = {
            "order": order,
            "payment": payment,
            "form": form,
        }
        return render(request, "orders/order_pay.html", context)


@role_required('client')
def order_list(request):
    orders_list = Order.objects.filter(customer=request.user).order_by("-created_at")
    paginator = Paginator(orders_list, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        "orders": page_obj, 
        "page_obj": page_obj, 
        "is_paginated": page_obj.has_other_pages()
    }
    return render(request, "orders/order_list.html", context)


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    user = request.user

    if not (user.is_staff or order.customer == user or order.florist == user or order.courier == user):
        messages.error(request, "У вас нет прав для просмотра этого заказа.")
        return redirect('catalog:bouquet_list') # или 'orders:order_list' для клиента

    context = {"order": order}

    if order.status == "delivering":
        context["shop_lat"] = float(settings.SHOP_LAT)
        context["shop_lon"] = float(settings.SHOP_LON)
        context["shop_name"] = settings.SHOP_NAME
    
    print(f"Shop coordinates for order {pk}: {context.get('shop_lat', 'N/A')}, {context.get('shop_lon', 'N/A')}")

    context["can_confirm_completion"] = (
        order.customer == request.user and order.status == "delivered"
    )
    return render(request, "orders/order_detail.html", context)


@role_required('client')
def order_confirm_completion(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=pk, customer=request.user)

        if order.status == "delivered":
            order.status = "completed"
            order.save()
            messages.success(request, f"Получение заказа №{order.id} подтверждено.")
        else:
            messages.warning(request, f"Невозможно подтвердить получение заказа №{order.id} в текущем статусе ({order.get_status_display()}).")
        
        return redirect("orders:order_detail", pk=pk)
    return HttpResponseNotAllowed(['POST'])


@role_required('florist')
def florist_dashboard(request):
    florist = request.user
    status_filter = request.GET.get("status", "paid")

    queryset = Order.objects.filter(florist=florist)

    if status_filter == "paid":
        queryset = queryset.filter(status="paid")
    elif status_filter == "ready":
        queryset = queryset.filter(status="ready")
    else: 
        queryset = queryset.filter(status__in=["paid", "ready"])

    assigned_orders_list = queryset.order_by("delivery_datetime")
    
    paginator = Paginator(assigned_orders_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "assigned_orders": page_obj,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "current_status_filter": status_filter,
    }
    return render(request, "orders/florist_dashboard.html", context)


@role_required('florist') # Раскомментируйте
def florist_task_complete(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=pk, florist=request.user)

        if order.status == "paid":
            try:
                # Вызываем основной метод для списания всех компонентов
                order.deduct_all_stock_components() 

                # Если списание прошло успешно, меняем статус заказа
                order.status = "ready"
                order.save(update_fields=['status']) # Сохраняем только измененное поле
                messages.success(request, f"Сборка заказа №{order.id} завершена. Остатки компонентов успешно списаны.")
            
            except ValidationError as e:
                # Если во время списания возникла ошибка (нехватка товара и т.д.)
                messages.error(request, f"Ошибка при завершении сборки заказа №{order.id}: {e}")
                # Статус заказа не меняется, остается "paid"
            
        elif order.status == "ready":
             messages.info(request, f"Заказ №{order.id} уже находится в статусе 'Готов к доставке'.")
        else:
            messages.warning(request, f"Невозможно завершить сборку для заказа №{order.id} в текущем статусе '{order.get_status_display()}'. Заказ должен быть оплачен.")
        
        return redirect("orders:order_detail", pk=pk) # Убедитесь, что URL-имя верное
    
    return HttpResponseNotAllowed(['POST'])


# --- Представления для Курьера ---
@role_required('courier')
def courier_dashboard(request):
    courier = request.user
    status_filter = request.GET.get("status", "ready")
    
    queryset = Order.objects.filter(courier=courier)

    if status_filter == "ready":
        queryset = queryset.filter(status="ready")
    elif status_filter == "delivering":
        queryset = queryset.filter(status="delivering")
    elif status_filter == "delivered":
        queryset = queryset.filter(status="delivered")
    elif status_filter == "completed": 
        queryset = queryset.filter(status="completed")
    else:  
        queryset = queryset.filter(status__in=["ready", "delivering", "delivered"])
    
    assigned_deliveries_list = queryset.order_by("delivery_datetime")
    print(f"Courier queryset for {courier.username} with filter '{status_filter}': {assigned_deliveries_list}")

    paginator = Paginator(assigned_deliveries_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "assigned_deliveries": page_obj,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "current_status_filter": status_filter,
    }
    return render(request, "orders/courier_dashboard.html", context)

@role_required('courier')
def courier_start_delivery(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=pk, courier=request.user)

        if order.status == "ready":
            order.status = "delivering"
            order.save()
            messages.success(request, f"Доставка заказа №{order.id} начата.")
        else:
            messages.warning(request, f"Невозможно начать доставку заказа №{order.id} в статусе '{order.get_status_display()}'.")
        
        return redirect("orders:order_detail", pk=pk) 
    return HttpResponseNotAllowed(['POST'])

@role_required('courier')
def courier_task_complete(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=pk, courier=request.user)

        if order.status == "delivering":
            order.status = "delivered"
            order.save()
            messages.success(request, f"Доставка заказа №{order.id} отмечена как выполненная. Ожидается подтверждение клиента.")
        elif order.status == "ready":
            messages.warning(request, f"Сначала необходимо начать доставку заказа №{order.id}.")
        else:
            messages.warning(request, f"Невозможно завершить доставку заказа №{order.id} в статусе '{order.get_status_display()}'.")
        
        return redirect("orders:order_detail", pk=pk) 
    return HttpResponseNotAllowed(['POST'])

@role_required('courier')
def courier_update_location(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=pk, courier=request.user, status='delivering')
        try:
            lat_str = request.POST.get('lat')
            lon_str = request.POST.get('lon')

            if lat_str is None or lon_str is None:
                 return JsonResponse({'status': 'error', 'message': 'Missing lat/lon parameters'}, status=400)

            lat = float(lat_str)
            lon = float(lon_str)
            
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return JsonResponse({'status': 'error', 'message': 'Coordinates out of valid range'}, status=400)
            
            order.courier_lat = round(lat, 6)
            order.courier_lon = round(lon, 6)
            order.courier_last_update = timezone.now()
            order.save(update_fields=['courier_lat', 'courier_lon', 'courier_last_update'])
            
            CourierLocation.objects.update_or_create(
                user=request.user,
                defaults={'latitude': order.courier_lat, 'longitude': order.courier_lon}
            )
            
            return JsonResponse({
                'status': 'success',
                'lat': order.courier_lat,
                'lon': order.courier_lon,
                'last_update': order.courier_last_update.strftime('%H:%M:%S')
            })
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid coordinates format. Must be float.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Server error: {str(e)}'}, status=500)
    return HttpResponseNotAllowed(['POST'])