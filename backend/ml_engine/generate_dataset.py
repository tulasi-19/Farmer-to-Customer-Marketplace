"""Regenerate the synthetic demo CSVs:  python ml_engine/generate_dataset.py  (run from backend/)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml_engine import common  # noqa: E402

if __name__ == '__main__':
    os.makedirs(common.DATASET_DIR, exist_ok=True)
    common.generate_demand_dataset().to_csv(os.path.join(common.DATASET_DIR, 'demand_training_data.csv'), index=False)
    common.generate_price_dataset().to_csv(os.path.join(common.DATASET_DIR, 'price_training_data.csv'), index=False)
    print('Wrote datasets/demand_training_data.csv and datasets/price_training_data.csv (SYNTHETIC demo data)')
