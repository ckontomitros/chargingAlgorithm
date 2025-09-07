# tests/test_building.py
import pytest
from src.models.building import Building

# Matrix data (converted to kW and kWh for 1-hour intervals)
HOURS = [8, 9, 10, 11, 12, 13, 14, 15]
PRODUCTION = [-20, -10, 20, 50, 120, 100, 50, 10]  # kW
P_CH = [62.5, 62.5, 20, 50, 62.5, 62.5, 17.5, 0]  # kW
P_DIS = [0, 0, 0, 18, 62.5, 62.5, 62.5, 62.5]  # kW
SOC = [37.5, 37.5, 57.5, 107.5, 170, 232.5, 250, 250]  # kWh


@pytest.fixture
def building():
    return Building(
        energy_consumption_profile=PRODUCTION,
        panel_area=1,  # Dummy value
        panel_efficiency=0.1,  # Dummy value
        peak_solar_irradiance=100,  # Dummy value
        battery_capacity=250,  # kWh
        battery_efficiency=0.9,
        initial_soc=0.15,  # 0.15 (15% SoC)
        dod=0.85,  # 85% DoD, min SoC 37.5 kWh
        duration=4  # hours
    )


def test_battery_operation(building):
    """Test battery charging/discharging based on production values from the matrix."""
    # Set initial SOC (37.5 kWh)
    building.soc = 37.5 / building.battery_capacity

    for hour, production, expected_p_ch, expected_p_dis, expected_soc in zip(HOURS, PRODUCTION, P_CH, P_DIS, SOC):
        if production > 0:
            # Positive production: charge battery with excess energy
            energy_charged = building.charge_battery(production)
            # Verify charging power matches expected
            assert abs(energy_charged - expected_p_ch) < 0.1, \
                f"Hour {hour}: Expected P_ch {expected_p_ch} kW, got {energy_charged:.1f} kW"
        else:
            # Negative production: discharge battery to cover deficit
            energy_discharged = building.discharge_battery(abs(production))
            # Verify discharging power matches expected
            assert abs(energy_discharged - expected_p_dis) < 0.1, \
                f"Hour {hour}: Expected P_dis {expected_p_dis} kW, got {energy_discharged:.1f} kW"

        # Verify SOC matches expected (convert from percentage to kWh for comparison)
        current_soc_kwh = building.soc * building.battery_capacity
        assert abs(current_soc_kwh - expected_soc) < 0.1, \
            f"Hour {hour}: Expected SOC {expected_soc} kWh, got {current_soc_kwh:.1f} kWh"


def test_dod_limit(building):
    """Test that DoD limit (15% SoC) is respected."""
    building.soc = 0.2  # 20% SoC (50 kWh)
    energy_discharged = building.discharge_battery(50)  # Attempt to discharge 50 kW
    expected_min_soc = 37.5  # 15% of 250 kWh
    assert building.soc * building.battery_capacity >= expected_min_soc - 0.1, \
        f"DoD limit violated: SoC {building.soc * building.battery_capacity:.1f} kWh < {expected_min_soc} kWh"


def test_charge_capacity_limit(building):
    """Test that charging does not exceed 100% capacity."""
    building.soc = 0.9  # 90% SoC (225 kWh)
    building.charge_battery(50)  # Attempt to charge 50 kW
    assert building.soc <= 1.0, \
        f"Charging exceeded capacity: SoC {building.soc} > 1.0"


def test_p_max_calculation(building):
    """Test that p_max is correctly calculated as battery_capacity / duration."""
    expected_p_max = 250 / 4  # 62.5 kW
    assert abs(building.p_max - expected_p_max) < 0.1, \
        f"Expected p_max {expected_p_max} kW, got {building.p_max} kW"


def test_soc_min_calculation(building):
    """Test that soc_min is correctly calculated as battery_capacity * (1 - dod)."""
    expected_soc_min = 250 * (1 - 0.85)  # 37.5 kWh
    assert abs(building.soc_min - expected_soc_min) < 0.1, \
        f"Expected soc_min {expected_soc_min} kWh, got {building.soc_min} kWh"
