# Single-Office Time Series Calculations (ELMAS)

This document records the calculations used to generate a synthetic
single-office hourly time series from the ELMAS dataset (Office cluster, #5).

## Data sources

Files used from `ELMAS_dataset/`:
- `Time_series_18_clusters.csv` (hourly cluster profiles, kW)
- `Clusters_after_manual_reclassification.csv` (NACE class -> cluster mapping)
- `Annual_energy_time_series.csv` (annual energy per class, kWh)
- `Nb_customers_time_series.csv` (number of customers per class)

## Step 1: Office cluster base series

Let `L_t` be the Office cluster (#5) hourly load from `Time_series_18_clusters.csv`.
This series is hourly for 2018 with `T = 8736` points.

Annual energy of the cluster series:

```
E_cluster = sum_{t=1..T} L_t
```

## Step 2: Per-customer annual energy for Office cluster

The Office cluster is identified using `Clusters_after_manual_reclassification.csv`
by selecting all rows where `Cluster = 5`. For each (Power_level, Class), the
annual energy `E_c` and number of customers `N_c` are taken from:
- `Annual_energy_time_series.csv`
- `Nb_customers_time_series.csv`

Per-customer annual energy for each class:

```
e_c = E_c / N_c
```

Target annual energy for a single office building uses the 75th percentile
of the per-customer values:

```
E_target = Q_0.75({e_c})
```

### Values used

```
Mean per-customer energy: 10429 kWh
P75 per-customer energy:  58831 kWh
Target method:            p75
Target annual energy:     58831 kWh
```

## Step 3: Scale the cluster profile to the target energy

The Office cluster series is scaled to match the target annual energy:

```
L_t_scaled = L_t * (E_target / E_cluster)
```

## Step 4: Add stochastic variability

Two multiplicative noise factors are applied:
- daily factor `alpha_d` (same for all hours of a day)
- hourly factor `beta_t` (unique for each hour)

```
alpha_d ~ Normal(1, sigma_d^2),   sigma_d = 0.08, clipped to [0.7, 1.3]
beta_t  ~ Normal(1, sigma_h^2),   sigma_h = 0.03, clipped to [0.9, 1.1]
```

Synthetic series before final normalization:

```
L_t_syn = L_t_scaled * alpha_d(t) * beta_t
```

Random seed used: `20260218`.

## Step 5: Re-normalize to preserve annual energy

After applying noise, the series is re-scaled to exactly match `E_target`:

```
L_t_final = L_t_syn * (E_target / sum_{t=1..T} L_t_syn)
```

## Resulting single-office series statistics

```
Annual energy:  58831 kWh
Mean load:      6.73 kW
Peak load:      11.92 kW
```

## Output file

Generated CSV:
- `office_single_building_timeseries.csv`
- Columns: `Time`, `Office_kW`

