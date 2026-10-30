from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from farms.models import Farm
from products.models import Category, Product

User = get_user_model()

CATEGORIES = ['Vegetables', 'Fruits', 'Grains', 'Pulses', 'Dairy', 'Spices']
DEMO_PASSWORD = 'Demo@12345'   # DEV ONLY - never use these accounts in production

FARMERS = [
    ('farmer_ravi', 'ravi@example.com', 'Ravi Green Farm', 'Andhra Pradesh', 'Visakhapatnam', [
        ('Tomato', 'Vegetables', '32.00', '120', 'kg'), ('Onion', 'Vegetables', '26.00', '200', 'kg'),
        ('Mango', 'Fruits', '110.00', '80', 'kg'), ('Banana', 'Fruits', '48.00', '60', 'kg')]),
    ('farmer_anita', 'anita@example.com', 'Anita Organic Fields', 'Maharashtra', 'Nashik', [
        ('Potato', 'Vegetables', '24.00', '300', 'kg'), ('Wheat', 'Grains', '31.00', '500', 'kg'),
        ('Chilli', 'Spices', '90.00', '40', 'kg')]),
]


class Command(BaseCommand):
    help = 'Create demo categories, users and products (development only).'

    def handle(self, *args, **opts):
        cats = {n: Category.objects.get_or_create(name=n, defaults={'slug': n.lower()})[0] for n in CATEGORIES}

        if not User.objects.filter(username='admin_demo').exists():
            User.objects.create_superuser('admin_demo', 'admin@example.com', DEMO_PASSWORD)
        if not User.objects.filter(username='customer_demo').exists():
            User.objects.create_user('customer_demo', 'customer@example.com', DEMO_PASSWORD,
                                     role='customer', phone='9876543210', address='12 MG Road, Visakhapatnam')

        for username, email, farm_name, state, district, products in FARMERS:
            user, _ = User.objects.get_or_create(username=username, defaults={'email': email, 'role': 'farmer'})
            if _:
                user.set_password(DEMO_PASSWORD)
                user.save()
            farm, _ = Farm.objects.get_or_create(user=user, defaults={
                'farm_name': farm_name, 'state': state, 'district': district,
                'description': f'Family-run farm in {district}.',
                # Demo farms are pre-approved so you can test immediately. Real farmers go through KYC.
                'kyc_status': Farm.KYCStatus.APPROVED})
            for name, cat, price, qty, unit in products:
                Product.objects.get_or_create(farm=farm, name=name, defaults={
                    'category': cats[cat], 'price': Decimal(price), 'quantity_available': Decimal(qty),
                    'unit': unit, 'origin': district, 'description': f'Fresh {name.lower()} from {farm_name}.'})

        self.stdout.write(self.style.SUCCESS(
            f'Seeded. Logins (password {DEMO_PASSWORD}): admin_demo, customer_demo, farmer_ravi, farmer_anita'))
