# scripts/run_simulation.py
from src.simulation.v2g_simulator import run_simulation
from src.utils.config import load_config
import sys
import os

if __name__ == "__main__":
    # Add parent directory to path if needed
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), "../data/config.yml")
    config = load_config(config_path)

    print("Starting V2G Charging Simulation...")
    print(f"Configuration loaded from: {config_path}")
    print(f"Simulation period: Hour {config['arrival_time']} to Hour {config['target_time']}")
    print(f"Target SoC: {config['desired_soc'] * 100:.0f}%")
    print("-" * 60)

    # Run simulation
    results = run_simulation(config)

    print("\nSimulation completed successfully!")