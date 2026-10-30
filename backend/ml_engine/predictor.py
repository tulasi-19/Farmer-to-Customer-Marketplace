"""
Loads the trained pipelines and produces predictions with honest metadata.
No Django imports: the model folder is a parameter, so this is testable on its own.

What a prediction contains
  value          : the forest's average prediction
  range_low/high : 10th-90th percentile of the individual trees' predictions.
                   This is the SPREAD between trees - NOT a statistical confidence interval.
  warnings       : unseen region, inputs outside the training range, missing history ...
  reliability    : 'normal' or 'low' (low whenever any warning applies)
"""
import json
import os

import joblib
import numpy as np
import pandas as pd

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_models')
_cache = {}


class ModelNotTrained(Exception):
    pass


class PredictionInputError(ValueError):
    pass


def load(kind, model_dir=None):
    """Load (and cache by file modification time) the pipeline + metadata for 'demand' or 'price'."""
    model_dir = model_dir or DEFAULT_DIR
    model_path = os.path.join(model_dir, f'{kind}_model.joblib')
    meta_path = os.path.join(model_dir, f'{kind}_meta.json')
    if not (os.path.exists(model_path) and os.path.exists(meta_path)):
        raise ModelNotTrained(
            f"The {kind} model has not been trained yet. From the backend/ folder run: "
            f"python ml_engine/train_{kind}_model.py")
    key = (model_path, os.path.getmtime(model_path))
    if key not in _cache:
        with open(meta_path) as fh:
            _cache[key] = (joblib.load(model_path), json.load(fh))
    return _cache[key]


def model_info(kind, model_dir=None):
    try:
        _, meta = load(kind, model_dir)
    except ModelNotTrained as exc:
        return {'trained': False, 'detail': str(exc)}
    keep = ['version', 'trained_at', 'data_source', 'data_note', 'n_rows', 'target', 'metrics',
            'categories', 'numeric_ranges', 'features']
    return {'trained': True, **{k: meta[k] for k in keep}}


def typical(kind, crop, month, model_dir=None):
    """Fallback inputs (training medians for this crop+month) for products with no history."""
    _, meta = load(kind, model_dir)
    key = 'typical_weekly_units' if kind == 'demand' else 'typical_market_price'
    return meta[key][crop][str(month)]


def match_crop(meta, crop):
    lookup = {c.lower(): c for c in meta['categories']['crop']}
    found = lookup.get((crop or '').strip().lower())
    if not found:
        raise PredictionInputError(
            f"'{crop}' is not a crop the model was trained on. Supported: {', '.join(sorted(lookup.values()))}.")
    return found


def predict(kind, features, model_dir=None):
    pipe, meta = load(kind, model_dir)
    cats, nums = meta['features']['categorical'], meta['features']['numeric']
    row, warnings = dict(features), []

    row['crop'] = match_crop(meta, row.get('crop'))

    month = row.get('month')
    if not isinstance(month, (int, np.integer)) or not 1 <= month <= 12:
        raise PredictionInputError('month must be a whole number from 1 to 12.')

    for c in cats:
        if row.get(c) in (None, ''):
            raise PredictionInputError(f'{c} is required.')
    for n in nums:
        try:
            row[n] = float(row[n])
        except (KeyError, TypeError, ValueError):
            raise PredictionInputError(f'{n} must be a number.')
        if not np.isfinite(row[n]):
            raise PredictionInputError(f'{n} must be a finite number.')

    for c in cats:
        if c != 'crop' and row[c] not in meta['categories'][c]:
            warnings.append(f"{c} '{row[c]}' was not in the training data; the estimate is less reliable.")
    for n in nums:
        lo, hi = meta['numeric_ranges'][n]
        if not lo <= row[n] <= hi:
            warnings.append(f"{n}={row[n]:g} is outside the training range ({lo:g} to {hi:g}); "
                            f"the model is extrapolating, so treat this as a rough guess.")

    X = pd.DataFrame([row])[cats + nums]
    value = float(pipe.predict(X)[0])
    Xt = pipe.named_steps['prep'].transform(X)
    per_tree = np.array([t.predict(Xt)[0] for t in pipe.named_steps['model'].estimators_])
    low, high = (float(v) for v in np.percentile(per_tree, [10, 90]))
    return {
        'value': max(value, 0.0), 'range_low': max(low, 0.0), 'range_high': max(high, 0.0),
        'warnings': warnings, 'reliability': 'low' if warnings else 'normal',
        'inputs': {k: row[k] for k in cats + nums},
        'model': {k: meta[k] for k in ('version', 'trained_at', 'data_source', 'data_note', 'metrics')},
    }
