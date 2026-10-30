from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from products.models import Product


class Review(models.Model):
    """A customer's rating of a product. Eligibility is proved through `order_item`:
    the customer must hold a DELIVERED purchase of that product (checked server-side)."""

    class Status(models.TextChoices):
        PUBLISHED = 'published', 'Published'
        HIDDEN = 'hidden', 'Hidden by moderator'

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    order_item = models.ForeignKey('orders.OrderItem', null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PUBLISHED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='one_review_per_user_per_product'),
            models.CheckConstraint(check=Q(rating__gte=1) & Q(rating__lte=5), name='review_rating_1_to_5'),
        ]

    def __str__(self):
        return f"{self.rating}* by {self.user.username} on {self.product.name}"
