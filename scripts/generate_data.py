# scripts/generate_data.py
import pandas as pd


def generate_sample_data():
    consumption = [10] * 24
    pd.DataFrame({'consumption': consumption}).to_csv("../data/consumption_profiles.csv", index=False)
    prices = [0.15, 0.12, 0.10, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30, 0.25, 0.20, 0.15] * 2
    pd.DataFrame({'price': prices}).to_csv("../data/price_profiles.csv", index=False)


generate_sample_data()
