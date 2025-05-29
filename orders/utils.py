# Убедитесь, что импортированы:
from django.db.models import Sum, F, ExpressionWrapper, fields, Q
from django.db import transaction # Для атомарных операций
from django.core.exceptions import ValidationError # Для ошибок

# (Ваши модели User, Order, OrderItem, Bouquet, BouquetFlower, Flower, StockFlower и т.д.)

def get_total_required_flowers_for_order(order_instance):
    """
    Возвращает QuerySet объектов Flower, аннотированных полем 'total_quantity_needed',
    указывающим, сколько единиц каждого цветка требуется для всего заказа.
    """
    
    # Мы хотим сгруппировать по Flower и посчитать, сколько каждого нужно.
    # Путь: Order -> OrderItem -> Bouquet -> BouquetFlower -> Flower
    # Нам нужно: SUM(OrderItem.quantity * BouquetFlower.quantity) для каждого Flower
    
    flowers_in_order = Flower.objects.filter(
        # Фильтруем цветы, которые есть в букетах, которые есть в позициях этого заказа
        bouquet_items__bouquet__order_items__order=order_instance 
    ).annotate(
        # Аннотируем общее количество этого цветка, необходимое для заказа.
        # F('bouquet_items__quantity') - кол-во этого цветка в ОДНОМ букете
        # F('bouquet_items__bouquet__order_items__quantity') - кол-во таких букетов в ЗАКАЗЕ
        
        # Это выражение вычисляет (BouquetFlower.quantity * OrderItem.quantity)
        # для каждого "пути" от цветка к позиции заказа
        quantity_per_order_item_path=ExpressionWrapper(
            F('bouquet_items__quantity') * F('bouquet_items__bouquet__order_items__quantity'),
            output_field=fields.IntegerField()
        ),
        # Суммируем эти произведения для каждого цветка.
        # Фильтр Q важен, чтобы гарантировать, что мы суммируем order_items
        # только для ТЕКУЩЕГО заказа, если цветок/букет используется в нескольких заказах.
        total_quantity_needed=Sum(
            'quantity_per_order_item_path',
            filter=Q(bouquet_items__bouquet__order_items__order=order_instance)
        )
    ).filter(
        total_quantity_needed__gt=0 # Убедимся, что берем только те, что нужны
    ).distinct() # Убрать дубликаты цветов, если они возникли из-за JOIN'ов
    
    return flowers_in_order

@transaction.atomic # Гарантирует, что все списания либо пройдут успешно, либо откатятся
def deduct_flowers_from_stock(order_instance):
    """
    Списывает необходимое количество цветов со склада для указанного заказа.
    Использует FIFO-стратегию (списывает из самых старых доступных партий).
    Выбрасывает ValidationError, если цветов недостаточно.
    """
    required_flowers_summary = get_total_required_flowers_for_order(order_instance)
    
    if not required_flowers_summary.exists():
        # print(f"Для заказа #{order_instance.id} не требуется цветов (возможно, пустой или уже обработан).")
        return # Ничего не делать, если цветов не требуется

    for flower_data in required_flowers_summary:
        flower_to_deduct = flower_data # Это объект Flower
        needed_quantity = flower_data.total_quantity_needed # Из аннотации

        # print(f"Для цветка '{flower_to_deduct.name}' (ID: {flower_to_deduct.id}) требуется {needed_quantity} шт.")

        # Получаем доступные партии этого цветка, отсортированные по дате поставки (FIFO)
        # и затем по ID для стабильной сортировки, если даты одинаковы.
        available_stock_items = StockFlower.objects.filter(
            flower=flower_to_deduct,
            status='available',
            quantity__gt=0
        ).order_by('delivery_date', 'id')

        deducted_count = 0
        for stock_item in available_stock_items:
            if deducted_count >= needed_quantity:
                break # Уже списали достаточно этого цветка

            quantity_to_take_from_batch = min(
                stock_item.quantity, 
                needed_quantity - deducted_count
            )
            
            stock_item.quantity -= quantity_to_take_from_batch
            deducted_count += quantity_to_take_from_batch
            
            # print(f"  Списано {quantity_to_take_from_batch} шт. из партии StockFlower ID {stock_item.id}. "
            #       f"Остаток в партии: {stock_item.quantity}.")

            if stock_item.quantity == 0:
                stock_item.status = 'is_used' # или 'out_of_stock'
                # print(f"  Партия StockFlower ID {stock_item.id} полностью использована, статус изменен на '{stock_item.status}'.")
            
            stock_item.save()

        if deducted_count < needed_quantity:
            # Недостаточно цветов на складе!
            error_message = (
                f"Недостаточно цветка '{flower_to_deduct.name}' на складе для заказа #{order_instance.id}. "
                f"Требовалось: {needed_quantity}, доступно и списано: {deducted_count}."
            )
            # print(f"ОШИБКА: {error_message}")
            raise ValidationError(error_message) # Это откатит транзакцию
            
    # print(f"Все необходимые цветы для заказа #{order_instance.id} успешно списаны со склада.")