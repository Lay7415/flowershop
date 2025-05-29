# users/views.py
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy 
from django.contrib import messages
from django.contrib.auth import login, authenticate 
from django.contrib.auth.decorators import login_required 
from .forms import UserRegistrationForm, CustomAuthenticationForm
import logging

logger = logging.getLogger(__name__)

def custom_login_view(request):
    if request.user.is_authenticated:
        user_role = request.user.role
        if user_role == 'courier':
            redirect_url = reverse('orders:courier_dashboard')
        elif user_role == 'florist':
            redirect_url = reverse('orders:florist_dashboard')
        else:
            redirect_url = reverse('catalog:bouquet_list')
        messages.info(request, "Вы уже вошли в систему.")
        return redirect(redirect_url)

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            logger.info(f"Successful login for user {user.email} with role {user.role}")
            
            if user.role == 'courier':
                url = reverse('orders:courier_dashboard')
            elif user.role == 'florist':
                url = reverse('orders:florist_dashboard')
            else:
                url = reverse('catalog:bouquet_list')
            
            logger.info(f"Redirecting user {user.email} to {url}")
            
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect(url)
        else:
            logger.warning(f"Failed login attempt for email: {request.POST.get('username', 'unknown')}")
    else:
        form = CustomAuthenticationForm(request)
        
    return render(request, 'registration/login.html', {'form': form})


def registration_view(request):
    if request.user.is_authenticated:
        messages.info(request, 'Вы уже вошли в систему.')
        return redirect('catalog:bouquet_list')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()  
            login(request, user)  
            messages.success(request, 'Регистрация прошла успешно! Вы вошли в систему.')
            return redirect('catalog:bouquet_list')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме регистрации.')
    else:
        form = UserRegistrationForm()
        
    return render(request, 'registration/register.html', {'form': form})