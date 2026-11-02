import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Quickly create an admin superuser account if it does not already exist."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default=os.getenv("ADMIN_USERNAME", "admin"),
            help="Admin username (default: env ADMIN_USERNAME or 'admin')",
        )
        parser.add_argument(
            "--email",
            default=os.getenv("ADMIN_EMAIL", "admin@shoppermart.com"),
            help="Admin email address",
        )
        parser.add_argument(
            "--password",
            default=os.getenv("ADMIN_PASSWORD", "Admin@12345"),
            help="Admin password (default: env ADMIN_PASSWORD or 'Admin@12345')",
        )

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"]
        custom_env_password = os.getenv("ADMIN_PASSWORD")

        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            user.is_staff = True
            user.is_superuser = True
            if custom_env_password:
                user.set_password(custom_env_password)
            user.save()
            self.stdout.write(
                self.style.WARNING(f"Superuser '{username}' already exists. Staff permissions verified.")
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Superuser '{username}' successfully created! You can now log in at /admin/ and /dashboard/."
            )
        )
