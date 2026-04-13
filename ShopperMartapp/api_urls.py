"""
ShopperMart REST API — Routing
Wires up the ViewSets and generics via the DRF SimpleRouter.
"""
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import api_views

router = SimpleRouter()
router.register(r'categories', api_views.CategoryViewSet, basename='api-category')
router.register(r'products', api_views.ProductViewSet, basename='api-product')
router.register(r'orders', api_views.OrderViewSet, basename='api-order')
router.register(r'wishlist', api_views.WishlistViewSet, basename='api-wishlist')

urlpatterns = [
    # Auth Endpoints
    path('auth/register/', api_views.RegisterAPIView.as_view(), name='api-register'),
    path('auth/login/', api_views.LoginAPIView.as_view(), name='api-login'),
    
    # Cart Endpoints (Custom non-ViewSet routes)
    path('cart/', api_views.CartRetrieveAPIView.as_view(), name='api-cart'),
    path('cart/add/', api_views.CartAddItemAPIView.as_view(), name='api-cart-add'),


    # ViewSet Router
    path('', include(router.urls)),
]
