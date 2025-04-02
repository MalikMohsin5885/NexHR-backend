from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class Company(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50)

    def __str__(self):
        return self.name

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

    id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="users", null=True, blank=True)
    fname = models.CharField(max_length=255)
    lname = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, null=True)
    password = models.CharField(max_length=255)
    status = models.CharField(max_length=10, null=True, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)  # New field

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['fname']

    def __str__(self):
        return f"{self.fname} {self.lname} ({'Verified' if self.is_verified else 'Unverified'})"
