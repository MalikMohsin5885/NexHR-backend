# seeder.py
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nexhr_backend.settings")
django.setup()

from accounts.models import User, Role

def run():
    roles = ["ADMIN", "FINANCE", "HR", "EMPLOYEE"]
    role_objs = {}
    for r in roles:
        role_objs[r], _ = Role.objects.get_or_create(name=r)

    users_data = [
        {"email": "admin@nexhr.com", "fname": "Admin", "role": "ADMIN"},
        {"email": "finance@nexhr.com", "fname": "Finance", "role": "FINANCE"},
        {"email": "hr@nexhr.com", "fname": "HR", "role": "HR"},
        {"email": "employee@nexhr.com", "fname": "Employee", "role": "EMPLOYEE"},
    ]

    for data in users_data:
        user, created = User.objects.get_or_create(
            email=data["email"],
            defaults={
                "fname": data["fname"],
                "is_active": True,
                "is_verified": True,
                "is_staff": False,
            },
        )

        # Always reset password to known value
        user.set_password("Password123!")
        user.is_verified = True
        user.is_active = True
        user.save()

        user.roles.add(role_objs[data["role"]])
        print(f"✔ Seeded user {user.email} with role {data['role']} (password = Password123!)")

if __name__ == "__main__":
    run()
