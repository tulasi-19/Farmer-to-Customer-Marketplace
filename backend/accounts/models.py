from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model (must exist before the very first migration).
    `role` drives permissions; it can NEVER be set through public APIs
    except to 'farmer' or 'customer' at registration.
    """

    class Role(models.TextChoices):
        FARMER = 'farmer', 'Farmer'
        CUSTOMER = 'customer', 'Customer'
        ADMIN = 'admin', 'Admin'

    email = models.EmailField('email address', unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CUSTOMER, db_index=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    REQUIRED_FIELDS = ['email']

    def save(self, *args, **kwargs):
        # `createsuperuser` must produce a real admin, not a "customer".
        if self.is_superuser:
            self.role = self.Role.ADMIN
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"
