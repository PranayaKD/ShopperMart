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
        {"name": "Apple iPhone 15 Pro", "cat": "Electronics", "price": 134900.00, "rating": 4.9, "reviews": 1280},
        {"name": "Samsung Galaxy S24 Ultra", "cat": "Electronics", "price": 129999.00, "rating": 4.8, "reviews": 950},
        {"name": "OnePlus 12 5G", "cat": "Electronics", "price": 64999.00, "rating": 4.6, "reviews": 420},
        {"name": "Sony WH-1000XM5 Wireless", "cat": "Electronics", "price": 29990.00, "rating": 4.9, "reviews": 2100},
        {"name": "MacBook Air M2", "cat": "Electronics", "price": 99900.00, "rating": 4.7, "reviews": 1500},
        
        # Fashion
        {"name": "Premium Linen Tailored Shirt", "cat": "Fashion", "price": 2499.00, "rating": 4.4, "reviews": 320},
        {"name": "Banarasi Silk Designer Saree", "cat": "Fashion", "price": 15999.00, "rating": 4.8, "reviews": 85},
        {"name": "Italian Leather Laptop Bag", "cat": "Fashion", "price": 4499.00, "rating": 4.5, "reviews": 110},
        {"name": "Classic Aviator Sunglasses", "cat": "Fashion", "price": 1299.00, "rating": 4.2, "reviews": 560},
        
        # Home & Living
        {"name": "Minimalist Coffee Table Pro", "cat": "Home & Living", "price": 8999.00, "rating": 4.3, "reviews": 140},
        {"name": "Royal Velvet Cushion Set", "cat": "Home & Living", "price": 1899.00, "rating": 4.7, "reviews": 90},
        {"name": "Ergonomic Mesh Office Chair", "cat": "Home & Living", "price": 12500.00, "rating": 4.5, "reviews": 280},
        
        # Books
        {"name": "Atomic Habits - Hardcover", "cat": "Books", "price": 799.00, "rating": 4.9, "reviews": 15000},
        {"name": "The Psychology of Money", "cat": "Books", "price": 399.00, "rating": 4.8, "reviews": 8900},
        
        # Sports
        {"name": "Smart Fitness Watch Ultra", "cat": "Sports", "price": 2499.00, "rating": 4.1, "reviews": 3400},
        {"name": "Pro Yoga Mat Thick", "cat": "Sports", "price": 1499.00, "rating": 4.6, "reviews": 1200},
    ]

    for p in products_data:
        prod, created = Product.objects.update_or_create(
            slug=slugify(p["name"]),
            defaults={
                "name": p["name"],
                "category": cat_objs[p["cat"]],
                "description": f"Experience the pinnacle of {p['cat']} with the {p['name']}. Meticulously crafted for the discerning Indian consumer, this object defines modern excellence.",
                "price": p["price"],
                "rating": p.get("rating", 4.5),
                "reviews_count": p.get("reviews", 120),
                "stock": random.randint(10, 100),
                "available": True
            }
        )
        if created:
            print(f"Created Product: {p['name']}")
        else:
            print(f"Updated Product: {p['name']}")

    print("Database population completed successfully!")

if __name__ == "__main__":
    populate()
