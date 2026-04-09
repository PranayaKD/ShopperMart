import os
import django
import random
from django.utils.text import slugify

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopperMart.settings')
django.setup()

from ShopperMartapp.models import Category, Product

def populate():
    print("Cleaning up database and restoring 'perfect' products...")
    # Clean up all existing products to ensure no duplicates
    Product.objects.all().delete()
    
    # 1. Categories
    categories = ["Electronics", "Fashion", "Home & Living", "Books", "Sports"]
    cat_objs = {}
    for cat_name in categories:
        c, created = Category.objects.get_or_create(
            name=cat_name, 
            defaults={'slug': slugify(cat_name)}
        )
        cat_objs[cat_name] = c
        if created:
            print(f"Created Category: {cat_name}")

    # 2. Perfect Products (Restored from manual work)
    products_data = [
        {
            "name": "Sony WH-1000XM5 Headphones",
            "cat": "Electronics",
            "price": 29990.00,
            "rating": 4.9,
            "reviews": 1280,
            "image": "products/Sony_WH-1000XM5_Headphones.webp",
            "desc": "The industry-leading noise cancelling headphones. Experience the height of audio excellence with dual processors and 8 microphones."
        },
        {
            "name": "Apple MacBook Air M2",
            "cat": "Electronics",
            "price": 99900.00,
            "rating": 4.8,
            "reviews": 2100,
            "image": "products/apple-macbook-air-2-up-front-240304.webp",
            "desc": "Redesigned around the next-generation M2 chip, MacBook Air is strikingly thin and brings exceptional speed and power efficiency."
        },
        {
            "name": "Apple iPhone 14 Pro",
            "cat": "Electronics",
            "price": 119900.00,
            "rating": 4.9,
            "reviews": 3400,
            "image": "products/iphone14.jpg",
            "desc": "A magical new way to interact with iPhone. Groundbreaking safety features designed to save lives. And an innovative 48MP camera for mind-blowing detail."
        },
        {
            "name": "Samsung Galaxy S25 Ultra",
            "cat": "Electronics",
            "price": 124999.00,
            "rating": 4.7,
            "reviews": 950,
            "image": "products/s25.png",
            "desc": "The ultimate Ultra experience. Feature-packed with our most advanced camera system and a stunning 200MP sensor."
        },
        {
            "name": "Smart 4K Ultra HD LED TV",
            "cat": "Electronics",
            "price": 45999.00,
            "rating": 4.5,
            "reviews": 560,
            "image": "products/tv.webp",
            "desc": "Breathtaking clarity and vibrant colors. Enhance your living room with a sleek design and immersive 4K HDR technology."
        },
        {
            "name": "Premium Luxury Fashion Watch",
            "cat": "Fashion",
            "price": 12499.00,
            "rating": 4.6,
            "reviews": 320,
            "image": "products/watch.jpg",
            "desc": "Timeless elegance for the modern individual. Crafted with premium materials and precision movements."
        },
    ]

    for p in products_data:
        prod = Product.objects.create(
            name=p["name"],
            slug=slugify(p["name"]),
            category=cat_objs[p["cat"]],
            description=p["desc"],
            price=p["price"],
            rating=p["rating"],
            reviews_count=p["reviews"],
            image=p["image"],
            stock=random.randint(10, 50),
            available=True
        )
        print(f"Restored Product: {p['name']}")

    print("Database restoration completed successfully!")

if __name__ == "__main__":
    populate()
