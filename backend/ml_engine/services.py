"""Glue between FarmBridge data and the ML predictor."""
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import APIException

from orders import state
from orders.models import OrderItem
from . import predictor
from .models import AIPrediction

DISCLAIMER = ('This is a statistical ESTIMATE from a model trained on SYNTHETIC demonstration data, '
              'not a guaranteed market price or sales figure.')


class Unprocessable(APIException):
    status_code = 422
    default_detail = 'The model cannot handle this request.'


class ModelUnavailable(APIException):
    status_code = 503
    default_detail = 'The model is not available.'


def _kg_factor(unit):
    """Models work in kg. quintal = 100 kg. Other units (dozen, litre...) are unsupported."""
    if unit == 'kg':
        return Decimal('1')
    if unit == 'quintal':
        return Decimal('100')
    raise Unprocessable(f"Predictions support products sold per kg or quintal, not '{unit}'.")


def _crop(product, requested):
    try:
        return predictor.match_crop(predictor.load('demand')[1], requested or product.name)
    except predictor.ModelNotTrained as exc:
        raise ModelUnavailable(str(exc))
    except predictor.PredictionInputError as exc:
        raise Unprocessable(str(exc))


def _forecast_window(month=None, today=None):
    today = today or date.today()
    if month is None or month == today.month:
        start = today
    else:
        year = today.year if month > today.month else today.year + 1
        start = date(year, month, 1)
    return start, start + timedelta(days=30)


def recent_weekly_units_kg(product, days=28):
    """Real sales: kg sold in the last `days` days (paid/confirmed orders only), per week."""
    since = timezone.now() - timedelta(days=days)
    total = (OrderItem.objects.filter(product=product, order__created_at__gte=since)
             .exclude(shipment__status__in=[state.PENDING, state.CANCELLED])
             .aggregate(t=Sum('quantity'))['t'] or Decimal('0'))
    return float(total * _kg_factor(product.unit)) / (days / 7)


def _run(kind, features):
    try:
        return predictor.predict(kind, features)
    except predictor.ModelNotTrained as exc:
        raise ModelUnavailable(str(exc))
    except predictor.PredictionInputError as exc:
        raise Unprocessable(str(exc))


def _save(product, user, kind, res):
    d = lambda v: Decimal(str(round(v, 2)))
    return AIPrediction.objects.create(
        product=product, requested_by=user, kind=kind, predicted_value=d(res['value']),
        range_low=d(res['range_low']), range_high=d(res['range_high']),
        inputs=res['inputs'], warnings=res['warnings'], model_version=res['model']['version'])


def demand_forecast(product, user, *, crop=None, month=None, supply_index=1.0, avg_weekly_units=None):
    factor = _kg_factor(product.unit)
    crop = _crop(product, crop)
    start, end = _forecast_window(month)
    warnings = []

    if avg_weekly_units is not None:
        weekly, source = float(avg_weekly_units), 'provided by you'
    else:
        weekly = recent_weekly_units_kg(product)
        source = 'your actual sales in the last 28 days'
        if weekly <= 0:
            weekly = predictor.typical('demand', crop, start.month)
            source = 'typical level for this crop and month (training data)'
            warnings.append('No sales history for this product yet, so a typical level for this crop was '
                            'used instead. Treat the forecast as a rough guide.')

    res = _run('demand', {
        'crop': crop, 'region': product.farm.state, 'month': start.month,
        'avg_weekly_units_prev_4w': weekly, 'current_price_per_kg': float(product.price / factor),
        'supply_index': float(supply_index)})
    res['warnings'] = warnings + res['warnings']
    res['reliability'] = 'low' if res['warnings'] else 'normal'
    rec = _save(product, user, 'demand', res)

    to_unit = lambda kg: round(kg / float(factor), 1)
    return {
        'prediction_id': rec.pk, 'type': 'demand',
        'product': {'id': product.pk, 'name': product.name, 'unit': product.unit},
        'crop': crop, 'region': product.farm.state,
        'forecast_period': {'start': start.isoformat(), 'end': end.isoformat(), 'days': 30},
        'predicted_units': to_unit(res['value']), 'unit': product.unit,
        'range': {'low': to_unit(res['range_low']), 'high': to_unit(res['range_high']),
                  'basis': 'Spread between the forest\'s individual trees (10th-90th percentile); not a statistical guarantee.'},
        'assumptions': {'recent_weekly_units_kg': round(weekly, 1), 'recent_sales_source': source,
                        'current_price_per_kg': round(float(product.price / factor), 2),
                        'supply_index': float(supply_index), 'month': start.month},
        'warnings': res['warnings'], 'reliability': res['reliability'],
        'model': res['model'], 'disclaimer': DISCLAIMER,
    }


def price_recommendation(product, user, *, crop=None, month=None, supply_index=1.0, grade='B',
                         market_price_per_kg=None):
    factor = _kg_factor(product.unit)
    crop = _crop(product, crop)
    month = month or date.today().month
    warnings = []
    if market_price_per_kg is not None:
        market = float(market_price_per_kg)
        market_src = 'provided by you'
    else:
        market = predictor.typical('price', crop, month)
        market_src = 'typical market price for this crop and month (training data)'
        warnings.append('No recent market price was supplied, so a typical value from the training data '
                        'was used. Supply the latest local mandi price for a better estimate.')

    res = _run('price', {
        'crop': crop, 'region': product.farm.state, 'month': month, 'grade': grade,
        'supply_index': float(supply_index), 'avg_market_price_prev_30d': market})
    res['warnings'] = warnings + res['warnings']
    res['reliability'] = 'low' if res['warnings'] else 'normal'
    rec = _save(product, user, 'price', res)

    to_unit = lambda per_kg: round(per_kg * float(factor), 2)
    recommended = to_unit(res['value'])
    current = float(product.price)
    return {
        'prediction_id': rec.pk, 'type': 'price',
        'product': {'id': product.pk, 'name': product.name, 'current_price': str(product.price)},
        'crop': crop, 'region': product.farm.state,
        'recommended_price': recommended, 'currency': 'INR', 'unit': product.unit,
        'range': {'low': to_unit(res['range_low']), 'high': to_unit(res['range_high'])},
        'difference_from_current_pct': round((recommended - current) / current * 100, 1),
        'assumptions': {'grade': grade, 'month': month, 'supply_index': float(supply_index),
                        'market_price_per_kg': round(market, 2), 'market_price_source': market_src},
        'warnings': res['warnings'], 'reliability': res['reliability'],
        'applied_automatically': False,   # your listing price is NEVER changed by this endpoint
        'model': res['model'], 'disclaimer': DISCLAIMER,
    }
