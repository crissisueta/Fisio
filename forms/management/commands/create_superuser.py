from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Creates or updates the default superuser (Kris)'

    def handle(self, *args, **options):
        User = get_user_model()
        username = 'Kris'
        email = 'admin@example.com'
        password = 'Kris'

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'is_staff': True, 'is_superuser': True},
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created successfully."))
        else:
            # Ensure existing user has superuser privileges and the correct password
            updated = False
            if not user.is_superuser or not user.is_staff:
                user.is_superuser = True
                user.is_staff = True
                updated = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' already exists — password updated."))
