# ShopperMartapp/admin.py
from django.contrib import admin
from .models import Product, Category, Profile
from .models import Order, OrderItem


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "full_name", "phone", "city", "state")
    search_fields = ("user__username", "full_name", "phone")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock", "available")
    list_filter = ("available", "category")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "email", "total", "created_at")
    inlines = [OrderItemInline]

admin.site.register(OrderItem)