import os
import shutil
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Backs up the SQLite database to a backups directory.'

    def handle(self, *args, **options):
        # 1. Ensure backup directory exists
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            self.stdout.write(self.style.SUCCESS(f'Created backup directory: {backup_dir}'))

        # 2. Get the database path from settings
        db_config = settings.DATABASES.get('default')
        if not db_config:
            self.stdout.write(self.style.ERROR('No default database configuration found.'))
            return

        db_engine = db_config.get('ENGINE')
        
        # We only handle SQLite automatically. For others, we provide guidance.
        if 'sqlite' in db_engine:
            db_path = db_config.get('NAME')
            if not os.path.exists(db_path):
                self.stdout.write(self.style.ERROR(f'Database file not found at: {db_path}'))
                return

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'db_backup_{timestamp}.sqlite3'
            backup_path = os.path.join(backup_dir, backup_filename)

            try:
                # Optimized for SQLite: Use VACUUM INTO for a safe, atomic backup (SQLite 3.27+)
                # Fallback to copy if engine is very old or VACUUM fails
                import sqlite3
                conn = sqlite3.connect(db_path)
                try:
                    # SQLite 3.27.0+ supports VACUUM INTO which is perfect for backups
                    conn.execute(f"VACUUM INTO '{backup_path.replace(\"'\", \"''\")}'")
                    self.stdout.write(self.style.SUCCESS(f'Atomic backup created via VACUUM INTO: {backup_path}'))
                except sqlite3.OperationalError:
                     # Fallback for older SQLite versions
                     shutil.copy2(db_path, backup_path)
                     self.stdout.write(self.style.SUCCESS(f'Database copied (legacy mode) to: {backup_path}'))
                finally:
                    conn.close()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to backup database: {str(e)}'))
        else:
            self.stdout.write(self.style.WARNING(
                f'Automatic backup not supported for database engine: {db_engine}. '
                'Please use specialized tools like pg_dump for production PostgreSQL databases.'
            ))
