from django.core.management.base import BaseCommand
from core.models import Merchant, LedgerEntry
from django_q.models import Schedule

class Command(BaseCommand):
    help = 'Seeds the database with test merchants and schedules the background retry task'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')
        
        # 1. Schedule the retry task if it doesn't exist
        Schedule.objects.get_or_create(
            func='core.tasks.retry_stuck_payouts',
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 1,
                'repeats': -1
            }
        )
        self.stdout.write('Scheduled retry\_stuck\_payouts task.')
        
        # 2. Seed Merchants
        if Merchant.objects.count() == 0:
            m1 = Merchant.objects.create(name='Acme Corp UI')
            m2 = Merchant.objects.create(name='Globex Design')
            m3 = Merchant.objects.create(name='Initech Agency')
            
            # Initial balances via CREDIT
            # Acme has 500000 paise (5000 INR)
            LedgerEntry.objects.create(merchant=m1, amount=500000, entry_type='CREDIT', reference='Initial Deposit')
            # Globex has 1000000 paise (10000 INR)
            LedgerEntry.objects.create(merchant=m2, amount=1000000, entry_type='CREDIT', reference='Initial Deposit')
            # Initech has 0
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created 3 merchants with seeded credits.'))
        else:
            self.stdout.write('Merchants already exist, skipping seed.')
