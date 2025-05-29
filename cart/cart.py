# cart/cart.py
from decimal import Decimal
from django.conf import settings
from catalog.models import Bouquet

class Cart:
    def __init__(self, request):
        """
        Инициализация корзины.
        """
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # Сохраняем пустую корзину в сессии
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, bouquet, quantity=1, update_quantity=False):
        """
        Добавить букет в корзину или обновить его количество.
        """
        bouquet_id = str(bouquet.id)
        if bouquet_id not in self.cart:
            self.cart[bouquet_id] = {'quantity': 0, 'price': str(bouquet.price)}

        if update_quantity:
            self.cart[bouquet_id]['quantity'] = quantity
        else:
            self.cart[bouquet_id]['quantity'] += quantity

        # Не допускаем отрицательное или нулевое количество
        if self.cart[bouquet_id]['quantity'] <= 0:
             self.remove(bouquet)
        else:
            self.save()


    def save(self):
        # Помечаем сессию как "измененную", чтобы убедиться, что она сохранится
        self.session.modified = True

    def remove(self, bouquet):
        """
        Удалить букет из корзины.
        """
        bouquet_id = str(bouquet.id)
        if bouquet_id in self.cart:
            del self.cart[bouquet_id]
            self.save()

    def __iter__(self):
        """
        Перебираем товары в корзине и получаем букеты из базы данных.
        """
        bouquet_ids = self.cart.keys()
        # Получаем объекты букетов и добавляем их в корзину
        bouquets = Bouquet.objects.filter(id__in=bouquet_ids, is_active=True)

        cart = self.cart.copy()
        for bouquet in bouquets:
            cart[str(bouquet.id)]['bouquet'] = bouquet

        for item in cart.values():
            # Проверяем, что объект букета был найден (он может быть неактивным)
            if 'bouquet' in item:
                item['price'] = Decimal(item['price'])
                item['total_price'] = item['price'] * item['quantity']
                yield item
            else:
                 # Если букета нет (удален/неактивен), удаляем его из сессии на лету
                 # Это не самый лучший способ, но для примера пойдет
                 bouquet_id_to_remove = None
                 for b_id, b_data in self.cart.items():
                     if 'bouquet' not in b_data: # Ищем элемент без объекта букета
                         bouquet_id_to_remove = b_id
                         break
                 if bouquet_id_to_remove:
                     del self.cart[bouquet_id_to_remove]
                     self.save()


    def __len__(self):
        """
        Считаем общее количество товаров в корзине.
        """
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        """
        Считаем общую стоимость товаров в корзине.
        """
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        # Удаляем корзину из сессии
        del self.session[settings.CART_SESSION_ID]
        self.save()