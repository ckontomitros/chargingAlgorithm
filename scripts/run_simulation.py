# scripts/run_simulation.py
import sys
import os

# Add project root to path before importing src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.config import load_config

# ------------------------------------------------------------------
# Choose which simulation to run
# ------------------------------------------------------------------
SIMULATION_TYPE = "multi_ev_v2g"  # options: "v2g", "multi_ev", "multi_ev_v2g"

# ------------------------------------------------------------------
if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # Load correct config
    if SIMULATION_TYPE == "multi_ev":
        config_path = os.path.join(project_root, "data", "multi_ev_config.yml")
        from src.simulation.multi_ev_simulator import run_multi_ev_simulation as run_sim

        sim_name = "Multi-EV Grid-Capacity Simulation"
        result_file = "simulation_results_multi.png"

    elif SIMULATION_TYPE == "multi_ev_v2g":
        config_path = os.path.join(project_root, "data", "multi_ev_v2g_config.yml")
        from src.simulation.multi_ev_v2g_simulator import run_multi_ev_v2g_simulation as run_sim

        sim_name = "Multi-EV V2G Simulation"
        result_file = "simulation_results_multi_v2g.png"

    else:  # "v2g" - single EV
        config_path = os.path.join(project_root, "data", "config.yml")
        from src.simulation.v2g_simulator import run_simulation as run_sim

        sim_name = "Single-EV V2G Simulation"
        result_file = "simulation_results.png"

    # Load config
    print("=" * 80)
    print(f"🔧 Loading configuration: {config_path}")

    if not os.path.exists(config_path):
        print(f"\n❌ ERROR: Config file not found at {config_path}")
        print("Please ensure the configuration file exists.")
        sys.exit(1)

    config = load_config(config_path)
    print("✅ Configuration loaded successfully")

    # Display simulation parameters
    print("\n" + "=" * 80)
    print(f"🚀 Starting {sim_name}")
    print("=" * 80)

    # Common parameters
    if 'simulation_start' in config and 'simulation_end' in config:
        print(f"⏰ Simulation window: Hour {config['simulation_start']} → {config['simulation_end']}")
    elif 'arrival_time' in config and 'target_time' in config:
        print(f"⏰ Simulation window: Hour {config['arrival_time']} → {config['target_time']}")

    # Multi-EV specific parameters
    if 'n_evs' in config:
        print(f"🚗 Number of EVs: {config['n_evs']}")
        print(f"📍 EV arrival window: Hours {config.get('ev_arrival_window', 'N/A')}")
        print(f"🎯 EV target window: Hours {config.get('ev_target_window', 'N/A')}")
        print(f"🔋 EV battery capacity: {config.get('ev_battery_capacity', 'N/A')} kWh")
        print(f"⚡ Max charge rate: {config.get('max_charge_rate', 'N/A')} kW")

        if SIMULATION_TYPE == "multi_ev_v2g":
            print(f"🔌 Max discharge rate: {config.get('max_discharge_rate', 'N/A')} kW")
            print(f"💰 V2G enabled: Yes")
        else:
            print(f"💰 V2G enabled: No (charge-only)")

    # Grid parameters
    if 'grid_capacity_per_hour' in config:
        capacity = config['grid_capacity_per_hour']
        if isinstance(capacity, dict):
            cap_values = list(capacity.values())
        else:
            cap_values = capacity
        print(f"⚡ Grid capacity range: {min(cap_values)}-{max(cap_values)} kW")

    # Algorithm parameters
    if 'rl_episodes' in config:
        print(f"\n🤖 RL Configuration:")
        print(f"   - Episodes: {config['rl_episodes']}")
        print(f"   - Learning rate: {config.get('rl_lr', 'N/A')}")
        print(f"   - Epsilon: {config.get('rl_epsilon', 'N/A')}")

    print("=" * 80)
    print("\n⏳ Running simulation... This may take a few moments.\n")

    # Run simulation
    try:
        results = run_sim(config)

        # Success message
        print("\n" + "=" * 80)
        print(f"✅ {sim_name} completed successfully!")
        print("=" * 80)
        print(f"📊 Results saved to: scripts/{result_file}")

        # Display key results
        if 'hours' in results:
            print(f"\n📈 Key Results:")

            for method in ['simple', 'rl']:
                if method in results and 'benefit' in results[method]:
                    total_benefit = sum(results[method]['benefit'])
                    print(f"   {method.upper()}: Total benefit = €{total_benefit:.2f}")

        print("=" * 80)

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ ERROR: Simulation failed!")
        print("=" * 80)
        print(f"Error details: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)