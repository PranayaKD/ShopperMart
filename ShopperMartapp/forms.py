# ShopperMartapp/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile
from .models import Product
import re

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email"]

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower()
        if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
            raise forms.ValidationError("Please provide a valid email domain (e.g. @gmail.com).")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = self.data.get("password1")
        
        if password:
            if len(password) < 6:
                self.add_error(None, "Password must be at least 6 characters.")
            if not any(char.isdigit() for char in password):
                self.add_error(None, "Password must contain at least one digit.")
            if not any(not char.isalnum() for char in password):
                self.add_error(None, "Password must contain at least one special character.")
            if not any(char.isupper() for char in password):
                self.add_error(None, "Password must contain an uppercase letter.")
            if not any(char.islower() for char in password):
                self.add_error(None, "Password must contain a lowercase letter.")
                
        return cleaned_data

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["full_name", "phone", "avatar", "address_line1", "address_line2", "landmark", "city", "state", "pincode"]


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["category", "name", "slug", "description", "price", "stock", "available", "image"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=100, label="Full Name")
    email = forms.EmailField(label="Email Address")
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label="Shipping Address")
    city = forms.CharField(max_length=100, label="City")
    postal_code = forms.CharField(max_length=20, label="Pincode")
    payment_method = forms.ChoiceField(choices=[
        ('card', 'Credit/Debit Card'), 
        ('upi', 'UPI'), 
        ('cod', 'Cash on Delivery')
    ], label="Payment Method")

