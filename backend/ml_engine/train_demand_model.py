"""
Train the DEMAND model.      Run from backend/:   python ml_engine/train_demand_model.py

Target : units_next_30d  = kilograms expected to sell in the 30 days starting in `month`
Inputs : crop, region (state), month, avg_weekly_units_prev_4w, current_price_per_kg, supply_index
Model  : RandomForestRegressor inside a scikit-learn Pipeline (one-hot encoding + forest)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml_engine import common  # noqa: E402

if __name__ == '__main__':
    df, path = common.load_dataset('demand_training_data.csv', common.generate_demand_dataset)
    df = common.clean(df, common.DEMAND_FEATURES)
    common.train_and_save('demand', common.DEMAND_FEATURES, df, path)
