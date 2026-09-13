# Railsync 2.0 — Layer 1 Colab Run Guide

## What Layer 1 does

This script consumes the **Layer 0 final dataset** and implements:

- Daily discrete-time survival using XGBoost (`binary:logistic`).
- Segment-month → daily expansion.
- Survival curve `S(t) = product(1 - daily_hazard)`.
- `risk_30d = 1 - S(30)`.
- Weibull AFT baseline using `lifelines`.
- Approximate Weibull hazard ratios derived from the AFT coefficients.
- Chronological timeline split: months 1–18 train, months 19–24 test.
- C-index, 30-day Brier score, calibration curve, Top-20 precision and base rate.
- Monotonic XGBoost constraints on age, Grade-3 defect count, defect count and overdue state.
- Cold-start Weibull priors by asset type + age bucket for history <60 days.
- XGBoost duration regressor + overrun classifier for maintenance duration.
- Per-segment output:
  - `risk_30d`
  - `expected_downtime_days`
  - `preventive_block_duration_hrs`
  - `confidence`

> Important modelling note: Weibull AFT is naturally an **accelerated-failure-time** model. Its native coefficients are time-ratio effects, not ordinary proportional-hazards coefficients. The script additionally reports an approximate hazard ratio as `exp(-rho * beta_lambda)` when the Weibull shape parameter is treated as common.

## Your Layer 0 dataset is already compatible

The supplied Layer 0 package contains:

- 50 segments
- 2 divisions: Agra and Delhi
- Track, S&T and Traction/OHE
- 24 monthly panel months
- defect events
- survival outcomes with right censoring
- maintenance tasks with planned/actual duration and overrun
- corridor blocks

The Layer 1 script reconstructs `overdue_tasks_active` from the maintenance task dates instead of pretending that the monthly panel already contains that field.

## Google Colab: exact steps

### Step 1 — Open Colab

Open:

https://colab.research.google.com/

Create **New Notebook**.

### Step 2 — Save the notebook to Drive

Click **File → Save a copy in Drive**.

Create a Drive folder such as:

`My Drive/Railsync_2.0/Layer_1/`

Google's Colab FAQ confirms that mounting Drive lets notebook code access files in your Drive after you grant authorization.

### Step 3 — Upload the Layer 1 package to Drive

On your Mac, unzip:

`Railsync_2.0_Layer_0_FINAL(1).zip`

You will see the CSV files and `RULES.md`.

In Google Drive create:

`My Drive/Railsync_2.0/Layer_1/data/`

Upload these five files into `data/`:

- `segments_master.csv`
- `segment_monthly_panel.csv`
- `survival_outcomes.csv`
- `defect_events.csv`
- `maintenance_tasks.csv`

You can also upload the other Layer 0 files for safekeeping, but Layer 1 needs the five above.

### Step 4 — Mount Drive

Run this as the first Colab cell:

```python
from google.colab import drive
drive.mount('/content/drive')
```

Authorize the Google account when Colab asks.

Then verify:

```python
from pathlib import Path

PROJECT = Path('/content/drive/MyDrive/Railsync_2.0/Layer_1')
DATA = PROJECT / 'data'

print(DATA)
print(list(DATA.glob('*.csv')))
```

You should see the five CSVs.

### Step 5 — Upload `layer1_train.py`

In Colab's left **Files** panel, you can upload `layer1_train.py` from your Mac.

Then copy it into your Drive project so it persists:

```python
import shutil

shutil.copy('/content/layer1_train.py',
            '/content/drive/MyDrive/Railsync_2.0/Layer_1/layer1_train.py')
```

If you upload it directly to Drive through the browser instead, skip the copy command.

### Step 6 — Install dependencies

Run:

```python
%pip install -q -U pandas numpy scikit-learn xgboost lifelines joblib matplotlib
```

If Colab asks for a runtime restart after installation, restart it and rerun the Drive mount cell.

### Step 7 — Point the script to your Drive data

The script expects a folder called `data`.

Run:

```python
%cd /content/drive/MyDrive/Railsync_2.0/Layer_1
```

Then:

```python
!python layer1_train.py
```

That is the main training command.

## Step 8 — Check the outputs

After training, you should get:

`layer1_outputs/`

with:

- `segment_failure_forecasts.csv`
- `metrics.json`
- `calibration_curve.csv`
- `calibration_curve.png`
- `evaluation_anchor_predictions.csv`
- `feature_importance.csv`
- `weibull_hazard_ratios.csv`
- `models/discrete_survival_xgboost.joblib`
- `models/weibull_aft.joblib`
- `models/duration_xgb_regressor.joblib`
- `models/overrun_xgb_classifier.joblib`

Because the notebook is running from Drive, these files persist after the Colab runtime disconnects.

## Step 9 — Inspect the final predictions

Run:

```python
import pandas as pd

pred = pd.read_csv('layer1_outputs/segment_failure_forecasts.csv')
pred.sort_values('risk_30d', ascending=False).head(20)
```

For SIH demo purposes, the most important columns are:

```text
segment_id
division
asset_type
risk_30d
expected_downtime_days
preventive_block_duration_hrs
overrun_probability
confidence
cold_start_fallback
forecast_as_of
```

## Step 10 — Print the required metrics

Run:

```python
import json

with open('layer1_outputs/metrics.json') as f:
    metrics = json.load(f)

for k, v in metrics.items():
    print(f'{k}: {v}')
```

The required evaluation fields are:

- `c_index`
- `brier_score_30d`
- `top20_precision`
- `base_rate`
- `top20_lift_vs_base_rate`

The duration head additionally prints:

- `duration_test_mae_hrs`
- `duration_test_rmse_hrs`
- `overrun_test_auc`

## Important interpretation for your SIH presentation

Say:

> “Layer 1 uses a discrete-time survival formulation. Each segment-month is expanded into daily risk rows. XGBoost estimates the daily conditional failure probability. The full survival curve is obtained by multiplying one minus the daily hazards. A chronological 18-month training / 6-month testing split prevents future-month leakage.”

For monotonicity:

> “The XGBoost hazard head has monotonic constraints so increasing age, Grade-3 defect burden and overdue-maintenance burden cannot mathematically decrease predicted hazard.”

For cold start:

> “Segments with less than 60 days of history use a Weibull prior indexed by asset type and age bucket rather than an unstable learned segment history.”

## One modelling caveat

The Layer 0 monthly panel contains `defect_count_month`, which represents the current month's total. The Layer 1 script deliberately uses a one-month lag (`defect_count_prev_month`) for forecasting so that the model does not use information from the month it is supposed to predict.

Similarly, the failure label is placed on the actual failure date from `defect_events.csv`, not blindly on the end of a month.

## If you get an error

First run:

```python
!pwd
!ls -lah
!ls -lah data
```

You should be in:

`/content/drive/MyDrive/Railsync_2.0/Layer_1`

and `data/` should contain the five required CSVs.

If the files are elsewhere, change `PROJECT` or move the CSVs into the `data` folder.

