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