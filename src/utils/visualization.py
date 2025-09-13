# src/utils/visualization.py
import matplotlib.pyplot as plt


def plot_energy_profiles(renewable_profile, consumption_profile, title="Energy Profiles"):
    plt.figure(figsize=(10, 6))
    plt.plot(range(24), renewable_profile, label="Renewable Production (kWh)")
    plt.plot(range(24), consumption_profile, label="Consumption (kWh)")
    plt.xlabel("Hour")
    plt.ylabel("Energy (kWh)")
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.savefig("energy_profiles.png")
    plt.close()
