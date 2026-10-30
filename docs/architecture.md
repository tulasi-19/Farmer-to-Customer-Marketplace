# Architecture

```
React (CRA) ──JSON/HTTPS──▶ Django + DRF ──SQL──▶ MySQL (InnoDB)
                                    │ services.py (business rules)   │
                                    └──▶ ml_engine/saved_models/*.joblib
```
Principles: (1) the backend is the single source of truth for prices, totals, stock, roles and payment status;
(2) thin views, rules in `services.py` (testable); (3) every multi-row change runs in `transaction.atomic()`;
(4) ML is trained offline and only *served* by Django; (5) KYC files are private, product images public.

## Checkout concurrency
`checkout()` locks the product rows (`SELECT … FOR UPDATE`, ordered by id to avoid deadlocks), validates stock against the locked rows, decrements stock and creates Order/Shipments/OrderItems in one transaction. Two buyers of the last 5 kg are serialised: one succeeds, the other gets a clear 400.

## State machine
See `backend/orders/state.py` (pure Python). Order status = least-advanced non-cancelled shipment.

## Payment state
Cash on delivery only. Order.payment_status: `cod_pending → cod_paid` (set by an admin once the cash is collected; farmers cannot).
