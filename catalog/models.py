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
    
    flowers = models.ManyToManyField('Flower', through='BouquetFlower', related_name='bouquets')
    ribbons = models.ManyToManyField('Ribbon', through='BouquetRibbon', related_name='bouquets')
    wrappers = models.ManyToManyField('Wrapper', through='BouquetWrapper', related_name='bouquets')

    class Meta:
        verbose_name = "Bouquet"
        verbose_name_plural = "Bouquets"
        app_label = 'catalog'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:bouquet_detail', args=[str(self.id)])

    @property
    def flower_items(self):
        return self.bouquetflower_set.all()

    @property
    def ribbon_items(self):
        return self.bouquetribbon_set.all()

    @property
    def wrapper_items(self):
        return self.bouquetwrapper_set.all()

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