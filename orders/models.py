from django.db import models
from django.conf import settings
from django.utils import timezone
from catalog.models import Bouquet
from django.db import transaction
from collections import defaultdict
from catalog.models import Flower, StockFlower, Ribbon, StockRibbon, Wrapper, StockWrapper

class CourierLocation(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                           related_name="location", verbose_name="User",
                           limit_choices_to={'role': 'courier'})
    longitude = models.FloatField("Longitude")
    latitude = models.FloatField("Latitude")
    last_update = models.DateTimeField("Last Update", auto_now=True)

    def __str__(self):
        return f"Location of {self.user}"

    class Meta:
        verbose_name = "Courier Location"
        verbose_name_plural = "Courier Locations"

class UserStatus(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                           related_name="status", verbose_name="User")
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('busy', 'Busy'),
    ]
    status = models.CharField("Status", max_length=30, choices=STATUS_CHOICES, default='available')

    def __str__(self):
        return f"Status of {self.user}"

    class Meta:
        verbose_name = "User Status"
        verbose_name_plural = "User Statuses"

class WorkRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                         related_name="work_records", verbose_name="User")
    start_time = models.DateTimeField("Shift start date/time")
    end_time = models.DateTimeField("Shift end date/time", null=True, blank=True)

    def __str__(self):
        return f"Shift of {self.user} from {self.start_time}"

    class Meta:
        verbose_name = "Work Record"
        verbose_name_plural = "Work Records"

class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('paid', 'Оплачен'),
        ('ready', 'Готов к доставке'),
        ('delivering', 'Доставляется'),
        ('delivered', 'Доставлен'),
        ('completed', 'Выполнен'),
        ('canceled', 'Отменен'),
    ]
    
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                             related_name='orders', verbose_name="Customer",
                             limit_choices_to={'role': 'client'})
    status = models.CharField("Order Status", max_length=30, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField("Created at", auto_now_add=True)
    updated_at = models.DateTimeField("Updated at", auto_now=True)
    delivery_datetime = models.DateTimeField("Delivery Date/Time")
    
    florist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                            related_name='handled_orders', verbose_name="Florist",
                            null=True, blank=True, limit_choices_to={'role': 'florist'})
    courier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                            related_name='delivered_orders', verbose_name="Courier",
                            null=True, blank=True, limit_choices_to={'role': 'courier'})
    
    total_cost = models.DecimalField("Total Cost", max_digits=10, decimal_places=2)
    delivery_cost = models.DecimalField("Delivery Cost", max_digits=10, decimal_places=2, default=0)
    delivery_distance = models.FloatField("Delivery Distance (meters)", default=0)
    
    delivery_address_name = models.CharField("Delivery Address", max_length=255)
    delivery_lat = models.FloatField("Delivery Latitude")
    delivery_lon = models.FloatField("Delivery Longitude")
    
    # Добавляем поля для отслеживания курьера
    courier_lat = models.FloatField("Courier Latitude", null=True, blank=True)
    courier_lon = models.FloatField("Courier Longitude", null=True, blank=True)
    courier_last_update = models.DateTimeField("Courier Location Last Update", null=True, blank=True)
    
    recipient_name = models.CharField("Recipient Name", max_length=255)
    recipient_phone = models.CharField("Recipient Phone", max_length=20)
    
    cart = models.OneToOneField('Cart', on_delete=models.PROTECT, 
                            related_name='order', verbose_name="Cart", null=True)

    def __str__(self):
        return f"Order #{self.id} from {self.created_at.date()}"

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        
    def get_bouquet_cost(self):
        return self.total_cost - self.delivery_cost
    
    def _deduct_flowers(self):
        required_flowers = defaultdict(int)
        for item in self.items.all():
            bouquet = item.bouquet
            order_item_quantity = item.quantity
            for bouquet_flower_item in bouquet.flower_items.all(): 
                required_flowers[bouquet_flower_item.flower_id] += bouquet_flower_item.quantity * order_item_quantity
        
        if not required_flowers:
            return

        for flower_id, total_quantity_to_deduct in required_flowers.items():
            try:
                flower_instance = Flower.objects.get(id=flower_id)
            except Flower.DoesNotExist:
                raise ValidationError(f"Цветок с ID {flower_id} не найден в каталоге.")

            available_stock_lots = StockFlower.objects.filter(
                flower_id=flower_id,
                status='available',
                quantity__gt=0
            ).order_by('delivery_date') 

            current_total_available = sum(lot.quantity for lot in available_stock_lots)
            if current_total_available < total_quantity_to_deduct:
                raise ValidationError(
                    f"Недостаточно цветка '{flower_instance.name}' на складе. "
                    f"Требуется: {total_quantity_to_deduct}, доступно: {current_total_available}."
                )

            quantity_left_to_deduct = total_quantity_to_deduct
            for stock_lot in available_stock_lots:
                if quantity_left_to_deduct <= 0:
                    break
                
                deduct_from_this_lot = min(stock_lot.quantity, quantity_left_to_deduct)
                stock_lot.quantity -= deduct_from_this_lot
                quantity_left_to_deduct -= deduct_from_this_lot
                
                if stock_lot.quantity == 0:
                    stock_lot.status = 'is_used'
                stock_lot.save()
            
            if quantity_left_to_deduct > 0: 
                raise ValidationError(f"Критическая ошибка при списании цветка '{flower_instance.name}'. Транзакция будет отменена.")
        print(f"Цветы для заказа #{self.id} успешно списаны.")


    def _deduct_ribbons(self):
        required_ribbons = defaultdict(float) 
        for item in self.items.all():
            bouquet = item.bouquet
            order_item_quantity = item.quantity
            for bouquet_ribbon_item in bouquet.ribbon_items.all(): 
                required_ribbons[bouquet_ribbon_item.ribbon_id] += bouquet_ribbon_item.length * order_item_quantity
        
        if not required_ribbons:
            return

        for ribbon_id, total_length_to_deduct in required_ribbons.items():
            try:
                ribbon_instance = Ribbon.objects.get(id=ribbon_id)
            except Ribbon.DoesNotExist:
                raise ValidationError(f"Лента с ID {ribbon_id} не найдена в каталоге.")

            available_stock_lots = StockRibbon.objects.filter(
                ribbon_id=ribbon_id,
                status='available',
                length__gt=0 
            ).order_by('delivery_date') 

            current_total_available = sum(lot.length for lot in available_stock_lots)
            if current_total_available < total_length_to_deduct:
                raise ValidationError(
                    f"Недостаточно ленты '{ribbon_instance.name}' на складе. "
                    f"Требуется: {total_length_to_deduct:.2f}м, доступно: {current_total_available:.2f}м."
                )

            length_left_to_deduct = total_length_to_deduct
            for stock_lot in available_stock_lots:
                if length_left_to_deduct <= 0:
                    break
                
                deduct_from_this_lot = min(float(stock_lot.length), length_left_to_deduct)
                
                stock_lot.length -= deduct_from_this_lot
                length_left_to_deduct -= deduct_from_this_lot
                
                if stock_lot.length <= 0.001: 
                    stock_lot.length = 0
                    stock_lot.status = 'out_of_stock'
                stock_lot.save()
            
            if length_left_to_deduct > 0.001: 
                raise ValidationError(f"Критическая ошибка при списании ленты '{ribbon_instance.name}'. Транзакция будет отменена.")
        print(f"Ленты для заказа #{self.id} успешно списаны.")

    def _deduct_wrappers(self):
        required_wrappers = defaultdict(float) 
        for item in self.items.all():
            bouquet = item.bouquet
            order_item_quantity = item.quantity
            for bouquet_wrapper_item in bouquet.wrapper_items.all(): # related_name="wrapper_items"
                required_wrappers[bouquet_wrapper_item.wrapper_id] += bouquet_wrapper_item.length * order_item_quantity

        if not required_wrappers:
            return

        for wrapper_id, total_length_to_deduct in required_wrappers.items():
            try:
                wrapper_instance = Wrapper.objects.get(id=wrapper_id)
            except Wrapper.DoesNotExist:
                raise ValidationError(f"Упаковка с ID {wrapper_id} не найдена в каталоге.")

            available_stock_lots = StockWrapper.objects.filter(
                wrapper_id=wrapper_id,
                status='available',
                length__gt=0
            ).order_by('delivery_date') 

            current_total_available = sum(lot.length for lot in available_stock_lots)
            if current_total_available < total_length_to_deduct:
                raise ValidationError(
                    f"Недостаточно упаковки '{wrapper_instance.name}' на складе. "
                    f"Требуется: {total_length_to_deduct:.2f}м, доступно: {current_total_available:.2f}м."
                )

            length_left_to_deduct = total_length_to_deduct
            for stock_lot in available_stock_lots:
                if length_left_to_deduct <= 0:
                    break
                
                deduct_from_this_lot = min(float(stock_lot.length), length_left_to_deduct)
                
                stock_lot.length -= deduct_from_this_lot
                length_left_to_deduct -= deduct_from_this_lot
                
                if stock_lot.length <= 0.001:
                    stock_lot.length = 0
                    stock_lot.status = 'out_of_stock'
                stock_lot.save()

            if length_left_to_deduct > 0.001: 
                raise ValidationError(f"Критическая ошибка при списании упаковки '{wrapper_instance.name}'. Транзакция будет отменена.")
        print(f"Упаковка для заказа #{self.id} успешно списана.")

    def deduct_all_stock_components(self):
        with transaction.atomic():
            self._deduct_flowers()
            self._deduct_ribbons()
            self._deduct_wrappers()
        
        print(f"Все компоненты для заказа #{self.id} успешно списаны со склада.")

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE,
                          related_name='items', verbose_name="Order")
    bouquet = models.ForeignKey(Bouquet, on_delete=models.PROTECT,
                            related_name='order_items', verbose_name="Bouquet")
    quantity = models.PositiveIntegerField("Quantity")
    price_per_item = models.DecimalField("Price per item", max_digits=10, decimal_places=2)

    def get_total(self):
        return self.quantity * self.price_per_item

    def __str__(self):
        return f"{self.quantity} x {self.bouquet.name} in Order #{self.order.id}"

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        unique_together = ('order', 'bouquet')

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Card Online'),
        ('cash', 'Cash on Delivery'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE,
                             related_name='payment', verbose_name="Order")
    amount = models.DecimalField("Amount", max_digits=10, decimal_places=2)
    status = models.CharField("Payment Status", max_length=30, 
                          choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField("Payment Method", max_length=30,
                                  choices=PAYMENT_METHOD_CHOICES)
    paid_at = models.DateTimeField("Paid at", null=True, blank=True)
    
    def __str__(self):
        return f"Payment for Order #{self.order.id}"

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

class Cart(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('ordered', 'Converted to Order'),
        ('canceled', 'Canceled'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                         related_name='carts', verbose_name="User")
    status = models.CharField("Status", max_length=30, 
                          choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField("Created at", auto_now_add=True)
    
    def __str__(self):
        return f"Cart of {self.user}"

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE,
                         related_name='items', verbose_name="Cart")
    bouquet = models.ForeignKey(Bouquet, on_delete=models.CASCADE,
                            related_name='cart_items', verbose_name="Bouquet")
    quantity = models.PositiveIntegerField("Quantity")
    
    def __str__(self):
        return f"{self.bouquet} x{self.quantity} in cart"

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"