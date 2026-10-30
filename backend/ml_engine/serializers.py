from rest_framework import serializers

from .models import AIPrediction


class _Base(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    crop = serializers.CharField(max_length=60, required=False, allow_blank=True)
    month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    supply_index = serializers.FloatField(min_value=0.1, max_value=5, required=False, default=1.0)


class DemandRequestSerializer(_Base):
    avg_weekly_units = serializers.FloatField(min_value=0, required=False)


class PriceRequestSerializer(_Base):
    grade = serializers.ChoiceField(choices=['A', 'B', 'C'], default='B')
    market_price_per_kg = serializers.FloatField(min_value=0.01, required=False)


class AIPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIPrediction
        fields = ['id', 'product', 'kind', 'predicted_value', 'range_low', 'range_high',
                  'warnings', 'model_version', 'created_at']
