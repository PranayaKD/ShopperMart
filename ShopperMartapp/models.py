import uuid
from django.db import models
from django.db.models import Avg, Count
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    landmark = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        return self.filter(available=True, is_deleted=False)

    def non_deleted(self):
        return self.filter(is_deleted=False)

    def search(self, query):
        if not query:
            return self
        return self.filter(
            models.Q(name__icontains=query) | models.Q(description__icontains=query)
        )

    def with_category(self):
        return self.select_related('category')

    def with_image_status(self):
        return self.annotate(
            has_image=models.Case(
                models.When(image__gt='', then=models.Value(True)),
                default=models.Value(False),
                output_field=models.BooleanField(),
            )
        )

    def sort_by(self, sort_option):
        options = {
            'price_asc': 'price',
            'price_desc': '-price',
            'rating': '-rating',
            'newest': '-created_at'
        }
        return self.order_by(options.get(sort_option, '-created_at'))


class ProductManager(models.Manager.from_queryset(ProductQuerySet)):
    pass


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5)
    reviews_count = models.PositiveIntegerField(default=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    is_deleted = models.BooleanField(default=False)

    objects = ProductManager()

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(stock__gte=0), name='product_stock_non_negative'),
            models.CheckConstraint(check=models.Q(price__gte=0), name='product_price_non_negative'),
        ]

    def __str__(self):
        return self.name

    @property
    def computed_rating(self):
        """Live rating from approved reviews. Falls back to the static 'rating' field."""
        agg = self.reviews.filter(is_approved=True).aggregate(
            avg=Avg('rating'), cnt=Count('id')
        )
        if agg['cnt'] and agg['cnt'] > 0:
            return round(agg['avg'], 1)
        return self.rating

    @property
    def computed_reviews_count(self):
        """Live count of approved reviews. Falls back to static 'reviews_count'."""
        cnt = self.reviews.filter(is_approved=True).count()
        return cnt if cnt > 0 else self.reviews_count

    @property
    def low_stock(self):
        """Returns True if stock is between 1 and 5 (urgency badge trigger)."""
        return 0 < self.stock <= 5


class Review(models.Model):
    """Product review with admin approval gating."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(max_length=1000)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')  # One review per user per product
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.user.username} on {self.product.name} ({self.rating}★)"


class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart", null=True, blank=True)
    session_key = models.CharField(max_length=100, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.username}"
        return f"Guest Cart ({self.session_key})"

    class Meta:
        verbose_name = "Shopping Cart"
        verbose_name_plural = "Shopping Carts"

    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

    def merge_with(self, other_cart):
        """Merge items from another cart (usually a guest cart) into this one."""
        if not other_cart or other_cart == self:
            return
            
        for item in other_cart.items.all():
            cart_item, created = CartItem.objects.get_or_create(
                cart=self, 
                product=item.product,
                defaults={'quantity': item.quantity}
            )
            if not created:
                cart_item.quantity += item.quantity
                cart_item.save()
            
        # Optional: Delete the merged cart
        other_cart.delete()


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(quantity__gt=0), name='cart_item_quantity_positive'),
            models.CheckConstraint(check=models.Q(quantity__lte=100), name='cart_item_quantity_reasonable'),
        ]

    @property
    def subtotal(self):
        return self.product.price * self.quantity


ORDER_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('shipped', 'Shipped'),
    ('out_for_delivery', 'Out for Delivery'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled'),
]

# Defines the visual order of the lifecycle steps (excluding cancelled)
ORDER_LIFECYCLE_STEPS = ['pending', 'processing', 'shipped', 'out_for_delivery', 'delivered']


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    address = models.TextField()
    landmark = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20)
    payment = models.CharField(max_length=50)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.full_name}"

    def change_status(self, new_status, user=None, note=""):
        """Safely transition order status with audit log and validation."""
        valid_transitions = {
            'pending': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['out_for_delivery'],
            'out_for_delivery': ['delivered'],
            'delivered': [],
            'cancelled': []
        }
        
        if new_status not in valid_transitions.get(self.status, []):
            raise ValueError(f"Illegal status transition from {self.status} to {new_status}")
            
        old_status = self.status
        self.status = new_status
        self.save()
        
        OrderStatusLog.objects.create(
            order=self,
            old_status=old_status,
            new_status=new_status,
            changed_by=user,
            note=note
        )

    class Meta:
        ordering = ['-created_at']

    @property
    def lifecycle_progress(self):
        """Returns the 0-based index of the current status in the lifecycle."""
        if self.status == 'cancelled':
            return -1
        try:
            return ORDER_LIFECYCLE_STEPS.index(self.status)
        except ValueError:
            return 0

    @property
    def lifecycle_percentage(self):
        """Returns percentage complete for the progress bar."""
        idx = self.lifecycle_progress
        if idx < 0:
            return 0
        return int((idx / (len(ORDER_LIFECYCLE_STEPS) - 1)) * 100)


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def get_total(self):
        return self.quantity * self.price

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(quantity__gt=0), name='order_item_quantity_positive'),
        ]


class OrderStatusLog(models.Model):
    """Audit trail for order status changes. Shows recruiters you understand event sourcing."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_logs")
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Order #{self.order_id}: {self.old_status} → {self.new_status}"


class Wishlist(models.Model):
    """User's collection of saved items. Demonstrates M2M relationship logic."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wishlist")
    products = models.ManyToManyField(Product, related_name="wishlisted_by", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_product_ids_for_user(cls, user):
        """Optimized way to get a list of product IDs in the user's wishlist."""
        if not user.is_authenticated:
            return []
        # get_or_create to ensure the wishlist exists without extra view-level logic
        wishlist, _ = cls.objects.get_or_create(user=user)
        return list(wishlist.products.values_list('id', flat=True))

    def __str__(self):
        return f"Wishlist of {self.user.username}"

    @property
    def item_count(self):
        return self.products.count()
