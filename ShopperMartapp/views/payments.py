"""
Razorpay Standard Web Checkout Integration Views
Implements:
1. POST /api/create-order: Creates order with Razorpay Orders API
2. POST /api/verify-payment: Verifies HMAC-SHA256 signature
"""
import hmac
import hashlib
import json
import logging
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from ..models import Order
from .cart import get_cart
from .orders import finalize_order

logger = logging.getLogger(__name__)


def _get_razorpay_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise ValueError("Razorpay credentials are not configured in settings.")
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@csrf_exempt
@require_POST
def create_order(request):
    """
    STEP 1: BACKEND - Create Order
    Endpoint: POST /api/create-order (and /api/v1/payments/create-order/)
    Calls: Razorpay API POST https://api.razorpay.com/v1/orders
    Request: { amount (paise), currency, receipt }
    Return: { order_id, amount, currency, key_id }
    Minimum amount: 100 paise
    """
    try:
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST.dict()
    except Exception:
        return JsonResponse({"error": "Invalid request payload"}, status=400)

    amount_raw = data.get('amount')
    currency = data.get('currency', 'INR')
    receipt = data.get('receipt', '')
    custom_order_id = data.get('order_id') or data.get('custom_order_id')

    # If linked to an existing Django order, amount MUST strictly be derived from DB (prevents tampering)
    if custom_order_id:
        try:
            order_obj = Order.objects.get(id=custom_order_id)
            # Ownership validation
            if request.user.is_authenticated:
                if order_obj.user != request.user:
                    return JsonResponse({"error": "Unauthorized order access"}, status=403)
            else:
                if order_obj.user is not None:
                    return JsonResponse({"error": "Unauthorized order access"}, status=403)
                last_order_id = request.session.get('last_order_id')
                if last_order_id and str(order_obj.id) != str(last_order_id):
                    return JsonResponse({"error": "Unauthorized order access"}, status=403)

            amount_paise = int(order_obj.total * 100)
            receipt = receipt or str(order_obj.id)
        except Order.DoesNotExist:
            return JsonResponse({"error": "Order not found"}, status=404)
    else:
        # Validate amount for standalone calls without order
        try:
            amount_paise = int(amount_raw)
        except (TypeError, ValueError):
            return JsonResponse({"error": "Amount is required and must be an integer in paise."}, status=400)

    if amount_paise < 100:
        return JsonResponse({"error": "Minimum amount is 100 paise (₹1.00)."}, status=400)

    try:
        client = _get_razorpay_client()
        order_payload = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": str(receipt)[:40] if receipt else "rcpt_shoppermart",
            "payment_capture": 1
        }
        razorpay_order = client.order.create(data=order_payload)
        
        logger.info(f"Razorpay order created successfully: {razorpay_order['id']} for amount {amount_paise} paise")
        
        return JsonResponse({
            "success": True,
            "order_id": razorpay_order["id"],
            "amount": razorpay_order["amount"],
            "currency": razorpay_order["currency"],
            "key_id": settings.RAZORPAY_KEY_ID
        }, status=200)

    except ValueError as e:
        logger.error(f"Razorpay configuration error: {e}")
        return JsonResponse({"error": str(e)}, status=401)
    except razorpay.errors.BadRequestError as e:
        logger.error(f"Razorpay BadRequestError: {e}")
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Razorpay Order Creation Exception: {e}", exc_info=True)
        return JsonResponse({"error": "Failed to create Razorpay order", "details": str(e)}, status=500)


@csrf_exempt
@require_POST
def verify_payment(request):
    """
    STEP 3: BACKEND - Verify Signature
    Endpoint: POST /api/verify-payment (and /api/v1/payments/verify-payment/)
    Algorithm: HMAC-SHA256(order_id + "|" + payment_id, KEY_SECRET)
    Compare generated signature with razorpay_signature
    Return success only if signatures match
    """
    try:
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST.dict()
    except Exception:
        return JsonResponse({"success": False, "error": "Invalid request format"}, status=400)

    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    custom_order_id = data.get('custom_order_id') or data.get('order_id')

    # Validate missing fields
    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        return JsonResponse({
            "success": False,
            "error": "Missing required fields (razorpay_order_id, razorpay_payment_id, razorpay_signature)."
        }, status=400)

    # HMAC-SHA256 verification per Razorpay Standard Checkout spec:
    key_secret = settings.RAZORPAY_KEY_SECRET
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8')
    generated_signature = hmac.new(key_secret.encode('utf-8'), msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(generated_signature, razorpay_signature):
        logger.warning(f"Razorpay signature mismatch: order={razorpay_order_id}, payment={razorpay_payment_id}")
        return JsonResponse({
            "success": False,
            "error": "Signature verification failed"
        }, status=400)

    # Signatures match! If attached to an internal Django order, finalize it
    if custom_order_id:
        try:
            order = Order.objects.get(id=custom_order_id)
            # Authorization / Ownership check
            if request.user.is_authenticated:
                if order.user != request.user:
                    logger.warning(f"Unauthorized payment verification attempt by user {request.user.id} on order {order.id}")
                    return JsonResponse({"success": False, "error": "Unauthorized order access"}, status=403)
            else:
                if order.user is not None:
                    return JsonResponse({"success": False, "error": "Unauthorized order access"}, status=403)
                last_order_id = request.session.get('last_order_id')
                if last_order_id and str(order.id) != str(last_order_id):
                    return JsonResponse({"success": False, "error": "Unauthorized order access"}, status=403)

            # Verification of paid amount from Razorpay
            try:
                client = _get_razorpay_client()
                payment_fetch = client.payment.fetch(razorpay_payment_id)
                expected_amount_paise = int(order.total * 100)
                if payment_fetch.get('amount') and payment_fetch.get('amount') != expected_amount_paise:
                    logger.error(f"PaymentAmountMismatch: order {order.id} expected {expected_amount_paise} got {payment_fetch.get('amount')}")
                    return JsonResponse({"success": False, "error": "Payment amount mismatch detected"}, status=400)
            except Exception as pe:
                logger.warning(f"Could not verify payment amount from Razorpay fetch API: {pe}")

            cart = get_cart(request)
            if order.status == 'pending':
                finalize_order(request, order, cart)
        except Order.DoesNotExist:
            logger.warning(f"Payment verified for unknown order ID: {custom_order_id}")
            return JsonResponse({"success": False, "error": "Order not found"}, status=404)
        except Exception as e:
            logger.error(f"Error finalizing order {custom_order_id}: {e}", exc_info=True)
            return JsonResponse({"success": False, "error": "Order finalization failed"}, status=500)

    logger.info(f"Razorpay payment verified successfully: payment_id={razorpay_payment_id}, order_id={razorpay_order_id}")
    return JsonResponse({
        "success": True,
        "message": "Payment verified successfully",
        "payment_id": razorpay_payment_id,
        "order_id": razorpay_order_id
    }, status=200)

