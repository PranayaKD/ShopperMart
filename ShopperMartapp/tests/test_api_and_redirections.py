"""
ShopperMart REST API & Route Integration Tests
Validates all REST API endpoints, JWT/Token authentication, OpenAPI documentation,
and ensures all information/legal pages redirect and render with 200 OK.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ShopperMartapp.models import Category, Product, Cart, CartItem, Order, OrderItem


class PageRedirectionsAndLegalViewsTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_all_legal_and_information_pages_render_200(self):
        """Verify that every legal and information page exists and renders 200 OK without dead links."""
        routes = [
            'privacy', 'terms', 'returns', 'shipping', 'faq',
            'legal', 'legal_privacy', 'legal_terms', 'legal_returns', 'legal_shipping',
            'about', 'contact', 'home', 'public_store', 'cart',
        ]
        for route_name in routes:
            url = reverse(route_name)
            response = self.client.get(url, secure=True)
            self.assertEqual(
                response.status_code, 200,
                f"Expected route '{route_name}' ({url}) to return 200 OK, got {response.status_code}"
            )

    def test_order_success_page_renders_with_session(self):
        """Verify order confirmation page renders cleanly when order session is set."""
        order = Order.objects.create(
            full_name="Rajesh Sharma",
            email="rajesh@example.com",
            address="Plot 42, Green Park",
            city="Bhadrak",
            state="Odisha",
            postal_code="756100",
            total=Decimal("250.00"),
            payment="cod",
            status="processing"
        )
        session = self.client.session
        session['last_order_id'] = str(order.id)
        session.save()

        response = self.client.get(reverse('order_success'), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Order Confirmed")
        self.assertContains(response, "Rajesh Sharma")
        self.assertContains(response, "250.00")


class OpenAPIDocumentationTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_schema_and_swagger_docs_accessible(self):
        """Verify OpenAPI schema, Swagger UI, and ReDoc all render successfully."""
        schema_resp = self.client.get(reverse('schema'))
        self.assertEqual(schema_resp.status_code, 200)

        swagger_resp = self.client.get(reverse('swagger-ui'))
        self.assertEqual(swagger_resp.status_code, 200)

        redoc_resp = self.client.get(reverse('redoc'))
        self.assertEqual(redoc_resp.status_code, 200)


class RestApiEndpointsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='apiuser',
            email='apiuser@example.com',
            password='ComplexPassword123!'
        )
        self.category = Category.objects.create(name='Snacks & Drinks', slug='snacks-drinks')
        self.product = Product.objects.create(
            category=self.category,
            name='Haldiram Bhujia',
            slug='haldiram-bhujia',
            price=Decimal('55.00'),
            stock=25,
            available=True
        )

    def test_auth_registration_and_login(self):
        """Test API registration, login, and profile fetching."""
        # 1. Register new user
        reg_resp = self.client.post('/api/v1/auth/register/', {
            'username': 'newshopper',
            'email': 'newshopper@example.com',
            'password': 'SecurePassWord789!'
        }, content_type='application/json')
        self.assertEqual(reg_resp.status_code, 201)
        self.assertIn('token', reg_resp.json())

        # 2. Login with registered user
        login_resp = self.client.post('/api/v1/auth/login/', {
            'username': 'newshopper',
            'password': 'SecurePassWord789!'
        }, content_type='application/json')
        self.assertEqual(login_resp.status_code, 200)
        token = login_resp.json()['token']

        # 3. Access authenticated me endpoint
        me_resp = self.client.get('/api/v1/auth/me/', HTTP_AUTHORIZATION=f'Token {token}')
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()['username'], 'newshopper')

    def test_jwt_token_obtain_and_refresh(self):
        """Test JWT token obtain endpoint."""
        token_resp = self.client.post('/api/v1/auth/token/', {
            'username': 'apiuser',
            'password': 'ComplexPassword123!'
        }, content_type='application/json')
        self.assertEqual(token_resp.status_code, 200)
        data = token_resp.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)

        # Access /api/v1/auth/me/ with JWT Bearer
        me_resp = self.client.get('/api/v1/auth/me/', HTTP_AUTHORIZATION=f"Bearer {data['access']}")
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()['username'], 'apiuser')

    def test_catalog_api_endpoints(self):
        """Test product and category list/retrieve APIs."""
        cat_resp = self.client.get('/api/v1/categories/')
        self.assertEqual(cat_resp.status_code, 200)
        self.assertTrue(len(cat_resp.json()['results']) >= 1)

        prod_resp = self.client.get('/api/v1/products/')
        self.assertEqual(prod_resp.status_code, 200)
        self.assertTrue(len(prod_resp.json()['results']) >= 1)

    def test_cart_and_atomic_order_creation_api(self):
        """Test complete Cart CRUD and atomic Order placement with stock deduction."""
        # 1. Fetch empty cart
        cart_resp = self.client.get('/api/v1/cart/')
        self.assertEqual(cart_resp.status_code, 200)

        # 2. Add product to cart
        add_resp = self.client.post('/api/v1/cart/add/', {
            'product_id': str(self.product.id),
            'quantity': 3
        }, content_type='application/json')
        self.assertEqual(add_resp.status_code, 200)
        self.assertEqual(add_resp.json()['item_count'], 1)
        item_id = add_resp.json()['items'][0]['id']

        # 3. Update quantity
        update_resp = self.client.post('/api/v1/cart/update/', {
            'item_id': item_id,
            'quantity': 5
        }, content_type='application/json')
        self.assertEqual(update_resp.status_code, 200)
        self.assertEqual(update_resp.json()['items'][0]['quantity'], 5)

        # 4. Atomic Order Placement via API
        initial_stock = self.product.stock
        order_resp = self.client.post('/api/v1/orders/create/', {
            'full_name': 'Amitabh Verma',
            'email': 'amitabh@example.com',
            'address': 'Flat 302, Sunrise Towers',
            'city': 'Bhadrak',
            'state': 'Odisha',
            'postal_code': '756100',
            'payment_method': 'cod'
        }, content_type='application/json')
        self.assertEqual(order_resp.status_code, 201)
        self.assertIn('order', order_resp.json())

        # 5. Verify database stock was atomically deducted
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock - 5)

        # 6. Verify cart was cleared
        post_order_cart = self.client.get('/api/v1/cart/')
        self.assertEqual(post_order_cart.json()['item_count'], 0)


class RazorpayStandardCheckoutIntegrationTest(TestCase):
    """
    Validates Razorpay Standard Web Checkout Integration:
    - POST /api/create-order (creates order via Razorpay API)
    - POST /api/verify-payment (HMAC-SHA256 signature verification)
    - Error handling: minimum amount, signature mismatch, missing parameters
    """
    def setUp(self):
        self.client = Client()

    def test_razorpay_create_order_valid_amount(self):
        """Test creating an order with valid amount >= 100 paise."""
        response = self.client.post('/api/create-order', {
            'amount': 25000,
            'currency': 'INR',
            'receipt': 'rcpt_test_unit'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('order_id', data)
        self.assertEqual(data.get('amount'), 25000)
        self.assertEqual(data.get('currency'), 'INR')
        self.assertEqual(data.get('key_id'), 'rzp_test_TtcFH4iZBKrBHN')

    def test_razorpay_create_order_below_minimum_amount(self):
        """Test creating an order with amount < 100 paise returns 400 error."""
        response = self.client.post('/api/create-order', {
            'amount': 50,
            'currency': 'INR',
        }, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_razorpay_verify_payment_valid_hmac(self):
        """Test payment verification with valid HMAC-SHA256 signature."""
        import hmac
        import hashlib
        from django.conf import settings

        order_id = "order_test_98765"
        payment_id = "pay_test_54321"
        secret = settings.RAZORPAY_KEY_SECRET.encode('utf-8')
        msg = f"{order_id}|{payment_id}".encode('utf-8')
        valid_signature = hmac.new(secret, msg, hashlib.sha256).hexdigest()

        response = self.client.post('/api/verify-payment', {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': valid_signature
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('payment_id'), payment_id)
        self.assertEqual(data.get('order_id'), order_id)

    def test_razorpay_verify_payment_signature_mismatch(self):
        """Test payment verification with forged/mismatched signature returns 400."""
        response = self.client.post('/api/verify-payment', {
            'razorpay_order_id': "order_test_98765",
            'razorpay_payment_id': "pay_test_54321",
            'razorpay_signature': "tampered_fake_signature_hash"
        }, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('error'), "Signature verification failed")

    def test_razorpay_verify_payment_missing_fields(self):
        """Test payment verification with missing required fields returns 400."""
        response = self.client.post('/api/verify-payment', {
            'razorpay_order_id': "order_test_98765"
        }, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data.get('success'))
        self.assertIn('Missing required fields', data.get('error', ''))

