# scripts/run_simulation.py
from src.simulation.simulator import run_simulation
from src.utils.config import load_config

if __name__ == "__main__":
    config = load_config("../data/config.yml")
    results = run_simulation(config)
    print("Simulation Results:", results)