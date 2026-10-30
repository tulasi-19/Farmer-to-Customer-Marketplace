import os
import unittest

from django.test import TestCase
from rest_framework.test import APIClient

from common.test_utils import make_farm, make_product, make_user
from ml_engine import predictor

TRAINED = (os.path.exists(os.path.join(predictor.DEFAULT_DIR, 'demand_model.joblib'))
           and os.path.exists(os.path.join(predictor.DEFAULT_DIR, 'price_model.joblib')))


class PredictionApiTests(TestCase):
    def setUp(self):
        self.farmer = make_user('fa', 'farmer')
        self.product = make_product(make_farm(self.farmer), 'Tomato', '30.00', '100')
        self.c = APIClient()
        self.c.force_authenticate(self.farmer)

    def test_customer_and_anonymous_blocked(self):
        self.c.force_authenticate(make_user('cust'))
        self.assertEqual(self.c.post('/api/v1/ai/demand-prediction/', {'product_id': self.product.pk}, format='json').status_code, 403)
        self.c.force_authenticate(None)
        self.assertEqual(self.c.post('/api/v1/ai/price-recommendation/', {'product_id': self.product.pk}, format='json').status_code, 401)

    def test_farmer_cannot_predict_for_someone_elses_product(self):
        other = make_product(make_farm(make_user('fb', 'farmer')), 'Onion')
        self.assertEqual(self.c.post('/api/v1/ai/demand-prediction/', {'product_id': other.pk}, format='json').status_code, 404)

    def test_input_validation(self):
        post = lambda d: self.c.post('/api/v1/ai/demand-prediction/', dict(product_id=self.product.pk, **d), format='json').status_code
        self.assertEqual(post({'month': 13}), 400)
        self.assertEqual(post({'supply_index': 'abc'}), 400)

    @unittest.skipUnless(TRAINED, 'run the ml_engine training scripts first')
    def test_demand_prediction_shape_and_honesty_fields(self):
        r = self.c.post('/api/v1/ai/demand-prediction/', {'product_id': self.product.pk}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['model']['data_source'], 'synthetic_demo')
        self.assertEqual(r.data['forecast_period']['days'], 30)
        self.assertGreater(r.data['predicted_units'], 0)
        self.assertEqual(r.data['reliability'], 'low')                       # new product: no sales history -> flagged
        self.assertTrue(r.data['warnings'])

    @unittest.skipUnless(TRAINED, 'run the ml_engine training scripts first')
    def test_price_recommendation_never_changes_listing_price(self):
        r = self.c.post('/api/v1/ai/price-recommendation/', {'product_id': self.product.pk, 'grade': 'A'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data['currency'], r.data['unit'], r.data['applied_automatically']), ('INR', 'kg', False))
        self.product.refresh_from_db()
        self.assertEqual(str(self.product.price), '30.00')

    @unittest.skipUnless(TRAINED, 'run the ml_engine training scripts first')
    def test_unsupported_crop_and_unit_give_422(self):
        weird = make_product(self.product.farm, 'Dragonfruit', '80', '10')
        self.assertEqual(self.c.post('/api/v1/ai/demand-prediction/', {'product_id': weird.pk}, format='json').status_code, 422)
        dozen = make_product(self.product.farm, 'Banana', '50', '10', unit='dozen')
        self.assertEqual(self.c.post('/api/v1/ai/demand-prediction/', {'product_id': dozen.pk}, format='json').status_code, 422)

    def test_untrained_model_gives_503_not_500(self):
        if TRAINED:
            self.skipTest('models are trained')
        r = self.c.post('/api/v1/ai/demand-prediction/', {'product_id': self.product.pk}, format='json')
        self.assertEqual(r.status_code, 503)
