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
Double-entry principles avoid storing derived states that can desync. By strictly deriving available balance directly from `CREDIT` and `DEBIT` entries using DB aggregations, it removes the class of bugs where Python arithmetic desyncs with the database during race conditions. When a pending payout is requested, a `DEBIT` is instantly inserted to "hold" funds out of the available pool. 

## 2. The Lock
**Code:**
```python
# Inside a transaction.atomic() block:
locked_merchant = Merchant.objects.select_for_update().get(id=merchant.id)
balance = locked_merchant.get_balance()
if balance < amount:
    # return Insufficient Funds
```
**Primitive relied on:**
This relies on PostgreSQL (and simulated cleanly in SQLite via locking behavior) `SELECT ... FOR UPDATE` row-level lock. It completely blocks any other concurrent read/write queries attempting to grab the same Merchant row with `select_for_update()`. Two concurrent 60 INR payout requests will serialize: thread A locks it, calculates balance, deducts, and releases lock. Thread B then gets the lock, recalculates balance dynamically, and sees it's too low.

## 3. The Idempotency
**How the system knows it's seen a key before:**
We create an `IdempotencyKey` record immediately with a DB-level composite unique constraint on `(merchant_id, key)`. 
**What happens if the first request is in-flight when the second arrives?**
The second request hits a database-level `IntegrityError` when attempting to INSERT the duplicate key since the first thread claimed it. We catch this `IntegrityError` and wait (or fetch) the initial key's `response_body` rather than launching a duplicate payment.

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
```
This is located in the `Payout` model in `core/models.py`. It guarantees a `FAILED` or `COMPLETED` target state throws an exception before attempting any updates.

## 5. The AI Audit
**The Mistake:**
AI tools often suggest fetching balance as `balance = merchant.available_balance` and then doing `balance -= amount` and `merchant.save()`. 
AI also tends to suggest `transaction.atomic()` *without* `select_for_update()`, mistakenly assuming explicit transactions magically serialize reads without locking primitives.
**What was given:**
During generation, AI might suggest:
```python
with transaction.atomic():
    merchant = Merchant.objects.get(id=id)
    if merchant.balance >= amount:
       merchant.balance -= amount
       merchant.save()
```
**What I caught & replaced:**
This classically yields a check-then-act race condition! Two requests start the transaction, read 100, subtract 60, and save 40. I explicitly forced the AI to implement `select_for_update()` to enforce row-locks, and strictly compute balance dynamically from the Ledger via `Sum()` and `F()` functions to guarantee total accuracy.
