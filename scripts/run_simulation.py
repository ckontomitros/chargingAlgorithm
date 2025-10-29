# scripts/run_simulation.py
import sys
import os
from src.utils.config import load_config

# ------------------------------------------------------------------
# Choose which simulation to run
# ------------------------------------------------------------------
SIMULATION_TYPE = "multi_ev"   # options: "v2g", "multi_ev"

# ------------------------------------------------------------------
if __name__ == "__main__":
    # Add project root to path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, project_root)

    # Load correct config
    if SIMULATION_TYPE == "multi_ev":
        config_path = os.path.join(project_root, "data", "multi_ev_config.yml")
        from src.simulation.multi_ev_simulator import run_multi_ev_simulation as run_sim
        sim_name = "Multi-EV Grid-Capacity Simulation"
    else:
        config_path = os.path.join(project_root, "data", "config.yml")
        from src.simulation.v2g_simulator import run_simulation as run_sim
        sim_name = "Single-EV V2G Simulation"

    # Load config
    print(f"Loading config: {config_path}")
    config = load_config(config_path)

    print(f"\nStarting {sim_name}...")
    print(f"Simulation window: Hour {config.get('simulation_start', config.get('arrival_time', 0))} "
          f"→ {config.get('simulation_end', config.get('target_time', 24))}")
    if 'n_evs' in config:
        print(f"Number of EVs: {config['n_evs']}")
    print("-" * 70)

    # Run simulation
    results = run_sim(config)

    print(f"\n{sim_name} completed!")
    print("Results saved to: scripts/simulation_results_multi.png (for multi-ev)")
    print("-" * 70)