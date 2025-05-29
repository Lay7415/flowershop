# orders/stock_utils.py (or a similar appropriate location)

from django.db import transaction
from django.core.exceptions import ValidationError
from catalog.models import StockFlower, StockRibbon, StockWrapper, Flower, Ribbon, Wrapper
from collections import defaultdict

def check_stock_availability_for_order(order):
    """
    Checks if there is enough stock for all items in the order.
    Returns a list of error messages if stock is insufficient, otherwise an empty list.
    """
    required_flowers = defaultdict(int)
    required_ribbons = defaultdict(float)
    required_wrappers = defaultdict(float)
    errors = []

    for item in order.items.all():
        bouquet = item.bouquet
        order_item_quantity = item.quantity # How many of this bouquet type

        for bf_item in bouquet.flower_items.all():
            required_flowers[bf_item.flower_id] += bf_item.quantity * order_item_quantity
        
        for br_item in bouquet.ribbon_items.all():
            required_ribbons[br_item.ribbon_id] += br_item.length * order_item_quantity

        for bw_item in bouquet.wrapper_items.all():
            required_wrappers[bw_item.wrapper_id] += bw_item.length * order_item_quantity

    for flower_id, needed_qty in required_flowers.items():
        flower = Flower.objects.get(id=flower_id)
        available_qty = flower.get_available_stock_quantity()
        if available_qty < needed_qty:
            errors.append(f"Недостаточно цветов '{flower.name}'. Требуется: {needed_qty}, Доступно: {available_qty}")

    for ribbon_id, needed_len in required_ribbons.items():
        ribbon = Ribbon.objects.get(id=ribbon_id)
        available_len = ribbon.get_available_stock_length()
        if available_len < needed_len:
            errors.append(f"Недостаточно ленты '{ribbon.name}'. Требуется: {needed_len}м, Доступно: {available_len}м")

    for wrapper_id, needed_len in required_wrappers.items():
        wrapper = Wrapper.objects.get(id=wrapper_id)
        available_len = wrapper.get_available_stock_length()
        if available_len < needed_len:
            errors.append(f"Недостаточно обертки '{wrapper.name}'. Требуется: {needed_len}м, Доступно: {available_len}м")
            
    return errors


def deduct_stock_for_order(order):
    """
    Deducts stock for all items in the given order.
    This function should be called within a transaction.
    Raises ValidationError if stock cannot be deducted (e.g. depleted between check and deduction).
    """
    for item in order.items.all(): # OrderItem
        bouquet = item.bouquet
        order_item_quantity = item.quantity # How many of this bouquet type in the order

        # 1. Deduct Flowers
        for bf_item in bouquet.flower_items.all(): # BouquetFlower
            flower_to_deduct = bf_item.flower
            quantity_needed_for_bouquet_type = bf_item.quantity
            total_quantity_to_deduct = quantity_needed_for_bouquet_type * order_item_quantity
            
            available_stock_batches = StockFlower.objects.filter(
                flower=flower_to_deduct, 
                status='available',
                quantity__gt=0 # Only batches that actually have quantity
            ).order_by('delivery_date', 'id') # Oldest first

            for stock_batch in available_stock_batches:
                if total_quantity_to_deduct <= 0:
                    break
                
                can_take_from_batch = min(stock_batch.quantity, total_quantity_to_deduct)
                stock_batch.quantity -= can_take_from_batch
                total_quantity_to_deduct -= can_take_from_batch
                
                if stock_batch.quantity == 0:
                    stock_batch.status = 'used'
                stock_batch.save()
            
            if total_quantity_to_deduct > 0:
                # This should ideally not happen if pre-check was done,
                # but could happen due to race conditions if not handled with select_for_update.
                raise ValidationError(f"Неожиданная нехватка цветов '{flower_to_deduct.name}' во время списания.")

        # 2. Deduct Ribbons
        for br_item in bouquet.ribbon_items.all(): # BouquetRibbon
            ribbon_to_deduct = br_item.ribbon
            length_needed_for_bouquet_type = br_item.length
            total_length_to_deduct = length_needed_for_bouquet_type * order_item_quantity

            available_stock_batches = StockRibbon.objects.filter(
                ribbon=ribbon_to_deduct,
                status='available',
                length__gt=0
            ).order_by('delivery_date', 'id')

            for stock_batch in available_stock_batches:
                if total_length_to_deduct <= 0:
                    break
                
                can_take_from_batch = min(stock_batch.length, total_length_to_deduct)
                stock_batch.length -= can_take_from_batch
                total_length_to_deduct -= can_take_from_batch
                
                if stock_batch.length == 0: # Or very close to 0 for floats
                    stock_batch.status = 'out_of_stock'
                stock_batch.save()

            if total_length_to_deduct > 0.001: # Tolerance for float comparison
                raise ValidationError(f"Неожиданная нехватка ленты '{ribbon_to_deduct.name}' во время списания.")
        
        # 3. Deduct Wrappers
        for bw_item in bouquet.wrapper_items.all(): # BouquetWrapper
            wrapper_to_deduct = bw_item.wrapper
            length_needed_for_bouquet_type = bw_item.length
            total_length_to_deduct = length_needed_for_bouquet_type * order_item_quantity
            
            available_stock_batches = StockWrapper.objects.filter(
                wrapper=wrapper_to_deduct,
                status='available',
                length__gt=0
            ).order_by('delivery_date', 'id')

            for stock_batch in available_stock_batches:
                if total_length_to_deduct <= 0:
                    break
                
                can_take_from_batch = min(stock_batch.length, total_length_to_deduct)
                stock_batch.length -= can_take_from_batch
                total_length_to_deduct -= can_take_from_batch
                
                if stock_batch.length == 0: # Or very close to 0 for floats
                    stock_batch.status = 'out_of_stock'
                stock_batch.save()
            
            if total_length_to_deduct > 0.001: # Tolerance for float comparison
                raise ValidationError(f"Неожиданная нехватка обертки '{wrapper_to_deduct.name}' во время списания.")