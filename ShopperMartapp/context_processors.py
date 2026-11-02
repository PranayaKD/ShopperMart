from .models import Category
from .views.cart import get_cart
from django.db.models import Sum
from django.conf import settings

def categories_processor(request):
    """
    A context processor to make categories available in all templates.
    """
    return {
        'categories': Category.objects.all()
    }

def cart_processor(request):
    """
    A context processor to make cart details available globally in base.html.
    Used for the capsule navigation badge and cart slide-over sidebar drawer.
    """
    from decimal import Decimal
    cart = get_cart(request)
    cart_items = cart.items.select_related('product').all()
    total_items = sum(item.quantity for item in cart_items)
    subtotal = Decimal(cart.total_price())
    applied_coupon = request.session.get('applied_coupon')
    discount = Decimal("0.00")
    if applied_coupon in ('FIRST100', 'SHOPPER100', 'ZEPTO100') and subtotal >= Decimal("100.00"):
        discount = min(Decimal("100.00"), subtotal)
    elif applied_coupon:
        discount = Decimal("0.00")
    total = max(Decimal("0.00"), subtotal - discount)

    return {
        'global_cart': cart,
        'global_cart_items': cart_items,
        'global_cart_item_count': total_items,
        'global_cart_subtotal': subtotal,
        'global_cart_discount': discount,
        'global_cart_total': total,
        'global_applied_coupon': applied_coupon,
    }

def wishlist_processor(request):
    """
    A context processor to make the total number of wishlist items available globally.
    """
    count = 0
    if request.user.is_authenticated:
        from .models import Wishlist
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        count = wishlist.item_count
    return {
        'global_wishlist_count': count
    }

def settings_processor(request):
    """
    Exposes essential public frontend settings to templates.
    """
    google_client_id = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {}).get('google', {}).get('APP', {}).get('client_id', '')
    google_oauth_enabled = bool(google_client_id and google_client_id not in ('', 'your-client-id'))
    return {
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        'RAZORPAY_KEY_ID': getattr(settings, 'RAZORPAY_KEY_ID', ''),
        'GOOGLE_OAUTH_ENABLED': google_oauth_enabled,
    }
