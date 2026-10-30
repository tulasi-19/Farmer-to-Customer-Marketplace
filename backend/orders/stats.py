"""Real dashboard numbers for a farmer, computed from the database."""
from collections import OrderedDict
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from products.models import Product
from . import state
from .models import OrderItem, Shipment

LOW_STOCK_THRESHOLD = Decimal('10')
TWO = Decimal('0.01')


def _money(value):
    """Sum() may return 60 on SQLite and 60.00 on MySQL; the API always returns 2 decimals."""
    return str(Decimal(value or 0).quantize(TWO))


def _month_keys(n=6):
    now = timezone.localtime()
    y, m = now.year, now.month
    keys = []
    for _ in range(n):
        keys.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(keys))


def farmer_dashboard(farm):
    products = Product.objects.filter(farm=farm)
    live = Shipment.objects.filter(farm=farm).exclude(status__in=[state.PENDING, state.CANCELLED])

    by_status = {r['status']: r['n'] for r in
                 Shipment.objects.filter(farm=farm).exclude(status=state.PENDING)
                 .values('status').annotate(n=Count('id'))}

    # Month bucketing is done in Python (not TruncMonth) so it behaves the same on
    # SQLite and MySQL even if MySQL's time-zone tables aren't loaded.
    months = OrderedDict((k, {'total': Decimal('0.00'), 'orders': 0}) for k in _month_keys(6))
    for created, subtotal in live.values_list('order__created_at', 'subtotal'):
        local = timezone.localtime(created)
        key = (local.year, local.month)
        if key in months:
            months[key]['total'] += subtotal
            months[key]['orders'] += 1

    top = (OrderItem.objects.filter(shipment__farm=farm)
           .exclude(shipment__status__in=[state.PENDING, state.CANCELLED])
           .values('product_name', 'unit')
           .annotate(units=Sum('quantity'), revenue=Sum('line_total')).order_by('-revenue')[:5])

    total_sales = live.aggregate(t=Sum('subtotal'))['t'] or Decimal('0.00')
    delivered_sales = live.filter(status=state.DELIVERED).aggregate(t=Sum('subtotal'))['t'] or Decimal('0.00')
    return {
        'kyc_status': farm.kyc_status,
        'products': {
            'total': products.count(),
            'active': products.filter(is_active=True).count(),
            'out_of_stock': products.filter(quantity_available=0).count(),
            'low_stock': products.filter(quantity_available__gt=0, quantity_available__lt=LOW_STOCK_THRESHOLD).count(),
            'low_stock_threshold': str(LOW_STOCK_THRESHOLD),
        },
        'shipments_by_status': by_status,
        'to_fulfil': sum(by_status.get(s, 0) for s in (state.CONFIRMED, state.PROCESSING)),
        'total_sales': _money(total_sales),
        'delivered_sales': _money(delivered_sales),
        'monthly_sales': [{'month': f'{y}-{m:02d}', 'total': _money(v['total']), 'orders': v['orders']}
                          for (y, m), v in months.items()],
        'top_products': [{'name': t['product_name'], 'unit': t['unit'],
                          'units': str(Decimal(t['units']).quantize(TWO)), 'revenue': _money(t['revenue'])} for t in top],
    }