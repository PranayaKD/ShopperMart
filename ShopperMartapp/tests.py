"""
ShopperMart — Comprehensive Test Suite
=======================================
Covers: Models, Signals, Cart Logic, Order Pipeline, View Security, and Forms.
Run with: python manage.py test ShopperMartapp -v 2
"""

from decimal import Decimal
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse

from .models import Profile, Category, Product, Cart, CartItem, Order, OrderItem


# ─────────────────────────────────────────────────────────────
#  1. SIGNAL TESTS — Profile auto-creation on User signup
# ─────────────────────────────────────────────────────────────
class ProfileSignalTest(TestCase):
    """Verify that the post_save signal creates a Profile automatically."""

    def test_profile_created_on_user_registration(self):
        user = User.objects.create_user(username="testuser", password="Test@1234")
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_profile_str_representation(self):
        user = User.objects.create_user(username="jane", password="Test@1234")
        self.assertEqual(str(user.profile), "Profile of jane")

    def test_profile_address_fields_persist(self):
        user = User.objects.create_user(username="addr_user", password="Test@1234")
        profile = user.profile
        profile.full_name = "Pranaya Kumar Dash"
        profile.city = "Bhubaneswar"
        profile.state = "Odisha"
        profile.pincode = "751024"
        profile.address_line1 = "123 Main Street"
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.city, "Bhubaneswar")
        self.assertEqual(profile.pincode, "751024")
        self.assertEqual(profile.address_line1, "123 Main Street")


# ─────────────────────────────────────────────────────────────
#  2. PRODUCT & CATEGORY MODEL TESTS
# ─────────────────────────────────────────────────────────────
class ProductModelTest(TestCase):
    """Verify product and category model behavior."""

    def setUp(self):
        self.category = Category.objects.create(name="Electronics", slug="electronics")
        self.product = Product.objects.create(
            category=self.category,
            name="Laptop Pro",
            slug="laptop-pro",
            description="High performance laptop",
            price=Decimal("79999.99"),
            stock=10,
            available=True,
        )

    def test_category_str(self):
        self.assertEqual(str(self.category), "Electronics")

    def test_product_str(self):
        self.assertEqual(str(self.product), "Laptop Pro")

    def test_product_default_rating(self):
        self.assertEqual(self.product.rating, Decimal("4.5"))

    def test_product_availability_flag(self):
        self.assertTrue(self.product.available)
        self.product.available = False
        self.product.save()
        self.product.refresh_from_db()
        self.assertFalse(self.product.available)


# ─────────────────────────────────────────────────────────────
#  3. CART LOGIC TESTS — Total calculation, quantities
# ─────────────────────────────────────────────────────────────
class CartLogicTest(TestCase):
    """Validate cart total price calculations and item management."""

    def setUp(self):
        self.user = User.objects.create_user(username="shopper", password="Test@1234")
        self.category = Category.objects.create(name="Clothing", slug="clothing")
        self.product_a = Product.objects.create(
            category=self.category, name="T-Shirt", slug="t-shirt",
            price=Decimal("999.00"), stock=50, available=True,
        )
        self.product_b = Product.objects.create(
            category=self.category, name="Jeans", slug="jeans",
            price=Decimal("2499.00"), stock=30, available=True,
        )
        self.cart = Cart.objects.create(user=self.user)

    def test_empty_cart_total_is_zero(self):
        self.assertEqual(self.cart.total_price(), 0)

    def test_single_item_subtotal(self):
        item = CartItem.objects.create(cart=self.cart, product=self.product_a, quantity=3)
        self.assertEqual(item.subtotal, Decimal("2997.00"))

    def test_cart_total_with_multiple_items(self):
        CartItem.objects.create(cart=self.cart, product=self.product_a, quantity=2)  # 1998
        CartItem.objects.create(cart=self.cart, product=self.product_b, quantity=1)  # 2499
        self.assertEqual(self.cart.total_price(), Decimal("4497.00"))

    def test_cart_str_authenticated_user(self):
        self.assertEqual(str(self.cart), "Cart of shopper")

    def test_cart_str_guest(self):
        guest_cart = Cart.objects.create(session_key="abc123guest")
        self.assertEqual(str(guest_cart), "Guest Cart (abc123guest)")

    def test_cart_item_quantity_update(self):
        item = CartItem.objects.create(cart=self.cart, product=self.product_a, quantity=1)
        item.quantity = 5
        item.save()
        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)
        self.assertEqual(item.subtotal, Decimal("4995.00"))


# ─────────────────────────────────────────────────────────────
#  4. ORDER PIPELINE TESTS — Creation, status, financials
# ─────────────────────────────────────────────────────────────
class OrderPipelineTest(TestCase):
    """Test order creation, status transitions, and financial accuracy."""

    def setUp(self):
        self.user = User.objects.create_user(username="buyer", password="Test@1234")
        self.category = Category.objects.create(name="Gadgets", slug="gadgets")
        self.product = Product.objects.create(
            category=self.category, name="Smartwatch", slug="smartwatch",
            price=Decimal("4999.00"), stock=20, available=True,
        )

    def test_order_creation(self):
        order = Order.objects.create(
            user=self.user, full_name="Buyer Name", email="buyer@test.com",
            address="123 Test Lane", city="Mumbai", postal_code="400001",
            payment="card", total=Decimal("4999.00"),
        )
        self.assertEqual(order.status, "pending")
        self.assertEqual(str(order), f"Order #{order.id} - Buyer Name")

    def test_order_item_total_calculation(self):
        order = Order.objects.create(
            user=self.user, full_name="Buyer", email="b@test.com",
            address="Test Addr", city="Delhi", postal_code="110001",
            payment="upi", total=Decimal("14997.00"),
        )
        item = OrderItem.objects.create(
            order=order, product=self.product, quantity=3, price=Decimal("4999.00")
        )
        self.assertEqual(item.get_total(), Decimal("14997.00"))

    def test_order_status_transitions(self):
        order = Order.objects.create(
            user=self.user, full_name="Trans Test", email="t@test.com",
            address="Addr", city="Pune", postal_code="411001",
            payment="cod", total=Decimal("4999.00"),
        )
        for status in ["paid", "shipped", "delivered"]:
            order.status = status
            order.save()
            order.refresh_from_db()
            self.assertEqual(order.status, status)

    def test_order_cancellation_restores_stock(self):
        """Simulate the cancel_order view logic at the model level."""
        original_stock = self.product.stock
        order = Order.objects.create(
            user=self.user, full_name="Cancel Test", email="c@test.com",
            address="Addr", city="Chennai", postal_code="600001",
            payment="card", total=Decimal("9998.00"),
        )
        OrderItem.objects.create(
            order=order, product=self.product, quantity=2, price=Decimal("4999.00")
        )
        # Simulate stock deduction during checkout
        self.product.stock -= 2
        self.product.save()
        self.assertEqual(self.product.stock, original_stock - 2)

        # Simulate cancellation stock restoration
        for item in order.items.all():
            if item.product:
                item.product.stock += item.quantity
                item.product.save()
        order.status = "cancelled"
        order.save()

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, original_stock)
        self.assertEqual(order.status, "cancelled")


# ─────────────────────────────────────────────────────────────
#  5. VIEW SECURITY TESTS — Auth gates & staff protection
# ─────────────────────────────────────────────────────────────
class ViewSecurityTest(TestCase):
    """Ensure authentication and authorization gates are enforced."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="regular", password="Test@1234")
        self.staff = User.objects.create_user(username="admin_staff", password="Test@1234", is_staff=True)
        self.category = Category.objects.create(name="Books", slug="books")
        self.product = Product.objects.create(
            category=self.category, name="Django Book", slug="django-book",
            price=Decimal("599.00"), stock=100, available=True,
        )

    # --- Public pages should be accessible without login ---
    def test_home_page_accessible_without_login(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_store_page_accessible_without_login(self):
        response = self.client.get(reverse("public_store"))
        self.assertEqual(response.status_code, 200)

    def test_product_detail_accessible_without_login(self):
        response = self.client.get(reverse("product_detail", kwargs={"slug": "django-book"}))
        self.assertEqual(response.status_code, 200)

    def test_category_page_accessible_without_login(self):
        response = self.client.get(reverse("category_products", kwargs={"slug": "books"}))
        self.assertEqual(response.status_code, 200)

    # --- Login-required pages should redirect anonymous users ---
    def test_profile_requires_login(self):
        response = self.client.get(reverse("profile"))
        self.assertNotEqual(response.status_code, 200)

    def test_my_orders_requires_login(self):
        response = self.client.get(reverse("my_orders"))
        self.assertNotEqual(response.status_code, 200)

    # --- Staff-only pages should block non-staff ---
    def test_product_management_blocked_for_regular_user(self):
        self.client.login(username="regular", password="Test@1234")
        response = self.client.get(reverse("product_list"))
        self.assertNotEqual(response.status_code, 200)

    def test_product_management_allowed_for_staff(self):
        self.client.login(username="admin_staff", password="Test@1234")
        response = self.client.get(reverse("product_list"))
        self.assertEqual(response.status_code, 200)

    def test_product_delete_blocked_for_non_staff(self):
        self.client.login(username="regular", password="Test@1234")
        response = self.client.get(reverse("product_delete", kwargs={"pk": self.product.pk}))
        self.assertNotEqual(response.status_code, 200)

    def test_product_update_allowed_for_staff(self):
        self.client.login(username="admin_staff", password="Test@1234")
        response = self.client.get(reverse("product_update", kwargs={"pk": self.product.pk}))
        self.assertEqual(response.status_code, 200)


# ─────────────────────────────────────────────────────────────
#  6. CART VIEW INTEGRATION TESTS — Add to cart via POST
# ─────────────────────────────────────────────────────────────
class CartViewTest(TestCase):
    """Test cart views for both authenticated and guest users."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="cartuser", password="Test@1234")
        self.category = Category.objects.create(name="Sports", slug="sports")
        self.product = Product.objects.create(
            category=self.category, name="Football", slug="football",
            price=Decimal("1299.00"), stock=25, available=True,
        )

    def test_add_to_cart_authenticated(self):
        self.client.login(username="cartuser", password="Test@1234")
        response = self.client.post(reverse("add_to_cart", kwargs={"product_id": self.product.id}))
        self.assertEqual(response.status_code, 302)  # Redirect to cart
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().product, self.product)

    def test_add_to_cart_guest(self):
        response = self.client.post(reverse("add_to_cart", kwargs={"product_id": self.product.id}))
        self.assertEqual(response.status_code, 302)
        # Guest cart created with session key
        self.assertTrue(Cart.objects.filter(user=None).exists())

    def test_cart_page_renders(self):
        self.client.login(username="cartuser", password="Test@1234")
        response = self.client.get(reverse("cart"))
        self.assertEqual(response.status_code, 200)

    def test_remove_from_cart(self):
        self.client.login(username="cartuser", password="Test@1234")
        cart = Cart.objects.create(user=self.user)
        item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        response = self.client.post(reverse("remove_from_cart", kwargs={"item_id": item.id}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(cart.items.count(), 0)


# ─────────────────────────────────────────────────────────────
#  7. CHECKOUT INTEGRATION TEST — Full order flow
# ─────────────────────────────────────────────────────────────
class CheckoutFlowTest(TestCase):
    """End-to-end checkout: cart → order → stock deduction."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="checkout_user", password="Test@1234")
        self.category = Category.objects.create(name="Home", slug="home-goods")
        self.product = Product.objects.create(
            category=self.category, name="Table Lamp", slug="table-lamp",
            price=Decimal("1599.00"), stock=10, available=True,
        )

    def test_successful_checkout_creates_order(self):
        self.client.login(username="checkout_user", password="Test@1234")
        # Add item to cart
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.post(reverse("checkout"), {
            "full_name": "Test Buyer",
            "email": "buyer@example.com",
            "address": "456 Test Avenue",
            "city": "Bangalore",
            "postal_code": "560001",
            "payment_method": "upi",
        })
        self.assertEqual(response.status_code, 302)  # Redirect to success

        # Order should exist
        order = Order.objects.filter(user=self.user).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.total, Decimal("3198.00"))
        self.assertEqual(order.status, "pending")

        # Stock should be decremented
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

        # Cart should be empty
        self.assertEqual(cart.items.count(), 0)

    def test_checkout_with_empty_cart_redirects(self):
        self.client.login(username="checkout_user", password="Test@1234")
        Cart.objects.create(user=self.user)
        response = self.client.post(reverse("checkout"), {
            "full_name": "Empty Cart", "email": "e@t.com",
            "address": "Addr", "city": "City", "postal_code": "000000",
            "payment_method": "cod",
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Order.objects.filter(user=self.user).exists())


# ─────────────────────────────────────────────────────────────
#  8. FORM VALIDATION TESTS
# ─────────────────────────────────────────────────────────────
class FormValidationTest(TestCase):
    """Test custom form validation rules."""

    def test_registration_rejects_duplicate_email(self):
        from .forms import UserRegistrationForm
        User.objects.create_user(username="existing", email="taken@test.com", password="Test@1234")
        form = UserRegistrationForm(data={
            "username": "newuser",
            "email": "taken@test.com",
            "password1": "Secure@123",
            "password2": "Secure@123",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_checkout_form_valid(self):
        from .forms import CheckoutForm
        form = CheckoutForm(data={
            "full_name": "Valid Buyer",
            "email": "valid@buyer.com",
            "address": "123 Valid Street",
            "city": "ValidCity",
            "postal_code": "123456",
            "payment_method": "card",
        })
        self.assertTrue(form.is_valid())

    def test_checkout_form_missing_required_fields(self):
        from .forms import CheckoutForm
        form = CheckoutForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("full_name", form.errors)
        self.assertIn("email", form.errors)
