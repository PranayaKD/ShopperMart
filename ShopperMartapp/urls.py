from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from .views import catalog, cart, orders, account

urlpatterns = [
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
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Profile
    path("profile/", account.profile_view, name="profile"),
    path("profile/edit/", account.profile_edit_view, name="profile_edit"),

    # Cart
    path("cart/", cart.cart_view, name="cart"),
    path("cart/add/<uuid:product_id>/", cart.add_to_cart, name="add_to_cart"),
    path("cart/remove/<uuid:item_id>/", cart.remove_from_cart, name="remove_from_cart"),
    path("cart/update/<uuid:item_id>/", cart.update_cart, name="update_cart"),

    # Checkout & Orders
    path("checkout/", orders.checkout, name="checkout"),
    path("payment/callback/", orders.payment_callback, name="payment_callback"),
    path("order-success/", orders.order_success, name="order_success"),
    path("my-orders/", orders.my_orders, name="my_orders"),
    path("orders/<uuid:order_id>/", orders.order_detail, name="order_detail"),
    path("orders/<uuid:order_id>/cancel/", orders.cancel_order, name="cancel_order"),

    # Reviews
    path("product/<uuid:product_id>/review/", catalog.submit_review, name="submit_review"),
    
    # Wishlist
    path("wishlist/", catalog.wishlist_view, name="wishlist"),
    path("wishlist/toggle/<uuid:product_id>/", catalog.toggle_wishlist, name="toggle_wishlist"),

    # Brand
    path("about/", catalog.about_view, name="about"),
    path("contact/", catalog.contact_view, name="contact"),
    path("legal/", TemplateView.as_view(template_name="stub.html"), name="legal"),

    # Product Management
    path("products/", catalog.product_list, name="product_list"),
    path("products/<uuid:pk>/update/", catalog.product_update, name="product_update"),
    path("products/<uuid:pk>/delete/", catalog.product_delete, name="product_delete"),
]
