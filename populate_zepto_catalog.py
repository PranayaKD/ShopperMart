import os
import sys
from decimal import Decimal
from PIL import Image

sys.path.append(r'c:\Users\dashp\dj1\ShopperMart-main')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopperMart.settings')
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import django
django.setup()

from django.core.files import File
from django.utils.text import slugify
from ShopperMartapp.models import Category, Product
import cloudinary
import cloudinary.uploader
from django.conf import settings

# Ensure folders exist
media_dir = os.path.join(settings.BASE_DIR, 'media')
cat_media_dir = os.path.join(media_dir, 'categories')
prod_media_dir = os.path.join(media_dir, 'products')
os.makedirs(cat_media_dir, exist_ok=True)
os.makedirs(prod_media_dir, exist_ok=True)

# 1. CATEGORY DEFINITIONS FROM SCREENSHOT 2 (Exact Zepto row order, rebranded ShopperMart Cafe)
categories_meta = [
    # Row 1
    {"name": "Fruits & Vegetables", "order": 1, "icon": "🥦", "crop": (0, 0), "is_new": False},
    {"name": "Dairy, Bread & Eggs", "order": 2, "icon": "🥛", "crop": (0, 1), "is_new": False},
    {"name": "Atta, Rice, Oil & Dals", "order": 3, "icon": "🌾", "crop": (0, 2), "is_new": False},
    {"name": "Meats, Fish & Eggs", "order": 4, "icon": "🥩", "crop": (0, 3), "is_new": False},
    {"name": "Masala, Dry Fruits & More", "order": 5, "icon": "🥜", "crop": (0, 4), "is_new": False},
    {"name": "Breakfast & Sauces", "order": 6, "icon": "🥣", "crop": (0, 5), "is_new": False},
    {"name": "Packaged Food", "order": 7, "icon": "🍜", "crop": (0, 6), "is_new": False},
    {"name": "ShopperMart Cafe", "order": 8, "icon": "☕", "crop": (0, 7), "is_new": False},
    {"name": "Tea, Coffee & More", "order": 9, "icon": "🍵", "crop": (0, 8), "is_new": False},
    {"name": "Ice Creams & More", "order": 10, "icon": "🍦", "crop": (0, 9), "is_new": False},
    # Row 2
    {"name": "Frozen Food", "order": 11, "icon": "❄️", "crop": (1, 0), "is_new": False},
    {"name": "Sweet Cravings", "order": 12, "icon": "🍫", "crop": (1, 1), "is_new": False},
    {"name": "Cold Drinks & Juices", "order": 13, "icon": "🧃", "crop": (1, 2), "is_new": False},
    {"name": "Munchies", "order": 14, "icon": "🍿", "crop": (1, 3), "is_new": False},
    {"name": "Biscuits", "order": 15, "icon": "🍪", "crop": (1, 4), "is_new": False},
    {"name": "Apparel & Lifestyle", "order": 16, "icon": "👕", "crop": (1, 5), "is_new": False},
    {"name": "Jewellery", "order": 17, "icon": "💎", "crop": (1, 6), "is_new": True},
    {"name": "Beauty & Personal Care", "order": 18, "icon": "💄", "crop": (1, 7), "is_new": False},
    {"name": "Skincare", "order": 19, "icon": "🧴", "crop": (1, 8), "is_new": False},
    {"name": "Makeup & Beauty", "order": 20, "icon": "✨", "crop": (1, 9), "is_new": False},
    # Additional sections requested in prompt
    {"name": "Laundry Care", "order": 21, "icon": "🧺", "crop": None, "is_new": False},
    {"name": "Cleaning Essentials", "order": 22, "icon": "🧹", "crop": None, "is_new": False},
    {"name": "Rice", "order": 23, "icon": "🍚", "crop": None, "is_new": False},
    {"name": "Hair Care", "order": 24, "icon": "💇", "crop": None, "is_new": False},
    {"name": "Dal & Pulses", "order": 25, "icon": "🫘", "crop": None, "is_new": False},
    {"name": "Personal Hygiene", "order": 26, "icon": "🧼", "crop": None, "is_new": False},
    {"name": "Oil & Ghee", "order": 27, "icon": "🛢️", "crop": None, "is_new": False},
    {"name": "Spices & Seasonings", "order": 28, "icon": "🧂", "crop": None, "is_new": False},
    {"name": "Salt, Sugar & Jaggery", "order": 29, "icon": "🍬", "crop": None, "is_new": False},
    {"name": "Chips, Namkeen & Crisps", "order": 30, "icon": "🥨", "crop": None, "is_new": False},
]

# Source screenshot for categories
cat_screenshot = r'C:\Users\dashp\.gemini\antigravity\brain\8c0fe4c9-6185-4a25-9e62-bfaae01873ea\.user_uploaded\media_1793285891167_0203a293.png'
cat_img = Image.open(cat_screenshot).convert('RGB')
w, h = cat_img.size
col_w = w / 10.0

print("--- PROCESSING CATEGORIES ---")
for cat_info in categories_meta:
    name = cat_info["name"]
    slug = slugify(name)
    cat, created = Category.objects.get_or_create(slug=slug, defaults={"name": name})
    cat.name = name
    cat.order = cat_info["order"]
    cat.icon = cat_info["icon"]
    cat.is_new = cat_info["is_new"]
    
    # If image already set, skip uploading
    if cat.image:
        cat.save()
        continue

    # Crop category thumbnail if from screenshot
    if cat_info["crop"] is not None:
        row_idx, col_idx = cat_info["crop"]
        y_range = (45, 145) if row_idx == 0 else (190, 290)
        cx = int(col_idx * col_w + col_w / 2)
        crop_box = (max(0, cx - 44), y_range[0], min(w, cx + 44), y_range[1])
        cropped = cat_img.crop(crop_box)
        
        # Save local image
        img_filename = f"cat_{slug}.png"
        img_path = os.path.join(cat_media_dir, img_filename)
        cropped.save(img_path)
        
        # Assign to model relative path
        cat.image = f"categories/{img_filename}"
        
        # Upload to Cloudinary
        try:
            public_id = f"media/categories/cat_{slug}"
            res = cloudinary.uploader.upload(img_path, public_id=public_id, overwrite=True)
            print(f"Uploaded Category {name} -> {res.get('secure_url')}")
        except Exception as e:
            print(f"Cloudinary upload skipped/failed for {name}: {e}")
            
    cat.save()
    print(f"Category saved: {cat.name} (order={cat.order}, is_new={cat.is_new})")

# 2. PRODUCT DEFINITIONS FROM SCREENSHOTS 3, 4, 5
# Laundry Care Products (Screenshot 3)
laundry_screenshot = r'C:\Users\dashp\.gemini\antigravity\brain\8c0fe4c9-6185-4a25-9e62-bfaae01873ea\.user_uploaded\media_1793285916861_202b2cad.png'
laundry_products = [
    {
        "name": "Beco Front Load Laundry Detergent Liquid Refill",
        "price": Decimal("298"),
        "mrp": Decimal("349"),
        "unit": "1 pack (2 L)",
        "rating": Decimal("4.8"),
        "reviews": 320,
        "col": 0
    },
    {
        "name": "Surf Excel Matic Liquid Detergent 5 kg for Top Load Washing Machine",
        "price": Decimal("664"),
        "mrp": Decimal("780"),
        "unit": "1 pack (5 kg)",
        "rating": Decimal("4.9"),
        "reviews": 840,
        "col": 1
    },
    {
        "name": "Morelight Detergent Liquid | Pouch",
        "price": Decimal("399"),
        "mrp": Decimal("640"),
        "unit": "1 pack (5 L)",
        "rating": Decimal("4.7"),
        "reviews": 190,
        "col": 2
    },
    {
        "name": "Beco Top Load Laundry Detergent Liquid Refill",
        "price": Decimal("269"),
        "mrp": Decimal("299"),
        "unit": "1 pack (2 L)",
        "rating": Decimal("4.8"),
        "reviews": 210,
        "col": 3
    },
    {
        "name": "Beco Top Load Laundry Detergent Liquid",
        "price": Decimal("154"),
        "mrp": Decimal("220"),
        "unit": "1 pc (960 ml)",
        "rating": Decimal("4.6"),
        "reviews": 145,
        "col": 4
    },
    {
        "name": "Ariel Power Gel Liquid Detergent for Front load washing machine",
        "price": Decimal("373"),
        "mrp": Decimal("429"),
        "unit": "1 pack (2 kg)",
        "rating": Decimal("4.9"),
        "reviews": 560,
        "col": 5
    },
    {
        "name": "Surf Excel Easy Wash Detergent Powder",
        "price": Decimal("237"),
        "mrp": Decimal("250"),
        "unit": "1 pack (1.5 kg)",
        "rating": Decimal("4.8"),
        "reviews": 430,
        "col": 6
    },
    {
        "name": "Ariel Power Gel Liquid Detergent for Top load washing machine",
        "price": Decimal("318"),
        "mrp": Decimal("365"),
        "unit": "1 pack (2 kg)",
        "rating": Decimal("4.9"),
        "reviews": 490,
        "col": 7
    },
]

# Cleaning Essentials Products (Screenshot 4)
cleaning_screenshot = r'C:\Users\dashp\.gemini\antigravity\brain\8c0fe4c9-6185-4a25-9e62-bfaae01873ea\.user_uploaded\media_1793285928612_a2db6055.png'
cleaning_products = [
    {
        "name": "Mr. Muscle Kitchen Cleaner Spray, Fresh Lemon",
        "price": Decimal("218"),
        "mrp": Decimal("249"),
        "unit": "1 pc (450 ml)",
        "rating": Decimal("4.8"),
        "reviews": 270,
        "col": 0
    },
    {
        "name": "Ezee Everyday Ultra Clean Bathroom Floor Cleaner - Removes Tough Stains",
        "price": Decimal("129"),
        "mrp": Decimal("200"),
        "unit": "1 pack (1 L)",
        "rating": Decimal("4.7"),
        "reviews": 310,
        "col": 1
    },
    {
        "name": "BECO Max Kitchen Cleaner Liquid",
        "price": Decimal("199"),
        "mrp": Decimal("249"),
        "unit": "1 pc (500 ml)",
        "rating": Decimal("4.8"),
        "reviews": 160,
        "col": 2
    },
    {
        "name": "Lizol Kitchen Cleaner & Degreaser Spray",
        "price": Decimal("188"),
        "mrp": Decimal("225"),
        "unit": "1 pc (450 ml)",
        "rating": Decimal("4.9"),
        "reviews": 680,
        "col": 3
    },
    {
        "name": "Ezee Everyday Ultra Clean Toilet Cleaner - Instant Freshness",
        "price": Decimal("143"),
        "mrp": Decimal("199"),
        "unit": "1 pack (1 L)",
        "rating": Decimal("4.7"),
        "reviews": 220,
        "col": 4
    },
    {
        "name": "Koparo Magic Foam Cleaner Spray for Kitchen, Tyres and Surfaces",
        "price": Decimal("235"),
        "mrp": Decimal("299"),
        "unit": "1 pc (460 ml)",
        "rating": Decimal("4.6"),
        "reviews": 110,
        "col": 5
    },
    {
        "name": "Harpic Original Toilet Cleaner Liquid",
        "price": Decimal("206"),
        "mrp": Decimal("245"),
        "unit": "1 pc (1 L)",
        "rating": Decimal("4.9"),
        "reviews": 950,
        "col": 6
    },
    {
        "name": "Urbanwipe Kitchen Cleaning Spray",
        "price": Decimal("199"),
        "mrp": Decimal("299"),
        "unit": "1 pc (500 ml)",
        "rating": Decimal("4.7"),
        "reviews": 130,
        "col": 7
    },
]

# Rice Products (Screenshot 5)
rice_screenshot = r'C:\Users\dashp\.gemini\antigravity\brain\8c0fe4c9-6185-4a25-9e62-bfaae01873ea\.user_uploaded\media_1793285968402_f1cfa2e0.png'
rice_products = [
    {
        "name": "BestValue Sona Masoori Raw Rice",
        "price": Decimal("76"),
        "mrp": Decimal("100"),
        "unit": "1 pack (1 kg)",
        "rating": Decimal("4.7"),
        "reviews": 410,
        "col": 0
    },
    {
        "name": "Daily Good Sona Masoori Raw Rice",
        "price": Decimal("89"),
        "mrp": Decimal("100"),
        "unit": "1 pack (1 kg)",
        "rating": Decimal("4.8"),
        "reviews": 530,
        "col": 1
    },
    {
        "name": "GTS Original Kolam Rice",
        "price": Decimal("582"),
        "mrp": Decimal("625"),
        "unit": "1 pack (5 kg)",
        "rating": Decimal("4.9"),
        "reviews": 320,
        "col": 2
    },
    {
        "name": "Daily Good Idli Rice",
        "price": Decimal("65"),
        "mrp": Decimal("100"),
        "unit": "1 pack (1 kg)",
        "rating": Decimal("4.7"),
        "reviews": 290,
        "col": 3
    },
    {
        "name": "Daily Good Dosa Rice",
        "price": Decimal("65"),
        "mrp": Decimal("100"),
        "unit": "1 pack (1 kg)",
        "rating": Decimal("4.7"),
        "reviews": 280,
        "col": 4
    },
    {
        "name": "India Gate Dubar Basmati Rice | Long Slender Grains",
        "price": Decimal("132"),
        "mrp": Decimal("167"),
        "unit": "1 pack (1 kg)",
        "rating": Decimal("4.9"),
        "reviews": 750,
        "col": 5
    },
    {
        "name": "Daawat Rozana Super Basmati Rice | Medium Grain",
        "price": Decimal("98"),
        "mrp": Decimal("100"),
        "unit": "1 pack (1 kg)",
        "rating": Decimal("4.8"),
        "reviews": 610,
        "col": 6
    },
    {
        "name": "India Gate Everyday Basmati Rice | Fluffy Medium Grains",
        "price": Decimal("92"),
        "mrp": Decimal("104"),
        "unit": "1 pack (1 kg)",
        "rating": Decimal("4.8"),
        "reviews": 890,
        "col": 7
    },
]

def add_rail_products(cat_name, screenshot_path, items, y_bounds):
    print(f"\n--- PROCESSING PRODUCTS FOR {cat_name} ---")
    cat = Category.objects.get(name=cat_name)
    im = Image.open(screenshot_path).convert('RGB')
    w, h = im.size
    col_w = w / 8.0
    
    for item in items:
        name = item["name"]
        slug = slugify(name)[:48].rstrip('-')
        col = item["col"]
        
        # Crop the image container cleanly
        crop_box = (int(col * col_w + 16), y_bounds[0], int((col + 1) * col_w - 16), y_bounds[1])
        cropped = im.crop(crop_box)
        
        img_filename = f"{slug}.png"
        img_path = os.path.join(prod_media_dir, img_filename)
        cropped.save(img_path)
        
        # Cloudinary upload
        try:
            public_id = f"media/products/{slug}"
            res = cloudinary.uploader.upload(img_path, public_id=public_id, overwrite=True)
            print(f"Cloudinary: {name} -> {res.get('secure_url')}")
        except Exception as e:
            print(f"Cloudinary error for {name}: {e}")
            
        prod, _ = Product.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "category": cat,
                "price": item["price"],
                "mrp_price": item["mrp"],
                "unit": item["unit"],
                "stock": 50,
                "available": True,
                "rating": item["rating"],
                "reviews_count": item["reviews"],
                "image": f"products/{img_filename}",
                "description": f"Authentic premium {name}. Fast 10-minute delivery by ShopperMart.",
            }
        )
        prod.name = name
        prod.category = cat
        prod.price = item["price"]
        prod.mrp_price = item["mrp"]
        prod.unit = item["unit"]
        prod.stock = 50
        prod.available = True
        prod.rating = item["rating"]
        prod.reviews_count = item["reviews"]
        prod.image = f"products/{img_filename}"
        prod.description = f"Authentic premium {name}. Delivered fresh in 10 minutes from your local ShopperMart store."
        prod.save()
        print(f"Product saved: {prod.name} | Rs. {prod.price} (MRP: Rs. {prod.mrp}) | {prod.unit}")

add_rail_products("Laundry Care", laundry_screenshot, laundry_products, (38, 140))
add_rail_products("Cleaning Essentials", cleaning_screenshot, cleaning_products, (40, 148))
add_rail_products("Rice", rice_screenshot, rice_products, (38, 146))

print("\n--- POPULATION COMPLETED SUCCESSFULLY! ---")
