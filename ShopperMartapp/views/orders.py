import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction

logger = logging.getLogger(__name__)
from .cart import get_cart
from ..models import Product, Order, OrderItem
from ..forms import CheckoutForm

# -------------------- CHECKOUT & ORDERS --------------------
@transaction.atomic
def checkout(request):
    """Checkout process - create an order from cart items. Support Guest Checkout."""
    cart = get_cart(request)
    cart_items = cart.items.select_related('product').all()
    total = cart.total_price()

    if request.method == "POST":
        if not cart_items:
            messages.error(request, "Your cart is empty.")
            return redirect("cart")

        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Create Order
            user = request.user if request.user.is_authenticated else None
            order = Order.objects.create(
                user=user,
                total=total,
                full_name=form.cleaned_data["full_name"],
                email=form.cleaned_data["email"],
                address=form.cleaned_data["address"],
                city=form.cleaned_data["city"],
                postal_code=form.cleaned_data["postal_code"],
                payment=form.cleaned_data["payment_method"],
                status='pending'
            )
            
            # Check stock and lock rows
            try:
                for item in cart_items:
                    # Lock the product row for update
                    product = Product.objects.select_for_update().get(id=item.product.id)
                    if item.quantity > product.stock:
                        messages.error(request, f"Not enough stock for {product.name}. Only {product.stock} left.")
                        # We raise a simple ValueError to trigger the atomic rollback
                        raise ValueError("Insufficient stock")

                    # Decrement stock
                    product.stock -= item.quantity
                    product.save()

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item.quantity,
                        price=product.price,
                    )
                
                # Clear cart (Only if everything above succeeded)
                cart.items.all().delete()
                
                # Store order ID in session for the order success page (especially for guests)
                request.session['last_order_id'] = order.id
                
                logger.info(f"OrderSuccess: Order {order.id} created for user {user}")
                messages.success(request, f"Order confirmed successfully! Order ID: {order.id}")
                return redirect("order_success")

            except ValueError:
                return redirect("cart")
    else:
        # Pre-fill form with profile data if authenticated
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                "full_name": getattr(request.user.profile, 'full_name', ''),
                "email": request.user.email,
                "address": f"{getattr(request.user.profile, 'address_line1', '')} {getattr(request.user.profile, 'address_line2', '')}",
                "city": getattr(request.user.profile, 'city', ''),
                "postal_code": getattr(request.user.profile, 'pincode', '')
            }
        form = CheckoutForm(initial=initial_data)

    return render(request, "ShopperMartapp/checkout.html", {
        "cart_items": cart_items,
        "total": total,
        "form": form
    })


def order_success(request):
    """Display order success page for both guests and logged-in users."""
    order_id = request.session.get('last_order_id')
    if not order_id:
        return redirect("home")
    
    order = get_object_or_404(Order, id=order_id)
    return render(request, "ShopperMartapp/order_success.html", {"order": order})


@login_required
def my_orders(request):
    """Display a list of orders for the logged-in user."""
    orders = Order.objects.filter(user=request.user).order_by("-created_at").prefetch_related("items__product")
    return render(request, "ShopperMartapp/my_orders.html", {"orders": orders})


@login_required
@transaction.atomic
def cancel_order(request, order_id):
    """Cancel an order, update status, and restore stock."""
    order = get_object_or_404(Order, user=request.user, id=order_id)
    
    if order.status == 'cancelled':
        messages.warning(request, "This order is already cancelled.")
        return redirect("my_orders")
        
    # Restore stock
    for item in order.items.all():
        if item.product:
            item.product.stock += item.quantity
            item.product.save()
            
    order.status = 'cancelled'
    order.save()
    messages.info(request, f"Order #{order_id} has been marked as cancelled. Catalog stock restored.")
    return redirect("my_orders")
