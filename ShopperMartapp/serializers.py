"""
ShopperMart REST API — Serializers
Converts Django models to/from JSON for the API layer.
Demonstrates: Nested serialization, computed fields, write validation.
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Category, Product, Review, Cart, CartItem,
    Order, OrderItem, OrderStatusLog, ORDER_LIFECYCLE_STEPS, Wishlist
)


# ═══════════ CATEGORY ═══════════
class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(source='products.count', read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='api-category-detail', lookup_field='slug')

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'product_count', 'url']


# ═══════════ REVIEW ═══════════
class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'username', 'rating', 'comment', 'is_approved', 'created_at']
        read_only_fields = ['is_approved', 'created_at']


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Write serializer — enforces one review per user per product."""
    class Meta:
        model = Review
        fields = ['rating', 'comment']

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_comment(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Comment must be at least 10 characters.")
        return value


# ═══════════ PRODUCT ═══════════
class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views (no heavy relations)."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    computed_rating = serializers.DecimalField(max_digits=3, decimal_places=1, read_only=True)
    computed_reviews_count = serializers.IntegerField(read_only=True)
    low_stock = serializers.BooleanField(read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'price', 'stock', 'available',
            'category_name', 'category_slug',
            'computed_rating', 'computed_reviews_count', 'low_stock',
            'image_url', 'created_at',
        ]

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full serializer with nested reviews for detail view."""
    category = CategorySerializer(read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True, source='approved_reviews')
    computed_rating = serializers.DecimalField(max_digits=3, decimal_places=1, read_only=True)
    computed_reviews_count = serializers.IntegerField(read_only=True)
    low_stock = serializers.BooleanField(read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'stock', 'available',
            'category', 'computed_rating', 'computed_reviews_count', 'low_stock',
            'image_url', 'created_at', 'updated_at', 'reviews',
        ]

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


# ═══════════ CART ═══════════
class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_name', 'product_slug',
            'product_price', 'product_image', 'quantity', 'subtotal',
        ]
        read_only_fields = ['subtotal']

    def get_product_image(self, obj):
        if obj.product.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.product.image.url)
        return None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, source='total_price')
    item_count = serializers.IntegerField(source='items.count', read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'item_count', 'total_price', 'items', 'created_at']


class AddToCartSerializer(serializers.Serializer):
    """Input serializer for adding items to cart (UUID Hardened)."""
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=50, default=1)

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value, available=True, is_deleted=False).exists():
            raise serializers.ValidationError("Product not found, unavailable, or archived.")
        return value


# ═══════════ ORDER ═══════════
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'total']

    def get_total(self, obj):
        return str(obj.get_total())


class OrderStatusLogSerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(source='changed_by.username', read_only=True, default=None)

    class Meta:
        model = OrderStatusLog
        fields = ['id', 'old_status', 'new_status', 'changed_by_username', 'note', 'created_at']


class OrderListSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(source='items.count', read_only=True)
    lifecycle_percentage = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'full_name', 'total', 'status',
            'item_count', 'lifecycle_percentage', 'created_at',
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_logs = OrderStatusLogSerializer(many=True, read_only=True)
    lifecycle_progress = serializers.IntegerField(read_only=True)
    lifecycle_percentage = serializers.IntegerField(read_only=True)
    lifecycle_steps = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'full_name', 'email', 'address', 'city', 'postal_code',
            'payment', 'total', 'status', 'created_at',
            'items', 'status_logs',
            'lifecycle_progress', 'lifecycle_percentage', 'lifecycle_steps',
        ]

    def get_lifecycle_steps(self, obj):
        return ORDER_LIFECYCLE_STEPS


# ═══════════ WISHLIST ═══════════
class WishlistSerializer(serializers.ModelSerializer):
    products = ProductListSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'item_count', 'products', 'created_at']


# ═══════════ USER / AUTH ═══════════
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
