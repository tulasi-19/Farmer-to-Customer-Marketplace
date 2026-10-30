import threading
from decimal import Decimal

from django.db import connection
from django.test import TestCase, TransactionTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from cart.models import Cart, CartItem
from common.test_utils import ADDRESS, make_farm, make_product, make_user, place_order
from orders import services
from orders.models import Order, Shipment


class Base(TestCase):
    def setUp(self):
        self.fa, self.fb = make_user('fa', 'farmer'), make_user('fb', 'farmer')
        self.farm_a, self.farm_b = make_farm(self.fa), make_farm(self.fb)
        self.tomato = make_product(self.farm_a, 'Tomato', '30.00', '100')
        self.mango = make_product(self.farm_b, 'Mango', '100.00', '50')
        self.cust = make_user('cust')
        self.c = APIClient()

    def login(self, user):
        self.c.force_authenticate(user)
        return self.c


class CartTests(Base):
    def test_add_update_remove_and_server_totals(self):
        self.login(self.cust)
        r = self.c.post('/api/v1/cart/items/', {'product_id': self.tomato.pk, 'quantity': '2.5', 'price': '0.01'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['subtotal'], '75.00')                       # client price ignored
        self.c.post('/api/v1/cart/items/', {'product_id': self.tomato.pk, 'quantity': '1'}, format='json')
        self.assertEqual(CartItem.objects.count(), 1)                        # no duplicate line
        item = CartItem.objects.get()
        self.assertEqual(item.quantity, Decimal('3.50'))
        self.assertEqual(self.c.patch(f'/api/v1/cart/items/{item.pk}/', {'quantity': '1'}, format='json').data['subtotal'], '30.00')
        self.assertEqual(self.c.delete(f'/api/v1/cart/items/{item.pk}/').data['item_count'], 0)

    def test_stock_and_quantity_validation(self):
        self.login(self.cust)
        post = lambda q: self.c.post('/api/v1/cart/items/', {'product_id': self.tomato.pk, 'quantity': q}, format='json')
        self.assertEqual(post('101').status_code, 400)
        self.assertEqual(post('0').status_code, 400)
        self.assertEqual(post('-3').status_code, 400)

    def test_cannot_touch_other_customers_cart_item(self):
        other = make_user('other')
        cart = Cart.objects.create(user=other)
        item = CartItem.objects.create(cart=cart, product=self.tomato, quantity=1)
        self.login(self.cust)
        self.assertEqual(self.c.patch(f'/api/v1/cart/items/{item.pk}/', {'quantity': '2'}, format='json').status_code, 404)
        self.assertEqual(self.c.delete(f'/api/v1/cart/items/{item.pk}/').status_code, 404)

    def test_farmers_have_no_cart(self):
        self.login(self.fa)
        self.assertEqual(self.c.get('/api/v1/cart/').status_code, 403)


class CheckoutTests(Base):
    def test_checkout_snapshots_price_splits_by_farm_and_reserves_stock(self):
        order = place_order(self.cust, [(self.tomato, 2), (self.mango, 1)])
        self.assertEqual(order.total_amount, Decimal('160.00'))
        self.assertEqual(order.shipments.count(), 2)                         # one per farmer
        self.tomato.refresh_from_db()
        self.assertEqual(self.tomato.quantity_available, Decimal('98.00'))
        self.assertEqual((order.status, order.payment_status), ('confirmed', 'cod_pending'))
        self.assertEqual(Cart.objects.get(user=self.cust).items.count(), 0)  # cart cleared
        self.tomato.price = Decimal('999.00'); self.tomato.save()            # later price change...
        self.assertEqual(order.items.get(product=self.tomato).unit_price, Decimal('30.00'))   # ...history unchanged

    def test_checkout_api_ignores_client_supplied_prices(self):
        self.login(self.cust)
        self.c.post('/api/v1/cart/items/', {'product_id': self.tomato.pk, 'quantity': '1'}, format='json')
        r = self.c.post('/api/v1/orders/checkout/', {
            'shipping_address': ADDRESS, 'shipping_phone': '9876543210', 'total_amount': '1.00', 'status': 'delivered', 'payment_status': 'paid'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.data['total_amount'], r.data['status'], r.data['payment_status']),
                         ('30.00', 'confirmed', 'cod_pending'))

    def test_empty_cart_and_bad_address_rejected(self):
        self.login(self.cust)
        body = {'shipping_address': ADDRESS, 'shipping_phone': '9876543210'}
        self.assertEqual(self.c.post('/api/v1/orders/checkout/', body, format='json').status_code, 400)
        self.c.post('/api/v1/cart/items/', {'product_id': self.tomato.pk, 'quantity': '1'}, format='json')
        self.assertEqual(self.c.post('/api/v1/orders/checkout/', dict(body, shipping_phone='abc'), format='json').status_code, 400)

    def test_second_buyer_of_last_stock_is_refused_and_nothing_goes_negative(self):
        self.mango.quantity_available = Decimal('5'); self.mango.save()
        other = make_user('other')
        c1 = Cart.objects.create(user=self.cust); CartItem.objects.create(cart=c1, product=self.mango, quantity=Decimal('4'))
        c2 = Cart.objects.create(user=other); CartItem.objects.create(cart=c2, product=self.mango, quantity=Decimal('4'))
        services.checkout(self.cust, shipping_address=ADDRESS, shipping_phone='9876543210')
        with self.assertRaises(ValidationError):
            services.checkout(other, shipping_address=ADDRESS, shipping_phone='9876543210')
        self.mango.refresh_from_db()
        self.assertEqual(self.mango.quantity_available, Decimal('1.00'))
        self.assertEqual(Order.objects.count(), 1)

    def test_orders_are_private_to_their_owner(self):
        order = place_order(self.cust, [(self.tomato, 1)])
        self.login(make_user('snoop'))
        self.assertEqual(self.c.get(f'/api/v1/orders/{order.pk}/').status_code, 404)
        self.assertEqual(self.c.post(f'/api/v1/orders/{order.pk}/cancel/').status_code, 404)
        self.assertEqual(self.c.get('/api/v1/orders/').data['count'], 0)


class ConcurrentCheckout(TransactionTestCase):
    """Real row-lock test. Only meaningful on MySQL/PostgreSQL (SQLite ignores SELECT FOR UPDATE)."""

    def test_parallel_checkouts_never_oversell(self):
        if connection.vendor == 'sqlite':
            self.skipTest('needs MySQL: SQLite does not support row locking')
        farmer = make_user('fa', 'farmer'); product = make_product(make_farm(farmer), 'Mango', '10', '5')
        carts = []
        for i in range(4):
            u = make_user(f'buyer{i}'); cart = Cart.objects.create(user=u)
            CartItem.objects.create(cart=cart, product=product, quantity=Decimal('2')); carts.append(u)
        results = []

        def buy(u):
            try:
                services.checkout(u, shipping_address=ADDRESS, shipping_phone='9876543210')
                results.append('ok')
            except ValidationError:
                results.append('refused')
            finally:
                connection.close()

        threads = [threading.Thread(target=buy, args=(u,)) for u in carts]
        [t.start() for t in threads]; [t.join() for t in threads]
        product.refresh_from_db()
        self.assertEqual(results.count('ok'), 2)                 # 5 kg / 2 kg = only 2 can succeed
        self.assertEqual(product.quantity_available, Decimal('1.00'))


class TrackingTests(Base):
    def setUp(self):
        super().setUp()
        self.order = place_order(self.cust, [(self.tomato, 2), (self.mango, 1)])   # confirmed, 2 shipments
        self.sa = self.order.shipments.get(farm=self.farm_a)
        self.sb = self.order.shipments.get(farm=self.farm_b)

    def set_status(self, user, shipment, status, **extra):
        self.login(user)
        return self.c.post(f'/api/v1/farmer/shipments/{shipment.pk}/status/', dict(status=status, **extra), format='json')

    def test_customer_cannot_change_status(self):
        self.login(self.cust)
        self.assertEqual(self.c.post(f'/api/v1/farmer/shipments/{self.sa.pk}/status/', {'status': 'delivered'}, format='json').status_code, 403)
        self.assertEqual(self.c.patch(f'/api/v1/orders/{self.order.pk}/', {'status': 'delivered'}, format='json').status_code, 405)

    def test_farmer_sees_only_own_shipment_and_cannot_touch_others(self):
        self.login(self.fa)
        r = self.c.get('/api/v1/farmer/shipments/')
        self.assertEqual([s['id'] for s in r.data['results']], [self.sa.pk])
        self.assertEqual([i['product_name'] for i in r.data['results'][0]['items']], ['Tomato'])
        self.assertNotIn('customer_email', r.data['results'][0])
        self.assertEqual(self.set_status(self.fa, self.sb, 'processing').status_code, 404)

    def test_full_lifecycle_and_derived_order_status(self):
        self.assertEqual(self.set_status(self.fa, self.sa, 'processing').status_code, 200)
        self.assertEqual(self.set_status(self.fa, self.sa, 'shipped', carrier='BlueDart', tracking_number='BD123').status_code, 200)
        self.assertEqual(self.set_status(self.fa, self.sa, 'delivered').status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'confirmed')            # farm B hasn't moved yet -> order not "delivered"
        for st in ('processing', 'shipped', 'delivered'):
            self.set_status(self.fb, self.sb, st)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'delivered')
        self.assertEqual(self.sa.__class__.objects.get(pk=self.sa.pk).tracking_number, 'BD123')
        self.login(self.cust)
        d = self.c.get(f'/api/v1/orders/{self.order.pk}/').data
        self.assertTrue(len(d['events']) >= 7)                      # a real timeline exists

    def test_invalid_transitions_rejected(self):
        self.assertEqual(self.set_status(self.fa, self.sa, 'delivered').status_code, 400)    # can't skip
        self.assertEqual(self.set_status(self.fa, self.sa, 'confirmed').status_code, 400)    # system-only
        self.assertEqual(self.set_status(self.fa, self.sa, 'bogus').status_code, 400)
        self.set_status(self.fa, self.sa, 'processing'); self.set_status(self.fa, self.sa, 'shipped')
        self.assertEqual(self.set_status(self.fa, self.sa, 'cancelled', note='x').status_code, 400)  # not after shipping

    def test_farmer_cancel_needs_reason_and_restores_stock(self):
        self.assertEqual(self.set_status(self.fa, self.sa, 'cancelled').status_code, 400)
        self.assertEqual(self.set_status(self.fa, self.sa, 'cancelled', note='Crop damaged').status_code, 200)
        self.tomato.refresh_from_db()
        self.assertEqual(self.tomato.quantity_available, Decimal('100.00'))

    def test_customer_cancel_restores_stock_until_processing_starts(self):
        self.login(self.cust)
        r = self.c.post(f'/api/v1/orders/{self.order.pk}/cancel/', {'reason': 'changed mind'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['status'], 'cancelled')
        self.tomato.refresh_from_db(); self.mango.refresh_from_db()
        self.assertEqual((self.tomato.quantity_available, self.mango.quantity_available), (Decimal('100.00'), Decimal('50.00')))

    def test_customer_cannot_cancel_once_processing(self):
        self.set_status(self.fa, self.sa, 'processing')
        self.login(self.cust)
        self.assertEqual(self.c.post(f'/api/v1/orders/{self.order.pk}/cancel/').status_code, 400)

    def test_only_admin_confirms_cod_cash(self):
        for s, f in ((self.sa, self.fa), (self.sb, self.fb)):
            for st in ('processing', 'shipped', 'delivered'):
                self.set_status(f, s, st)
        url = f'/api/v1/admin/orders/{self.order.pk}/mark-cod-paid/'
        self.login(self.fa)
        self.assertEqual(self.c.post(url).status_code, 403)
        self.login(make_user('boss', 'admin'))
        self.assertEqual(self.c.post(url).data['payment_status'], 'cod_paid')

    def test_farmer_dashboard_uses_real_numbers(self):
        self.login(self.fa)
        d = self.c.get('/api/v1/farmer/dashboard/').data
        self.assertEqual(d['total_sales'], '60.00')
        self.assertEqual(d['products']['total'], 1)
        self.assertEqual(d['to_fulfil'], 1)
