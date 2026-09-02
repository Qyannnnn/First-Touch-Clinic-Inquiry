from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from core.models import Clinic


class Command(BaseCommand):
    help = "Prepare the local Nightingale demonstration environment"

    def handle(self, *args, **options):

        if not settings.DEBUG:
            raise CommandError(
                "setup_demo is only available when DEBUG=True."
            )

        self.stdout.write("Preparing Nightingale demo...")

        # Create database tables
        call_command("migrate", interactive=False)

        # Create demo clinic
        clinic, created = Clinic.objects.get_or_create(
            slug="nightingale-demo",
            defaults={
                "name": "Nightingale Demo Clinic",
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS("Created demo clinic.")
            )
        else:
            self.stdout.write(
                "Demo clinic already exists."
            )

        # Create demo staff account
        User = get_user_model()

        username = "demo_staff"
        password = "NightingaleDemo123!"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": "demo@nightingale.local",
            },
        )

        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Nightingale demo is ready."
            )
        )

        self.stdout.write("")
        self.stdout.write("Staff Portal:")
        self.stdout.write(
            "http://127.0.0.1:8000/staff/"
        )

        self.stdout.write("")
        self.stdout.write("Demo staff login:")
        self.stdout.write(
            f"Username: {username}"
        )
        self.stdout.write(
            f"Password: {password}"
        )

        self.stdout.write("")
        self.stdout.write(
            "Demo credentials only - not for production use."
        )