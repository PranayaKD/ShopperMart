import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from ShopperMartapp.models import Cart, CartItem

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Purges inactive guest shopping carts older than the specified retention window (default 7 days) to prevent table bloat."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Retention threshold in days after which unauthenticated guest carts expire (default: 7)."
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the cleanup without actually deleting database rows."
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        cutoff_time = timezone.now() - timedelta(days=days)

        self.stdout.write(
            self.style.NOTICE(
                f"Scanning for guest carts created before {cutoff_time.strftime('%Y-%m-%d %H:%M:%S %Z')} (Retention: {days} days)..."
            )
        )

        # Query only guest carts (user is None) that exceed the retention window
        expired_carts_qs = Cart.objects.filter(
            user__isnull=True,
            created_at__lte=cutoff_time
        )

        total_carts = expired_carts_qs.count()
        if total_carts == 0:
            self.stdout.write(self.style.SUCCESS("[OK] No expired guest carts found. Database is completely lean."))
            return

        total_items = CartItem.objects.filter(cart__in=expired_carts_qs).count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Found {total_carts} expired guest cart(s) with {total_items} item(s) eligible for deletion."
                )
            )
            return

        # Perform deletion in an atomic transaction
        with transaction.atomic():
            deleted_items_count, _ = CartItem.objects.filter(cart__in=expired_carts_qs).delete()
            deleted_carts_count, _ = expired_carts_qs.delete()

        msg = (
            f"[OK] Successfully purged {deleted_carts_count} expired guest cart(s) "
            f"and {deleted_items_count} item(s) older than {days} days."
        )
        logger.info(msg)
        self.stdout.write(self.style.SUCCESS(msg))
