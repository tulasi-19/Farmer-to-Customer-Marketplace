from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from common.validators import validate_image_upload
from farms.models import Farm


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    class Unit(models.TextChoices):
        KG = 'kg', 'Kilogram'
        GRAM = 'gram', 'Gram'
        QUINTAL = 'quintal', 'Quintal'
        DOZEN = 'dozen', 'Dozen'
        LITRE = 'litre', 'Litre'
        PIECE = 'piece', 'Piece'

    # PROTECT: a farm/category with products can't be silently deleted.
    farm = models.ForeignKey(Farm, on_delete=models.PROTECT, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    name = models.CharField(max_length=150, db_index=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2,
                                validators=[MinValueValidator(Decimal('0.01'))])  # per unit
    quantity_available = models.DecimalField(max_digits=10, decimal_places=2,
                                             validators=[MinValueValidator(Decimal('0'))])
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.KG)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True,
                              validators=[validate_image_upload])
    origin = models.CharField(max_length=150, blank=True, help_text='e.g. village / farm plot')
    # is_active=False means "archived/hidden", used instead of deleting products that have order history.
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['price']),
        ]
        constraints = [
            models.CheckConstraint(check=Q(price__gt=0), name='product_price_positive'),
            models.CheckConstraint(check=Q(quantity_available__gte=0), name='product_stock_non_negative'),
        ]

    def __str__(self):
        return f"{self.name} - {self.farm.farm_name}"
