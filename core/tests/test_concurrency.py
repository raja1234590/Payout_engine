import uuid
import threading
from django.test import TransactionTestCase
from django.db import connection
from rest_framework.test import APIClient
from core.models import Merchant, LedgerEntry, Payout

class PayoutConcurrencyTest(TransactionTestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(name='Test Merchant')
        LedgerEntry.objects.create(merchant=self.merchant, amount=10000, entry_type='CREDIT') # 100 rupees
        self.client1 = APIClient()
        self.client2 = APIClient()

    def test_concurrent_payouts_prevent_overdraw(self):
        # We simulate two concurrent threads trying to withdraw 6000 paise (60 rupees).
        # Only one should succeed because 10000 < 6000 + 6000.
        
        results = []
        def make_request(client, amount):
            key = str(uuid.uuid4())
            try:
                response = client.post('/api/v1/payouts', {
                    'amount_paise': amount,
                    'bank_account_id': 'test_acc'
                }, HTTP_IDEMPOTENCY_KEY=key, HTTP_X_MERCHANT_ID=str(self.merchant.id))
                results.append(response.status_code)
            except Exception:
                # SQLite locking can throw OperationalError directly in threads
                pass
            finally:
                connection.close()
            
        t1 = threading.Thread(target=make_request, args=(self.client1, 6000))
        t2 = threading.Thread(target=make_request, args=(self.client2, 6000))
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        # One must succeed (201). In Postgres the other correctly yields 400.
        # In SQLite, both threads might hit a Database Error if locked simultaneously.
        if results:
            self.assertIn(201, results)
        
        if len(results) == 2:
            self.assertIn(400, results)
            
        self.assertEqual(Payout.objects.count(), 1)
        
        # Verify balance is strictly 4000
        self.merchant.refresh_from_db()
        self.assertEqual(self.merchant.get_balance(), 4000)
