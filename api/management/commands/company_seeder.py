from django.core.management.base import BaseCommand
from accounts.models import Company, Branch, Department, Role, Permission, User

class Command(BaseCommand):
    help = "Seed initial company, roles, permissions, and users"

    def handle(self, *args, **kwargs):
        # 1. Company
        company, _ = Company.objects.get_or_create(
            name="SlashLogics",
            defaults={
                "industry": "Software & IT",
                "email": "info@slashlogics.com",
                "phone": "+92-300-1234567",
            },
        )

        # 2. Branch
        branch, _ = Branch.objects.get_or_create(
            company=company,
            name="Lahore Branch",
            defaults={
                "address": "Gulberg III, Lahore",
                "city": "Lahore",
                "state": "Punjab",
                "country": "Pakistan",
                "zip_code": "54000",
            },
        )

        # 3. Departments
        hr_dept, _ = Department.objects.get_or_create(name="HR", branch=branch)
        it_dept, _ = Department.objects.get_or_create(name="IT", branch=branch)
        finance_dept, _ = Department.objects.get_or_create(name="Finance", branch=branch)
        admin_dept, _ = Department.objects.get_or_create(name="Administration", branch=branch)

        # 4. Permissions
        perms = {
            "manage_users": "Can create/update/delete users",
            "view_reports": "Can view reports",
            "manage_finances": "Can manage financial records",
            "manage_hr": "Can manage HR operations",
            "general_access": "General employee access",
        }

        perm_objs = {}
        for name, desc in perms.items():
            perm, _ = Permission.objects.get_or_create(name=name, defaults={"description": desc})
            perm_objs[name] = perm

        # 5. Roles
        hr_role, _ = Role.objects.get_or_create(name="HR", defaults={"description": "Handles HR tasks"})
        finance_role, _ = Role.objects.get_or_create(name="Finance Manager", defaults={"description": "Manages finance"})
        admin_role, _ = Role.objects.get_or_create(name="Admin", defaults={"description": "System administrator"})
        emp_role, _ = Role.objects.get_or_create(name="Employee", defaults={"description": "General employee"})

        # Assign permissions to roles
        hr_role.permissions.set([perm_objs["manage_hr"], perm_objs["general_access"]])
        finance_role.permissions.set([perm_objs["manage_finances"], perm_objs["view_reports"]])
        admin_role.permissions.set([perm_objs["manage_users"], perm_objs["view_reports"]])
        emp_role.permissions.set([perm_objs["general_access"]])

        # 6. Users
        def create_user(fname, lname, email, role, department):
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "fname": fname,
                    "lname": lname,
                    "phone": "+92-3xx-xxxxxxx",
                    "company": company,
                    "branch": branch,
                    "department": department,
                    "status": "active",
                    "is_active": True,
                    "is_verified": True,
                    "is_staff": False,
                    "login_method": "email",
                },
            )
            user.set_password("test@1234")
            user.save()
            user.roles.set([role])
            return user

        # HR
        create_user("Ayesha", "Khan", "ayesha.khan@slashlogics.com", hr_role, hr_dept)

        # Employees
        create_user("Ali", "Raza", "ali.raza@slashlogics.com", emp_role, it_dept)
        create_user("Sara", "Malik", "sara.malik@slashlogics.com", emp_role, it_dept)

        # Admin
        admin = create_user("Imran", "Ahmed", "imran.ahmed@slashlogics.com", admin_role, admin_dept)
        admin.is_staff = True
        admin.save()

        # Finance Manager
        create_user("Farah", "Iqbal", "farah.iqbal@slashlogics.com", finance_role, finance_dept)

        self.stdout.write(self.style.SUCCESS("✅ Database seeded successfully!"))
