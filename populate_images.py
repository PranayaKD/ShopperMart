import os
import django
from django.core.files import File
from django.conf import settings
import shutil

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopperMart.settings')
django.setup()

from ShopperMartapp.models import Product

def populate_images():
    # Source paths (Update these with actual filenames from your environment if they differ)
    # I will use the paths returned by the tools previously
    BASE_DIR = r"C:\Users\dashp\.gemini\antigravity\brain\e699c045-e29a-40d4-8ddd-245ffe13a7de"
    
    IMG_FASHION = os.path.join(BASE_DIR, "fashion_category_1769881597027.png")
    IMG_TECH = os.path.join(BASE_DIR, "electronics_category_1769881611283.png")
    IMG_DEFAULT = os.path.join(BASE_DIR, "modern_product_placeholder_1769880855056.png")
    
    # Check existence
    for p in [IMG_FASHION, IMG_TECH, IMG_DEFAULT]:
        if not os.path.exists(p):
            print(f"Warning: File not found: {p}")
            # If default is missing, we can't do much, but we proceed
            
    # Keywords for categorization
    FASHION_KEYWORDS = ["shirt", "dress", "jacket", "hoodie", "jeans", "t-shirt", "kurta", "saree"]
    TECH_KEYWORDS = ["mixer", "grinder", "kettle", "iron", "phone", "mobile", "laptop", "watch", "speaker", "earphone", "headphone", "t.v", "tv", "macbook", "iphone", "sony", "samsung"]
    
    products = Product.objects.all()
    print(f"Processing {products.count()} products...")

    for product in products:
        name_lower = product.name.lower()
        category_name = product.category.name.lower() if product.category else ""
        category_slug = product.category.slug if product.category else ""
        
        target_img_path = IMG_DEFAULT # Default fallback
        target_img_name = "default_product.png"
        
        # Determine specific image
        if any(k in name_lower for k in FASHION_KEYWORDS) or any(k in category_name for k in ['fashion', 'clothing']):
            target_img_path = IMG_FASHION
            target_img_name = "fashion_product.png"
        elif any(k in name_lower for k in TECH_KEYWORDS) or any(k in category_name for k in ['electronics', 'appliances', 'tech']):
            target_img_path = IMG_TECH
            target_img_name = "tech_product.png"
            
        print(f"Updating {product.name} -> {target_img_name}")
        
        # Open and assign
        if os.path.exists(target_img_path):
            with open(target_img_path, 'rb') as f:
                product.image.save(target_img_name, File(f), save=True)
        else:
             print(f"  Skipping: Source image not found for {target_img_name}")

if __name__ == "__main__":
    populate_images()
