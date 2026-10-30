"""
Train the PRICE model.       Run from backend/:   python ml_engine/train_price_model.py

Target : selling_price_per_kg (Rs/kg)
Inputs : crop, region (state), month, grade (A/B/C), supply_index, avg_market_price_prev_30d
Leakage check: no input is derived from the target, and the demand model's output is NOT used here.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml_engine import common  # noqa: E402

if __name__ == '__main__':
    df, path = common.load_dataset('price_training_data.csv', common.generate_price_dataset)
    df = common.clean(df, common.PRICE_FEATURES)
    common.train_and_save('price', common.PRICE_FEATURES, df, path)
