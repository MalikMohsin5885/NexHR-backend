from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.contrib.contenttypes.models import ContentType


class Company(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.name


class Branch(models.Model):
    id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, null=True)
    zip_code = models.CharField(max_length=20, null=True)

    def __str__(self):
        return f"{self.name} - {self.city}, {self.country}"


class Department(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='departments')

    def __str__(self):
        return f"{self.name} - {self.branch.name}"   
<<<<<<< HEAD


=======
    


class Role(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    permissions = models.ManyToManyField(
        "Permission",
        related_name="roles",
        blank=True
    )

    def __str__(self):
        return self.name


class Permission(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


    
>>>>>>> development
class UserManager(BaseUserManager):
    def create_user(self, email, fname, lname=None, phone=None, password=None, company=None):
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(
            email=self.normalize_email(email),
            fname=fname,
            lname=lname or None,
            phone=phone or "",
            company=company
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, fname, lname=None, password=None, phone=None, company=None):
        user = self.create_user(email=email, fname=fname, lname=lname, phone=phone, password=password, company=company)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    LOGIN_METHOD_CHOICES = [
        ('email', 'Email/Password'),
        ('google', 'Google'),
    ]

    ROLE_CHOICES = [
        ("ADMIN", "Admin"),
        ("FINANCE", "Finance"),
        ("HR", "HR"),
        ("EMPLOYEE", "Employee"),
    ]

    id = models.AutoField(primary_key=True)
    fname = models.CharField(max_length=255)
    lname = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, null=True)
    password = models.CharField(max_length=255, null=True)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="FINANCE")

    status = models.CharField(max_length=10, null=True, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    login_method = models.CharField(max_length=20, choices=LOGIN_METHOD_CHOICES, default='email')

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="users", null=True, blank=True)
    branch = models.ForeignKey('Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name="users")
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)

    
    # ✅ ManyToMany instead of explicit join table
    roles = models.ManyToManyField(Role, related_name="users", blank=True)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['fname']

    def get_roles_with_permissions(self):
        return [
            {
                "role": role.name,
                "permissions": [p.name for p in role.permissions.all()]
            }
            for role in self.roles.prefetch_related("permissions")
        ]

    def __str__(self):
        return f"{self.fname} {self.lname or ''} ({'Verified' if self.is_verified else 'Unverified'})"



class CompanyLinkedInAuth(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='linkedin_auth')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    access_token = models.TextField(null=True, blank=True)
    id_token = models.TextField(null=True, blank=True)
    person_urn = models.TextField(null=True, blank=True)
    
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
