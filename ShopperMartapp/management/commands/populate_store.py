import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from ShopperMartapp.models import Category, Product

class Command(BaseCommand):
    help = 'Populates the store with curated premium products and categories.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing products and categories before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Data cleared.'))

        data = {
            "Electronics": [
                ("Apple MacBook Air M3", "cat_Electronics_cUWi3XA.png", 114900, 4.8, 2341),
                ("Apple iPhone 16 Pro", "cat_Electronics_K4nFfLl.png", 119900, 4.7, 5872),
                ("LG 55-inch OLED Smart TV", "cat_Electronics_0QJJRQj.png", 99990, 4.6, 1203),
                ("Redmi Pad SE", "cat_Electronics_SNiz7hm.png", 12999, 4.3, 8421),
                ("Samsung Galaxy S25 Ultra", "cat_Electronics.png", 134999, 4.8, 3654),
                ("Samsung Galaxy Watch 7", "cat_Electronics_vLTRvkr.png", 29999, 4.5, 1876),
                ("Sony WH-1000XM5 Headphones", "cat_Electronics_vp5EVzc.png", 24990, 4.9, 6102),
                ("boAt Airdopes 141", "cat_Electronics_l7EAiIg.png", 1299, 4.2, 42308),
            ],
            "Fashion": [
                ("Leather Wallet Brown", "cat_Fashion_oQ4tV2L.png", 699, 4.3, 3210),
                ("Men's Cotton T-Shirt Navy Blue", "cat_Fashion.png", 499, 4.1, 12540),
                ("Men's Slim Fit Jeans", "cat_Fashion_YWY48p2.png", 1799, 4.4, 7832),
                ("Unisex Sports Hoodie Grey", "cat_Fashion_G1IZv00.png", 1599, 4.3, 5671),
                ("Women's Running Shoes", "cat_Fashion_cFNoUNu.png", 2999, 4.5, 4209),
                ("Women's Summer Dress Floral Print", "cat_Fashion_DEGgbC7.png", 1299, 4.2, 6087),
                ("Women's Winter Jacket Black", "cat_Fashion_3KfFnBP.png", 2499, 4.6, 2934),
            ],
            "Groceries": [
                ("Aashirvaad Atta 10kg", "cat_Groceries.png", 485, 4.6, 28431),
                ("Amul Butter 500g", "cat_Groceries_xzLHR53.png", 285, 4.8, 54203),
                ("Cadbury Dairy Milk Silk (Pack of 3)", "cat_Groceries_aGbpDbG.png", 450, 4.7, 19876),
                ("Fortune Basmati Rice 5kg", "cat_Groceries_lf0vJJn.png", 599, 4.5, 15320),
                ("Maggi 2-Minute Noodles (Pack of 12)", "cat_Groceries_YX1V9xY.png", 168, 4.6, 67541),
                ("Saffola Gold Oil 5L", "cat_Groceries_6iGTDPP.png", 899, 4.4, 11203),
                ("Tata Gold Tea 500g", "cat_Groceries_w14M1I0.png", 320, 4.5, 23109),
            ],
            "Books": [
                ("Atomic Habits by James Clear", "cat_Books.png", 399, 4.9, 31204),
                ("Harry Potter and the Philosopher's Stone", "cat_Books_8lf8ZGF.png", 350, 4.8, 44871),
                ("Ikigai: The Japanese Secret to a Long Life", "cat_Books_D8KvS1p.png", 299, 4.7, 18654),
                ("Rich Dad Poor Dad by Robert Kiyosaki", "cat_Books_ijg9GOG.png", 349, 4.7, 27430),
                ("The Alchemist by Paulo Coelho", "cat_Books_UPxY4vZ.png", 299, 4.8, 38921),
                ("The Psychology of Money by Morgan Housel", "cat_Books_jFla4zw.png", 350, 4.8, 22317),
            ],
            "Beauty & Personal Care": [
                ("Dove Shampoo Intense Repair 650ml", "cat_Beauty_and_Personal_Care_GBLfZtO.png", 375, 4.4, 9832),
                ("Himalaya Neem Face Wash 150ml", "cat_Beauty_and_Personal_Care.png", 180, 4.5, 34210),
                ("L'Oreal Paris Revitalift Night Cream 50g", "cat_Beauty_and_Personal_Care_UVE0nNT.png", 850, 4.3, 6541),
                ("Lakme Sunscreen SPF 50 100ml", "cat_Beauty_and_Personal_Care_2ebHsgp.png", 499, 4.4, 12087),
                ("Maybelline Fit Me Foundation", "cat_Beauty_and_Personal_Care_huDs2aZ.png", 549, 4.3, 15432),
                ("Nivea Moisturizing Cream 200ml", "cat_Beauty_and_Personal_Care_kdsnQnF.png", 285, 4.6, 21903),
            ],
            "Home & Kitchen": [
                ("Bamboo Cutting Board Set", "cat_Home_and_Kitchen_a73pLe7.png", 699, 4.3, 4521),
                ("Ceramic Dinner Set 16 Pieces", "cat_Home_and_Kitchen.png", 2499, 4.5, 3208),
                ("Cotton Bedsheet King Size", "cat_Home_and_Kitchen_qmHgetJ.png", 1299, 4.4, 7654),
                ("Electric Kettle 1.5L", "cat_Home_and_Kitchen_tXz0fCe.png", 899, 4.5, 18320),
                ("Mixer Grinder 750W", "cat_Home_and_Kitchen_erGU0MF.png", 3499, 4.6, 9871),
                ("Non-Stick Frying Pan 28cm", "cat_Home_and_Kitchen_TD86Zou.png", 799, 4.4, 11203),
                ("Stainless Steel Water Bottle 1L", "cat_Home_and_Kitchen_6hNSSV7.png", 599, 4.5, 16432),
            ]
        }

        for cat_name, products in data.items():
            category, created = Category.objects.get_or_create(
                name=cat_name,
                defaults={'slug': slugify(cat_name)}
            )
            self.stdout.write(f'Category: {cat_name} ({"Created" if created else "Existing"})')

            for name, filename, price, rating, reviews in products:
                p_slug = slugify(name)
                # Check if product exists to avoid duplicates if not clearing
                if Product.objects.filter(name=name, category=category).exists():
                    self.stdout.write(self.style.WARNING(f'  - Skipped: {name} (Already exists)'))
                    continue

                # Handle slug collisions
                counter = 1
                original_slug = p_slug
                while Product.objects.filter(slug=p_slug).exists():
                    p_slug = f'{original_slug}-{counter}'
                    counter += 1

                Product.objects.create(
                    category=category,
                    name=name,
                    slug=p_slug,
                    price=Decimal(price),
                    rating=Decimal(rating),
                    reviews_count=reviews,
                    stock=50,
                    image=f'products/{filename}'
                )
                self.stdout.write(self.style.SUCCESS(f'  - Added: {name}'))

        self.stdout.write(self.style.SUCCESS('Store population complete!'))
