# tests/test_building.py
import pytest
from src.models.building import Building

def test_building_discharge_dod():
    building = Building(
        energy_consumption_profile=[10] * 24, panel_area=50, panel_efficiency=0.2,
        peak_solar_irradiance=800, battery_capacity=50, battery_efficiency=0.9,
        initial_soc=0.5, dod=0.8
    )
    building.discharge_battery(40)  # Attempt to discharge 40 kWh
    assert building.soc >= 0.2, "SoC should not go below DoD limit (20%)"