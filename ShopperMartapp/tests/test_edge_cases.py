from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Product, Category, Cart, CartItem, Order, Wishlist
import uuid

class EdgeCaseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='password123')
        self.category = Category.objects.create(name='Gear', slug='gear')
        self.product = Product.objects.create(
            category=self.category,
            name='Test Jacket',
            slug='test-jacket',
            price=100.00,
            stock=10
        )
        self.client = Client()

    def test_negative_stock_constraint(self):
        """Edge Case #1: DB level constraint should prevent negative stock."""
        from django.db import IntegrityError
        # Try to force a negative stock via raw or bypass logic
        with self.assertRaises(IntegrityError):
            self.product.stock = -5
            self.product.save()

    def test_cart_quantity_overflow(self):
        """Edge Case #4: Cart should cap quantity at 50 even if stock is 1000."""
        self.product.stock = 1000
        self.product.save()
        
        # Try adding 60 items
        response = self.client.post(reverse('add_to_cart', kwargs={'product_id': self.product.id}), {'quantity': 60})
        cart = Cart.objects.first()
        # Should be redirected to cart with error or capped
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 0) # Should have failed entirely with error message

    def test_idor_order_access(self):
        """Edge Case #6: User B should not be able to view User A's order."""
        order = Order.objects.create(
            user=self.user,
            full_name='User A',
            total=100,
            status='pending'
        )
        user_b = User.objects.create_user(username='userb', password='password123')
        login_success = self.client.login(username='userb', password='password123')
        self.assertTrue(login_success)
        
        # Use follow=True to see if it redirects to login or 404s as expected
        response = self.client.get(reverse('order_detail', kwargs={'order_id': order.id}), follow=True)
        # Should be a 404 because the order-user filter fails
        self.assertEqual(response.status_code, 404)

    def test_illegal_status_transition(self):
        """Edge Case #3: Cannot transition from Delivered to Cancelled."""
        order = Order.objects.create(
            user=self.user,
            full_name='Test',
            total=100,
            status='delivered'
        )
        with self.assertRaises(ValueError):
            order.change_status('cancelled')

    def test_soft_delete_preservation(self):
        """Edge Case #18: Orders should still reference products even after soft delete."""
        order = Order.objects.create(user=self.user, full_name='T', total=100)
        from ..models import OrderItem
        OrderItem.objects.create(order=order, product=self.product, quantity=1, price=100)
        
        # Soft delete
        self.product.is_deleted = True
        self.product.save()
        
        # Order should still see it
        self.assertEqual(order.items.first().product, self.product)
        
        # But catalog should NOT
        self.assertFalse(Product.objects.available().filter(id=self.product.id).exists())
