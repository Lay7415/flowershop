import random
from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from faker import Faker

from orders.models import Order, OrderItem, Payment, CourierLocation, UserStatus, WorkRecord, Cart, CartItem
from catalog.models import (
    Bouquet, Flower, Ribbon, Wrapper,
    StockFlower, StockRibbon, StockWrapper,
    BouquetFlower, BouquetRibbon, BouquetWrapper
)

User = get_user_model()
fake = Faker('ru_RU')

class Command(BaseCommand):
    help = 'Seeds the database with initial data for flower shop (excluding orders)'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Deleting old data...")
        OrderItem.objects.all().delete()
        Payment.objects.all().delete()
        if BouquetFlower.objects.exists(): BouquetFlower.objects.all().delete()
        if BouquetRibbon.objects.exists(): BouquetRibbon.objects.all().delete()
        if BouquetWrapper.objects.exists(): BouquetWrapper.objects.all().delete()
        if CartItem.objects.exists(): CartItem.objects.all().delete()
        Order.objects.all().delete()
        Cart.objects.all().delete()
        if StockFlower.objects.exists(): StockFlower.objects.all().delete()
        if StockRibbon.objects.exists(): StockRibbon.objects.all().delete()
        if StockWrapper.objects.exists(): StockWrapper.objects.all().delete()
        if Bouquet.objects.exists(): Bouquet.objects.all().delete()
        if Flower.objects.exists(): Flower.objects.all().delete()
        if Ribbon.objects.exists(): Ribbon.objects.all().delete()
        if Wrapper.objects.exists(): Wrapper.objects.all().delete()
        if CourierLocation.objects.exists(): CourierLocation.objects.all().delete()
        if WorkRecord.objects.exists(): WorkRecord.objects.all().delete()
        if UserStatus.objects.exists(): UserStatus.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()
        self.stdout.write("Old data deleted.")

        self.stdout.write("Creating users...")
        try:
            admin_user = User.objects.get(username="admin", is_superuser=True)
        except User.DoesNotExist:
            admin_user = User.objects.create_superuser("admin", "admin@example.com", "adminpass")
            admin_user.first_name = "Admin"
            admin_user.last_name = "User"
            admin_user.phone = fake.phone_number()
            admin_user.save()

        clients = []
        for i in range(5):
            email = f"client{i}@example.com"
            username = f"client_user_{i}{random.randint(100,999)}"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'role': 'client',
                    'phone': fake.phone_number()
                }
            )
            if created:
                user.set_password("clientpass")
                user.save()
            clients.append(user)

        florists = []
        for i in range(2):
            email = f"florist{i}@example.com"
            username = f"florist_user_{i}{random.randint(100,999)}"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'role': 'florist',
                    'phone': fake.phone_number()
                }
            )
            if created:
                user.set_password("floristpass")
                user.save()
            florists.append(user)
            UserStatus.objects.get_or_create(user=user, defaults={'status': random.choice([s[0] for s in UserStatus.STATUS_CHOICES])})
            for _ in range(random.randint(1, 3)):
                start_time = timezone.now() - timedelta(days=random.randint(1, 30), hours=random.randint(0,12))
                end_time = start_time + timedelta(hours=random.randint(4, 8))
                WorkRecord.objects.create(user=user, start_time=start_time, end_time=end_time)

        couriers = []
        for i in range(3):
            email = f"courier{i}@example.com"
            username = f"courier_user_{i}{random.randint(100,999)}"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'role': 'courier',
                    'phone': fake.phone_number()
                }
            )
            if created:
                user.set_password("courierpass")
                user.save()
            couriers.append(user)
            UserStatus.objects.get_or_create(user=user, defaults={'status': random.choice([s[0] for s in UserStatus.STATUS_CHOICES])})
            CourierLocation.objects.get_or_create(
                user=user,
                defaults={ 'longitude': fake.longitude(), 'latitude': fake.latitude()}
            )
            for _ in range(random.randint(1, 3)):
                start_time = timezone.now() - timedelta(days=random.randint(1, 30), hours=random.randint(0,12))
                end_time = start_time + timedelta(hours=random.randint(4, 8))
                WorkRecord.objects.create(user=user, start_time=start_time, end_time=end_time)
        self.stdout.write(f"Created/Ensured Users.")

        self.stdout.write("Creating catalog items...")
        created_flowers, created_ribbons, created_wrappers, created_bouquets = [], [], [], []
        flowers_data = [
            {"name": "Красная Роза", "price": Decimal("150.00"), "description": "Классическая красная роза.", "photo": None},
            {"name": "Белая Лилия", "price": Decimal("180.00"), "description": "Элегантная белая лилия.", "photo": None},
        ]
        for data in flowers_data:
            flower, _ = Flower.objects.get_or_create(name=data['name'], defaults=data)
            created_flowers.append(flower)
            StockFlower.objects.create(flower=flower, delivery_date=timezone.now().date() - timedelta(days=random.randint(1, 10)), quantity=random.randint(50, 200), number=f"BATCH-F{random.randint(1000,9999)}", status='available')

        ribbons_data = [{"name": "Красная атласная лента", "price": Decimal("50.00"), "description": "Для ярких акцентов.", "photo": None}]
        for data in ribbons_data:
            ribbon, _ = Ribbon.objects.get_or_create(name=data['name'], defaults=data)
            created_ribbons.append(ribbon)
            StockRibbon.objects.create(ribbon=ribbon, delivery_date=timezone.now().date() - timedelta(days=random.randint(1,10)), length=random.randint(50, 100), status='available')

        wrappers_data = [{"name": "Прозрачная пленка", "price": Decimal("30.00"), "description": "Стандартная упаковка.", "photo": None}]
        for data in wrappers_data:
            wrapper, _ = Wrapper.objects.get_or_create(name=data['name'], defaults=data)
            created_wrappers.append(wrapper)
            StockWrapper.objects.create(wrapper=wrapper, delivery_date=timezone.now().date() - timedelta(days=random.randint(1,10)), length=random.randint(30, 80), status='available')

        if created_flowers and created_ribbons and created_wrappers:
            bouquet_data_list = [
                {"name": "Романтический сюрприз", "price": Decimal("2500.00"), "description": "Букет из красных роз и лилий.", "tag": "любовь", "is_active": True, "photo": None},
                {"name": "Весеннее настроение", "price": Decimal("1800.00"), "description": "Яркие тюльпаны.", "tag": "весна", "is_active": True, "photo": None},
            ]
            for data in bouquet_data_list:
                bouquet, _ = Bouquet.objects.get_or_create(name=data['name'], defaults=data)
                created_bouquets.append(bouquet)
                try:
                    flower1 = random.choice(created_flowers)
                    BouquetFlower.objects.create(bouquet=bouquet, flower=flower1, quantity=random.randint(3,7))
                    if len(created_flowers) > 1:
                        available_flowers_for_second = [f for f in created_flowers if f != flower1]
                        if available_flowers_for_second:
                            flower2 = random.choice(available_flowers_for_second)
                            BouquetFlower.objects.create(bouquet=bouquet, flower=flower2, quantity=random.randint(2,5))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Could not add flower to {bouquet.name}: {e}"))
                BouquetRibbon.objects.create(bouquet=bouquet, ribbon=random.choice(created_ribbons), length=round(random.uniform(0.5, 1.5),1))
                BouquetWrapper.objects.create(bouquet=bouquet, wrapper=random.choice(created_wrappers), length=round(random.uniform(0.3, 1.0),1))
        self.stdout.write("Catalog items and bouquets created.")

        if not created_bouquets or not clients:
            self.stdout.write(self.style.WARNING("No bouquets or clients to create Carts."))
        else:
            self.stdout.write("Creating carts...")
            for client_user in clients:
                # Create active carts
                if random.choice([True, False]):
                    cart, _ = Cart.objects.get_or_create(user=client_user, status='active', defaults={'created_at': timezone.now()})
                    num_items_in_cart = random.randint(1, min(2, len(created_bouquets)))
                    bouquets_for_cart = random.sample(created_bouquets, num_items_in_cart)
                    for bouquet_to_add in bouquets_for_cart:
                        CartItem.objects.get_or_create(cart=cart, bouquet=bouquet_to_add, defaults={'quantity': random.randint(1, 2)})

                # --- START OF REMOVED ORDER CREATION BLOCK ---
                # for _ in range(random.randint(0, 1)): # This loop created Orders and 'ordered' Carts
                #     temp_cart_user = client_user
                #     temp_cart = Cart.objects.create(
                #         user=temp_cart_user,
                #         status='ordered',
                #         created_at=timezone.now() - timedelta(days=random.randint(1,60))
                #     )
                #     order_items_data = []
                #     order_total_cost = Decimal("0.0")
                #     num_items_in_order = random.randint(1, min(2, len(created_bouquets)))
                #     bouquets_for_order = random.sample(created_bouquets, num_items_in_order)

                #     for bouquet_instance in bouquets_for_order:
                #         quantity = random.randint(1, 2)
                #         price = bouquet_instance.price
                #         order_items_data.append({'bouquet': bouquet_instance, 'quantity': quantity, 'price_per_item': price})
                #         order_total_cost += price * quantity
                #         CartItem.objects.create(cart=temp_cart, bouquet=bouquet_instance, quantity=quantity)

                #     delivery_cost = Decimal(random.randrange(300, 701, 50))
                #     order_total_cost += delivery_cost
                #     order_florist = random.choice(florists) if florists else None
                #     order_courier = random.choice(couriers) if couriers else None
                #     order_status = random.choice([s[0] for s in Order.STATUS_CHOICES if s[0] not in ['new']])
                #     order_created_at = timezone.now() - timedelta(days=random.randint(1, 60))
                #     delivery_datetime = order_created_at + timedelta(days=random.randint(0,2), hours=random.randint(2,10))
                #     if delivery_datetime < order_created_at:
                #         delivery_datetime = order_created_at + timedelta(hours=random.randint(2,5))

                #     order, order_created_flag = Order.objects.get_or_create(
                #         customer=client_user,
                #         delivery_datetime=delivery_datetime,
                #         defaults={
                #             'status': order_status,
                #             'created_at': order_created_at,
                #             'updated_at': order_created_at + timedelta(minutes=random.randint(5,60)),
                #             'florist': order_florist,
                #             'courier': order_courier,
                #             'total_cost': order_total_cost,
                #             'delivery_cost': delivery_cost,
                #             'delivery_distance': random.uniform(1000, 15000),
                #             'delivery_address_name': fake.address(),
                #             'delivery_lat': fake.latitude(),
                #             'delivery_lon': fake.longitude(),
                #             'recipient_name': f"{fake.first_name()} {fake.last_name()}",
                #             'recipient_phone': fake.phone_number(),
                #             'cart': temp_cart
                #         }
                #     )
                #     if not order_created_flag:
                #         order.status = order_status
                #         order.florist = order_florist
                #         order.courier = order_courier
                #         order.total_cost = order_total_cost
                #         order.save()

                #     if order_courier and order_status in ['delivering', 'delivered', 'completed']:
                #         order.courier_lat = fake.latitude()
                #         order.courier_lon = fake.longitude()
                #         order.courier_last_update = delivery_datetime - timedelta(minutes=random.randint(5,30))
                #         order.save()

                #     for item_data in order_items_data:
                #         OrderItem.objects.get_or_create(
                #             order=order,
                #             bouquet=item_data['bouquet'],
                #             defaults={'quantity': item_data['quantity'], 'price_per_item': item_data['price_per_item']}
                #         )
                #     payment_status = 'success'
                #     if order_status == 'new': payment_status = 'pending'
                #     elif order_status == 'paid': payment_status = 'success'
                #     elif order_status == 'canceled': payment_status = 'refunded' if random.choice([True, False]) else 'failed'
                #     Payment.objects.get_or_create(
                #         order=order,
                #         defaults={
                #             'amount': order.total_cost,
                #             'status': payment_status,
                #             'payment_method': random.choice([p[0] for p in Payment.PAYMENT_METHOD_CHOICES]),
                #             'paid_at': (order_created_at + timedelta(minutes=random.randint(5,20))) if payment_status == 'success' else None
                #         }
                #     )
                # --- END OF REMOVED ORDER CREATION BLOCK ---

            self.stdout.write("Carts created.")
        self.stdout.write(self.style.SUCCESS("Database seeding complete (Orders not created)."))