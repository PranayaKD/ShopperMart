import os
import django
import random

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopperMart.settings')
django.setup()

from ShopperMartapp.models import Category, Product
from django.utils.text import slugify

def populate():
    print("Populating database...")

    # 1. Create Categories
    categories = [
        "Electronics",
        "Fashion",
        "Home & Living",
        "Books",
        "Sports"
    ]
    
    cat_objs = {}
    for cat_name in categories:
        c, created = Category.objects.get_or_create(
            name=cat_name, 
            defaults={'slug': slugify(cat_name)}
        )
        cat_objs[cat_name] = c
        if created:
            print(f"Created Category: {cat_name}")
        else:
            print(f"Category already exists: {cat_name}")

    # 2. Create Products
    products_data = [
        # Electronics
        {"name": "Smartphone X", "cat": "Electronics", "price": 699.00},
        {"name": "4K Ultra HD TV", "cat": "Electronics", "price": 450.00},
        {"name": "Wireless Noise Cancelling Headphones", "cat": "Electronics", "price": 199.99},
        
        # Fashion
        {"name": "Men's Denim Jacket", "cat": "Fashion", "price": 49.99},
        {"name": "Summer Floral Dress", "cat": "Fashion", "price": 35.50},
        {"name": "Classic Leather Sneakers", "cat": "Fashion", "price": 89.00},
        
        # Home
        {"name": "Modern Coffee Table", "cat": "Home & Living", "price": 120.00},
        {"name": "Ceramic Plant Pot Set", "cat": "Home & Living", "price": 25.00},
        
        # Sports
        {"name": "Yoga Mat Premium", "cat": "Sports", "price": 20.00},
        {"name": "Resistance Bands Set", "cat": "Sports", "price": 15.00},
    ]

    for p in products_data:
        prod, created = Product.objects.get_or_create(
            name=p["name"],
            defaults={
                "slug": slugify(p["name"]),
                "category": cat_objs[p["cat"]],
                "description": f"This is a high-quality {p['name']} from our {p['cat']} collection.",
                "price": p["price"],
                "stock": random.randint(5, 50),
                "available": True
            }
        )
        if created:
            print(f"Created Product: {p['name']}")
        else:
            print(f"Product already exists: {p['name']}")

    print("Database population completed successfully!")

if __name__ == "__main__":
    populate()
