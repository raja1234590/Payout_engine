from rest_framework import serializers
from .models import Merchant, LedgerEntry, Payout

class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ['id', 'amount', 'entry_type', 'reference', 'created_at']

class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = ['id', 'amount_paise', 'bank_account_id', 'status', 'idempotency_key', 'created_at']
        read_only_fields = ['id', 'status', 'idempotency_key', 'created_at']

class MerchantSerializer(serializers.ModelSerializer):
    available_balance = serializers.SerializerMethodField()
    held_balance = serializers.SerializerMethodField()
    recent_transactions = serializers.SerializerMethodField()
    recent_payouts = serializers.SerializerMethodField()

    class Meta:
        model = Merchant
        fields = ['id', 'name', 'available_balance', 'held_balance', 'recent_transactions', 'recent_payouts']

    def get_available_balance(self, obj):
        return obj.get_balance()

    def get_held_balance(self, obj):
        from django.db.models import Sum
        return obj.payouts.filter(status__in=['PENDING', 'PROCESSING']).aggregate(
            total=Sum('amount_paise')
        )['total'] or 0

    def get_recent_transactions(self, obj):
        entries = obj.ledger_entries.order_by('-created_at')[:10]
        return LedgerEntrySerializer(entries, many=True).data

    def get_recent_payouts(self, obj):
        payouts = obj.payouts.order_by('-created_at')[:10]
        return PayoutSerializer(payouts, many=True).data
