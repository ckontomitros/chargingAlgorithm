"""Generate publication-quality figures for Chapter 3 of the thesis."""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import os

plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linestyle': '--',
})

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'thesis', 'figures')
os.makedirs(OUTPUT_DIR, exist_ok=True)

hours = np.arange(24)
hour_labels = [f'{h:02d}:00' for h in hours]


def plot_electricity_prices():
    purchase = [
        0.0285, 0.0198, 0.0120, 0.0096,
        0.0190, 0.0420, 0.0447, 0.0483,
        0.0481, 0.0460, 0.0444, 0.0450,
        0.0415, 0.0384, 0.0372, 0.0376,
        0.0422, 0.0502, 0.0620, 0.0552,
        0.0432, 0.0412, 0.0368, 0.0350,
    ]
    sellback = [
        0.0228, 0.0158, 0.0096, 0.0076,
        0.0152, 0.0336, 0.0357, 0.0387,
        0.0384, 0.0368, 0.0355, 0.0360,
        0.0332, 0.0307, 0.0298, 0.0301,
        0.0338, 0.0402, 0.0496, 0.0442,
        0.0346, 0.0330, 0.0294, 0.0280,
    ]

    purchase_mwh = [p * 1000 for p in purchase]
    sellback_mwh = [s * 1000 for s in sellback]

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(hours, purchase_mwh, 'o-', color='#2166ac', linewidth=2,
            markersize=5, label='Purchase price (day-ahead)', zorder=3)
    ax.plot(hours, sellback_mwh, 's--', color='#b2182b', linewidth=2,
            markersize=5, label='Sell-back price (80% of purchase)', zorder=3)

    ax.fill_between(hours, sellback_mwh, purchase_mwh,
                     alpha=0.12, color='#666666', label='Spread (grid fees + margin)')

    peak_h = np.argmax(purchase_mwh)
    ax.annotate(f'{purchase_mwh[peak_h]:.1f} €/MWh',
                xy=(peak_h, purchase_mwh[peak_h]),
                xytext=(peak_h - 3.5, purchase_mwh[peak_h] + 5),
                arrowprops=dict(arrowstyle='->', color='#2166ac', lw=1.2),
                fontsize=9, color='#2166ac', fontweight='bold')

    trough_h = np.argmin(purchase_mwh)
    ax.annotate(f'{purchase_mwh[trough_h]:.1f} €/MWh',
                xy=(trough_h, purchase_mwh[trough_h]),
                xytext=(trough_h + 1.5, purchase_mwh[trough_h] - 5),
                arrowprops=dict(arrowstyle='->', color='#2166ac', lw=1.2),
                fontsize=9, color='#2166ac', fontweight='bold')

    ax.axvspan(0, 3.5, alpha=0.05, color='navy', label='Off-peak')
    ax.axvspan(16, 19.5, alpha=0.08, color='red', label='Evening peak')

    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Price (EUR/MWh)')
    ax.set_title('Day-Ahead Electricity Prices — France EPEX SPOT, March 12, 2018')
    ax.set_xticks(hours)
    ax.set_xticklabels(hour_labels, rotation=45, ha='right')
    ax.set_xlim(-0.5, 23.5)
    ax.set_ylim(0, 75)
    ax.legend(loc='upper left', framealpha=0.9)

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'electricity_price_profile.png'))
    plt.close(fig)
    print('Saved electricity_price_profile.png')


def plot_solar_production():
    irradiance_w_m2 = [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        41.52, 168.33, 196.26, 69.71, 212.76,
        187.07, 241.45, 132.07, 487.29, 195.35,
        26.62, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    ]

    panel_area = 150      # m²
    panel_eff = 0.20
    solar_kw = [I * panel_area * panel_eff / 1000 for I in irradiance_w_m2]

    fig, ax1 = plt.subplots(figsize=(10, 5))

    color_irr = '#e6550d'
    color_pow = '#31a354'

    ax1.bar(hours, irradiance_w_m2, width=0.7, color=color_irr, alpha=0.30,
            label='Irradiance (W/m²)', zorder=2)
    ax1.set_ylabel('Solar Irradiance (W/m²)', color=color_irr)
    ax1.tick_params(axis='y', labelcolor=color_irr)
    ax1.set_ylim(0, max(irradiance_w_m2) * 1.15)

    ax2 = ax1.twinx()
    ax2.plot(hours, solar_kw, 'o-', color=color_pow, linewidth=2.5,
             markersize=6, label='PV output (kW)', zorder=3)
    ax2.fill_between(hours, 0, solar_kw, alpha=0.15, color=color_pow)
    ax2.set_ylabel('PV Power Output (kW)', color=color_pow)
    ax2.tick_params(axis='y', labelcolor=color_pow)
    ax2.set_ylim(0, max(solar_kw) * 1.15)

    peak_h = int(np.argmax(solar_kw))
    ax2.annotate(f'{solar_kw[peak_h]:.1f} kW',
                 xy=(peak_h, solar_kw[peak_h]),
                 xytext=(peak_h + 2, solar_kw[peak_h] + 0.5),
                 arrowprops=dict(arrowstyle='->', color=color_pow, lw=1.2),
                 fontsize=9, color=color_pow, fontweight='bold')

    total_kwh = sum(solar_kw)
    ax1.text(0.98, 0.95, f'Daily total: {total_kwh:.1f} kWh',
             transform=ax1.transAxes, ha='right', va='top',
             fontsize=10, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                       edgecolor=color_pow, alpha=0.9))

    ax1.set_xlabel('Hour of Day')
    ax1.set_title('Hourly Solar PV Production — March 12, 2018 (PVGIS, Paris 48.86°N)')
    ax1.set_xticks(hours)
    ax1.set_xticklabels(hour_labels, rotation=45, ha='right')
    ax1.set_xlim(-0.5, 23.5)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', framealpha=0.9)

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'solar_production_profile.png'))
    plt.close(fig)
    print('Saved solar_production_profile.png')


def plot_building_consumption():
    consumption_kw = [
        6.4866, 6.6216, 6.3942, 6.5357, 6.4078, 7.4681,
        7.6718, 8.3609, 9.7445, 9.6174, 9.3268, 9.6767,
        9.1439, 9.7545, 8.9817, 9.0912, 8.8404, 8.4119,
        8.0242, 8.2074, 7.2935, 6.6164, 6.8120, 6.2006,
    ]

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.fill_between(hours, 0, consumption_kw, alpha=0.25, color='#3182bd')
    ax.plot(hours, consumption_kw, 'o-', color='#3182bd', linewidth=2.5,
            markersize=5, label='Building load', zorder=3)

    mean_load = np.mean(consumption_kw)
    ax.axhline(y=mean_load, color='#e6550d', linestyle='--', linewidth=1.5,
               label=f'Mean load ({mean_load:.2f} kW)')

    peak_h = int(np.argmax(consumption_kw))
    peak_val = max(consumption_kw)
    ax.annotate(f'Peak: {peak_val:.1f} kW',
                xy=(peak_h, peak_val),
                xytext=(peak_h + 2, peak_val + 0.6),
                arrowprops=dict(arrowstyle='->', color='#3182bd', lw=1.2),
                fontsize=9, color='#3182bd', fontweight='bold')

    total_kwh = sum(consumption_kw)
    ax.text(0.98, 0.95, f'Daily total: {total_kwh:.1f} kWh',
            transform=ax.transAxes, ha='right', va='top',
            fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                      edgecolor='#3182bd', alpha=0.9))

    ax.axvspan(8, 17, alpha=0.06, color='orange', label='Business hours')

    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Power Consumption (kW)')
    ax.set_title('Office Building Hourly Energy Consumption — March 12, 2018')
    ax.set_xticks(hours)
    ax.set_xticklabels(hour_labels, rotation=45, ha='right')
    ax.set_xlim(-0.5, 23.5)
    ax.set_ylim(0, max(consumption_kw) * 1.25)
    ax.legend(loc='upper left', framealpha=0.9)

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'building_consumption_profile.png'))
    plt.close(fig)
    print('Saved building_consumption_profile.png')


# --- Chapter 4 (Results): values from tab:annual_savings, tab:sensitivity_price, tab:charge_only_renewable
METHODS_3 = ['Level 0\n(Simple)', 'Level 1\n(RL charge-only)', 'Level 2\n(V2G + RL)']
ANNUAL_COST_EUR = [10_873, 10_753, 10_820]
DAILY_COST_EUR = [29.79, 29.46, 29.64]
ANNUAL_SAVINGS_EUR = [0, 120, 53]

COLORS_3 = ['#4d4d4d', '#2166ac', '#31a354']


def _annotate_bars(ax, bars, values, fmt='{:.0f}', offset=(0, 4)):
    for bar, val in zip(bars, values):
        ax.annotate(
            fmt.format(val),
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=offset,
            textcoords='offset points',
            ha='center', va='bottom', fontsize=9, fontweight='bold',
        )


def plot_annual_cost_three_methods():
    """Bar chart: annual electricity cost for the three intelligence levels (365-day 2018)."""
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(METHODS_3))
    bars = ax.bar(x, ANNUAL_COST_EUR, width=0.55, color=COLORS_3,
                  edgecolor='white', linewidth=0.8, zorder=3)
    _annotate_bars(ax, bars, ANNUAL_COST_EUR, fmt='€{:,.0f}')

    baseline = ANNUAL_COST_EUR[0]
    for i in (1, 2):
        saving = baseline - ANNUAL_COST_EUR[i]
        ax.annotate(
            f'−€{saving} vs Simple',
            xy=(i, ANNUAL_COST_EUR[i]),
            xytext=(0, -28),
            textcoords='offset points',
            ha='center', fontsize=8, color=COLORS_3[i],
        )

    ax.set_ylabel('Annual Cost (€)')
    ax.set_title('Annual Electricity Cost by Intelligence Level\n(365 days, 2018 PVGIS + wholesale prices)')
    ax.set_xticks(x)
    ax.set_xticklabels(METHODS_3)
    ax.set_ylim(10_700, 10_950)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))

    note = (
        f'Daily averages: €{DAILY_COST_EUR[0]:.2f} | '
        f'€{DAILY_COST_EUR[1]:.2f} | €{DAILY_COST_EUR[2]:.2f}'
    )
    ax.text(0.5, 0.02, note, transform=ax.transAxes, ha='center', fontsize=9,
            style='italic', color='#555555')

    fig.tight_layout()
    for name in ('annual_cost_three_methods.png', 'cost_comparison_all_levels.png'):
        fig.savefig(os.path.join(OUTPUT_DIR, name))
        print(f'Saved {name}')
    plt.close(fig)


def plot_annual_savings_vs_simple():
    """Bar chart: annual savings relative to Simple baseline."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    labels = ['Level 1\n(RL charge-only)', 'Level 2\n(V2G + RL)']
    savings = ANNUAL_SAVINGS_EUR[1:]
    colors = COLORS_3[1:]
    x = np.arange(len(labels))
    bars = ax.bar(x, savings, width=0.5, color=colors, edgecolor='white', zorder=3)
    _annotate_bars(ax, bars, savings, fmt='€{:,.0f}')

    for i, (lab, sav) in enumerate(zip(labels, savings)):
        pct = 100 * sav / ANNUAL_COST_EUR[0]
        ax.text(i, sav / 2, f'{pct:.1f}%', ha='center', va='center',
                fontsize=10, color='white', fontweight='bold')

    ax.set_ylabel('Annual Savings vs Simple (€)')
    ax.set_title('Annual Cost Savings — RL Methods vs Simple Baseline')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, max(savings) * 1.25)

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'annual_savings_vs_simple.png'))
    plt.close(fig)
    print('Saved annual_savings_vs_simple.png')


def plot_price_sensitivity_comparison():
    """Grouped bars: daily cost under different price-variation scenarios."""
    scenarios = ['Flat rate', 'Low (±20%)', 'Base (±50%)', 'High (±100%)']
    simple = [33.07, 31.12, 31.63, 32.14]
    rl = [33.07, 30.02, 30.45, 29.88]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(scenarios))
    w = 0.35
    ax.bar(x - w / 2, simple, w, label='Simple', color='#4d4d4d', zorder=3)
    ax.bar(x + w / 2, rl, w, label='RL (charge-only)', color='#2166ac', zorder=3)

    ax.set_ylabel('Daily Cost (€)')
    ax.set_title('Price Sensitivity — Daily Cost by Method and Price Scenario')
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=15, ha='right')
    ax.legend(loc='upper right', framealpha=0.9)
    ax.set_ylim(28.5, 34)

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'price_sensitivity_comparison.png'))
    plt.close(fig)
    print('Saved price_sensitivity_comparison.png')


def plot_grid_energy_charge_only():
    """Bar chart: grid energy use (charge-only scenario)."""
    methods = ['Simple', 'RL']
    grid_kwh = [728.5, 706.3]
    reduction_pct = 100 * (grid_kwh[0] - grid_kwh[1]) / grid_kwh[0]

    fig, ax = plt.subplots(figsize=(6, 4.5))
    x = np.arange(len(methods))
    bars = ax.bar(x, grid_kwh, width=0.45,
                  color=['#4d4d4d', '#2166ac'], edgecolor='white', zorder=3)
    _annotate_bars(ax, bars, grid_kwh, fmt='{:.1f} kWh')

    ax.annotate(f'−{reduction_pct:.1f}% grid energy',
                xy=(1, grid_kwh[1]), xytext=(0.5, 30),
                textcoords='offset points', ha='center', fontsize=9,
                color='#2166ac', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='#2166ac', lw=1.2))

    ax.set_ylabel('Grid Energy (kWh / day)')
    ax.set_title('Grid Energy Consumption — Charge-Only Scenario')
    ax.set_xticks(x)
    ax.set_xticklabels(methods)
    ax.set_ylim(680, 760)

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'grid_energy_charge_only.png'))
    plt.close(fig)
    print('Saved grid_energy_charge_only.png')


def plot_v2g_sell_price_invariance():
    """Grouped bars: V2G cost/revenue unchanged across sell-price multipliers (annual avg)."""
    multipliers = ['80% of buy', '100% of buy', '120% of buy']
    simple_cost = [29.79, 29.79, 29.79]
    rl_cost = [29.64, 29.64, 29.64]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(multipliers))
    w = 0.35
    ax.bar(x - w / 2, simple_cost, w, label='V2G Simple', color='#4d4d4d', zorder=3)
    ax.bar(x + w / 2, rl_cost, w, label='V2G RL', color='#31a354', zorder=3)

    ax.axhline(y=29.79, color='#b2182b', linestyle=':', linewidth=1.2,
               label='V2G revenue = €0 (all cases)')

    ax.set_ylabel('Avg Daily Cost (€)')
    ax.set_title('V2G Sell-Price Sensitivity — No Discharge at Any Multiplier\n(365-day annual average, 2018)')
    ax.set_xticks(x)
    ax.set_xticklabels(multipliers)
    ax.legend(loc='upper right', framealpha=0.9, fontsize=9)
    ax.set_ylim(29.4, 30.0)

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, 'v2g_sell_price_invariance.png'))
    plt.close(fig)
    print('Saved v2g_sell_price_invariance.png')


if __name__ == '__main__':
    plot_electricity_prices()
    plot_solar_production()
    plot_building_consumption()
    plot_annual_cost_three_methods()
    plot_annual_savings_vs_simple()
    plot_price_sensitivity_comparison()
    plot_grid_energy_charge_only()
    plot_v2g_sell_price_invariance()
    print('All figures generated.')
