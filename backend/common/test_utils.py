"""Small factories shared by the test-suites."""
import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings

from cart.models import Cart, CartItem
from farms.models import Farm
from orders import services as order_services
from products.models import Category, Product

User = get_user_model()
PASSWORD = 'Str0ng!Pass#1'
ADDRESS = '12 MG Road, Visakhapatnam, Andhra Pradesh'


def make_user(username, role='customer'):
    return User.objects.create_user(username, f'{username}@example.com', PASSWORD, role=role, phone='9876543210')


def make_farm(user, approved=True, state='Andhra Pradesh'):
    return Farm.objects.create(
        user=user, farm_name=f'{user.username} farm', state=state, district='Visakhapatnam',
        kyc_status=Farm.KYCStatus.APPROVED if approved else Farm.KYCStatus.NOT_SUBMITTED)


def make_product(farm, name='Tomato', price='30.00', qty='100', unit='kg'):
    cat, _ = Category.objects.get_or_create(name='Vegetables', defaults={'slug': 'vegetables'})
    return Product.objects.create(farm=farm, category=cat, name=name, price=Decimal(price),
                                  quantity_available=Decimal(qty), unit=unit)


def place_order(customer, items):
    """items: [(product, quantity), ...]  -> cash-on-delivery Order created through the real checkout service."""
    cart, _ = Cart.objects.get_or_create(user=customer)
    for product, qty in items:
        CartItem.objects.create(cart=cart, product=product, quantity=Decimal(str(qty)))
    return order_services.checkout(customer, shipping_address=ADDRESS, shipping_phone='9876543210')


class TempPrivateMedia:
    """Mixin: KYC uploads go to a throw-away folder."""
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.mkdtemp()
        self._ov = override_settings(PRIVATE_MEDIA_ROOT=self._tmp)
        self._ov.enable()

    def tearDown(self):
        self._ov.disable()
        shutil.rmtree(self._tmp, ignore_errors=True)
        super().tearDown()
