import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from ShopperMartapp.models import Order, Product

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Automatically expires pending orders older than the specified timeout (default 15 mins) and restores inventory stock."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=15,
            help="Timeout threshold in minutes after which pending orders expire (default: 15)."
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the cleanup without updating database or restoring stock."
        )

    def handle(self, *args, **options):
        timeout_minutes = options["timeout"]
        dry_run = options["dry_run"]
        cutoff_time = timezone.now() - timedelta(minutes=timeout_minutes)

        self.stdout.write(
            self.style.NOTICE(
                f"Scanning for pending orders created before {cutoff_time.strftime('%Y-%m-%d %H:%M:%S %Z')} (Timeout: {timeout_minutes}m)..."
            )
        )

        expired_orders_qs = Order.objects.filter(
            status="pending",
            created_at__lte=cutoff_time
        ).order_by("created_at")

        total_orders = expired_orders_qs.count()
        if total_orders == 0:
            self.stdout.write(self.style.SUCCESS("No expired pending orders found. Everything is up to date."))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"[DRY RUN] Found {total_orders} order(s) eligible for cancellation:")
            )
            for order in expired_orders_qs:
                self.stdout.write(f"  - Order #{order.id} | Total: Rs. {order.total} | Created: {order.created_at}")
            return

        cancelled_count = 0
        restored_items_count = 0

        for order in expired_orders_qs:
            try:
                with transaction.atomic():
                    # Lock the order to prevent race conditions with concurrent payment webhooks
                    locked_order = Order.objects.select_for_update().filter(id=order.id, status="pending").first()
                    if not locked_order:
                        continue

                    # Restore stock for each item in the order
                    for item in locked_order.items.select_related("product").all():
                        if item.product_id:
                            product = Product.objects.select_for_update().filter(id=item.product_id).first()
                            if product:
                                product.stock = F("stock") + item.quantity
                                product.save(update_fields=["stock"])
                                restored_items_count += item.quantity

                    # Cancel the order and record audit log
                    locked_order.change_status(
                        "cancelled",
                        user=None,
                        note=f"Auto-cancelled: Payment window expired after {timeout_minutes} minutes."
                    )
                    cancelled_count += 1
                    logger.info(f"Order #{locked_order.id} auto-cancelled due to {timeout_minutes}m timeout.")

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error cancelling Order #{order.id}: {e}"))
                logger.error(f"Failed to auto-expire Order #{order.id}: {e}", exc_info=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully cancelled {cancelled_count}/{total_orders} expired pending order(s) and restored {restored_items_count} item(s) to stock."
            )
        )
