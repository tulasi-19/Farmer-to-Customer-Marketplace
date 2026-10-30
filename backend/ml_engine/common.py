"""
Shared ML code for FarmBridge AI (NO Django imports, so training runs standalone).

DATA HONESTY NOTE
-----------------
A new marketplace has no sales history, so the bundled datasets are SYNTHETIC
(generated from the seasonal/price formulas below + random noise). They exist
so the whole pipeline - cleaning, features, train/test split, metrics, saving,
serving - works end to end. High scores on this data only show that the model
can recover the formulas used to create it. They say NOTHING about accuracy on
real Indian mandi prices or real FarmBridge sales. To go real, replace the CSVs
in datasets/ with real data that has the same columns and re-run the trainers.
"""
import json
import math
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(HERE, 'datasets')
MODEL_DIR = os.path.join(HERE, 'saved_models')
DATA_SOURCE = 'synthetic_demo'
MODEL_VERSION = '2.0'

# ---------------------------- domain constants ----------------------------
# crop: (base retail price Rs/kg, base weekly demand kg for a typical region, peak month, seasonality strength)
CROPS = {
    'Tomato':      (28, 220, 12, 0.25),
    'Onion':       (24, 300, 1, 0.15),
    'Potato':      (22, 340, 2, 0.12),
    'Wheat':       (30, 420, 4, 0.10),
    'Rice':        (48, 460, 10, 0.08),
    'Mango':       (95, 160, 5, 0.70),
    'Banana':      (45, 250, 8, 0.15),
    'Cauliflower': (32, 150, 1, 0.35),
    'Brinjal':     (30, 140, 7, 0.20),
    'Chilli':      (85, 90, 11, 0.20),
}
# region: (demand multiplier, price multiplier)
REGIONS = {
    'Maharashtra': (1.15, 1.05), 'Punjab': (0.95, 0.92), 'Tamil Nadu': (1.10, 1.02),
    'Karnataka': (1.05, 1.00), 'Uttar Pradesh': (1.25, 0.95), 'Andhra Pradesh': (1.00, 0.98),
    'Gujarat': (0.90, 1.03), 'West Bengal': (1.08, 1.04),
}
GRADES = {'A': 1.12, 'B': 1.00, 'C': 0.88}

DEMAND_FEATURES = {
    'categorical': ['crop', 'region'],
    'numeric': ['month', 'avg_weekly_units_prev_4w', 'current_price_per_kg', 'supply_index'],
    'target': 'units_next_30d',
}
PRICE_FEATURES = {
    'categorical': ['crop', 'region', 'grade'],
    'numeric': ['month', 'supply_index', 'avg_market_price_prev_30d'],
    'target': 'selling_price_per_kg',
}


def seasonal(crop, month):
    peak, amp = CROPS[crop][2], CROPS[crop][3]
    return 1 + amp * math.cos(2 * math.pi * (month - peak) / 12)


# ---------------------------- synthetic data -------------------------------
def generate_demand_dataset(n_rows=5000, seed=42):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n_rows):
        crop = rng.choice(list(CROPS)); region = rng.choice(list(REGIONS)); month = int(rng.integers(1, 13))
        base_price, base_units = CROPS[crop][0], CROPS[crop][1]
        d_mult, p_mult = REGIONS[region]
        supply = float(rng.uniform(0.6, 1.5))
        price = base_price * p_mult * seasonal(crop, month) ** -0.5 * rng.uniform(0.9, 1.1)
        prev_month = 12 if month == 1 else month - 1
        prev4w = base_units * d_mult * seasonal(crop, prev_month) * rng.uniform(0.85, 1.15)
        # the target uses the true seasonal/regional drivers, a price effect and noise
        units = (4.3 * base_units * d_mult * seasonal(crop, month)
                 * (base_price * p_mult / price) ** 0.6 / supply ** 0.3 * rng.uniform(0.9, 1.1))
        rows.append({'crop': crop, 'region': region, 'month': month,
                     'avg_weekly_units_prev_4w': round(prev4w, 1), 'current_price_per_kg': round(price, 2),
                     'supply_index': round(supply, 2), 'units_next_30d': round(units, 1)})
    return pd.DataFrame(rows)


def generate_price_dataset(n_rows=5000, seed=7):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n_rows):
        crop = rng.choice(list(CROPS)); region = rng.choice(list(REGIONS)); month = int(rng.integers(1, 13))
        grade = rng.choice(list(GRADES), p=[0.3, 0.5, 0.2])
        base_price = CROPS[crop][0]; p_mult = REGIONS[region][1]
        supply = float(rng.uniform(0.6, 1.5))
        prev_month = 12 if month == 1 else month - 1
        # market price last month: drivers only (it is NOT computed from the target)
        prev30 = base_price * p_mult * (2 - seasonal(crop, prev_month)) * rng.uniform(0.92, 1.08)
        price = (base_price * p_mult * (2 - seasonal(crop, month)) * GRADES[grade]
                 / supply ** 0.35 * rng.uniform(0.95, 1.05))
        rows.append({'crop': crop, 'region': region, 'month': month, 'grade': grade,
                     'supply_index': round(supply, 2), 'avg_market_price_prev_30d': round(prev30, 2),
                     'selling_price_per_kg': round(price, 2)})
    return pd.DataFrame(rows)


# ---------------------------- training -------------------------------------
def load_dataset(filename, generator):
    """Read the documented CSV; create it from the generator if it does not exist yet."""
    os.makedirs(DATASET_DIR, exist_ok=True)
    path = os.path.join(DATASET_DIR, filename)
    if not os.path.exists(path):
        generator().to_csv(path, index=False)
        print(f'Created demo dataset {path}')
    return pd.read_csv(path), path


def clean(df, spec):
    """Drop duplicates / rows with missing values / impossible values."""
    cols = spec['categorical'] + spec['numeric'] + [spec['target']]
    before = len(df)
    df = df[cols].drop_duplicates().dropna()
    df = df[(df[spec['target']] > 0)]
    if 'month' in df:
        df = df[df['month'].between(1, 12)]
    for c in spec['categorical']:
        df[c] = df[c].astype(str).str.strip()
    print(f'Cleaning: {before} rows -> {len(df)} rows')
    return df.reset_index(drop=True)


def build_pipeline(spec):
    prep = ColumnTransformer(
        [('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), spec['categorical'])],
        remainder='passthrough')
    model = RandomForestRegressor(n_estimators=100, min_samples_leaf=8, max_depth=16, random_state=42, n_jobs=-1)
    return Pipeline([('prep', prep), ('model', model)])


def _typical(df, col, digits):
    out = {}
    for (crop, month), v in df.groupby(['crop', 'month'])[col].median().items():
        out.setdefault(crop, {})[str(int(month))] = round(float(v), digits)
    return out


def train_and_save(name, spec, df, dataset_path):
    X, y = df[spec['categorical'] + spec['numeric']], df[spec['target']]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    pipe = build_pipeline(spec)
    pipe.fit(X_train, y_train)                       # the TEST set is never seen during fitting
    pred = pipe.predict(X_test)
    metrics = {
        'mae': float(mean_absolute_error(y_test, pred)),
        'rmse': float(math.sqrt(mean_squared_error(y_test, pred))),
        'r2': float(r2_score(y_test, pred)),
        'baseline_mae_predict_train_mean': float(mean_absolute_error(y_test, np.full(len(y_test), y_train.mean()))),
        'cv_r2_mean_5fold_on_train': float(cross_val_score(build_pipeline(spec), X_train, y_train,
                                                           cv=5, scoring='r2').mean()),
        'n_train': int(len(X_train)), 'n_test': int(len(X_test)),
    }
    meta = {
        'name': name, 'version': MODEL_VERSION,
        'trained_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'data_source': DATA_SOURCE,
        'data_note': 'SYNTHETIC demonstration data. Metrics reflect this generated data only, '
                     'not real market accuracy.',
        'dataset_file': os.path.basename(dataset_path), 'n_rows': int(len(df)),
        'features': {'categorical': spec['categorical'], 'numeric': spec['numeric']},
        'target': spec['target'], 'metrics': metrics,
        'categories': {c: sorted(df[c].unique().tolist()) for c in spec['categorical']},
        'numeric_ranges': {c: [float(df[c].min()), float(df[c].max())] for c in spec['numeric']},
        'sklearn_version': sklearn.__version__,
        'hyperparameters': {'n_estimators': 100, 'min_samples_leaf': 8, 'max_depth': 16, 'random_state': 42},
    }
    # Typical recent values per crop AND month: fallback for products with no history yet
    # (keeps seasonality instead of using one flat number).
    if 'avg_weekly_units_prev_4w' in df:
        meta['typical_weekly_units'] = _typical(df, 'avg_weekly_units_prev_4w', 1)
    if 'avg_market_price_prev_30d' in df:
        meta['typical_market_price'] = _typical(df, 'avg_market_price_prev_30d', 2)

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(pipe, os.path.join(MODEL_DIR, f'{name}_model.joblib'))
    with open(os.path.join(MODEL_DIR, f'{name}_meta.json'), 'w') as fh:
        json.dump(meta, fh, indent=2)
    print(f"\n[{name}] test-set results (n_test={metrics['n_test']})")
    print(f"  MAE  : {metrics['mae']:.2f}   (baseline 'always predict the mean': {metrics['baseline_mae_predict_train_mean']:.2f})")
    print(f"  RMSE : {metrics['rmse']:.2f}")
    print(f"  R^2  : {metrics['r2']:.3f}   (5-fold CV on train: {metrics['cv_r2_mean_5fold_on_train']:.3f})")
    print('  NOTE : scores are on SYNTHETIC data - see ml_engine/README.md')
    return pipe, meta
