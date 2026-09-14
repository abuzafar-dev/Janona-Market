from django.core.exceptions import ValidationError
from django.forms import Form, CharField, PasswordInput, ModelForm

from apps.models import Order, Withdrawal


class LoginForm(Form):
    phone_number = CharField(max_length=20, label="Telefon")
    password = CharField(widget=PasswordInput, label="Parol")


class RegisterForm(Form):
    phone_number = CharField(max_length=20, label="Telefon")
    password = CharField(widget=PasswordInput, label="Parol")
    conf_password = CharField(widget=PasswordInput, label="Parolni takrorlash")

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        conf_password = cleaned_data.get('conf_password')
        if password and conf_password and password != conf_password:
            raise ValidationError("Parollar mos tushmadi!")
        return cleaned_data


class OrderForm(ModelForm):
    class Meta:
        model = Order
        fields = ['full_name', 'phone_number', 'quantity']

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity < 1:
            raise ValidationError("Soni kamida 1 bo'lishi kerak.")
        return quantity


class WithdrawalForm(ModelForm):
    class Meta:
        model = Withdrawal
        fields = ['card_number', 'amount', 'type']

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_card_number(self):
        card_number = self.cleaned_data['card_number'].replace(' ', '').replace('-', '')
        if not card_number.isdigit() or len(card_number) != 16:
            raise ValidationError("Karta raqami 16 ta raqamdan iborat bo'lishi kerak.")
        return card_number

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise ValidationError("Summani to'g'ri kiriting.")
        if self.user and amount > self.user.main_balance:
            raise ValidationError("Hisobingizdagi mavjud summadan ko'p miqdor kiritdingiz.")
        return amount
