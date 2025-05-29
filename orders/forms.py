# orders/forms.py
from django import forms
from .models import Order

class OrderCreateForm(forms.ModelForm):
    # Добавляем скрытые поля для координат и расстояния
    delivery_lat = forms.FloatField(widget=forms.HiddenInput(), required=False)
    delivery_lon = forms.FloatField(widget=forms.HiddenInput(), required=False)
    delivery_distance = forms.FloatField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Order
        fields = [
            'recipient_name', 'recipient_phone',
            'delivery_address_name', 'delivery_lat', 'delivery_lon',
            'delivery_datetime', 'delivery_distance'
        ]
        widgets = {
            'recipient_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя получателя'}),
            'recipient_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Телефон получателя'}),
            'delivery_address_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_address', 'placeholder': 'Введите адрес или выберите на карте'}),
            'delivery_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
        labels = {
            'recipient_name': 'Имя получателя',
            'recipient_phone': 'Телефон получателя',
            'delivery_address_name': 'Адрес доставки',
            'delivery_datetime': 'Желаемые дата и время доставки',
        }

    def clean(self):
        cleaned_data = super().clean()
        lat = cleaned_data.get('delivery_lat')
        lon = cleaned_data.get('delivery_lon')
        distance = cleaned_data.get('delivery_distance')

        if not all([lat, lon]):
            raise forms.ValidationError('Пожалуйста, выберите точку доставки на карте')
        
        if not distance:
            raise forms.ValidationError('Не удалось рассчитать стоимость доставки. Пожалуйста, выберите другой адрес.')

        return cleaned_data


# Форма для имитации оплаты (данные не сохраняются)
class PaymentForm(forms.Form):
    card_number = forms.CharField(
        label="Номер карты",
        max_length=19, # 16 цифр + 3 пробела
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'xxxx xxxx xxxx xxxx'}),
        required=True
    )
    expiry_date = forms.CharField(
        label="Срок действия",
        max_length=5, # MM/YY
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'MM/YY'}),
        required=True
    )
    cvv = forms.CharField(
        label="CVV",
        max_length=4,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '***'}), # Скрыть ввод
        required=True
    )