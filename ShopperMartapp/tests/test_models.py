import uuid
from django.test import TestCase
from django.contrib.auth.models import User
from ShopperMartapp.models import Category, Product, Wishlist

class ModelIntegrityTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.category = Category.objects.create(name="Electronics", slug="electronics")
        self.product = Product.objects.create(
            category=self.category,
            name="Laptop",
            slug="laptop",
            price=999.99,
            stock=10
        )

    def test_uuid_primary_keys(self):
        """Verify that models are using UUIDs instead of integers."""
        self.assertIsInstance(self.product.id, uuid.UUID)
        self.assertIsInstance(self.category.id, uuid.UUID)

    def test_product_manager_available(self):
        """Verify the custom manager correctly filters available products."""
        self.product.available = False
        self.product.save()
        self.assertEqual(Product.objects.available().count(), 0)

    def test_wishlist_optimization(self):
        """Verify the wishlist helper returns correct IDs."""
        wishlist, _ = Wishlist.objects.get_or_create(user=self.user)
        wishlist.products.add(self.product)
        
        wishlisted_ids = Wishlist.get_product_ids_for_user(self.user)
        self.assertIn(self.product.id, wishlisted_ids)
        self.assertEqual(len(wishlisted_ids), 1)
