import os
import sys
import io
import urllib.request
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
from ShopperMartapp.models import Product

prod_media_dir = os.path.join(r'c:\Users\dashp\dj1\ShopperMart-main', 'media', 'products')
os.makedirs(prod_media_dir, exist_ok=True)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
}

clean_product_images = {
    # Laundry Care
    "surf-excel-matic-liquid-detergent-5-kg-for-top-l": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/665a1d0b-20b8-4096-ab43-9f96a03e6ef6/Surf-Excel-Matic-Liquid-Detergent-5-kg-for-Top-Load.jpg",
    "beco-front-load-laundry-detergent-liquid-refill": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/01436964-c530-4a6d-b545-60226b7484a4/BECO-Front-Load-Laundry-Detergent-Liquid-Refill.png",
    "morelight-detergent-liquid-pouch": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/7db7048e-b3b7-4e56-b914-51b97b76f572/Morelight-Detergent-Liquid.jpg",
    "beco-top-load-laundry-detergent-liquid-refill": "https://www.letsbeco.com/cdn/shop/files/1FL1L.png",
    "beco-top-load-laundry-detergent-liquid": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/8bafce62-bac1-4b54-9a11-404aad2f3355/Beco-Top-Load-Laundry-Detergent-Liquid.jpg",
    "ariel-power-gel-liquid-detergent-for-front-load": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/1aaed251-649d-4120-a1ac-d26cc2aceed8/Ariel-Power-Gel-Liquid-Detergent-for-Top-load-washing-machine.jpeg",
    "surf-excel-easy-wash-detergent-powder": "https://rukminim3.flixcart.com/image/480/480/xif0q/washing-powder/a/m/1/-enriched-transparent-original-imahhg838jnegzax.png?q=90",
    "ariel-power-gel-liquid-detergent-for-top-load-wa": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/1aaed251-649d-4120-a1ac-d26cc2aceed8/Ariel-Power-Gel-Liquid-Detergent-for-Top-load-washing-machine.jpeg",

    # Cleaning Essentials
    "mr-muscle-kitchen-cleaner-spray-fresh-lemon": "https://www.bbassets.com/media/uploads/p/l/263939_16-mr-muscles-kitchen-cleaner-powers-through-grease-grime.jpg",
    "ezee-everyday-ultra-clean-bathroom-floor-cleaner": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/2e4f3573-4dd9-4bc0-a86b-f777f92742fe/Ezee-Everyday-Ultra-Clean-Bathroom-Floor-Cleaner-Removes-Bathroom-Stains.jpg",
    "beco-max-kitchen-cleaner-liquid": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/01cfa818-10b3-4fc8-816c-1f88be7fe8ff/BECO-Max-Kitchen-Cleaner-Liquid.jpeg",
    "lizol-kitchen-cleaner-degreaser-spray": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/7ca07853-0593-4266-b702-cc652f2c11ae/Lizol-Kitchen-Cleaner-Degreaser-Spray.jpg",
    "ezee-everyday-ultra-clean-toilet-cleaner-instant": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/da44374c-af3a-468a-9032-33b75a1ff652/Ezee-Everyday-Ultra-Clean-Toilet-Cleaner-Instant-Freshness.jpg",
    "koparo-magic-foam-cleaner-spray-for-kitchen-tyre": "https://koparoclean.com/cdn/shop/files/8_26026e12-5682-4aa0-8351-636c2b576071.png",
    "harpic-original-toilet-cleaner-liquid": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/67f31743-d647-415e-b549-85a3878a8605/Harpic-Original-Toilet-Cleaner-Liquid.jpeg",
    "urbanwipe-kitchen-cleaning-spray": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/ccd189e4-599d-48dc-825a-cd2205b4aad7/Urbanwipe-Kitchen-Cleaning-Spray.png",

    # Rice
    "bestvalue-sona-masoori-raw-rice": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/3be8c499-62ae-4e2d-8a0e-3d45975260e4/BestValue-Sona-Masoori-Raw-Rice.jpg",
    "daily-good-sona-masoori-raw-rice": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/f483c2fc-7527-45a2-82ca-3d4e02e5a9fe/Daily-Good-Sona-Masoori-Raw-Rice.jpeg",
    "gts-original-kolam-rice": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/0a9edcdb-36ba-4b9c-9336-aa7bf46abc71/GTS-Kolam-Rice.jpg",
    "daily-good-idli-rice": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/14505487-04fc-43e7-ad56-56c10df16ff0/Daily-Good-Idli-Rice.jpg",
    "daily-good-dosa-rice": "https://cdn.zeptonow.com/production/ik-seo/cms/product_variant/2436ee19-df6d-4113-b1e7-236e5a879412/Daily-Good-Dosa-Rice.jpg",
    "india-gate-dubar-basmati-rice-long-slender-grain": "https://services.kpnfresh.com/media/v1/products/images/d89d8f03-a1bb-4dad-851c-578945ff20db/india-gate-classic-basmati-rice.webp?c_type=C1",
    "daawat-rozana-super-basmati-rice-medium-grain": "https://www.bbassets.com/media/uploads/p/l/40075196_8-daawat-basmati-rice-rozana-super-90.jpg",
    "india-gate-everyday-basmati-rice-fluffy-medium-g": "https://d2zibpmra2kiio.cloudfront.net/public/products/everyday/1kg/pack-front.png"
}

print("--- DOWNLOADING AND UPLOADING CLEAN PRODUCT IMAGES ---")
for slug, img_url in clean_product_images.items():
    try:
        req = urllib.request.Request(img_url, headers=headers)
        data = urllib.request.urlopen(req, timeout=10).read()
        im = Image.open(io.BytesIO(data))
        
        # Convert RGBA to RGB on white background if transparent
        if im.mode in ('RGBA', 'LA'):
            bg = Image.new('RGB', im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert('RGB')
            
        # Create a clean square image (e.g. 500x500) with white padding
        w, h = im.size
        max_dim = max(w, h)
        square_im = Image.new('RGB', (max_dim, max_dim), (255, 255, 255))
        offset = ((max_dim - w) // 2, (max_dim - h) // 2)
        square_im.paste(im, offset)
        
        # Resize to 500x500 for crisp fast loading
        final_im = square_im.resize((500, 500), Image.Resampling.LANCZOS)
        
        img_filename = f"{slug}.png"
        img_path = os.path.join(prod_media_dir, img_filename)
        final_im.save(img_path, format="PNG", optimize=True)
        
        # Upload to Cloudinary
        res = cloudinary.uploader.upload(img_path, public_id=f"media/products/{slug}", overwrite=True)
        print(f"SUCCESS: {slug} -> {res.get('secure_url')}")
        
        # Update product
        prod = Product.objects.filter(slug=slug).first()
        if prod:
            prod.image = f"products/{img_filename}"
            prod.save()
            
    except Exception as e:
        print(f"FAILED {slug} ({img_url}): {e}")

print("--- COMPLETED CLEAN IMAGES UPDATE ---")

