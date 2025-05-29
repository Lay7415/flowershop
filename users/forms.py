# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User

class UserRegistrationForm(UserCreationForm):
    # Добавляем стандартные поля, если нужно (email уже есть в модели)
    first_name = forms.CharField(max_length=30, required=False, label="Имя")
    last_name = forms.CharField(max_length=150, required=False, label="Фамилия")
    phone = forms.CharField(max_length=20, required=False, label="Телефон")

    class Meta(UserCreationForm.Meta):
        model = User
        # Указываем поля, которые будут в форме
        fields = ('username', 'email', 'first_name', 'last_name', 'phone')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем поля более user-friendly в форме
        for field_name, field in self.fields.items():
             field.widget.attrs.update({'class': 'form-control mb-2'})
             if field_name == 'phone':
                 field.widget.attrs['placeholder'] = '+7 (XXX) XXX-XX-XX'

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={'autofocus': True}), label="Email")

    class Meta:
        model = User
        fields = ('username', 'password')