import random
import json
import os
from decimal import Decimal
from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from orders.models import Order, OrderItem, Payment, CourierLocation, UserStatus, WorkRecord, Cart, CartItem
from catalog.models import (
    Bouquet, Flower, Ribbon, Wrapper,
    StockFlower, StockRibbon, StockWrapper,
    BouquetFlower, BouquetRibbon, BouquetWrapper
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with initial data for flower shop'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Загружаем данные из JSON файла
        json_path = Path(__file__).parent / 'seed_data.json'
        with open(json_path, 'r', encoding='utf-8') as f:
            self.seed_data = json.load(f)

    @property
    def FLOWERS_DATA(self):
        return self.seed_data['flowers']

    @property
    def RIBBONS_DATA(self):
        return self.seed_data['ribbons']

    @property
    def WRAPPERS_DATA(self):
        return self.seed_data['wrappers']

    @property
    def BOUQUETS_DATA(self):
        return self.seed_data['bouquets']

    @property
    def CLIENTS_DATA(self):
        return self.seed_data['clients']

    @property
    def FLORISTS_DATA(self):
        return self.seed_data['florists']

    @property
    def COURIERS_DATA(self):
        return self.seed_data['couriers']

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
        # Создаем пользователей из предопределенных данных
        clients = self.create_clients()
        florists = self.create_florists()
        couriers = self.create_couriers()
        self.stdout.write(f"Created/Ensured Users.")

        # Создаем базовые компоненты
        created_flowers = self.create_flowers()
        created_ribbons = self.create_ribbons()
        created_wrappers = self.create_wrappers()

        # Создаем справочники для быстрого поиска по имени
        flowers_dict = {flower.name: flower for flower in created_flowers}
        ribbons_dict = {ribbon.name: ribbon for ribbon in created_ribbons}
        wrappers_dict = {wrapper.name: wrapper for wrapper in created_wrappers}

        # Создаем букеты
        created_bouquets = self.create_bouquets(flowers_dict, ribbons_dict, wrappers_dict)
        self.stdout.write("Catalog items and bouquets created.")

        if not created_bouquets or not clients:
            self.stdout.write(self.style.WARNING("No bouquets or clients to create Carts."))
        else:
            self.stdout.write("Creating carts...")
            for client_user in clients:
                if random.choice([True, False]):
                    cart, _ = Cart.objects.get_or_create(user=client_user, status='active', defaults={'created_at': timezone.now()})
                    num_items_in_cart = random.randint(1, min(2, len(created_bouquets)))
                    bouquets_for_cart = random.sample(created_bouquets, num_items_in_cart)
                    for bouquet_to_add in bouquets_for_cart:
                        CartItem.objects.get_or_create(cart=cart, bouquet=bouquet_to_add, defaults={'quantity': random.randint(1, 2)})

            self.stdout.write("Carts created.")
        self.stdout.write(self.style.SUCCESS("Database seeding complete."))

    def create_flowers(self):
        """Create flowers from predefined data"""
        created_flowers = []
        self.stdout.write("Creating flowers...")
        for flower_data in self.FLOWERS_DATA:
            flower, created = Flower.objects.get_or_create(
                name=flower_data['name'],
                defaults={
                    'price': Decimal(flower_data['price']),
                    'description': flower_data['description'],
                    'photo': flower_data['photo'],
                }
            )
            created_flowers.append(flower)
            # Создаем запись о наличии на складе
            StockFlower.objects.create(
                flower=flower,
                delivery_date=timezone.now().date() - timedelta(days=random.randint(1, 10)),
                quantity=random.randint(50, 200),
                number=f"BATCH-F{random.randint(1000,9999)}",
                status='available'
            )
        return created_flowers

    def create_ribbons(self):
        """Create ribbons from predefined data"""
        created_ribbons = []
        self.stdout.write("Creating ribbons...")
        for ribbon_data in self.RIBBONS_DATA:
            ribbon, created = Ribbon.objects.get_or_create(
                name=ribbon_data['name'],
                defaults={
                    'price': Decimal(ribbon_data['price']),
                    'description': ribbon_data['description'],
                    'photo': ribbon_data['photo'],
                }
            )
            created_ribbons.append(ribbon)
            # Создаем запись о наличии на складе
            StockRibbon.objects.create(
                ribbon=ribbon,
                delivery_date=timezone.now().date() - timedelta(days=random.randint(1, 10)),
                length=random.randint(50, 100),
                status='available'
            )
        return created_ribbons

    def create_wrappers(self):
        """Create wrappers from predefined data"""
        created_wrappers = []
        self.stdout.write("Creating wrappers...")
        for wrapper_data in self.WRAPPERS_DATA:
            wrapper, created = Wrapper.objects.get_or_create(
                name=wrapper_data['name'],
                defaults={
                    'price': Decimal(wrapper_data['price']),
                    'description': wrapper_data['description'],
                    'photo': wrapper_data['photo'],
                }
            )
            created_wrappers.append(wrapper)
            # Создаем запись о наличии на складе
            StockWrapper.objects.create(
                wrapper=wrapper,
                delivery_date=timezone.now().date() - timedelta(days=random.randint(1, 10)),
                length=random.randint(30, 80),
                status='available'
            )
        return created_wrappers

    def create_bouquets(self, flowers_dict, ribbons_dict, wrappers_dict):
        """Create bouquets from predefined data"""
        created_bouquets = []
        self.stdout.write("Creating bouquets...")
        for bouquet_data in self.BOUQUETS_DATA:
            bouquet, created = Bouquet.objects.get_or_create(
                name=bouquet_data['name'],
                defaults={
                    'price': Decimal(bouquet_data['price']),
                    'description': bouquet_data['description'],
                    'photo': bouquet_data['photo'],
                    'tag': bouquet_data['tag'],
                    'is_active': bouquet_data['is_active'],
                }
            )
            created_bouquets.append(bouquet)

            # Добавляем компоненты букета
            for flower_item in bouquet_data['composition']['flowers']:
                flower = flowers_dict.get(flower_item['name'])
                if flower:
                    BouquetFlower.objects.get_or_create(
                        bouquet=bouquet,
                        flower=flower,
                        defaults={'quantity': flower_item['quantity']}
                    )

            for ribbon_item in bouquet_data['composition']['ribbons']:
                ribbon = ribbons_dict.get(ribbon_item['name'])
                if ribbon:
                    BouquetRibbon.objects.get_or_create(
                        bouquet=bouquet,
                        ribbon=ribbon,
                        defaults={'length': ribbon_item['length']}
                    )

            for wrapper_item in bouquet_data['composition']['wrappers']:
                wrapper = wrappers_dict.get(wrapper_item['name'])
                if wrapper:
                    BouquetWrapper.objects.get_or_create(
                        bouquet=bouquet,
                        wrapper=wrapper,
                        defaults={'length': wrapper_item['length']}
                    )
        return created_bouquets

    def create_clients(self):
        """Create client users from predefined data"""
        created_clients = []
        self.stdout.write("Creating clients...")
        for client_data in self.CLIENTS_DATA:
            user, created = User.objects.get_or_create(
                email=client_data['email'],
                defaults={
                    'username': client_data['username'],
                    'first_name': client_data['first_name'],
                    'last_name': client_data['last_name'],
                    'role': client_data['role'],
                    'phone': client_data['phone']
                }
            )
            if created:
                user.set_password(client_data['password'])
                user.save()
            created_clients.append(user)
        return created_clients

    def create_florists(self):
        """Create florist users from predefined data"""
        created_florists = []
        self.stdout.write("Creating florists...")
        for florist_data in self.FLORISTS_DATA:
            user, created = User.objects.get_or_create(
                email=florist_data['email'],
                defaults={
                    'username': florist_data['username'],
                    'first_name': florist_data['first_name'],
                    'last_name': florist_data['last_name'],
                    'role': florist_data['role'],
                    'phone': florist_data['phone']
                }
            )
            if created:
                user.set_password(florist_data['password'])
                user.save()
            
            # Создаем или обновляем статус
            UserStatus.objects.update_or_create(
                user=user,
                defaults={'status': florist_data['status']}
            )

            # Создаем записи о работе
            for record in florist_data['work_records']:
                start_time = timezone.now() - timedelta(days=record['days_ago'])
                WorkRecord.objects.create(
                    user=user,
                    start_time=start_time,
                    end_time=start_time + timedelta(hours=record['duration_hours'])
                )
            
            created_florists.append(user)
        return created_florists

    def create_couriers(self):
        """Create courier users from predefined data"""
        created_couriers = []
        self.stdout.write("Creating couriers...")
        for courier_data in self.COURIERS_DATA:
            user, created = User.objects.get_or_create(
                email=courier_data['email'],
                defaults={
                    'username': courier_data['username'],
                    'first_name': courier_data['first_name'],
                    'last_name': courier_data['last_name'],
                    'role': courier_data['role'],
                    'phone': courier_data['phone']
                }
            )
            if created:
                user.set_password(courier_data['password'])
                user.save()
            
            # Создаем или обновляем статус
            UserStatus.objects.update_or_create(
                user=user,
                defaults={'status': courier_data['status']}
            )

            # Создаем или обновляем местоположение
            CourierLocation.objects.update_or_create(
                user=user,
                defaults={
                    'latitude': courier_data['location']['latitude'],
                    'longitude': courier_data['location']['longitude']
                }
            )

            # Создаем записи о работе
            for record in courier_data['work_records']:
                start_time = timezone.now() - timedelta(days=record['days_ago'])
                WorkRecord.objects.create(
                    user=user,
                    start_time=start_time,
                    end_time=start_time + timedelta(hours=record['duration_hours'])
                )
            
            created_couriers.append(user)
        return created_couriers