import os
import sys
import io
import urllib.request
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

import cloudinary
import cloudinary.uploader
from django.utils.text import slugify
from ShopperMartapp.models import Category, Product

prod_media_dir = os.path.join(r'c:\Users\dashp\dj1\ShopperMart-main', 'media', 'products')
os.makedirs(prod_media_dir, exist_ok=True)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
}

extra_products = [
    # Laundry Care
    {
        "category": "laundry-care",
        "name": "Comfort After Wash Fabric Conditioner Morning Fresh",
        "price": Decimal("215"),
        "mrp": Decimal("240"),
        "unit": "1 pc (860 ml)",
        "rating": Decimal("4.8"),
        "reviews": 380,
        "image_url": "https://www.bbassets.com/media/uploads/p/l/267012_9-comfort-after-wash-fabric-conditioner-morning-fresh.jpg"
    },
    {
        "category": "laundry-care",
        "name": "Tide Plus Extra Power Detergent Powder Jasmine & Rose",
        "price": Decimal("245"),
        "mrp": Decimal("280"),
        "unit": "1 pack (2 kg)",
        "rating": Decimal("4.7"),
        "reviews": 510,
        "image_url": "https://www.bbassets.com/media/uploads/p/l/266969_19-tide-plus-extra-power-detergent-washing-powder-jasmine-rose.jpg"
    },
    {
        "category": "laundry-care",
        "name": "Vanish Oxi Action Fabric Stain Remover Liquid",
        "price": Decimal("219"),
        "mrp": Decimal("255"),
        "unit": "1 pc (800 ml)",
        "rating": Decimal("4.8"),
        "reviews": 420,
        "image_url": "https://www.bbassets.com/media/uploads/p/l/40003058_11-vanish-all-in-one-detergent-booster-liquid.jpg"
    },
    {
        "category": "laundry-care",
        "name": "Rin Advanced Detergent Bar",
        "price": Decimal("80"),
        "mrp": Decimal("95"),
        "unit": "4 x 250 g",
        "rating": Decimal("4.6"),
        "reviews": 290,
        "image_url": "https://www.bbassets.com/media/uploads/p/l/266951_16-rin-detergent-bar.jpg"
    },

    # Cleaning Essentials
    {
        "category": "cleaning-essentials",
        "name": "Colin Glass and Surface Cleaner Spray",
        "price": Decimal("108"),
        "mrp": Decimal("125"),
        "unit": "1 pc (500 ml)",
        "rating": Decimal("4.9"),
        "reviews": 920,
        "image_url": "https://www.bbassets.com/media/uploads/p/l/263935_18-colin-glass-cleaner-ultra.jpg"
    },
    {
        "category": "cleaning-essentials",
        "name": "Scotch-Brite Sponge Wipe & Scrub Sponge",
        "price": Decimal("115"),
        "mrp": Decimal("135"),
        "unit": "Pack of 3",
        "rating": Decimal("4.8"),
        "reviews": 410,
        "image_url": "https://www.bbassets.com/media/uploads/p/l/40049448_8-scotch-brite-sponge-wipe-large.jpg"
    },
    {
        "category": "cleaning-essentials",
        "name": "Dettol Disinfectant Liquid Lime Fresh",
        "price": Decimal("338"),
        "mrp": Decimal("399"),
        "unit": "1 pc (1 L)",
        "rating": Decimal("4.9"),
        "reviews": 880,
        "image_url": "https://www.bbassets.com/media/uploads/p/l/267027_12-dettol-disinfectant-sanitizer-liquid-lime-fresh.jpg"
    },
    {
        "category": "cleaning-essentials",
        "name": "Odonil Room Air Freshener Blocks Assorted",
        "price": Decimal("165"),
        "mrp": Decimal("199"),
        "unit": "Pack of 4 (200 g)",
        "rating": Decimal("4.7"),
        "reviews": 330,
        "image_url": "https://www.bbassets.com/media/uploads/p/l/1204481_2-odonil-air-freshener-block-assorted.jpg"
    },

    # Rice
    {
        "category": "rice",
        "name": "Fortune Everyday Full Grain Basmati Rice",
        "price": Decimal("110"),
        "mrp": Decimal("145"),
        "unit": "1 pack (1 kg)",
        "rating": Decimal("4.8"),
        "reviews": 470,
        "image_url": "https://www.bbassets.com/media/uploads/p/l/40149909_7-fortune-everyday-full-grain-basmati-rice.jpg"
    },
    {
        "category": "rice",
        "name": "Kohinoor Super Silver Authentic Basmati Rice",
        "price": Decimal("142"),
        "mrp": Decimal("180"),
        "unit": "1 pack (1 kg)",
        "rating": Decimal("4.9"),
        "reviews": 610,
        "image_url": "https://www.bbassets.com/media/uploads/p/l/284420_7-kohinoor-super-silver-basmati-rice.jpg"
    },
    {
        "category": "rice",
        "name": "Aashirvaad Superior MP Sharbati Atta",
        "price": Decimal("285"),
        "mrp": Decimal("330"),
        "unit": "1 pack (5 kg)",
        "rating": Decimal("4.9"),
        "reviews": 1250,
        "image_url": "https://www.bbassets.com/media/uploads/p/l/126906_10-aashirvaad-atta-whole-wheat.jpg"
    },
    {
        "category": "rice",
        "name": "Daily Good Organic Brown Rice",
        "price": Decimal("115"),
        "mrp": Decimal("140"),
        "unit": "1 pack (1 kg)",
        "rating": Decimal("4.7"),
        "reviews": 230,
        "image_url": "https://www.bbassets.com/media/uploads/p/l/40194747_6-bb-royal-organic-brown-rice.jpg"
    }
]

print("--- DOWNLOADING & CREATING EXTRA PRODUCTS TO ENSURE LONG SCROLLABLE RAILS ---")
for item in extra_products:
    cat = Category.objects.filter(slug=item["category"]).first()
    if not cat:
        print("Missing cat:", item["category"])
        continue
        
    slug = slugify(item["name"])[:48].rstrip('-')
    img_filename = f"{slug}.png"
    img_path = os.path.join(prod_media_dir, img_filename)
    
    try:
        req = urllib.request.Request(item["image_url"], headers=headers)
        data = urllib.request.urlopen(req, timeout=8).read()
        im = Image.open(io.BytesIO(data))
        if im.mode in ('RGBA', 'LA'):
            bg = Image.new('RGB', im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert('RGB')
        
        w, h = im.size
        max_dim = max(w, h)
        square_im = Image.new('RGB', (max_dim, max_dim), (255, 255, 255))
        square_im.paste(im, ((max_dim - w) // 2, (max_dim - h) // 2))
        final_im = square_im.resize((500, 500), Image.Resampling.LANCZOS)
        final_im.save(img_path, format="PNG", optimize=True)
        
        # Upload Cloudinary
        res = cloudinary.uploader.upload(img_path, public_id=f"media/products/{slug}", overwrite=True)
        print("Uploaded:", slug, res.get("secure_url"))
    except Exception as e:
        print("Image fetch error for", slug, e)
        
    prod, _ = Product.objects.get_or_create(
        slug=slug,
        defaults={
            "name": item["name"],
            "category": cat,
            "price": item["price"],
            "mrp_price": item["mrp"],
            "unit": item["unit"],
            "stock": 45,
            "available": True,
            "rating": item["rating"],
            "reviews_count": item["reviews"],
            "image": f"products/{img_filename}",
            "description": f"Authentic {item['name']}. Delivered fresh in 10 minutes from ShopperMart."
        }
    )
    prod.name = item["name"]
    prod.category = cat
    prod.price = item["price"]
    prod.mrp_price = item["mrp"]
    prod.unit = item["unit"]
    prod.image = f"products/{img_filename}"
    prod.save()
    print("Saved product:", prod.name)

print("--- FINISHED EXTRA PRODUCTS POPULATION ---")

