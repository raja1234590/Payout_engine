import uuid
from django.db import models
from django.db.models import Sum, F, Case, When, Value
from django.db.models.functions import Coalesce

class Merchant(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_balance(self):
        """
        Calculates balance using database-level operations exclusively.
        The sum of credits minus debits must always equal the displayed balance.
        """
        agg = self.ledger_entries.aggregate(
            total=Coalesce(
                Sum(
                    Case(
                        When(entry_type='CREDIT', then=F('amount')),
                        When(entry_type='DEBIT', then=-F('amount')),
                        default=Value(0)
                    )
                ), 
                Value(0)
            )
        )
        return agg['total']

    def __str__(self):
        return self.name


class LedgerEntry(models.Model):
    ENTRY_TYPES = [
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit'),
    ]
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='ledger_entries')
    amount = models.BigIntegerField()
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    reference = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.merchant.name} - {self.entry_type} - {self.amount}"


class Payout(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='payouts')
    amount_paise = models.BigIntegerField()
    bank_account_id = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    idempotency_key = models.UUIDField(db_index=True)
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def change_status(self, new_status):
        """
        State machine enforcement:
        Legal: pending to processing to completed, OR pending to processing to failed.
        Illegal (must be rejected): completed to pending, failed to completed, anything backwards.
        """
        valid_transitions = {
            'PENDING': ['PROCESSING', 'FAILED'],
            'PROCESSING': ['COMPLETED', 'FAILED'],
            'COMPLETED': [],
            'FAILED': []
        }
        
        if new_status not in valid_transitions.get(self.status, []):
            raise ValueError(f"Illegal state transition from {self.status} to {new_status}")
            
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])

    def __str__(self):
        return f"Payout {self.id} - {self.status}"


class IdempotencyKey(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE)
    key = models.UUIDField()
    response_status = models.IntegerField()
    response_body = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('merchant', 'key')
