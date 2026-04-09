import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from .models import Profile, Cart, CartItem

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        
        # Send Welcome Email immediately upon account creation
        if instance.email:
            try:
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@shoppermart.com')
                send_mail(
                    subject="Welcome to ShopperMart!",
                    message=f"Hello {instance.username},\n\nWelcome to ShopperMart! Your account has been successfully created, and we are excited to have you on board. Start exploring our latest collections today!\n\nBest regards,\nThe ShopperMart Team",
                    from_email=from_email,
                    recipient_list=[instance.email],
                    fail_silently=True,
                )
                logger.info(f"Welcome email dispatched for {instance.email}")
            except Exception as e:
                logger.error(f"Failed to send welcome email to {instance.email}: {e}")

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()

@receiver(user_logged_in)
@transaction.atomic
def merge_carts(sender, user, request, **kwargs):
    """
    When a user logs in, merge their session-based guest cart into their permanent user cart.
    """
    session_key = request.session.session_key
    if not session_key:
        return

    try:
        # 1. Find guest cart
        guest_cart = Cart.objects.get(session_key=session_key, user=None)
        
        # 2. Get or create user cart
        user_cart, _ = Cart.objects.get_or_create(user=user)
        
        # 3. Transfer items
        guest_items = guest_cart.items.all()
        for item in guest_items:
            # Check if product already exists in user cart
            user_item, created = CartItem.objects.get_or_create(cart=user_cart, product=item.product)
            if not created:
                user_item.quantity += item.quantity
            else:
                user_item.quantity = item.quantity
            user_item.save()
        
        # 4. Cleanup guest cart
        guest_cart.delete()
        logger.info(f"CartMerge: Merged guest cart items into user {user.id}'s permanent cart.")
        
    except Cart.DoesNotExist:
        # No guest cart found, nothing to merge
        pass
