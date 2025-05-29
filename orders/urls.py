# orders/urls.py
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Клиентские URL
    path('create/', views.order_create, name='order_create'),
    path('<int:order_id>/pay/', views.order_pay, name='order_pay'),
    path('my/', views.order_list, name='order_list'),
    path('<int:pk>/', views.order_detail, name='order_detail'),
    path('<int:pk>/confirm/', views.order_confirm_completion, name='order_confirm'),

    # URL Флориста
    path('florist/dashboard/', views.florist_dashboard, name='florist_dashboard'),
    path('florist/task/<int:pk>/complete/', views.florist_task_complete, name='florist_task_complete'),

    # URL Курьера
    path('courier/dashboard/', views.courier_dashboard, name='courier_dashboard'),
    path('courier/task/<int:pk>/start/', views.courier_start_delivery, name='courier_start_delivery'),
    path('courier/task/<int:pk>/complete/', views.courier_task_complete, name='courier_task_complete'),
    path('courier/task/<int:pk>/update-location/', views.courier_update_location, name='courier_update_location'),
]