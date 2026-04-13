from .models import Category
from .views.cart import get_cart
from django.db.models import Sum

def categories_processor(request):
    """
    A context processor to make categories available in all templates.
    """
    return {
        'categories': Category.objects.all()
    }

def cart_processor(request):
    """
    A context processor to make the total number of cart items available globally.
    Used for the capsule navigation badge.
    """
    cart = get_cart(request)
    total_items = cart.items.aggregate(total=Sum('quantity'))['total'] or 0
    return {
        'global_cart_item_count': total_items
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
