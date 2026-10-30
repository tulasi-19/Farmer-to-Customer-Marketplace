from django.test import TestCase
from rest_framework.test import APIClient

from common.test_utils import make_farm, make_product, make_user, place_order
from products.models import Category, Product


class ProductTests(TestCase):
    def setUp(self):
        self.f1, self.f2 = make_user('f1', 'farmer'), make_user('f2', 'farmer')
        self.farm1, self.farm2 = make_farm(self.f1), make_farm(self.f2)
        self.cat = Category.objects.create(name='Fruits', slug='fruits')
        self.c = APIClient()

    def _payload(self, **over):
        d = {'name': 'Mango', 'category': self.cat.pk, 'price': '90.00', 'quantity_available': '50', 'unit': 'kg'}
        d.update(over)
        return d

    def test_approved_farmer_creates_product_on_own_farm(self):
        self.c.force_authenticate(self.f1)
        r = self.c.post('/api/v1/products/', self._payload(farm=self.farm2.pk), format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Product.objects.get().farm, self.farm1)       # farm field in body is ignored

    def test_unapproved_farmer_and_customer_cannot_create(self):
        newbie = make_user('new', 'farmer'); make_farm(newbie, approved=False)
        self.c.force_authenticate(newbie)
        self.assertEqual(self.c.post('/api/v1/products/', self._payload(), format='json').status_code, 403)
        self.c.force_authenticate(make_user('cust'))
        self.assertEqual(self.c.post('/api/v1/products/', self._payload(), format='json').status_code, 403)
        self.c.force_authenticate(None)
        self.assertEqual(self.c.post('/api/v1/products/', self._payload(), format='json').status_code, 401)

    def test_invalid_price_and_negative_stock_rejected(self):
        self.c.force_authenticate(self.f1)
        self.assertEqual(self.c.post('/api/v1/products/', self._payload(price='0'), format='json').status_code, 400)
        self.assertEqual(self.c.post('/api/v1/products/', self._payload(quantity_available='-5'), format='json').status_code, 400)

    def test_farmer_cannot_edit_or_delete_others_product(self):
        p = make_product(self.farm2)
        self.c.force_authenticate(self.f1)
        self.assertEqual(self.c.patch(f'/api/v1/products/{p.pk}/', {'price': '1.00'}, format='json').status_code, 404)
        self.assertEqual(self.c.delete(f'/api/v1/products/{p.pk}/').status_code, 404)
        p.refresh_from_db()
        self.assertEqual(str(p.price), '30.00')

    def test_owner_updates_stock_and_deletes(self):
        p = make_product(self.farm1)
        self.c.force_authenticate(self.f1)
        self.assertEqual(self.c.patch(f'/api/v1/products/{p.pk}/', {'quantity_available': '5'}, format='json').status_code, 200)
        self.assertEqual(self.c.delete(f'/api/v1/products/{p.pk}/').status_code, 204)

    def test_product_with_orders_is_archived_not_deleted(self):
        p = make_product(self.farm1)
        place_order(make_user('cust'), [(p, 1)])
        self.c.force_authenticate(self.f1)
        r = self.c.delete(f'/api/v1/products/{p.pk}/')
        self.assertEqual(r.status_code, 200)
        p.refresh_from_db()
        self.assertFalse(p.is_active)

    def test_public_listing_search_filters_pagination(self):
        make_product(self.farm1, 'Tomato', '30', '10')
        make_product(self.farm1, 'Mango', '120', '0')
        make_product(self.farm2, 'Onion', '20', '5')
        hidden = make_product(self.farm2, 'Hidden', '5', '5'); Product.objects.filter(pk=hidden.pk).update(is_active=False)
        g = lambda q: self.c.get('/api/v1/products/' + q).data
        self.assertEqual(g('')['count'], 3)
        self.assertEqual(g('?search=mango')['count'], 1)
        self.assertEqual(g('?max_price=25')['count'], 1)
        self.assertEqual(g('?available=true')['count'], 2)
        self.assertEqual(g('?ordering=-price')['results'][0]['name'], 'Mango')
        self.assertEqual(len(g('?page_size=2')['results']), 2)
        self.assertEqual(self.c.get('/api/v1/products/?min_price=abc').status_code, 400)

    def test_unapproved_farm_products_not_public(self):
        newbie = make_user('new', 'farmer'); farm = make_farm(newbie, approved=False)
        make_product(farm)
        self.assertEqual(self.c.get('/api/v1/products/').data['count'], 0)
