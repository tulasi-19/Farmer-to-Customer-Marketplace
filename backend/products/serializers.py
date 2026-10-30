from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class ProductSerializer(serializers.ModelSerializer):
    farm_id = serializers.IntegerField(source='farm.id', read_only=True)
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    farm_district = serializers.CharField(source='farm.district', read_only=True)
    farm_state = serializers.CharField(source='farm.state', read_only=True)
    farm_is_verified = serializers.BooleanField(source='farm.is_verified', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'farm_id', 'farm_name', 'farm_district', 'farm_state', 'farm_is_verified',
            'name', 'category', 'category_name', 'description', 'price', 'quantity_available',
            'unit', 'image', 'origin', 'is_active', 'in_stock', 'average_rating', 'review_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_in_stock(self, obj):
        return obj.quantity_available > 0

    def get_average_rating(self, obj):
        avg = getattr(obj, 'avg_rating', None)
        return round(float(avg), 1) if avg else None

    def get_review_count(self, obj):
        return getattr(obj, 'n_reviews', 0)

    def validate_name(self, v):
        v = v.strip()
        if not v:
            raise serializers.ValidationError('Name is required.')
        return v
