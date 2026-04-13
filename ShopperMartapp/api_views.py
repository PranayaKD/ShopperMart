"""
ShopperMart REST API — Views
Provides RESTful endpoints for Product Catalog, Orders, Cart, and Auth.
Demonstrates ViewSets, mixins, custom action endpoints, and permission classes.
"""
from rest_framework import viewsets, mixins, generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, ScopedRateThrottle
from django.contrib.auth import authenticate
from django.db import transaction

from .models import Product, Category, Review, Order, Cart, CartItem, Wishlist
from .serializers import (
    ProductListSerializer, ProductDetailSerializer,
    CategorySerializer, ReviewSerializer, ReviewCreateSerializer,
    CartSerializer, AddToCartSerializer,
    OrderListSerializer, OrderDetailSerializer,
    UserSerializer, RegisterSerializer, WishlistSerializer
)
from .views.cart import get_cart


# ═══════════ AUTH API ═══════════
class RegisterAPIView(generics.CreateAPIView):
    """Register a new user and return an auth token."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]  # Edge Case #11: Auth Rate Limiting

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        }, status=status.HTTP_201_CREATED)


class LoginAPIView(generics.GenericAPIView):
    """Authenticate user and return token (Throttled)."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle] # Case #11

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({"token": token.key, "user": UserSerializer(user).data})
        return Response({"error": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST)


# ═══════════ CATALOG API ═══════════
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve categories."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve active products (Archiving Aware).
    Supports filtering by category, search by name/description, and ordering by price/rating.
    """
    queryset = Product.objects.select_related('category').filter(available=True, is_deleted=False)
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category__slug']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def review(self, request, slug=None):
        """Submit a review for a specific product."""
        product = self.get_object()
        serializer = ReviewCreateSerializer(data=request.data)
        if serializer.is_valid():
            Review.objects.update_or_create(
                product=product,
                user=request.user,
                defaults={
                    'rating': serializer.validated_data['rating'],
                    'comment': serializer.validated_data['comment'],
                    'is_approved': False
                }
            )
            return Response({"message": "Review submitted and pending approval."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ═══════════ CART API ═══════════
class CartRetrieveAPIView(generics.RetrieveAPIView):
    """Retrieve the current user's or guest's cart."""
    serializer_class = CartSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        return get_cart(self.request)


class CartAddItemAPIView(generics.GenericAPIView):
    """Add an item to the cart."""
    serializer_class = AddToCartSerializer
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        cart = get_cart(request)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data['product_id']
            quantity = serializer.validated_data['quantity']
            product = get_object_or_404(Product, id=product_id)

            if quantity > product.stock:
                return Response(
                    {"error": f"Supply Gating: Only {product.stock} units available in local registry."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Edge Case #4: Cumulative overflow protection (Case #32)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            new_qty = quantity if created else cart_item.quantity + quantity
            
            if new_qty > 50:
                 return Response(
                    {"error": "Manifest Violation: Selection exceeds 50 units per registry entry."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart_item.quantity = new_qty
            cart_item.save()
            return Response(CartSerializer(cart, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ═══════════ ORDERS API ═══════════
class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """List and retrieve the authenticated user's orders."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return OrderDetailSerializer
        return OrderListSerializer

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, pk=None):
        """Cancel an order if it's still pending/processing."""
        order = self.get_object()
        if order.status in ['pending', 'processing']:
            order.status = 'cancelled'
            order.save()
            # Restore stock
            for item in order.items.all():
                if item.product:
                    item.product.stock += item.quantity
                    item.product.save()
            return Response({"message": "Order cancelled and stock restored."}, status=status.HTTP_200_OK)
        return Response({"error": "Order cannot be cancelled."}, status=status.HTTP_400_BAD_REQUEST)


# ═══════════ WISHLIST API ═══════════
class WishlistViewSet(viewsets.ModelViewSet):
    """
    Manage the authenticated user's wishlist.
    Only retrieve and custom action 'toggle' are primarily used.
    """
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

    def get_object(self):
        wishlist, created = Wishlist.objects.get_or_create(user=self.request.user)
        return wishlist

    @action(detail=False, methods=['post'], url_path=r'toggle/(?P<product_id>[0-9a-f-]+)')
    def toggle(self, request, product_id=None):
        """Add or remove a product from the wishlist."""
        wishlist = self.get_object()
        try:
            product = Product.objects.get(id=product_id)
        except (Product.DoesNotExist, ValidationError):
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        if wishlist.products.filter(id=product_id).exists():
            wishlist.products.remove(product)
            return Response({"status": "removed", "item_count": wishlist.item_count})
        else:
            wishlist.products.add(product)
            return Response({"status": "added", "item_count": wishlist.item_count})

    @action(detail=False, methods=['get'], url_path=r'check/(?P<product_id>[0-9a-f-]+)')
    def check(self, request, product_id=None):
        """Check if a product is in the user's wishlist."""
        wishlist = self.get_object()
        is_saved = wishlist.products.filter(id=product_id).exists()
        return Response({"is_wishlisted": is_saved})
