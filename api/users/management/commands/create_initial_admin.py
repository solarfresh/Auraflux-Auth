from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings

# This command creates an initial admin user if none exists.
# It is useful for initial setup and deployment.

class Command(BaseCommand):
    """
    Django management command to create an initial admin user if no users exist.
    """
    help = 'Creates an initial admin user if no users exist in the database.'

    def handle(self, *args, **options):
        # Use get_user_model() to retrieve the correct user model.
        # This is the best practice for custom user models.
        User = get_user_model()

        # Check if any users already exist in the database.
        if User.objects.exists():
            self.stdout.write(self.style.SUCCESS('A user already exists. Initial admin not created.'))
            return

        # Get credentials from settings or use a default.
        # It's best practice to use environment variables for sensitive data.
        admin_username = getattr(settings, 'INITIAL_ADMIN_USERNAME', 'admin')
        admin_password = getattr(settings, 'INITIAL_ADMIN_PASSWORD', 'password')
        admin_email = getattr(settings, 'INITIAL_ADMIN_EMAIL', 'admin@example.com')

        try:
            # Create a new superuser with full permissions.
            admin_user = User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_password
            )

            # Set the role to 'admin' using your custom `User.Role` enum.
            admin_user.role = User.Role.ADMIN
            admin_user.save()

            self.stdout.write(self.style.SUCCESS(f'Successfully created initial admin user: {admin_username}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred while creating the admin user: {e}'))