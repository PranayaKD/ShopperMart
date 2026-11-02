import os
import sys
from PIL import Image

sys.path.append(r'c:\Users\dashp\dj1\ShopperMart-main')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopperMart.settings')

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import django
django.setup()
import cloudinary.uploader
from ShopperMartapp.models import Category

cat_img = Image.open(r'C:\Users\dashp\.gemini\antigravity\brain\8c0fe4c9-6185-4a25-9e62-bfaae01873ea\.user_uploaded\media_1793293912922_25799172.png').convert('RGB')
w, h = cat_img.size
print('Cat img size:', w, h)

# 7 cards across width 1024
col_w = w / 7.0
cards = [
    ('fruits-vegetables', 0),
    ('dairy-bread-eggs', 1),
    ('atta-rice-oil-dals', 2),
    ('meats-fish-eggs', 3),
    ('masala-dry-fruits-more', 4),
    ('breakfast-sauces', 5),
    ('packaged-food', 6),
]

cat_media_dir = os.path.join(r'c:\Users\dashp\dj1\ShopperMart-main', 'media', 'categories')

for slug, col_idx in cards:
    cx = int(col_idx * col_w + col_w / 2)
    # The rounded gray card is roughly width 110, y from 40 to 150
    crop_box = (max(0, cx - 55), 40, min(w, cx + 55), 150)
    cropped = cat_img.crop(crop_box)
    
    img_filename = f"cat_hi_{slug}.png"
    out_path = os.path.join(cat_media_dir, img_filename)
    cropped.save(out_path)
    
    try:
        res = cloudinary.uploader.upload(out_path, public_id=f"media/categories/cat_{slug}", overwrite=True)
        print(f"Uploaded high-res category: {slug} -> {res.get('secure_url')}")
        cat = Category.objects.filter(slug=slug).first()
        if cat:
            cat.image = f"categories/{img_filename}"
            cat.save()
    except Exception as e:
        print(f"Upload failed for {slug}: {e}")

print("High-res category cards uploaded successfully!")

