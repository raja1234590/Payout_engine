from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction, IntegrityError
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, F, Case, When, Value
from django.db.models.functions import Coalesce
import uuid
import json

from .models import Merchant, Payout, LedgerEntry, IdempotencyKey
from .serializers import MerchantSerializer, PayoutSerializer
from django_q.tasks import async_task

@api_view(['GET'])
def merchant_dashboard(request):
    merchant_id = request.headers.get('X-Merchant-Id', 1)
    try:
        merchant_id = int(merchant_id)
    except (TypeError, ValueError):
        merchant_id = 1

    merchant, created = Merchant.objects.get_or_create(
        id=merchant_id,
        defaults={'name': 'Test Merchant'}
    )

    if created:
        LedgerEntry.objects.create(
            merchant=merchant,
            amount=500000,
            entry_type='CREDIT',
            reference='initial-seed'
        )

    serializer = MerchantSerializer(merchant)
    return Response(serializer.data)

@api_view(['POST'])
def create_payout(request):
    merchant_id = request.headers.get('X-Merchant-Id', 1)
    idemp_key_str = request.headers.get('Idempotency-Key')
    
    if not idemp_key_str:
        return Response({'error': 'Idempotency-Key header is required'}, status=400)

    try:
        key_uuid = uuid.UUID(idemp_key_str)
    except ValueError:
        return Response({'error': 'Invalid UUID for Idempotency-Key'}, status=400)

    amount = request.data.get('amount_paise')
    bank_account_id = request.data.get('bank_account_id')
    
    if not amount or int(amount) <= 0:
        return Response({'error': 'Valid amount_paise is required'}, status=400)
    
    amount = int(amount)

    try:
        merchant = Merchant.objects.get(id=merchant_id)
    except Merchant.DoesNotExist:
        return Response({'error': 'Merchant not found'}, status=404)

    # Idempotency expiration check
    cutoff = timezone.now() - timedelta(hours=24)
    expired_keys = IdempotencyKey.objects.filter(merchant=merchant, key=key_uuid, created_at__lt=cutoff)
    if expired_keys.exists():
        expired_keys.delete() # Expired, so we delete it and start over

    # Fast path check for idempotency
    existing_key = IdempotencyKey.objects.filter(merchant=merchant, key=key_uuid).first()
    if existing_key:
        return Response(existing_key.response_body, status=existing_key.response_status)

    try:
        with transaction.atomic():
            # Create idempotency key immediately to detect concurrent requests with same key
            # This triggers IntegrityError if another request inserts it between our checks
            locked_key = IdempotencyKey.objects.create(
                merchant=merchant,
                key=key_uuid,
                response_status=202, # placeholder
                response_body={}
            )

            # --- CONCURRENCY LOCK ---
            # Lock the merchant row so that two requests cannot read the balance simultaneously
            locked_merchant = Merchant.objects.select_for_update().get(id=merchant.id)

            # DB-level calculation guarantees memory/python arithmetic won't cause race conditions
            balance = locked_merchant.get_balance()
            
            if balance < amount:
                # Need to update our idempotency key with the final fast-path result
                resp_body = {'error': 'Insufficient funds'}
                locked_key.response_status = 400
                locked_key.response_body = resp_body
                locked_key.save()
                return Response(resp_body, status=400)

            # Create the Payout in PENDING
            payout = Payout.objects.create(
                merchant=locked_merchant,
                amount_paise=amount,
                bank_account_id=bank_account_id,
                status='PENDING',
                idempotency_key=key_uuid
            )

            # Debit the un-settled funds immediately to prevent double spending
            LedgerEntry.objects.create(
                merchant=locked_merchant,
                amount=amount,
                entry_type='DEBIT',
                reference=f'payout-{payout.id}'
            )

            serializer = PayoutSerializer(payout)
            resp_body = serializer.data
            
            # Save final response to the idempotency key tracker
            locked_key.response_status = 201
            locked_key.response_body = resp_body
            locked_key.save()

            # Schedule the background task to process this payout
            async_task('core.tasks.process_payout', payout.id)
            
            return Response(resp_body, status=201)

    except IntegrityError:
        # Integrity error means another thread created the IdempotencyKey first!
        # Because we're using Postgres/SQLite's unique constraint, only one wins.
        # Wait for the blocking transaction to finish (or retry if simple) and return its result.
        # But for brevity, we handle it natively or tell the client to retry. Actually, we can fetch the key.
        existing_key = IdempotencyKey.objects.filter(merchant=merchant, key=key_uuid).first()
        if existing_key:
            return Response(existing_key.response_body, status=existing_key.response_status)
        return Response({'error': 'Concurrent request detected on idempotency. Retry later.'}, status=409)
