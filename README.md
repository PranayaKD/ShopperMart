# ShopperMart - Modular E-Commerce & Inventory Management System

[![Django](https://img.shields.io/badge/Django-5.2+-092e20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.16+-a30000?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Razorpay](https://img.shields.io/badge/Payments-Razorpay-0c2340?style=for-the-badge&logo=razorpay&logoColor=white)](https://razorpay.com/)
[![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

🔗 **Live Demo**: [https://shoppermart-hiem.onrender.com](https://shoppermart-hiem.onrender.com) | 📂 **GitHub**: [https://github.com/PranayaKD/ShopperMart](https://github.com/PranayaKD/ShopperMart)

## 1. Project Overview
ShopperMart is a full-featured e-commerce platform and inventory management system built with Django and Django REST Framework. The application provides an end-to-end commerce workflow featuring guest and authenticated shopping cart sessions, atomic order checkout transactions, Razorpay payment processing with cryptographic verification, automated lifecycle order state machines with audit logging, and role-based administration dashboards for inventory and review moderation.

## 2. Tech Stack
- Python 3.11 / 3.13
- Django 5.2.12
- Django REST Framework (DRF)
- PostgreSQL (via psycopg2-binary and dj-database-url)
- Razorpay Python SDK
- Django-Allauth (Google OAuth 2.0)
- Django-Filter (API query filtering)
- Django-Ratelimit (Brute-force protection on authentication endpoints)
- Django-CSP (Content Security Policy security headers)
- WhiteNoise (Compressed static asset serving)
- Gunicorn (WSGI HTTP server)
- Python-Decouple (Environment variable management)
- Bootstrap 5 & Custom CSS (Responsive frontend interface)

## 3. Architecture
The project follows a decoupled domain architecture separating presentation views, administrative panels, and REST API controllers:

```
ShopperMart/
├── manage.py                   # Django management script
├── Procfile                    # Web service process configuration
├── build.sh                    # Production deployment build script
├── render.yaml                 # Infrastructure as Code configuration for Render
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── ShopperMart/                # Core Django project root
│   ├── settings.py             # Security, DB, auth, and REST configuration
│   ├── urls.py                 # Root URL router and media routing
│   ├── wsgi.py                 # WSGI application entry point
│   └── asgi.py                 # ASGI application entry point
├── ShopperMartapp/             # Primary commerce domain application
│   ├── models.py               # UUID-backed domain models with database constraints
│   ├── forms.py                # Checkout, profile, review, and inventory forms
│   ├── middleware.py           # Pre-login session cart migration middleware
│   ├── context_processors.py   # Cart counts, wishlist IDs, and category processors
│   ├── urls.py                 # Web application view endpoints
│   ├── api_urls.py             # DRF router and endpoint registrations
│   ├── api_views.py            # DRF ViewSets with filtering, throttling, and pagination
│   └── views/                  # Domain-specific web view controllers
│       ├── catalog.py          # Product catalog, category listings, reviews, and search
│       ├── cart.py             # Guest and authenticated cart item operations
│       ├── orders.py           # Checkout transactions and Razorpay callbacks
│       ├── account.py          # User registration, profile, and order history
│       └── administrator.py    # Custom dashboard for inventory, orders, and reviews
├── templates/                  # Server-side HTML templates (Auth, Cart, Orders, Admin)
└── static/                     # CSS stylesheets, JavaScript helpers, and icons
```

## 4. Features
- **UUID-Backed Domain Modeling**: All entity primary keys use UUIDv4 to eliminate insecure direct object reference (IDOR) vulnerabilities and numeric enumeration.
- **Atomic Checkout Engine**: Checkout processing wrapped in `transaction.atomic()` with checkout token idempotency, price-lock validation, and live inventory verification.
- **Guest-to-User Cart Migration**: Anonymous session carts are tracked and automatically merged into the user's persistent cart upon authentication via `PreLoginSessionMiddleware`.
- **Integrated Razorpay Payments**: Server-side order creation and client-side modal integration with HMAC-SHA256 signature verification.
- **Order State Machine with Audit Trail**: Formal order status progression (`pending` → `processing` → `shipped` → `out_for_delivery` → `delivered`) with immutable `OrderStatusLog` records.
- **RESTful Commerce API**: ViewSets for categories, products, orders, cart, and wishlist with token authentication, pagination, search filters, and throttling.
- **Brute-Force & Rate Limiting**: IP-based rate limiting on login routes (`5 requests/minute`) via `django-ratelimit`.
- **Administrative Operations Hub**: Dedicated management interface for product upserts, soft-deletions, order fulfillment, and customer review moderation.
- **Customer Wishlist & Reviews**: Multi-item product favoriting and gated customer reviews requiring administrator approval.

## 5. Database Design
- **Profile** (`ShopperMartapp.models.Profile`)
  - `id`: UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  - `user`: OneToOneField(`auth.User`, on_delete=CASCADE, related_name='profile')
  - `full_name`: CharField(max_length=150, blank=True)
  - `phone`: CharField(max_length=20, blank=True)
  - `avatar`: ImageField(upload_to='avatars/', null=True, blank=True)
  - `address_line1`: CharField(max_length=255, blank=True)
  - `address_line2`: CharField(max_length=255, blank=True)
  - `landmark`: CharField(max_length=255, blank=True)
  - `city`: CharField(max_length=80, blank=True)
  - `state`: CharField(max_length=80, blank=True)
  - `pincode`: CharField(max_length=10, blank=True)
  - `created_at`: DateTimeField(auto_now_add=True)

- **Category** (`ShopperMartapp.models.Category`)
  - `id`: UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  - `name`: CharField(max_length=100)
  - `slug`: SlugField(unique=True)

- **Product** (`ShopperMartapp.models.Product`)
  - `id`: UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  - `category`: ForeignKey(`Category`, on_delete=CASCADE, related_name='products')
  - `name`: CharField(max_length=200)
  - `slug`: SlugField(unique=True)
  - `description`: TextField(blank=True)
  - `price`: DecimalField(max_digits=10, decimal_places=2)
  - `stock`: PositiveIntegerField(default=0)
  - `available`: BooleanField(default=True)
  - `rating`: DecimalField(max_digits=3, decimal_places=1, default=4.5)
  - `reviews_count`: PositiveIntegerField(default=120)
  - `image`: ImageField(upload_to='products/', null=True, blank=True)
  - `is_deleted`: BooleanField(default=False)
  - `created_at`: DateTimeField(auto_now_add=True)
  - `updated_at`: DateTimeField(auto_now=True)
  - Constraints: `stock >= 0`, `price >= 0`

- **Review** (`ShopperMartapp.models.Review`)
  - `id`: UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  - `product`: ForeignKey(`Product`, on_delete=CASCADE, related_name='reviews')
  - `user`: ForeignKey(`auth.User`, on_delete=CASCADE, related_name='reviews')
  - `rating`: PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
  - `comment`: TextField(max_length=1000)
  - `is_approved`: BooleanField(default=False)
  - `created_at`: DateTimeField(auto_now_add=True)
  - Constraint: Unique `(product, user)`

- **Cart** (`ShopperMartapp.models.Cart`)
  - `id`: UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  - `user`: OneToOneField(`auth.User`, on_delete=CASCADE, null=True, blank=True, related_name='cart')
  - `session_key`: CharField(max_length=100, null=True, blank=True, unique=True)
  - `created_at`: DateTimeField(auto_now_add=True)

- **CartItem** (`ShopperMartapp.models.CartItem`)
  - `id`: UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  - `cart`: ForeignKey(`Cart`, on_delete=CASCADE, related_name='items')
  - `product`: ForeignKey(`Product`, on_delete=CASCADE)
  - `quantity`: PositiveIntegerField(default=1)
  - Constraints: `quantity > 0`, `quantity <= 100`

- **Order** (`ShopperMartapp.models.Order`)
  - `id`: UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  - `user`: ForeignKey(`auth.User`, on_delete=SET_NULL, null=True, blank=True)
  - `full_name`: CharField(max_length=200)
  - `email`: EmailField()
  - `address`: TextField()
  - `landmark`: CharField(max_length=255, blank=True)
  - `city`: CharField(max_length=100)
  - `state`: CharField(max_length=100, blank=True)
  - `postal_code`: CharField(max_length=20)
  - `payment`: CharField(max_length=50)
  - `total`: DecimalField(max_digits=10, decimal_places=2)
  - `status`: CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
  - `created_at`: DateTimeField(auto_now_add=True)

- **OrderItem** (`ShopperMartapp.models.OrderItem`)
  - `id`: UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  - `order`: ForeignKey(`Order`, on_delete=CASCADE, related_name='items')
  - `product`: ForeignKey(`Product`, on_delete=SET_NULL, null=True)
  - `quantity`: PositiveIntegerField()
  - `price`: DecimalField(max_digits=10, decimal_places=2)
  - Constraint: `quantity > 0`

- **OrderStatusLog** (`ShopperMartapp.models.OrderStatusLog`)
  - `id`: UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  - `order`: ForeignKey(`Order`, on_delete=CASCADE, related_name='status_logs')
  - `old_status`: CharField(max_length=20, blank=True)
  - `new_status`: CharField(max_length=20)
  - `changed_by`: ForeignKey(`auth.User`, on_delete=SET_NULL, null=True, blank=True)
  - `note`: TextField(blank=True)
  - `created_at`: DateTimeField(auto_now_add=True)

- **Wishlist** (`ShopperMartapp.models.Wishlist`)
  - `id`: UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  - `user`: OneToOneField(`auth.User`, on_delete=CASCADE, related_name='wishlist')
  - `products`: ManyToManyField(`Product`, related_name='wishlisted_by', blank=True)
  - `created_at`: DateTimeField(auto_now_add=True)
  - `updated_at`: DateTimeField(auto_now=True)

## 6. API Endpoints
- POST /api/v1/auth/register/ — Register a new customer account via API — auth required: no
- POST /api/v1/auth/login/ — Obtain DRF auth token for API authentication — auth required: no
- GET /api/v1/cart/ — Retrieve current user/guest shopping cart — auth required: no
- POST /api/v1/cart/add/ — Add an item to shopping cart — auth required: no
- GET, POST /api/v1/categories/ — List categories or create category — auth required: no (GET) / yes (POST)
- GET, PUT, PATCH, DELETE /api/v1/categories/<id>/ — Category detail, update, delete — auth required: no (GET) / yes (write)
- GET, POST /api/v1/products/ — List filtered products or create product — auth required: no (GET) / yes (POST)
- GET, PUT, PATCH, DELETE /api/v1/products/<id>/ — Product detail, update, soft delete — auth required: no (GET) / yes (write)
- GET, POST /api/v1/orders/ — List authenticated user's orders or create order — auth required: yes
- GET, PUT, PATCH /api/v1/orders/<id>/ — Order detail and lifecycle management — auth required: yes
- GET, POST /api/v1/wishlist/ — View customer wishlist or add item — auth required: yes
- DELETE /api/v1/wishlist/<id>/ — Remove item from wishlist — auth required: yes
- GET / — Home storefront with featured products and hero carousel — auth required: no
- GET /store/ — Full product catalog with sorting and search filters — auth required: no
- GET /category/<slug>/ — Products filtered by category slug — auth required: no
- GET /product/<pk>/ — Product detail accessed by UUID — auth required: no
- GET /product/<slug>/ — Product detail accessed by SEO slug — auth required: no
- GET, POST /register/ — Customer registration page — auth required: no
- GET, POST /login/ — Customer login page (rate-limited to 5/min per IP) — auth required: no
- POST /logout/ — User session termination — auth required: yes
- GET /profile/ — User profile view — auth required: yes
- GET, POST /profile/edit/ — Edit user profile and delivery address — auth required: yes
- GET /cart/ — Shopping cart view — auth required: no
- POST /cart/add/<product_id>/ — Add product to cart — auth required: no
- POST /cart/remove/<item_id>/ — Remove item from cart — auth required: no
- POST /cart/update/<item_id>/ — Update cart item quantity — auth required: no
- GET, POST /checkout/ — Checkout summary, validation, and Razorpay initiation — auth required: no
- POST /payment/callback/ — Razorpay payment verification callback — auth required: no
- GET /order-success/ — Post-checkout confirmation page — auth required: no
- GET /my-orders/ — Authenticated user order history — auth required: yes
- GET /orders/<order_id>/ — Detailed order view with status progress bar — auth required: yes
- POST /orders/<order_id>/cancel/ — Cancel pending/processing order — auth required: yes
- POST /product/<product_id>/review/ — Submit customer product review — auth required: yes
- GET /wishlist/ — Saved items wishlist page — auth required: yes
- POST /wishlist/toggle/<product_id>/ — Toggle item in wishlist — auth required: yes
- GET /about/ — About page — auth required: no
- GET /contact/ — Contact page — auth required: no
- GET /dashboard/ — Admin operational dashboard with analytics — auth required: yes (staff)
- GET /dashboard/inventory/ — Admin inventory management table — auth required: yes (staff)
- GET, POST /dashboard/inventory/new/ — Admin product creation form — auth required: yes (staff)
- GET, POST /dashboard/inventory/<pk>/edit/ — Admin product editor — auth required: yes (staff)
- POST /dashboard/inventory/<pk>/delete/ — Admin product soft deletion — auth required: yes (staff)
- GET /dashboard/orders/ — Admin order fulfillment table — auth required: yes (staff)
- GET, POST /dashboard/orders/<order_id>/ — Admin order detail and status transitions — auth required: yes (staff)
- GET, POST /dashboard/moderation/ — Admin customer review approval queue — auth required: yes (staff)

## 7. Authentication
ShopperMart implements a hybrid authentication architecture:
1. **Django REST Framework Token Authentication**: Used for programmatic API clients on `/api/v1/*`. Clients exchange credentials at `/api/v1/auth/login/` for an authentication token provided in HTTP `Authorization: Token <key>` headers.
2. **Google OAuth 2.0**: Configured via `django-allauth` to allow one-click single sign-on.
3. **Session Authentication with IP Rate Limiting**: Standard web authentication decorated with `@ratelimit(key='ip', rate='5/m', block=True)` on the login view to prevent brute-force credential stuffing.

## 8. Key Engineering Decisions
- **UUID Primary Keys Across All Models**:
  - *Problem*: Sequential auto-incrementing IDs expose total order volume, customer counts, and allow attackers to iterate across order details via IDOR attacks.
  - *Implementation*: Configured `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)` on `Profile`, `Category`, `Product`, `Review`, `Cart`, `CartItem`, `Order`, `OrderItem`, `OrderStatusLog`, and `Wishlist`.
  - *Rationale*: Eliminates ID enumeration risks and decouples entity identity from database sequence generation.
- **Database-Level Data Integrity Constraints**:
  - *Problem*: Relying solely on application-layer form validation allows negative inventory stock or pricing corruption during race conditions.
  - *Implementation*: Added SQL `CheckConstraint` definitions on `Product` (`stock >= 0`, `price >= 0`), `CartItem` (`quantity > 0`, `quantity <= 100`), and `OrderItem` (`quantity > 0`).
  - *Rationale*: Enforces invariants at the database engine level regardless of whether updates originate from views, APIs, or background workers.
- **Idempotent Atomic Checkout with Pre-Transaction Price Locks**:
  - *Problem*: Double-clicking checkout or price fluctuations during session browsing can lead to double billing or incorrect charge amounts.
  - *Implementation*: Wrapped `checkout()` inside `@transaction.atomic`. The view enforces a single-use `checkout_token` in session and validates that client-posted total matches server-calculated subtotal before creating `Order` and `OrderItem` rows.
  - *Rationale*: Guarantees all-or-nothing database transactions and prevents duplicate orders.
- **Pre-Login Cart Migration Middleware**:
  - *Problem*: Guest shoppers who build a shopping cart lose their selected items upon logging in.
  - *Implementation*: Created `PreLoginSessionMiddleware` which captures the anonymous session key before login and calls `Cart.merge_with()` to transfer cart items to the newly authenticated user's cart.
  - *Rationale*: Eliminates cart abandonment and creates a seamless guest-to-buyer conversion funnel.
- **Audit-Trail Event Sourcing for Order Fulfillment**:
  - *Problem*: Modifying order statuses in-place lacks traceability regarding who performed the change, when it occurred, or why.
  - *Implementation*: `Order.change_status()` updates the order and creates an immutable `OrderStatusLog` entry capturing `old_status`, `new_status`, `changed_by`, and audit notes.
  - *Rationale*: Provides a complete compliance audit trail for dispute resolution and order tracking.

## 9. Environment Variables
- `SECRET_KEY`: Django secret key for cryptographic signing and sessions.
- `DEBUG`: Boolean flag controlling development debug mode.
- `ALLOWED_HOSTS`: Comma-separated list of valid hostnames.
- `DATABASE_URL`: PostgreSQL database connection URL (falls back to `sqlite:///db.sqlite3` in local development).
- `RAZORPAY_KEY_ID`: Razorpay public API key ID.
- `RAZORPAY_KEY_SECRET`: Razorpay private API secret key.
- `GOOGLE_CLIENT_ID`: Google OAuth 2.0 Client ID for allauth.
- `GOOGLE_CLIENT_SECRET`: Google OAuth 2.0 Client Secret for allauth.
- `SECURE_SSL_REDIRECT`: Boolean flag to enforce SSL redirection in production.

## 10. Local Setup Instructions
Follow these steps to run ShopperMart locally:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/PranayaKD/ShopperMart.git
   cd ShopperMart
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   Set a `SECRET_KEY` and development flags in `.env`.

5. **Apply database migrations**:
   ```bash
   python manage.py migrate
   ```

6. **Create an administrator superuser**:
   ```bash
   python manage.py createsuperuser
   ```

7. **Start the development server**:
   ```bash
   python manage.py runserver
   ```
   Access the store at `http://127.0.0.1:8000/`.
