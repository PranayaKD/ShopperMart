import os
import subprocess
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Backs up the PostgreSQL database to a backups directory using pg_dump.'

    def handle(self, *args, **options):
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            self.stdout.write(self.style.SUCCESS(f'Created backup directory: {backup_dir}'))

        db_config = settings.DATABASES.get('default')
        if not db_config:
            self.stdout.write(self.style.ERROR('No default database configuration found.'))
            return

        db_name = db_config.get('NAME')
        db_user = db_config.get('USER')
        db_host = db_config.get('HOST', 'localhost')
        db_port = str(db_config.get('PORT', 5432))
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'pg_backup_{db_name}_{timestamp}.sql'
        backup_path = os.path.join(backup_dir, backup_filename)

        env = os.environ.copy()
        if db_config.get('PASSWORD'):
            env['PGPASSWORD'] = str(db_config.get('PASSWORD'))

        pg_dump_cmd = [
            'pg_dump',
            '-h', db_host,
            '-p', db_port,
            '-U', db_user or 'postgres',
            '-F', 'c',  # Custom compressed PostgreSQL archive format
            '-f', backup_path,
            db_name
        ]

        try:
            subprocess.run(pg_dump_cmd, env=env, check=True)
            self.stdout.write(self.style.SUCCESS(f'PostgreSQL backup created successfully: {backup_path}'))
        except FileNotFoundError:
            self.stdout.write(self.style.WARNING('pg_dump command not in PATH. Ensure PostgreSQL client tools are installed.'))
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f'pg_dump failed with return code {e.returncode}'))
