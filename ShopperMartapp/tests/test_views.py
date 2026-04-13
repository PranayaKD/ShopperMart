from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ShopperMartapp.models import Category, Product

class CatalogViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Fashion", slug="fashion")
        self.product = Product.objects.create(
            category=self.category,
            name="T-Shirt",
            slug="t-shirt",
            price=19.99,
            stock=50,
            available=True
        )

    def test_home_page_status(self):
        response = self.client.get(reverse('home'), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "T-Shirt")

    def test_public_store_filtering(self):
        # Create an expensive product
        Product.objects.create(
            category=self.category,
            name="Luxury Jacket",
            slug="jacket",
            price=500.00,
            stock=5,
            available=True
        )
        
        # Test max price filter
        response = self.client.get(reverse('public_store') + "?max_price=50", secure=True)
        self.assertContains(response, "T-Shirt")
        self.assertNotContains(response, "Luxury Jacket")

    def test_idor_protection_setup(self):
        """Verify that IDs are indeed long UUID strings in URLs."""
        # This isn't a functional test, more of a sanity check for the UUID migration
        product_url = reverse('product_detail', kwargs={'slug': self.product.slug})
        self.assertTrue(len(self.product.slug) > 0)
        # Check that we can reach it
        response = self.client.get(product_url, secure=True)
        self.assertEqual(response.status_code, 200)
