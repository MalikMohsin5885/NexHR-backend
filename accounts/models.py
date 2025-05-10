from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class Company(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=255)
    location = models.CharField(max_length=255, null=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.name

    def get_departments(self):
        from .models import Department
        ctype = ContentType.objects.get_for_model(Company)
        return Department.objects.filter(content_type=ctype, object_id=self.id)


class Branch(models.Model):
    id = models.AutoField(primary_key=True)
    company_id = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.name} - {self.company_id.name}"

    def get_departments(self):
        from .models import Department
        ctype = ContentType.objects.get_for_model(Branch)
        return Department.objects.filter(content_type=ctype, object_id=self.id)


class Department(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)

    # Polymorphic association
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    parent = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"{self.name} - {self.parent}"
    
    
    
class UserManager(BaseUserManager):
    def create_user(self, email, fname, lname=None, phone=None, password=None, company=None):
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(
            email=self.normalize_email(email),
            fname=fname,
            lname=lname or None,  # Ensuring None is stored instead of an empty string
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

    id = models.AutoField(primary_key=True)
    fname = models.CharField(max_length=255)
    lname = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, null=True)
    password = models.CharField(max_length=255, null=True)
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

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['fname']

    def get_roles_with_permissions(self):
        data = []
        for ur in self.roles.select_related('role').prefetch_related('role__permissions__permission'):
            data.append({
                "role": ur.role.name,
                "permissions": [p.permission.name for p in ur.role.permissions.all()]
            })
        return data

    def __str__(self):
        return f"{self.fname} {self.lname} ({'Verified' if self.is_verified else 'Unverified'})"
