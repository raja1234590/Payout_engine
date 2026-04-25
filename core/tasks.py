import time
import random
from django.db import transaction
from .models import Payout, LedgerEntry

@transaction.atomic
def process_payout(payout_id):
    try:
        # FIX 2: DB lock to prevent multiple workers processing the same payout
        payout = Payout.objects.select_for_update().get(id=payout_id)
    except Payout.DoesNotExist:
        return

    # FIX 1: Only process PENDING payouts
    if payout.status != 'PENDING':
        return  # already being processed or done

    payout.change_status('PROCESSING')
    payout.attempts += 1
    payout.save(update_fields=['attempts'])
    
    # Simulate processing time
    time.sleep(1)

    outcome = random.choices(
        ['success', 'fail', 'hang'],
        weights=[0.70, 0.20, 0.10],
        k=1
    )[0]

    if outcome == 'hang':
        # Hang: leave it in PROCESSING state. The scheduled retry job will catch it.
        return
        
    elif outcome == 'success':
        payout.change_status('COMPLETED')
        
    elif outcome == 'fail':
        # MUST refund the ledger exactly as specified
        payout.change_status('FAILED')
        LedgerEntry.objects.create(
            merchant=payout.merchant,
            amount=payout.amount_paise,
            entry_type='CREDIT',
            reference=f'payout-failed-{payout.id}'
        )

def retry_stuck_payouts():
    """
    Scheduled job to retry stuck payouts > 30s.
    """
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_time = timezone.now() - timedelta(seconds=30)
    stuck_payouts = Payout.objects.filter(status='PROCESSING', updated_at__lt=cutoff_time)
    
    for payout in stuck_payouts:
        with transaction.atomic():
            # Lock the payout row
            locked_payout = Payout.objects.select_for_update().get(id=payout.id)
            
            # Double check it is still PROCESSING
            if locked_payout.status != 'PROCESSING':
                continue
                
            if locked_payout.attempts >= 3:
                # Max retries reached, fail it forever and refund
                locked_payout.change_status('FAILED')
                LedgerEntry.objects.create(
                    merchant=locked_payout.merchant,
                    amount=locked_payout.amount_paise,
                    entry_type='CREDIT',
                    reference=f'payout-failed-max-retries-{locked_payout.id}'
                )
            else:
                # Retry simulation in the cron job itself to bypass the PENDING check
                locked_payout.attempts += 1
                locked_payout.save(update_fields=['attempts'])
                
                outcome = random.choices(['success', 'fail', 'hang'], weights=[0.70, 0.20, 0.10], k=1)[0]
                
                if outcome == 'hang':
                    continue
                elif outcome == 'success':
                    locked_payout.change_status('COMPLETED')
                elif outcome == 'fail':
                    locked_payout.change_status('FAILED')
                    LedgerEntry.objects.create(
                        merchant=locked_payout.merchant,
                        amount=locked_payout.amount_paise,
                        entry_type='CREDIT',
                        reference=f'payout-failed-retry-{locked_payout.id}'
                    )
