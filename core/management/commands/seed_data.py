from django.core.management.base import BaseCommand
from core.models import Merchant, LedgerEntry

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        merchant = Merchant.objects.create(name="Test Merchant")

        LedgerEntry.objects.create(
            merchant=merchant,
            amount=500000,  # ₹5000
            entry_type='CREDIT',
            reference="initial"
        )

        self.stdout.write(self.style.SUCCESS("Seed data created"))