from django.test import TestCase
from rest_framework.test import APIClient

from common.test_utils import make_farm, make_product, make_user, place_order
from orders import services
from reviews.models import Review


class ReviewTests(TestCase):
    def setUp(self):
        self.fa = make_user('fa', 'farmer')
        self.product = make_product(make_farm(self.fa))
        self.cust = make_user('cust')
        self.c = APIClient()

    def deliver(self, customer):
        order = place_order(customer, [(self.product, 1)])
        s = order.shipments.get()
        for st in ('processing', 'shipped', 'delivered'):
            services.update_shipment_status(s.pk, actor=self.fa, new_status=st)

    def post(self, rating=5, comment='Great'):
        return self.c.post('/api/v1/reviews/', {'product': self.product.pk, 'rating': rating, 'comment': comment}, format='json')

    def test_cannot_review_without_delivered_purchase(self):
        self.c.force_authenticate(self.cust)
        self.assertEqual(self.post().status_code, 400)
        place_order(self.cust, [(self.product, 1)])                   # ordered but not delivered
        self.assertEqual(self.post().status_code, 400)
        self.assertFalse(self.c.get(f'/api/v1/reviews/eligibility/?product={self.product.pk}').data['can_review'])

    def test_review_after_delivery_once_only_with_clean_text(self):
        self.deliver(self.cust)
        self.c.force_authenticate(self.cust)
        r = self.post(4, '<script>alert(1)</script>Tasty')
        self.assertEqual(r.status_code, 201)
        self.assertNotIn('<script>', r.data['comment'])
        self.assertEqual(self.post().status_code, 400)                       # duplicate blocked
        self.assertEqual(Review.objects.count(), 1)

    def test_rating_range_validated(self):
        self.deliver(self.cust)
        self.c.force_authenticate(self.cust)
        self.assertEqual(self.post(0).status_code, 400)
        self.assertEqual(self.post(6).status_code, 400)

    def test_others_cannot_edit_or_delete_my_review(self):
        self.deliver(self.cust); self.c.force_authenticate(self.cust)
        rid = self.post().data['id']
        self.c.force_authenticate(make_user('snoop'))
        self.assertEqual(self.c.patch(f'/api/v1/reviews/{rid}/', {'rating': 1}, format='json').status_code, 404)
        self.assertEqual(self.c.delete(f'/api/v1/reviews/{rid}/').status_code, 404)

    def test_moderation_hides_review_and_average_ignores_it(self):
        self.deliver(self.cust); self.c.force_authenticate(self.cust)
        rid = self.post(5).data['id']
        self.c.force_authenticate(None)
        self.assertEqual(self.c.get(f'/api/v1/products/{self.product.pk}/').data['average_rating'], 5.0)
        self.c.force_authenticate(make_user('boss', 'admin'))
        self.assertEqual(self.c.patch(f'/api/v1/admin/reviews/{rid}/', {'status': 'hidden'}, format='json').status_code, 200)
        self.c.force_authenticate(None)
        self.assertEqual(self.c.get('/api/v1/reviews/').data['count'], 0)
        self.assertIsNone(self.c.get(f'/api/v1/products/{self.product.pk}/').data['average_rating'])

    def test_customers_cannot_moderate(self):
        self.c.force_authenticate(self.cust)
        self.assertEqual(self.c.get('/api/v1/admin/reviews/').status_code, 403)
