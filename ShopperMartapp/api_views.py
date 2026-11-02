"""
ShopperMart REST API — Views
Provides production-ready RESTful endpoints for Product Catalog, Orders, Cart, Wishlist, and Auth.
Demonstrates ViewSets, mixins, custom action endpoints, throttling, and atomic transactions.
"""
import logging
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import F, Q, Avg, Count, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins, generics, views, status, permissions
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, ScopedRateThrottle

from .models import Product, Category, Review, Order, OrderItem, Cart, CartItem, Wishlist
from .serializers import (
    ProductListSerializer, ProductDetailSerializer,
    CategorySerializer, ReviewSerializer, ReviewCreateSerializer,
    CartSerializer, AddToCartSerializer, UpdateCartItemSerializer, RemoveCartItemSerializer,
    OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer,
    UserSerializer, RegisterSerializer, LoginSerializer, LogoutSerializer, WishlistSerializer
)
from .views.cart import get_cart

logger = logging.getLogger(__name__)


# ═══════════ AUTH API ═══════════
class RegisterAPIView(generics.CreateAPIView):
    """Register a new user and return an auth token."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        }, status=status.HTTP_201_CREATED)


class LoginAPIView(generics.GenericAPIView):
    """Authenticate user and return auth token."""
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data.get("username")
        password = serializer.validated_data.get("password")
        user = authenticate(username=username, password=password)
        
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({"token": token.key, "user": UserSerializer(user).data})
        return Response({"error": "Invalid username or password credentials."}, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserAPIView(generics.RetrieveAPIView):
    """Get the currently authenticated user's profile."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutAPIView(views.APIView):
    """
    Revoke authentication tokens (both DRF auth token and SimpleJWT refresh token).
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogoutSerializer

    @extend_schema(
        request=LogoutSerializer,
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}}
    )
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception as e:
                logger.debug(f"RefreshToken blacklist error: {e}")

        return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)


# ═══════════ CATALOG API ═══════════
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve categories with optimized product count annotations."""
    serializer_class = CategorySerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return Category.objects.annotate(
            annotated_product_count=Count('products', filter=Q(products__available=True, products__is_deleted=False))
        ).order_by('name')


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve active products.
    Supports filtering by category, search by name/description, and ordering by price/rating.
    Optimized with pre-aggregated review metrics to eliminate N+1 queries.
    """
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category__slug', 'available']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'rating']
    lookup_field = 'slug'

    def get_queryset(self):
        qs = Product.objects.select_related('category').filter(available=True, is_deleted=False)
        qs = qs.annotate(
            annotated_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
            annotated_reviews_count=Count('reviews', filter=Q(reviews__is_approved=True))
        )
        if self.action == 'retrieve':
            qs = qs.prefetch_related(
                Prefetch('reviews', queryset=Review.objects.filter(is_approved=True).select_related('user'), to_attr='approved_reviews')
            )
        return qs.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def review(self, request, slug=None):
        """Submit or update a review for a specific product."""
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
            return Response({"message": "Review submitted and pending moderation."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ═══════════ CART API ═══════════
class CartRetrieveAPIView(generics.RetrieveAPIView):
    """Retrieve the current user's or guest's cart."""
    serializer_class = CartSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        return get_cart(self.request)


class CartAddItemAPIView(generics.GenericAPIView):
    """Add an item to the shopping cart with live stock check."""
    serializer_class = AddToCartSerializer
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        cart = get_cart(request)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data['product_id']
            quantity = serializer.validated_data['quantity']
            product = get_object_or_404(Product, id=product_id, available=True, is_deleted=False)

            if quantity > product.stock:
                return Response(
                    {"error": f"Only {product.stock} units currently available in stock."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            new_qty = quantity if created else cart_item.quantity + quantity
            
            if new_qty > 50:
                return Response(
                    {"error": "Order limit: Maximum 50 units allowed per item."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            if new_qty > product.stock:
                return Response(
                    {"error": f"Cannot add {quantity} more. Only {product.stock} units in stock."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart_item.quantity = new_qty
            cart_item.save()
            cart_data = CartSerializer(cart, context={'request': request}).data
            
            # Serialize state for Slide-Over Drawer & 5-Second Popup
            from .views.cart import serialize_cart_state
            state = serialize_cart_state(request, cart)
            added_item_data = {
                "id": str(product.id),
                "name": product.name,
                "price": float(product.price),
                "mrp": float(product.mrp),
                "unit": product.unit or "1 pc",
                "quantity": cart_item.quantity,
                "added_qty": quantity,
                "image_url": product.image.url if product.image else ""
            }
            cart_data.update({
                "success": True,
                "added_item": added_item_data,
                "cart": state,
                "total_items": state["total_items"]
            })
            return Response(cart_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CartUpdateItemAPIView(generics.GenericAPIView):
    """Update item quantity in cart."""
    serializer_class = UpdateCartItemSerializer
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        cart = get_cart(request)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            item_id = serializer.validated_data['item_id']
            quantity = serializer.validated_data['quantity']
            
            try:
                cart_item = CartItem.objects.get(id=item_id, cart=cart)
            except (CartItem.DoesNotExist, ValidationError):
                return Response({"error": "Cart item not found."}, status=status.HTTP_404_NOT_FOUND)

            if quantity > cart_item.product.stock:
                return Response(
                    {"error": f"Only {cart_item.product.stock} units available."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart_item.quantity = quantity
            cart_item.save()
            return Response(CartSerializer(cart, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CartRemoveItemAPIView(generics.GenericAPIView):
    """Remove an item from the cart."""
    serializer_class = RemoveCartItemSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        cart = get_cart(request)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            item_id = serializer.validated_data['item_id']
            try:
                cart_item = CartItem.objects.get(id=item_id, cart=cart)
                cart_item.delete()
                return Response(CartSerializer(cart, context={'request': request}).data, status=status.HTTP_200_OK)
            except (CartItem.DoesNotExist, ValidationError):
                return Response({"error": "Cart item not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CartClearAPIView(views.APIView):
    """Clear all items from the cart."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=None, responses={200: CartSerializer})
    def post(self, request, *args, **kwargs):
        cart = get_cart(request)
        cart.items.all().delete()
        return Response({"message": "Cart cleared successfully.", "cart": CartSerializer(cart).data}, status=status.HTTP_200_OK)


# ═══════════ ORDERS API ═══════════
class OrderCreateAPIView(generics.GenericAPIView):
    """Create a new order from current cart items with atomic stock verification."""
    serializer_class = OrderCreateSerializer
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        cart = get_cart(request)
        cart_items = cart.items.select_related('product').all()
        
        if not cart_items.exists():
            return Response({"error": "Cannot place order: Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 1. Stock check with lock
        for item in cart_items:
            product = Product.objects.select_for_update().get(id=item.product.id)
            if item.quantity > product.stock:
                return Response(
                    {"error": f"Insufficient stock for {product.name}. Requested: {item.quantity}, Available: {product.stock}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 2. Server-side total calculation
        total = cart.total_price()
        user = request.user if request.user.is_authenticated else None

        # 3. Create Order
        order = Order.objects.create(
            user=user,
            total=total,
            full_name=data["full_name"],
            email=data["email"],
            address=data["address"],
            city=data["city"],
            state=data["state"],
            postal_code=data["postal_code"],
            landmark=data.get("landmark", ""),
            payment=data["payment_method"],
            status='processing' if data["payment_method"] == 'cod' else 'pending'
        )

        # 4. Create OrderItems & deduct stock
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )
            product = Product.objects.select_for_update().get(id=item.product.id)
            product.stock = F('stock') - item.quantity
            product.save()

        # 5. Clear cart upon placement
        cart.items.all().delete()

        logger.info(f"API Order Created: Order #{order.id} for ₹{total}")
        return Response({
            "message": "Order placed successfully.",
            "order": OrderDetailSerializer(order).data
        }, status=status.HTTP_201_CREATED)


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """List and retrieve the authenticated user's orders."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Order.objects.none()
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return OrderDetailSerializer
        return OrderListSerializer

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, pk=None):
        """Cancel an order and restore stock if still pending/processing."""
        order = self.get_object()
        if order.status in ['pending', 'processing']:
            order.status = 'cancelled'
            order.save()
            for item in order.items.all():
                if item.product:
                    item.product.stock = F('stock') + item.quantity
                    item.product.save()
            return Response({"message": "Order cancelled and inventory stock restored."}, status=status.HTTP_200_OK)
        return Response({"error": f"Cannot cancel order in '{order.status}' status."}, status=status.HTTP_400_BAD_REQUEST)


# ═══════════ WISHLIST API ═══════════
class WishlistViewSet(viewsets.ModelViewSet):
    """Manage user's wishlist."""
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Wishlist.objects.none()
        return Wishlist.objects.filter(user=self.request.user)

    def get_object(self):
        wishlist, _ = Wishlist.objects.get_or_create(user=self.request.user)
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
