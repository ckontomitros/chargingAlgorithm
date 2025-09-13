# src/utils/data_generator.py
import pandas as pd
import numpy as np


def load_consumption_profile(file_path):
    """Load consumption profile from CSV."""
    return pd.read_csv(file_path)['consumption'].tolist()


def generate_solar_irradiance(day_of_year, location='Athens'):
    """Generate synthetic solar irradiance profile."""
    # Example: Simplified model for Athens in September
    return [800 * np.sin(np.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 0 for hour in range(24)]
