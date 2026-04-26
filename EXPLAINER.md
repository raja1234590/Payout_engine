# EXPLAINER.md


## 1. The Ledger
**Query:**
```python
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
balance = agg['total']
```
**Why modeled this way?**
The ledger stores each event as either a `CREDIT` or a `DEBIT`, and the balance is derived from those entries in the database. This avoids a separate stored balance that can drift out of sync. Using DB-level aggregation guarantees the displayed balance always matches the ledger, and a payout request holds funds instantly by inserting a `DEBIT`.

## 2. The Lock
**Code:**
```python
with transaction.atomic():
    locked_merchant = Merchant.objects.select_for_update().get(id=merchant.id)
    balance = locked_merchant.get_balance()
    if balance < amount:
        # return Insufficient Funds
```
**Primitive relied on:**
This relies on row-level locking via `SELECT ... FOR UPDATE` in PostgreSQL (or equivalent DB row-locking behavior). The `select_for_update()` call locks the merchant row so another concurrent payout request cannot read and deduct from the same balance at the same time. That serializes concurrent requests and prevents overdrawing.

## 3. The Idempotency
**How the system knows it's seen a key before:**
Every payout request stores its `Idempotency-Key` in the `IdempotencyKey` table with a unique `(merchant, key)` constraint. Once a key is stored, the system can recognize duplicates.

**What happens if the first request is in-flight when the second arrives?**
The second request will either wait for the first transaction or hit a duplicate-key error on insert. We catch the resulting duplicate and return the already-stored response body instead of creating a second payout.

## 4. The State Machine
**Verification Code Blocking Bad Transitions:**
```python
def change_status(self, new_status):
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
```
This lives in the `Payout` model in `core/models.py`. It blocks illegal transitions like `FAILED -> COMPLETED` or `COMPLETED -> PENDING`, so `failed-to-completed` is explicitly rejected.

## 5. The AI Audit
**The Mistake:**
AI often suggested naive balance updates using Python state (`merchant.balance -= amount`) instead of ledger aggregation. It also suggested `transaction.atomic()` without `select_for_update()`, which is not enough to prevent races.

**What was given:**
```python
with transaction.atomic():
    merchant = Merchant.objects.get(id=id)
    if merchant.balance >= amount:
        merchant.balance -= amount
        merchant.save()
```

**What I caught & replaced:**
That code creates a check-then-act race condition. Two concurrent requests can read the same balance and both succeed. I replaced it with `select_for_update()` plus a DB-level ledger balance query (`Sum`, `Case`, `When`) so the balance is calculated safely and the merchant row is locked during the payout creation.
