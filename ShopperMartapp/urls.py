from django.urls import path
from django.contrib.auth import views as auth_views
from django_ratelimit.decorators import ratelimit
from django.views.generic import TemplateView
from .views import catalog, cart, orders, account, administrator, location

urlpatterns = [
    # Location
    path("api/location/", location.delivery_location, name="delivery_location"),
    path("api/set-location/", location.delivery_location, name="set_delivery_location"),

    # Search Suggestions API
    path("api/search/suggestions/", catalog.search_suggestions, name="search_suggestions"),

    # Home / Shop
    path("", catalog.shop_home, name="home"),
    path("store/", catalog.public_store, name="public_store"),

    # Categories & Products
    path("category/<slug:slug>/", catalog.category_products, name="category_products"),
    path("product/<uuid:pk>/", catalog.product_detail_by_id, name="product_detail_by_id"),
    path("product/<slug:slug>/", catalog.product_detail, name="product_detail"),

    # Auth
    path("register/", account.register_view, name="register"),
    path("signup/", account.register_view, name="signup"),  
    path("login/", ratelimit(key='ip', rate='5/m', block=True)(auth_views.LoginView.as_view(template_name="registration/login.html")), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("auth/google/", account.google_login_dispatcher, name="google_login_dispatcher"),

    # Profile
    path("profile/", account.profile_view, name="profile"),
    path("profile/edit/", account.profile_edit_view, name="profile_edit"),

    # Cart
    path("api/cart/add/", cart.api_add_to_cart, name="api_add_to_cart"),
    path("api/cart/data/", cart.api_get_cart, name="api_get_cart"),
    path("api/cart/update-quantity/", cart.api_update_cart_quantity, name="api_update_cart_quantity"),
    path("api/cart/apply-coupon/", cart.api_apply_coupon_ajax, name="api_apply_coupon_ajax"),
    path("cart/", cart.cart_view, name="cart"),
    path("cart/coupon/", cart.apply_coupon, name="apply_coupon"),
    path("cart/add/<uuid:product_id>/", cart.add_to_cart, name="add_to_cart"),
    path("cart/remove/<uuid:item_id>/", cart.remove_from_cart, name="remove_from_cart"),
    path("cart/update/<uuid:item_id>/", cart.update_cart, name="update_cart"),

    # Checkout & Orders
    path("checkout/", orders.checkout, name="checkout"),
    path("payment/callback/", orders.payment_callback, name="payment_callback"),
    path("payment/webhook/", orders.razorpay_webhook, name="razorpay_webhook"),
    path("order-success/", orders.order_success, name="order_success"),
    path("my-orders/", orders.my_orders, name="my_orders"),
    path("orders/<uuid:order_id>/", orders.order_detail, name="order_detail"),
    path("orders/<uuid:order_id>/cancel/", orders.cancel_order, name="cancel_order"),

    # Reviews
    path("product/<uuid:product_id>/review/", catalog.submit_review, name="submit_review"),
    
    # Wishlist
    path("wishlist/", catalog.wishlist_view, name="wishlist"),
    path("wishlist/toggle/<uuid:product_id>/", catalog.toggle_wishlist, name="toggle_wishlist"),

    # Brand & Information Pages
    path("about/", catalog.about_view, name="about"),
    path("contact/", catalog.contact_view, name="contact"),
    path("faq/", catalog.faq_view, name="faq"),
    path("privacy/", catalog.privacy_view, name="privacy"),
    path("terms/", catalog.terms_view, name="terms"),
    path("returns/", catalog.returns_view, name="returns"),
    path("shipping/", catalog.shipping_view, name="shipping"),
    path("legal/", catalog.terms_view, name="legal"),
    path("legal/privacy/", catalog.privacy_view, name="legal_privacy"),
    path("legal/terms/", catalog.terms_view, name="legal_terms"),
    path("legal/returns/", catalog.returns_view, name="legal_returns"),
    path("legal/shipping/", catalog.shipping_view, name="legal_shipping"),

    # Product Management (Legacy/Redirects)
    path("products/", catalog.product_list, name="product_list"),
    path("products/<uuid:pk>/update/", catalog.product_update, name="product_update"),
    path("products/<uuid:pk>/delete/", catalog.product_delete, name="product_delete"),

    # --- ADVANCED DASHBOARD SYSTEM ---
    path("dashboard/", administrator.admin_dashboard, name="admin_dashboard"),
    path("dashboard/inventory/", administrator.admin_product_list, name="admin_product_list"),
    path("dashboard/inventory/new/", administrator.admin_product_upsert, name="admin_product_upsert"),
    path("dashboard/inventory/<uuid:pk>/edit/", administrator.admin_product_upsert, name="admin_product_edit"),
    path("dashboard/inventory/<uuid:pk>/delete/", administrator.admin_product_delete, name="admin_product_delete"),
    path("dashboard/orders/", administrator.admin_order_list, name="admin_order_list"),
    path("dashboard/orders/<uuid:order_id>/", administrator.admin_order_detail, name="admin_order_detail"),
    path("dashboard/moderation/", administrator.admin_review_list, name="admin_review_list"),
]
