from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from api.models import Role, UserRoles


class Command(BaseCommand):
    help = "Create default roles and assign them to predefined users by email."

    def handle(self, *args, **options):
        with transaction.atomic():
            hr_role, _ = Role.objects.get_or_create(name="HR")
            admin_role, _ = Role.objects.get_or_create(name="Admin")
            finance_role, _ = Role.objects.get_or_create(name="Finance Manager")
            emp_role, _ = Role.objects.get_or_create(name="Employee")

            users_roles = [
                ("ayesha.khan@slashlogics.com", hr_role),
                ("imran.ahmed@slashlogics.com", admin_role),
                ("farah.iqbal@slashlogics.com", finance_role),
                ("ali.raza@slashlogics.com", emp_role),
                ("sara.malik@slashlogics.com", emp_role),
            ]

            for email, role in users_roles:
                try:
                    user = User.objects.get(email=email)
                    UserRoles.objects.get_or_create(user=user, role=role)
                    self.stdout.write(self.style.SUCCESS(f"Assigned {role.name} to {email}"))
                except User.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"User {email} not found"))

        self.stdout.write(self.style.SUCCESS("Role assignment completed."))


