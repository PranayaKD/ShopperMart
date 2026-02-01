from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Home / Shop
    path("", views.shop_home, name="home"),

    # Categories & Products
    path("category/<slug:slug>/", views.category_products, name="category_products"),
    path("product/<int:pk>/", views.product_detail_by_id, name="product_detail_by_id"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),

    # Auth
    path("register/", views.register_view, name="register"),
    path("signup/", views.register_view, name="signup"),  
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Profile
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.profile_edit_view, name="profile_edit"),

    # Cart
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),  # fixed
    path("cart/update/<int:item_id>/", views.update_cart, name="update_cart"),            # fixed

    # Checkout & Orders
    path("checkout/", views.checkout, name="checkout"),
    path("my-orders/", views.my_orders, name="my_orders"),
    path("orders/<int:order_id>/cancel/", views.cancel_order, name="cancel_order"),
    
    # Product Management
    path("products/", views.product_list, name="product_list"),
    path("products/<int:pk>/update/", views.product_update, name="product_update"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
]
