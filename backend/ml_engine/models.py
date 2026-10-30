from django.conf import settings
from django.db import models

from products.models import Product


class AIPrediction(models.Model):
    """Audit trail of predictions shown to farmers. The predicted price is stored HERE,
    separately from Product.price, which is never changed automatically."""

    class Kind(models.TextChoices):
        DEMAND = 'demand', 'Demand'
        PRICE = 'price', 'Price recommendation'

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ai_predictions')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    kind = models.CharField(max_length=10, choices=Kind.choices, db_index=True)
    predicted_value = models.DecimalField(max_digits=12, decimal_places=2)
    range_low = models.DecimalField(max_digits=12, decimal_places=2)
    range_high = models.DecimalField(max_digits=12, decimal_places=2)
    inputs = models.JSONField(default=dict)
    warnings = models.JSONField(default=list)
    model_version = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
