import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import F

logger = logging.getLogger(__name__)
from .cart import get_cart
from ..models import Product, Order, OrderItem, OrderStatusLog, ORDER_LIFECYCLE_STEPS
from ..forms import CheckoutForm
import razorpay
from django.conf import settings

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

        # 1. IDEMPOTENCY CHECK (Edge Case #5 - Double Submission)
        checkout_token = request.POST.get("checkout_token")
        if not checkout_token or checkout_token == request.session.get('last_checkout_token'):
            messages.warning(request, "This order is already being processed or has been completed.")
            return redirect("cart")

        # 2. PRICE LOCK VERIFICATION (Edge Case #16 - Price change during checkout)
        posted_total = request.POST.get("total_verify")
        if posted_total and float(posted_total) != float(total):
             messages.error(request, "The prices in your cart have changed. Please review and try again.")
             return redirect("cart")

        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Create Order
            user = request.user if request.user.is_authenticated else None
            
            # Start atomic block for stock gating
            try:
                order = Order.objects.create(
                    user=user,
                    total=total,
                    full_name=form.cleaned_data["full_name"],
                    email=form.cleaned_data["email"],
                    address=form.cleaned_data["address"],
                    landmark=form.cleaned_data["landmark"],
                    city=form.cleaned_data["city"],
                    state=form.cleaned_data["state"],
                    postal_code=form.cleaned_data["postal_code"],
                    payment=form.cleaned_data["payment_method"],
                    status='pending'
                )
                
                for item in cart_items:
                    # select_for_update handles Edge Case #4 (Inventory Race Condition)
                    product = Product.objects.select_for_update().get(id=item.product.id)
                    if item.quantity > product.stock:
                        messages.error(request, f"Not enough stock for {product.name}. Only {product.stock} left.")
                        raise ValueError("Insufficient stock")

                    product.stock = F('stock') - item.quantity
                    product.save()

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item.quantity,
                        price=product.price,
                    )
                
                # Mark token as used
                request.session['last_checkout_token'] = checkout_token
                
                # Clear cart and set last order id
                cart.items.all().delete()
                request.session['last_order_id'] = str(order.id)
                
                if form.cleaned_data["payment_method"] in ['card', 'upi']:
                    # Initiate Razorpay SDK
                    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                    payment_data = {
                        "amount": int(total * 100),  # amount in paise
                        "currency": "INR",
                        "receipt": str(order.id)
                    }
                    razorpay_order = client.order.create(data=payment_data)
                    
                    logger.info(f"PaymentInitiated: Razorpay order created for Django order {order.id}")
                    
                    return render(request, "ShopperMartapp/payment.html", {
                        "order": order,
                        "razorpay_order_id": razorpay_order["id"],
                        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                        "amount": int(total * 100)
                    })
                
                else:
                    # Cash on delivery
                    order.change_status('processing', user=user, note="Order verified (COD) and processing started.")
                    logger.info(f"OrderSuccess: Order {order.id} created for user {user} via COD")
                    messages.success(request, f"Order confirmed successfully! Order ID: {order.id}")
                    return redirect("order_success")

            except ValueError as ve:
                messages.error(request, str(ve))
                return redirect("cart")
            except Exception as e:
                logger.error(f"CheckoutError: {e}")
                messages.error(request, "An unexpected error occurred during checkout. Please try again.")
                return redirect("cart")
    else:
        # Pre-fill form with profile data if authenticated
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                "full_name": getattr(request.user.profile, 'full_name', ''),
                "email": request.user.email,
                "address": getattr(request.user.profile, 'address_line1', ''),
                "landmark": getattr(request.user.profile, 'landmark', ''),
                "city": getattr(request.user.profile, 'city', ''),
                "state": getattr(request.user.profile, 'state', ''),
                "postal_code": getattr(request.user.profile, 'pincode', '')
            }
        form = CheckoutForm(initial=initial_data)

    # Generate unique checkout token
    import secrets
    checkout_token = secrets.token_hex(16)

    return render(request, "ShopperMartapp/checkout.html", {
        "cart_items": cart_items,
        "total": total,
        "form": form,
        "checkout_token": checkout_token
    })


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def payment_callback(request):
    """Handle Razorpay success callback verify signature."""
    if request.method == "POST":
        razorpay_payment_id = request.POST.get('razorpay_payment_id', '')
        razorpay_order_id = request.POST.get('razorpay_order_id', '')
        razorpay_signature = request.POST.get('razorpay_signature', '')
        order_id_str = request.POST.get('custom_order_id', '')

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        try:
            client.utility.verify_payment_signature(params_dict)
            # Signature matches!
            order = Order.objects.get(id=order_id_str)
            if order.status == 'pending':
                order.change_status('processing', note=f"Razorpay payment verified. ID: {razorpay_payment_id}")
            
            messages.success(request, "Payment successful! Your order has been placed.")
            return redirect("order_success")
            
        except razorpay.errors.SignatureVerificationError:
            logger.error("PaymentFailed: Razorpay signature verification failed.")
            messages.error(request, "Payment verification failed. Please try again.")
            return redirect("home")
        except Exception as e:
            logger.error(f"PaymentCallbackError: {e}")
            messages.error(request, "An error occurred with your payment.")
            return redirect("home")

    return redirect("home")


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
def order_detail(request, order_id):
    """Display detailed order tracking with lifecycle progress bar."""
    order = get_object_or_404(Order, user=request.user, id=order_id)
    status_logs = order.status_logs.all()
    lifecycle_steps = ORDER_LIFECYCLE_STEPS
    
    return render(request, "ShopperMartapp/order_detail.html", {
        "order": order,
        "status_logs": status_logs,
        "lifecycle_steps": lifecycle_steps,
    })


@login_required
@transaction.atomic
def cancel_order(request, order_id):

    """Cancel an order, update status, and restore stock."""
    order = get_object_or_404(Order, user=request.user, id=order_id)
    
    if order.status == 'cancelled':
        messages.warning(request, "This order is already cancelled.")
        return redirect("my_orders")
    
    # 3. SHIPMENT LOCK (Edge Case #8 - Cancelled a Shipped Order)
    if order.status not in ['pending', 'processing']:
        messages.error(request, f"Cancellation failed: Order is already in '{order.status}' state.")
        return redirect("order_detail", order_id=order.id)
        
    # Restore stock
    for item in order.items.all():
        if item.product:
            # We use select_for_update here too to be safe
            product = Product.objects.select_for_update().get(id=item.product.id)
            product.stock = F('stock') + item.quantity
            product.save()
            
    # Use the formal state transition
    order.change_status('cancelled', user=request.user, note="User cancelled the order.")
    
    messages.info(request, "Order cancelled successfully. Items have been returned to our inventory.")
    return redirect("my_orders")
