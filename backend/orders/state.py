"""
Order / shipment status rules. Pure Python (no Django imports) so the rules are
easy to read and unit-test.

Lifecycle of ONE shipment (one farmer's part of an order):

    pending -> confirmed -> processing -> shipped -> out_for_delivery -> delivered

  Any of pending / confirmed / processing may also go to -> cancelled
  (cancelling is only possible BEFORE the shipment is shipped).

  * pending   : waiting for online payment.   Set by the system only.
  * confirmed : payment received (or COD).    Set by the system only.
  * The farmer / admin may set: processing, shipped, out_for_delivery, delivered, cancelled.
  * The customer may cancel the whole order while every shipment is pending/confirmed.

The ORDER's status is derived from its shipments (see derive_order_status), so it
can never disagree with the shipments.
"""

PENDING = 'pending'
CONFIRMED = 'confirmed'
PROCESSING = 'processing'
SHIPPED = 'shipped'
OUT_FOR_DELIVERY = 'out_for_delivery'
DELIVERED = 'delivered'
CANCELLED = 'cancelled'

ALL_STATUSES = [PENDING, CONFIRMED, PROCESSING, SHIPPED, OUT_FOR_DELIVERY, DELIVERED, CANCELLED]

TRANSITIONS = {
    PENDING: {CONFIRMED, CANCELLED},
    CONFIRMED: {PROCESSING, CANCELLED},
    PROCESSING: {SHIPPED, CANCELLED},
    SHIPPED: {OUT_FOR_DELIVERY, DELIVERED},
    OUT_FOR_DELIVERY: {DELIVERED},
    DELIVERED: set(),
    CANCELLED: set(),
}

# What a human operator may set. 'pending' and 'confirmed' are driven by payment
# events only, so nobody can "skip" payment by clicking a button.
STAFF_SETTABLE = {PROCESSING, SHIPPED, OUT_FOR_DELIVERY, DELIVERED, CANCELLED}
CUSTOMER_CANCELLABLE = {PENDING, CONFIRMED}

_RANK = {PENDING: 0, CONFIRMED: 1, PROCESSING: 2, SHIPPED: 3, OUT_FOR_DELIVERY: 4, DELIVERED: 5}


def can_transition(current, new):
    return new in TRANSITIONS.get(current, set())


def allowed_next_for_staff(current):
    """Statuses a farmer/admin can move a shipment to right now."""
    return sorted(TRANSITIONS.get(current, set()) & STAFF_SETTABLE,
                  key=lambda s: ALL_STATUSES.index(s))


def derive_order_status(shipment_statuses):
    """Order status = the status of its LEAST advanced non-cancelled shipment.
    All delivered -> delivered; all cancelled -> cancelled."""
    statuses = list(shipment_statuses)
    active = [s for s in statuses if s != CANCELLED]
    if not statuses or not active:
        return CANCELLED
    return min(active, key=lambda s: _RANK[s])
