import logging
from decimal import Decimal
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
    """Show current user's cart (authenticated or guest) with FIRST100 discount calculation."""
    cart = get_cart(request)
    cart_items = cart.items.select_related("product")
    subtotal = Decimal(cart.total_price())

    applied_coupon = request.session.get('applied_coupon')
    discount = Decimal("0.00")
    if applied_coupon in ('FIRST100', 'SHOPPER100', 'ZEPTO100') and subtotal >= Decimal("100.00"):
        discount = min(Decimal("100.00"), subtotal)
    elif applied_coupon:
        request.session.pop('applied_coupon', None)
        applied_coupon = None

    free_delivery_threshold = Decimal("149.00")
    if cart_items.exists():
        delivery_fee = Decimal("0.00") if subtotal >= free_delivery_threshold else Decimal("25.00")
    else:
        delivery_fee = Decimal("0.00")

    total = max(Decimal("0.00"), subtotal - discount + delivery_fee)

    return render(request, "ShopperMartapp/cart.html", {
        "cart": cart,
        "cart_items": cart_items,
        "subtotal": subtotal,
        "discount": discount,
        "delivery_fee": delivery_fee,
        "free_delivery_threshold": free_delivery_threshold,
        "applied_coupon": applied_coupon,
        "total": total,
    })


@require_POST
def apply_coupon(request):
    """Apply or remove promo codes like FIRST100 for ₹100 OFF on first 3 orders."""
    code = request.POST.get('coupon_code', '').strip().upper()
    cart = get_cart(request)
    subtotal = Decimal(cart.total_price())

    if code in ('FIRST100', 'SHOPPER100', 'ZEPTO100'):
        if subtotal < Decimal("100.00"):
            messages.error(request, "Minimum cart amount to apply FIRST100 is ₹100.")
        else:
            request.session['applied_coupon'] = 'FIRST100'
            messages.success(request, "🎉 Code FIRST100 applied successfully! ₹100 OFF your order.")
    elif code == 'REMOVE':
        request.session.pop('applied_coupon', None)
        messages.info(request, "Coupon removed.")
    else:
        messages.error(request, f"Coupon code '{code}' is invalid or expired.")

    return redirect(request.META.get('HTTP_REFERER', 'cart'))


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
            if quantity > 50:
                messages.error(request, "Individual limit is 50 units per order. For bulk orders, please contact support.")
                return redirect("cart")
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


def serialize_cart_state(request, cart):
    """Helper to serialize complete cart state for the Slide-Over Sidebar Drawer & Popups."""
    cart_items = cart.items.select_related("product").all()
    subtotal = Decimal(cart.total_price())
    applied_coupon = request.session.get('applied_coupon')
    discount = Decimal("0.00")
    if applied_coupon in ('FIRST100', 'SHOPPER100', 'ZEPTO100') and subtotal >= Decimal("100.00"):
        discount = min(Decimal("100.00"), subtotal)
    elif applied_coupon:
        request.session.pop('applied_coupon', None)
        applied_coupon = None

    free_delivery_threshold = Decimal("149.00")
    total_items = sum(item.quantity for item in cart_items)
    if total_items > 0:
        delivery_fee = Decimal("0.00") if subtotal >= free_delivery_threshold else Decimal("25.00")
    else:
        delivery_fee = Decimal("0.00")

    total = max(Decimal("0.00"), subtotal - discount + delivery_fee)

    items_data = []
    for it in cart_items:
        items_data.append({
            "id": str(it.id),
            "product_id": str(it.product.id),
            "name": it.product.name,
            "slug": it.product.slug,
            "unit": it.product.unit or "1 pc",
            "price": float(it.product.price),
            "mrp": float(it.product.mrp),
            "quantity": it.quantity,
            "image_url": it.product.image.url if it.product.image else "",
            "item_total": float(it.subtotal),
            "stock": it.product.stock
        })

    return {
        "is_authenticated": request.user.is_authenticated,
        "user_name": request.user.get_full_name() or request.user.username if request.user.is_authenticated else "",
        "items": items_data,
        "total_items": total_items,
        "subtotal": float(subtotal),
        "discount": float(discount),
        "delivery_fee": float(delivery_fee),
        "free_delivery_threshold": float(free_delivery_threshold),
        "total": float(total),
        "applied_coupon": applied_coupon,
        "delivery_time": "10 Mins"
    }


def api_get_cart(request):
    """JSON API to fetch full cart state for the Slide-Over Sidebar."""
    from django.http import JsonResponse
    cart = get_cart(request)
    state = serialize_cart_state(request, cart)
    return JsonResponse({"success": True, "cart": state})


@require_POST
@transaction.atomic
def api_update_cart_quantity(request):
    """JSON API to increment, decrement, or set quantity from the Cart Sidebar Stepper."""
    import json
    from django.http import JsonResponse
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        item_id = data.get('item_id')
        delta = data.get('delta')
        new_qty = data.get('quantity')

        cart = get_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        if delta is not None:
            target_quantity = cart_item.quantity + int(delta)
        elif new_qty is not None:
            target_quantity = int(new_qty)
        else:
            return JsonResponse({'success': False, 'error': 'Missing quantity or delta.'}, status=400)

        if target_quantity <= 0:
            cart_item.delete()
        else:
            if target_quantity > 50:
                return JsonResponse({'success': False, 'error': 'Maximum 50 units per item.'}, status=400)
            if target_quantity > cart_item.product.stock:
                return JsonResponse({'success': False, 'error': f'Only {cart_item.product.stock} units currently available.'}, status=400)
            cart_item.quantity = target_quantity
            cart_item.save()

        state = serialize_cart_state(request, cart)
        return JsonResponse({"success": True, "cart": state})
    except Exception as e:
        logger.error(f"api_update_cart_quantity error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_POST
def api_apply_coupon_ajax(request):
    """JSON API to apply or remove coupon directly inside the Cart Sidebar."""
    import json
    from django.http import JsonResponse
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        code = data.get('coupon_code', '').strip().upper()
        cart = get_cart(request)
        subtotal = Decimal(cart.total_price())

        if code in ('FIRST100', 'SHOPPER100', 'ZEPTO100'):
            if subtotal < Decimal("100.00"):
                return JsonResponse({'success': False, 'error': 'Minimum cart amount to apply FIRST100 is ₹100.'}, status=400)
            request.session['applied_coupon'] = 'FIRST100'
            msg = "Code FIRST100 applied! ₹100 OFF your order."
        elif code == 'REMOVE':
            request.session.pop('applied_coupon', None)
            msg = "Coupon removed."
        else:
            return JsonResponse({'success': False, 'error': f"Coupon code '{code}' is invalid or expired."}, status=400)

        state = serialize_cart_state(request, cart)
        return JsonResponse({"success": True, "message": msg, "cart": state})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_POST
@transaction.atomic
def api_add_to_cart(request):
    """JSON API to add product to cart with added_item and full cart state for the 5s popup."""
    import json
    from django.http import JsonResponse
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        if quantity < 1:
            quantity = 1
        product = get_object_or_404(Product, id=product_id, available=True, is_deleted=False)
        cart = get_cart(request)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        new_quantity = quantity if created else cart_item.quantity + quantity
        if new_quantity > 50:
            return JsonResponse({'success': False, 'error': 'Maximum limit reached (50 units per item).'}, status=400)
        if new_quantity > product.stock:
            return JsonResponse({'success': False, 'error': f'Only {product.stock} units currently available.'}, status=400)
        cart_item.quantity = new_quantity
        cart_item.save()

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

        return JsonResponse({
            'success': True,
            'message': f'{product.name} added to cart.',
            'added_item': added_item_data,
            'cart': state,
            'total_items': state['total_items'],
            'item_id': str(cart_item.id),
            'quantity': cart_item.quantity
        })
    except Exception as e:
        logger.error(f"api_add_to_cart error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
