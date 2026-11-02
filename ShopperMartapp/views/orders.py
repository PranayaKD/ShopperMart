import logging
import json
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import F
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)
from .cart import get_cart
from ..models import Product, Order, OrderItem, OrderStatusLog, ORDER_LIFECYCLE_STEPS
from ..forms import CheckoutForm
import razorpay
from django.conf import settings
from django_ratelimit.decorators import ratelimit
from decimal import Decimal, InvalidOperation

from datetime import timedelta
from django.utils import timezone

def cleanup_stale_pending_orders(user=None, timeout_minutes=15):
    """Auto-cancel pending orders older than 15 mins to restore inventory stock."""
    try:
        cutoff = timezone.now() - timedelta(minutes=timeout_minutes)
        qs = Order.objects.filter(status='pending', created_at__lte=cutoff)
        if user and user.is_authenticated:
            qs = qs.filter(user=user)
        for order in qs[:20]:
            with transaction.atomic():
                locked_order = Order.objects.select_for_update().filter(id=order.id, status='pending').first()
                if not locked_order:
                    continue
                for item in locked_order.items.select_related('product').all():
                    if item.product_id:
                        Product.objects.filter(id=item.product_id).update(stock=F('stock') + item.quantity)
                locked_order.change_status('cancelled', note=f"Auto-cancelled: Payment window expired after {timeout_minutes} minutes.")
    except Exception as e:
        logger.warning(f"Opportunistic stale order cleanup notice: {e}")

# -------------------- CHECKOUT & ORDERS --------------------
@ratelimit(key='ip', rate='10/m', block=True)
@transaction.atomic
def checkout(request):
    """Checkout process - create an order from cart items with FIRST100 coupon support. Support Guest Checkout."""
    # Opportunistically expire user's stale pending orders
    cleanup_stale_pending_orders(user=request.user if request.user.is_authenticated else None)

    cart = get_cart(request)
    cart_items = cart.items.select_related('product').all()
    subtotal = Decimal(cart.total_price())

    applied_coupon = request.session.get('applied_coupon')
    discount = Decimal("0.00")
    if applied_coupon in ('FIRST100', 'SHOPPER100', 'ZEPTO100') and subtotal >= Decimal("100.00"):
        discount = min(Decimal("100.00"), subtotal)
    else:
        applied_coupon = None

    free_delivery_threshold = Decimal("149.00")
    if cart_items:
        delivery_fee = Decimal("0.00") if subtotal >= free_delivery_threshold else Decimal("25.00")
    else:
        delivery_fee = Decimal("0.00")

    total = max(Decimal("0.00"), subtotal - discount + delivery_fee)

    if request.method == "POST":
        if not cart_items:
            messages.error(request, "Your cart is empty.")
            return redirect("cart")

        # 1. IDEMPOTENCY CHECK
        checkout_token = request.POST.get("checkout_token")
        if not checkout_token or checkout_token == request.session.get('last_checkout_token'):
            messages.warning(request, "This order is already being processed or has been completed.")
            return redirect("cart")

        # 2. PRICE LOCK VERIFICATION (Fixed: Guard against malformed input)
        posted_total = request.POST.get("total_verify")
        try:
            if posted_total and Decimal(posted_total) != Decimal(total):
                 messages.error(request, "The prices in your cart have changed. Please review and try again.")
                 return redirect("cart")
        except (InvalidOperation, TypeError):
            messages.error(request, "Price verification failed. Please try again.")
            return redirect("cart")

        # 3. STOCK PRE-CHECK
        for item in cart_items:
            if item.quantity > item.product.stock:
                messages.error(request, f"Sorry, {item.product.name} is no longer available in the requested quantity.")
                return redirect("cart")

        form = CheckoutForm(request.POST)
        if form.is_valid():
            user = request.user if request.user.is_authenticated else None
            
            try:
                # Create Order (status remains pending)
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
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price,
                    )
                
                # Mark token as used
                request.session['last_checkout_token'] = checkout_token
                
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

                    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
                        profile = getattr(order.user, 'profile', None) if order.user else None
                        return JsonResponse({
                            "success": True,
                            "order_id": str(order.id),
                            "razorpay_order_id": razorpay_order["id"],
                            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                            "amount": int(total * 100),
                            "currency": "INR",
                            "customer_name": order.full_name,
                            "customer_email": order.email,
                            "customer_contact": getattr(profile, 'phone', '')
                        })
                    
                    return render(request, "ShopperMartapp/payment.html", {
                        "order": order,
                        "razorpay_order_id": razorpay_order["id"],
                        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                        "amount": int(total * 100)
                    })
                
                else:
                    # Cash on delivery - finalize immediately
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
                        finalize_order(request, order, cart)
                        return JsonResponse({
                            "success": True,
                            "order_id": str(order.id),
                            "redirect_url": reverse("order_success")
                        })
                    return finalize_order(request, order, cart)

            except Exception as e:
                logger.error(f"CheckoutError: {e}")
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({"success": False, "error": str(e)}, status=500)
                messages.error(request, "An unexpected error occurred during checkout. Please try again.")
                return redirect("cart")
    else:
        initial_data = {}
        if request.user.is_authenticated:
            # Handle potential missing profile
            profile = getattr(request.user, 'profile', None)
            initial_data = {
                "full_name": getattr(profile, 'full_name', ''),
                "email": request.user.email,
                "address": getattr(profile, 'address_line1', ''),
                "landmark": getattr(profile, 'landmark', ''),
                "city": getattr(profile, 'city', ''),
                "state": getattr(profile, 'state', ''),
                "postal_code": getattr(profile, 'pincode', '')
            }

        # Seamlessly fallback to session delivery location (from GPS / Map pin)
        session_loc = request.session.get('delivery_location', {})
        if session_loc:
            if not initial_data.get('address'):
                initial_data['address'] = session_loc.get('address') or session_loc.get('locality', '')
            if not initial_data.get('city'):
                initial_data['city'] = session_loc.get('city', '')
            if not initial_data.get('state'):
                initial_data['state'] = session_loc.get('state', '')
            if not initial_data.get('postal_code'):
                initial_data['postal_code'] = session_loc.get('postal_code', '')
            if not initial_data.get('landmark') and session_loc.get('landmark'):
                initial_data['landmark'] = session_loc.get('landmark', '')
        form = CheckoutForm(initial=initial_data)

    import secrets
    checkout_token = secrets.token_hex(16)

    return render(request, "ShopperMartapp/checkout.html", {
        "cart_items": cart_items,
        "subtotal": subtotal,
        "discount": discount,
        "delivery_fee": delivery_fee,
        "free_delivery_threshold": free_delivery_threshold,
        "applied_coupon": applied_coupon,
        "total": total,
        "form": form,
        "checkout_token": checkout_token
    })


def finalize_order(request, order, cart):
    """Internal helper to deduct stock and clear cart once payment is confirmed."""
    try:
        # Stock deduction and cart clearing must be atomic
        with transaction.atomic():
            for item in order.items.all():
                # select_for_update to prevent race conditions during final deduction
                product = Product.objects.select_for_update().get(id=item.product.id)
                if item.quantity > product.stock:
                    raise ValueError(f"Insufficient stock for {product.name} during finalization.")

                product.stock = F('stock') - item.quantity
                product.save()

            # CLEAR CART (AS REQUESTED: Only clear after success)
            cart.items.all().delete()
            request.session.pop('applied_coupon', None)

            # Status change MUST be inside the atomic block for transactional consistency
            user = request.user if request.user.is_authenticated else None
            order.change_status('processing', user=user, note="Stock deducted and order confirmed.")
        
        request.session['last_order_id'] = str(order.id)
        logger.info(f"OrderSuccess: Order {order.id} finalized.")
        messages.success(request, f"Order confirmed successfully! Order ID: {order.id}")
        return redirect("order_success")
        
    except ValueError as ve:
        # Atomic block has rolled back. Now we handle the failure state.
        logger.error(f"FinalizationError: {ve}")
        # Cancellation and user messaging happen outside the rolled-back transaction
        order.change_status('cancelled', note=str(ve))
        messages.error(request, "Unfortunately, some items sold out while you were paying. Your payment (if any) will be refunded.")
        return redirect("cart")


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
            order = Order.objects.get(id=order_id_str)
            cart = get_cart(request)
            
            # Verify amount matches order total if fetch succeeds
            try:
                payment_fetch = client.payment.fetch(razorpay_payment_id)
                expected_amount_paise = int(order.total * 100)
                if payment_fetch.get('amount') and payment_fetch.get('amount') != expected_amount_paise:
                    logger.error(f"PaymentAmountMismatch: order {order.id} expected {expected_amount_paise} got {payment_fetch.get('amount')}")
                    messages.error(request, "Payment amount mismatch detected. Please contact support.")
                    return redirect("cart")
            except Exception as pe:
                logger.warning(f"Could not verify payment amount from Razorpay fetch API: {pe}")

            if order.status == 'pending':
                return finalize_order(request, order, cart)
            
            return redirect("order_success")
            
        except razorpay.errors.SignatureVerificationError:
            logger.error("PaymentFailed: Razorpay signature verification failed.")
            messages.error(request, "Payment verification failed. Please try again.")
            return redirect("cart") # Take back to cart if payment fails
        except Exception as e:
            logger.error(f"PaymentCallbackError: {e}")
            messages.error(request, "An error occurred with your payment.")
            return redirect("cart")

    return redirect("home")


@csrf_exempt
def razorpay_webhook(request):
    """
    Asynchronous Razorpay webhook handler.
    Ensures that orders are marked paid and processed even if customer loses connection
    or closes their mobile browser tab after UPI PIN authorization.
    """
    if request.method != "POST":
        return HttpResponse(status=405)

    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '') or settings.RAZORPAY_KEY_SECRET
    webhook_signature = request.headers.get("X-Razorpay-Signature", "")
    webhook_body = request.body.decode('utf-8')

    if webhook_secret:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            client.utility.verify_webhook_signature(webhook_body, webhook_signature, webhook_secret)
        except razorpay.errors.SignatureVerificationError:
            logger.warning("Razorpay Webhook: Invalid signature received.")
            return HttpResponse("Invalid signature", status=400)

    try:
        data = json.loads(webhook_body)
        event = data.get('event')

        if event in ('order.paid', 'payment.captured'):
            payload = data.get('payload', {}).get('payment', {}).get('entity', {})
            order_id_notes = payload.get('notes', {}).get('order_id')
            payment_id = payload.get('id')

            if order_id_notes:
                with transaction.atomic():
                    order = Order.objects.select_for_update().filter(id=order_id_notes).first()
                    if order and order.status == 'pending':
                        order.change_status('processing', note=f"Paid via Razorpay Webhook (Payment ID: {payment_id})")
                        order.save()
                        logger.info(f"Webhook finalized Order #{order.id} from event {event}")
        return HttpResponse("Webhook processed", status=200)
    except Exception as e:
        logger.error(f"Razorpay Webhook Error: {e}", exc_info=True)
        return HttpResponse("Server error", status=500)


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
    cleanup_stale_pending_orders(user=request.user)
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
@require_POST
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
