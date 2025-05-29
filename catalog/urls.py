# catalog/urls.py
from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.bouquet_list_view, name="bouquet_list"),
    path("<int:pk>/", views.bouquet_detail_view, name="bouquet_detail"),
]
