"""
ShopperMart REST API — Routing
Wires up ViewSets, JWT authentication, and generic endpoints.
"""
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import api_views
from .views import payments, cart

router = SimpleRouter()
router.register(r'categories', api_views.CategoryViewSet, basename='api-category')
router.register(r'products', api_views.ProductViewSet, basename='api-product')
router.register(r'orders', api_views.OrderViewSet, basename='api-order')
router.register(r'wishlist', api_views.WishlistViewSet, basename='api-wishlist')

urlpatterns = [
    # Auth Endpoints
    path('auth/register/', api_views.RegisterAPIView.as_view(), name='api-register'),
    path('auth/login/', api_views.LoginAPIView.as_view(), name='api-login'),
    path('auth/logout/', api_views.LogoutAPIView.as_view(), name='api-logout'),
    path('auth/me/', api_views.CurrentUserAPIView.as_view(), name='api-me'),
    path('auth/token/', TokenObtainPairView.as_view(), name='api-token-obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='api-token-refresh'),
    
    # Cart Endpoints
    path('cart/', api_views.CartRetrieveAPIView.as_view(), name='api-cart'),
    path('cart/data/', cart.api_get_cart, name='api-cart-data'),
    path('cart/add/', api_views.CartAddItemAPIView.as_view(), name='api-cart-add'),
    path('cart/update-quantity/', cart.api_update_cart_quantity, name='api-cart-update-quantity'),
    path('cart/apply-coupon/', cart.api_apply_coupon_ajax, name='api-cart-apply-coupon'),
    path('cart/update/', api_views.CartUpdateItemAPIView.as_view(), name='api-cart-update'),
    path('cart/remove/', api_views.CartRemoveItemAPIView.as_view(), name='api-cart-remove'),
    path('cart/clear/', api_views.CartClearAPIView.as_view(), name='api-cart-clear'),

    # Order Creation Endpoint
    path('orders/create/', api_views.OrderCreateAPIView.as_view(), name='api-order-create'),

    # Razorpay Payment Endpoints
    path('payments/create-order/', payments.create_order, name='api-payment-create-order'),
    path('payments/verify-payment/', payments.verify_payment, name='api-payment-verify-payment'),
    path('create-order/', payments.create_order, name='api-create-order'),
    path('verify-payment/', payments.verify_payment, name='api-verify-payment'),

    # ViewSet Router
    path('', include(router.urls)),
]
