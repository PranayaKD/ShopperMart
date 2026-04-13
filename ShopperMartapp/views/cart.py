import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import Product, Cart, CartItem

logger = logging.getLogger(__name__)

# -------------------- HELPERS --------------------
def get_cart(request):
    """Retrieve or create a cart for authenticated users or guests."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        # Ensure session exists for guest carts
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
    return cart


# -------------------- CART --------------------
def cart_view(request):
    """Show current user's cart (authenticated or guest)."""
    cart = get_cart(request)
    cart_items = cart.items.select_related("product")
    total = cart.total_price()

    return render(request, "ShopperMartapp/cart.html", {
        "cart": cart,
        "cart_items": cart_items,
        "total": total,
    })


@require_POST
@transaction.atomic
def add_to_cart(request, product_id):
    """Add product to cart (authenticated or guest) with safety gates."""
    try:
        product = get_object_or_404(Product, id=product_id, available=True, is_deleted=False)
    except ValidationError:
        return render(request, "404.html", status=404)

    cart = get_cart(request)
    
    # Read quantity from POST data
    quantity = 1
    if request.method == "POST":
        try:
            quantity = int(request.POST.get("quantity", 1))
            if quantity < 1: quantity = 1
            # Edge Case #4: Overflow protection
            if quantity > 50:
                messages.warning(request, "For bulk orders, please contact support. Individual limit is 50 units.")
                quantity = 50
        except (ValueError, TypeError):
            quantity = 1
    
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    new_quantity = quantity if created else cart_item.quantity + quantity
    
    # Check total quantity cap
    if new_quantity > 50:
        messages.error(request, "Maximum limit reached (50 units per item).")
        return redirect("cart")

    if new_quantity > product.stock:
        messages.error(request, f"Sorry, only {product.stock} units are currently in stock.")
        return redirect("cart")

    cart_item.quantity = new_quantity
    cart_item.save()
    
    logger.info(f"CartUpdate: User {request.user} added product {product.id} (Qty: {quantity})")
    messages.success(request, f"{product.name} has been added to your bag.")
    return redirect("cart")


@require_POST
@transaction.atomic
def update_cart(request, item_id):
    """Update quantity of a cart item with UUID safety."""
    cart = get_cart(request)
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    except ValidationError:
        return render(request, "404.html", status=404)

    if request.method == "POST":
        try:
            quantity = int(request.POST.get("quantity", 1))
            if quantity > 0:
                if quantity > 50:
                    messages.error(request, "Maximum of 50 units allowed per item.")
                elif quantity > cart_item.product.stock:
                    messages.error(request, f"Only {cart_item.product.stock} units currently available.")
                else:
                    cart_item.quantity = quantity
                    cart_item.save()
                    messages.success(request, f"Updated quantity for {cart_item.product.name}.")
            else:
                cart_item.delete()
                messages.info(request, f"{cart_item.product.name} removed from your bag.")
        except (ValueError, TypeError):
             messages.error(request, "Invalid quantity provided.")
             
    return redirect("cart")
             
    return redirect("cart")


@require_POST
@transaction.atomic
def remove_from_cart(request, item_id):
    """Remove product from cart with UUID safety."""
    cart = get_cart(request)
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    except ValidationError:
        return render(request, "404.html", status=404)
        
    product_name = cart_item.product.name
    cart_item.delete()
    messages.info(request, f"{product_name} removed from your bag.")
    return redirect("cart")
