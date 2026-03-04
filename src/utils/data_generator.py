# src/utils/data_generator.py
import pandas as pd
import numpy as np


def load_consumption_profile(file_path, column=None):
    """
    Load consumption profile from CSV.
    
    Args:
        file_path: Path to CSV file
        column: Column name to use. If None, auto-detects from common names.
        
    Returns:
        List of hourly consumption values (24 hours)
    """
    df = pd.read_csv(file_path)
    
    # Auto-detect column name
    if column is None:
        # Try common column names
        possible_columns = ['consumption', 'Office_kW', 'kW', 'power', 'load', 'demand']
        for col in possible_columns:
            if col in df.columns:
                column = col
                break
        
        # If still not found, use second column (first is often timestamp)
        if column is None and len(df.columns) >= 2:
            column = df.columns[1]
    
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in {file_path}. Available: {list(df.columns)}")
    
    values = df[column].tolist()
    
    # If more than 24 values, extract first day or average by hour
    if len(values) > 24:
        # Average consumption by hour of day across all days
        df['hour'] = df.index % 24
        hourly_avg = df.groupby('hour')[column].mean().tolist()
        return hourly_avg
    
    return values


def generate_solar_irradiance(day_of_year, location='Athens'):
    """Generate synthetic solar irradiance profile."""
    # Example: Simplified model for Athens in September
    return [800 * np.sin(np.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 0 for hour in range(24)]


def load_irradiance_pvgis(file_path, date_str):
    """
    Load irradiance data from PVGIS CSV for a specific date.
    
    Args:
        file_path: Path to PVGIS CSV file
        date_str: Date string in format 'YYYYMMDD' (e.g., '20180312' for March 12, 2018)
        
    Returns:
        List of 24 hourly irradiance values (W/m²)
    """
    irradiance = [0.0] * 24
    
    with open(file_path, 'r') as f:
        for line in f:
            # Skip header lines (don't start with a digit)
            if not line[0].isdigit():
                continue
            
            parts = line.strip().split(',')
            if len(parts) < 2:
                continue
            
            # Parse timestamp: YYYYMMDD:HHMM
            timestamp = parts[0]
            if not timestamp.startswith(date_str):
                continue
            
            # Extract hour from timestamp (e.g., "20180312:0910" -> 9)
            time_part = timestamp.split(':')[1]
            hour = int(time_part[:2])
            
            # G(i) is the second column - global irradiance on inclined plane (W/m²)
            irradiance_value = float(parts[1])
            irradiance[hour] = irradiance_value
    
    return irradiance


def load_irradiance_averaged(file_path, month=None):
    """
    Load irradiance data from PVGIS CSV, averaged by hour across all days or specific month.
    
    Args:
        file_path: Path to PVGIS CSV file
        month: Optional month (1-12) to filter. If None, averages all months.
        
    Returns:
        List of 24 hourly average irradiance values (W/m²)
    """
    hourly_sums = [0.0] * 24
    hourly_counts = [0] * 24
    
    with open(file_path, 'r') as f:
        for line in f:
            if not line[0].isdigit():
                continue
            
            parts = line.strip().split(',')
            if len(parts) < 2:
                continue
            
            timestamp = parts[0]
            # Extract month from YYYYMMDD:HHMM
            line_month = int(timestamp[4:6])
            
            # Filter by month if specified
            if month is not None and line_month != month:
                continue
            
            time_part = timestamp.split(':')[1]
            hour = int(time_part[:2])
            irradiance_value = float(parts[1])
            
            hourly_sums[hour] += irradiance_value
            hourly_counts[hour] += 1
    
    # Calculate averages
    irradiance = [
        hourly_sums[h] / hourly_counts[h] if hourly_counts[h] > 0 else 0.0
        for h in range(24)
    ]
    
    return irradiance
