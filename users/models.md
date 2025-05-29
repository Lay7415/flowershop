from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('client', 'Клиент'),
        ('florist', 'Флорист'),
        ('courier', 'Курьер'),
        # Администратор определяется через is_staff=True или is_superuser=True
    )
    # Поле email делаем уникальным и обязательным для удобства
    email = models.EmailField('Email', unique=True)
    role = models.CharField(
        "Роль",
        max_length=10,
        choices=ROLE_CHOICES,
        default='client'
    )
    phone = models.CharField(
        "Телефон",
        max_length=20,
        blank=True,
        null=True
    )

    # Указываем email как поле для логина вместо username
    USERNAME_FIELD = 'email'
    # Указываем поля, которые требуются при создании через createsuperuser
    REQUIRED_FIELDS = ['username'] # username все еще нужен для совместимости

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.email

    @property
    def is_client(self):
        return self.role == 'client'

    @property
    def is_florist(self):
        return self.role == 'florist'

    @property
    def is_courier(self):
        return self.role == 'courier'

    # Добавьте другие свойства или методы при необходимости

from django.db import models
from django.conf import settings
from django.utils import timezone
from catalog.models import Bouquet

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

    def get_available_stock(self):
        return self.stock_items.filter(status='available').aggregate(
            total=models.Sum('quantity')
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

    def get_available_stock(self):
        return self.stock_items.filter(status='available').aggregate(
            total=models.Sum('length')
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

    def get_available_stock(self):
        return self.stock_items.filter(status='available').aggregate(
            total=models.Sum('length')
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
        ('is_used', 'Used'),
        ('reserved', 'Reserved'),
        ('damaged', 'Damaged'),
        ('expired', 'Expired'),
    ]
    
    flower = models.ForeignKey(Flower, on_delete=models.CASCADE, 
                             related_name="stock_items")
    delivery_date = models.DateField("Delivery Date")
    quantity = models.PositiveIntegerField("Quantity")
    number = models.CharField("Batch Number", max_length=50)
    status = models.CharField("Stock Item Status", max_length=30, 
                           choices=STATUS_CHOICES, default='available')

    def __str__(self):
        return f"{self.flower} in stock ({self.quantity} pcs.)"

    class Meta:
        verbose_name = "Stock Flower"
        verbose_name_plural = "Stock Flowers"

class StockRibbon(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('out_of_stock', 'Out of Stock'),
    ]
    
    ribbon = models.ForeignKey(Ribbon, on_delete=models.CASCADE, 
                            related_name="stock_items")
    delivery_date = models.DateField("Delivery Date")
    length = models.PositiveIntegerField("Length")
    status = models.CharField("Stock Item Status", max_length=30, 
                           choices=STATUS_CHOICES, default='available')

    def __str__(self):
        return f"{self.ribbon} in stock ({self.length} m)"

    class Meta:
        verbose_name = "Stock Ribbon"
        verbose_name_plural = "Stock Ribbons"

class StockWrapper(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('out_of_stock', 'Out of Stock'),
    ]
    
    wrapper = models.ForeignKey(Wrapper, on_delete=models.CASCADE, 
                              related_name="stock_items")
    delivery_date = models.DateField("Delivery Date")
    length = models.PositiveIntegerField("Length")
    status = models.CharField("Stock Item Status", max_length=30, 
                           choices=STATUS_CHOICES, default='available')

    def __str__(self):
        return f"{self.wrapper} in stock ({self.length} m)"

    class Meta:
        verbose_name = "Stock Wrapper"
        verbose_name_plural = "Stock Wrappers"