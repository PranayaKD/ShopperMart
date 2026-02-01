import os
import django
import requests
from django.core.files import File
from io import BytesIO
import urllib.parse

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopperMart.settings')
django.setup()

from ShopperMartapp.models import Product

def download_exact_images():
    products = Product.objects.all()
    print(f"Starting specific image download for {products.count()} products...")

    for product in products:
        # Create a search query from the product name
        # Remove special characters to help the search
        query = product.name.replace('', '').replace('(', '').replace(')', '').replace('/', ' ')
        
        # Use loremflickr with specific keywords
        # Format: https://loremflickr.com/640/480/keyword1,keyword2/all
        keywords = query.replace(' ', ',')
        url = f"https://loremflickr.com/640/480/{urllib.parse.quote(keywords)}/all"
        
        print(f"Fetching image for '{product.name}' using query: {keywords}...")
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Use the content of the response to save the image
                img_temp = BytesIO(response.content)
                filename = f"{product.slug}.jpg"
                
                # Delete old image if it exists to overwrite
                if product.image:
                    storage = product.image.storage
                    if storage.exists(product.image.name):
                        storage.delete(product.image.name)
                
                product.image.save(filename, File(img_temp), save=True)
                print(f"  Successfully updated image for {product.name}")
            else:
                print(f"  Failed to fetch image for {product.name} (Status: {response.status_code})")
        except Exception as e:
            print(f"  Error downloading image for {product.name}: {e}")

if __name__ == "__main__":
    download_exact_images()
