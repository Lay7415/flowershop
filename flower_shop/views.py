from django.shortcuts import redirect
from django.views import View

class HomeView(View):
    def get(self, request):
        if request.user.is_authenticated:
            if request.user.role == 'florist':
                return redirect('orders:florist_dashboard')
            elif request.user.role == 'courier':
                return redirect('orders:courier_dashboard')
        return redirect('catalog:bouquet_list')