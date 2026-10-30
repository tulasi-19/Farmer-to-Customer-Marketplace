from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from common.test_utils import TempPrivateMedia, make_farm, make_user
from farms.models import Farm, KYCApplication

PDF = b'%PDF-1.4 fake test document'


class KYCTests(TempPrivateMedia, TestCase):
    def setUp(self):
        super().setUp()
        self.farmer = make_user('ravi', 'farmer')
        self.farm = make_farm(self.farmer, approved=False)
        self.admin = make_user('boss', 'admin')
        self.c = APIClient()

    def _submit(self, content=PDF, name='id.pdf'):
        return self.c.post('/api/v1/farmer/kyc/', {
            'id_type': 'aadhaar', 'id_number': '123412341234',
            'document': SimpleUploadedFile(name, content)}, format='multipart')

    def test_submit_sets_pending_and_stores_only_last4(self):
        self.c.force_authenticate(self.farmer)
        r = self._submit()
        self.assertEqual(r.status_code, 201)
        self.farm.refresh_from_db()
        self.assertEqual(self.farm.kyc_status, 'pending')
        self.assertEqual(KYCApplication.objects.get().id_number_last4, '1234')
        self.assertNotIn('123412341234', str(r.data))

    def test_bad_file_rejected(self):
        self.c.force_authenticate(self.farmer)
        self.assertEqual(self._submit(b'MZ not a pdf', 'evil.pdf').status_code, 400)   # wrong content
        self.assertEqual(self._submit(PDF, 'x.exe').status_code, 400)                  # wrong extension

    def test_cannot_submit_twice_while_pending(self):
        self.c.force_authenticate(self.farmer)
        self._submit()
        self.assertEqual(self._submit().status_code, 400)

    def test_admin_approves_and_records_reviewer(self):
        self.c.force_authenticate(self.farmer)
        app_id = self._submit().data['id']
        self.c.force_authenticate(self.admin)
        self.assertEqual(self.c.post(f'/api/v1/admin/kyc-applications/{app_id}/approve/').status_code, 200)
        app = KYCApplication.objects.get(pk=app_id)
        self.farm.refresh_from_db()
        self.assertEqual((app.status, app.reviewed_by, self.farm.kyc_status), ('approved', self.admin, 'approved'))
        self.assertIsNotNone(app.reviewed_at)

    def test_reject_requires_reason_then_farmer_can_resubmit(self):
        self.c.force_authenticate(self.farmer)
        app_id = self._submit().data['id']
        self.c.force_authenticate(self.admin)
        url = f'/api/v1/admin/kyc-applications/{app_id}/reject/'
        self.assertEqual(self.c.post(url, {}, format='json').status_code, 400)
        self.assertEqual(self.c.post(url, {'reason': 'Blurry photo'}, format='json').status_code, 200)
        self.c.force_authenticate(self.farmer)
        self.assertEqual(self.c.get('/api/v1/farmer/kyc/').data['applications'][0]['decision_reason'], 'Blurry photo')
        self.assertEqual(self._submit().status_code, 201)

    def test_non_admins_cannot_decide(self):
        self.c.force_authenticate(self.farmer)
        app_id = self._submit().data['id']
        self.assertEqual(self.c.post(f'/api/v1/admin/kyc-applications/{app_id}/approve/').status_code, 403)
        self.c.force_authenticate(make_user('cust', 'customer'))
        self.assertEqual(self.c.post(f'/api/v1/admin/kyc-applications/{app_id}/approve/').status_code, 403)

    def test_document_visible_only_to_owner_and_admin(self):
        self.c.force_authenticate(self.farmer)
        app_id = self._submit().data['id']
        url = f'/api/v1/admin/kyc-applications/{app_id}/document/'
        self.assertEqual(self.c.get(f'/api/v1/farmer/kyc/{app_id}/document/').status_code, 200)
        other = make_user('other', 'farmer')
        self.c.force_authenticate(other)
        self.assertEqual(self.c.get(f'/api/v1/farmer/kyc/{app_id}/document/').status_code, 404)
        self.c.force_authenticate(self.admin)
        self.assertEqual(self.c.get(url).status_code, 200)
        self.c.force_authenticate(None)
        self.assertEqual(self.c.get(url).status_code, 401)

    def test_public_farm_api_hides_unapproved_and_kyc_data(self):
        self.assertEqual(self.c.get('/api/v1/farms/').data['count'], 0)
        Farm.objects.filter(pk=self.farm.pk).update(kyc_status='approved')
        r = self.c.get('/api/v1/farms/')
        self.assertEqual(r.data['count'], 1)
        self.assertNotIn('kyc_status', r.data['results'][0])
        self.assertNotIn('document', str(r.data))
