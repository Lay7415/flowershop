from django.shortcuts import redirect
from django.views import View
from django.contrib import messages

class HomeView(View):
    def get(self, request):
        if request.user.is_authenticated:
            if request.user.role == 'florist':
                return redirect('orders:florist_dashboard')
            elif request.user.role == 'courier':
                return redirect('orders:courier_dashboard')
            else:
                # Только для обычных пользователей показываем каталог
                return redirect('catalog:bouquet_list')
        else:
            # Неавторизованные пользователи видят каталог
            return redirect('catalog:bouquet_list')