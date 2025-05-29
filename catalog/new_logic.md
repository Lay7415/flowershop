from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError

class Bouquet(models.Model):
    name = models.CharField("Name", max_length=100)
    price = models.DecimalField("Price", max_digits=10, decimal_places=2)
    description = models.TextField("Description")
    photo = models.ImageField("Photo", upload_to="bouquets/", blank=True, null=True)
    tag = models.CharField("Tag", max_length=100)
    is_active = models.BooleanField("Active", default=True)
    
    # Добавляем ManyToMany связи через промежуточные модели
    flowers = models.ManyToManyField('Flower', through='BouquetFlower', related_name='bouquets')
    ribbons = models.ManyToManyField('Ribbon', through='BouquetRibbon', related_name='bouquets')
    wrappers = models.ManyToManyField('Wrapper', through='BouquetWrapper', related_name='bouquets')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:bouquet_detail', args=[str(self.id)])

    class Meta:
        verbose_name = "Bouquet"
        verbose_name_plural = "Bouquets"

class Flower(models.Model):
    name = models.CharField("Name", max_length=100)
    price = models.DecimalField("Price", max_digits=10, decimal_places=2)
    description = models.TextField("Description")
    photo = models.ImageField("Photo", upload_to="flowers/", blank=True, null=True)

    def __str__(self):
        return self.name

    def get_available_stock_quantity(self):
        # Sums quantity from StockFlower items that are 'available'
        # Ensure StockFlower has a status field and 'available' is a valid choice
        return self.stock_items.filter(status='available').aggregate(
            total=Sum('quantity')
        )['total'] or 0

    class Meta:
        verbose_name = "Flower"
        verbose_name_plural = "Flowers"

class Ribbon(models.Model):
    name = models.CharField("Name", max_length=100)
    price = models.DecimalField("Price", max_digits=10, decimal_places=2)
    description = models.TextField("Description")
    photo = models.ImageField("Photo", upload_to="ribbons/", blank=True, null=True)

    def __str__(self):
        return self.name

    def get_available_stock_length(self):
        # Sums length from StockRibbon items that are 'available'
        return self.stock_items.filter(status='available').aggregate(
            total=Sum('length')
        )['total'] or 0

    class Meta:
        verbose_name = "Ribbon"
        verbose_name_plural = "Ribbons"

class Wrapper(models.Model):
    name = models.CharField("Name", max_length=100)
    price = models.DecimalField("Price", max_digits=10, decimal_places=2)
    description = models.TextField("Description")
    photo = models.ImageField("Photo", upload_to="wrappers/", blank=True, null=True)

    def __str__(self):
        return self.name

    def get_available_stock_length(self):
        # Sums length from StockWrapper items that are 'available'
        return self.stock_items.filter(status='available').aggregate(
            total=Sum('length')
        )['total'] or 0

    class Meta:
        verbose_name = "Wrapper"
        verbose_name_plural = "Wrappers"

class BouquetFlower(models.Model):
    bouquet = models.ForeignKey(Bouquet, on_delete=models.CASCADE, 
                            related_name="flower_items")
    flower = models.ForeignKey(Flower, on_delete=models.CASCADE, 
                             related_name="bouquet_items")
    quantity = models.PositiveIntegerField("Quantity")

    def clean(self):
        # Проверяем наличие на складе при сохранении
        available = self.flower.get_available_stock()
        if available < self.quantity:
            raise ValidationError(
                f'Недостаточно цветов на складе. Доступно: {available}, требуется: {self.quantity}'
            )

    def __str__(self):
        return f"{self.flower} in {self.bouquet}"

    class Meta:
        verbose_name = "Bouquet Flower"
        verbose_name_plural = "Bouquet Flowers"

class BouquetRibbon(models.Model):
    bouquet = models.ForeignKey(Bouquet, on_delete=models.CASCADE, 
                            related_name="ribbon_items")
    ribbon = models.ForeignKey(Ribbon, on_delete=models.CASCADE, 
                            related_name="bouquet_items")
    length = models.FloatField("Length")

    def clean(self):
        # Проверяем наличие на складе при сохранении
        available = self.ribbon.get_available_stock()
        if available < self.length:
            raise ValidationError(
                f'Недостаточно ленты на складе. Доступно: {available}м, требуется: {self.length}м'
            )

    def __str__(self):
        return f"{self.ribbon} for {self.bouquet}"

    class Meta:
        verbose_name = "Bouquet Ribbon"
        verbose_name_plural = "Bouquet Ribbons"

class BouquetWrapper(models.Model):
    bouquet = models.ForeignKey(Bouquet, on_delete=models.CASCADE, 
                            related_name="wrapper_items")
    wrapper = models.ForeignKey(Wrapper, on_delete=models.CASCADE, 
                              related_name="bouquet_items")
    length = models.FloatField("Length")

    def clean(self):
        # Проверяем наличие на складе при сохранении
        available = self.wrapper.get_available_stock()
        if available < self.length:
            raise ValidationError(
                f'Недостаточно упаковки на складе. Доступно: {available}м, требуется: {self.length}м'
            )

    def __str__(self):
        return f"{self.wrapper} for {self.bouquet}"

    class Meta:
        verbose_name = "Bouquet Wrapper"
        verbose_name_plural = "Bouquet Wrappers"

class StockFlower(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('used', 'Used'), # Changed from is_used for consistency
        ('reserved', 'Reserved'),
        ('damaged', 'Damaged'),
        ('expired', 'Expired'),
    ]
    
    flower = models.ForeignKey(Flower, on_delete=models.CASCADE, 
                             related_name="stock_items")
    delivery_date = models.DateField("Delivery Date")
    quantity = models.PositiveIntegerField("Quantity") # Ensure this can go to 0
    number = models.CharField("Batch Number", max_length=50)
    status = models.CharField("Stock Item Status", max_length=30, 
                           choices=STATUS_CHOICES, default='available')

    def __str__(self):
        return f"{self.flower} in stock ({self.quantity} pcs.) - {self.status}"

    class Meta:
        verbose_name = "Stock Flower"
        verbose_name_plural = "Stock Flowers"
        ordering = ['delivery_date', 'id'] # Oldest first

class StockRibbon(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('out_of_stock', 'Out of Stock'),
        # Add other statuses if needed, e.g., 'used_partial'
    ]
    
    ribbon = models.ForeignKey(Ribbon, on_delete=models.CASCADE, 
                            related_name="stock_items")
    delivery_date = models.DateField("Delivery Date")
    length = models.FloatField("Length") # Changed to FloatField for partial usage
    status = models.CharField("Stock Item Status", max_length=30, 
                           choices=STATUS_CHOICES, default='available')

    def __str__(self):
        return f"{self.ribbon} in stock ({self.length} m) - {self.status}"

    class Meta:
        verbose_name = "Stock Ribbon"
        verbose_name_plural = "Stock Ribbons"
        ordering = ['delivery_date', 'id'] # Oldest first

class StockWrapper(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('out_of_stock', 'Out of Stock'),
    ]
    
    wrapper = models.ForeignKey(Wrapper, on_delete=models.CASCADE, 
                              related_name="stock_items")
    delivery_date = models.DateField("Delivery Date")
    length = models.FloatField("Length") # Changed to FloatField for partial usage
    status = models.CharField("Stock Item Status", max_length=30, 
                           choices=STATUS_CHOICES, default='available')

    def __str__(self):
        return f"{self.wrapper} in stock ({self.length} m) - {self.status}"

    class Meta:
        verbose_name = "Stock Wrapper"
        verbose_name_plural = "Stock Wrappers"
        ordering = ['delivery_date', 'id'] # Oldest first


# orders/views.py
import time
import random
from decimal import Decimal
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseNotAllowed
from django.core.paginator import Paginator
from .models import CourierLocation, Order, OrderItem, Payment
from .forms import OrderCreateForm, PaymentForm
from cart.cart import Cart
from core.decorators import role_required


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


@role_required('florist')
def florist_task_complete(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=pk, florist=request.user)

        if order.status == "paid":
            try:
                with transaction.atomic():
                    # 1. Pre-check stock availability
                    stock_errors = check_stock_availability_for_order(order)
                    if stock_errors:
                        for error_msg in stock_errors:
                            messages.warning(request, error_msg)
                        # Do not proceed if stock is insufficient
                        return redirect("orders:order_detail", pk=pk) 

                    # 2. Deduct stock (this is now safe due to pre-check and transaction)
                    deduct_stock_for_order(order) # This might raise ValidationError if something unexpected happens

                    # 3. Update order status
                    order.status = "ready"
                    order.save()
                    
                    messages.success(request, f"Сборка заказа №{order.id} завершена. Остатки на складе обновлены.")

            except ValidationError as e:
                # This catches errors from deduct_stock_for_order if an unexpected shortfall occurs
                # or any other validation error within the transaction.
                messages.error(request, f"Ошибка при завершении сборки заказа №{order.id}: {e}")
            except Exception as e:
                # Catch any other unexpected errors during the transaction
                messages.error(request, f"Произошла непредвиденная ошибка при обработке заказа №{order.id}: {str(e)}. Обратитесь в поддержку.")
        
        elif order.status == "ready":
             messages.info(request, f"Сборка заказа №{order.id} уже была завершена.")
        else:
            messages.warning(request, f"Невозможно завершить сборку заказа №{order.id} в статусе '{order.get_status_display()}'. Заказ должен быть оплачен.")
        
        return redirect("orders:order_detail", pk=pk) 

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