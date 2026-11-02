import os
import glob
from django.core.management.base import BaseCommand
from django.conf import settings
import cloudinary
import cloudinary.uploader

class Command(BaseCommand):
    help = "Sync all existing local media files to Cloudinary persistent CDN storage."

    def handle(self, *args, **options):
        cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', '')
        api_key = getattr(settings, 'CLOUDINARY_API_KEY', '')
        api_secret = getattr(settings, 'CLOUDINARY_API_SECRET', '')

        if not (cloud_name and api_key and api_secret):
            self.stdout.write(self.style.ERROR("Cloudinary credentials missing in settings/.env!"))
            return

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )

        media_root = str(settings.MEDIA_ROOT)
        pattern = os.path.join(media_root, "products", "*.*")
        files = glob.glob(pattern)

        if not files:
            self.stdout.write(self.style.WARNING("No local product media files found."))
            return

        self.stdout.write(self.style.NOTICE(f"Syncing {len(files)} product images to Cloudinary ({cloud_name})..."))
        success_count = 0

        for idx, file_path in enumerate(files, 1):
            filename = os.path.basename(file_path)
            # Remove extension for public_id
            name_without_ext, _ = os.path.splitext(filename)
            public_id = f"media/products/{name_without_ext}"

            try:
                res = cloudinary.uploader.upload(
                    file_path,
                    public_id=public_id,
                    overwrite=True,
                    resource_type="image"
                )
                self.stdout.write(self.style.SUCCESS(f"[{idx}/{len(files)}] Synced: {filename} -> {res.get('secure_url')}"))
                success_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{idx}/{len(files)}] Failed {filename}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nAll Done! Successfully synced {success_count}/{len(files)} product images to Cloudinary."
        ))
