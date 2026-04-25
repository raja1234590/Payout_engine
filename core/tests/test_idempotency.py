import uuid
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from core.models import Merchant, LedgerEntry, Payout, IdempotencyKey

class IdempotencyTest(TransactionTestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(name='Test Merchant')
        LedgerEntry.objects.create(merchant=self.merchant, amount=50000, entry_type='CREDIT')
        self.client = APIClient()

    def test_idempotent_requests(self):
        key = str(uuid.uuid4())
        payload = {'amount_paise': 2000, 'bank_account_id': 'test_acc'}
        
        # Request 1
        res1 = self.client.post('/api/v1/payouts', payload, HTTP_IDEMPOTENCY_KEY=key, HTTP_X_MERCHANT_ID=str(self.merchant.id))
        self.assertEqual(res1.status_code, 201)
        
        # Request 2 (Exact same key)
        res2 = self.client.post('/api/v1/payouts', payload, HTTP_IDEMPOTENCY_KEY=key, HTTP_X_MERCHANT_ID=str(self.merchant.id))
        self.assertEqual(res2.status_code, 201)
        
        # Assert same response body
        self.assertEqual(res1.json(), res2.json())
        
        # Assert only ONE payout was created
        self.assertEqual(Payout.objects.count(), 1)
        self.assertEqual(IdempotencyKey.objects.count(), 1)
