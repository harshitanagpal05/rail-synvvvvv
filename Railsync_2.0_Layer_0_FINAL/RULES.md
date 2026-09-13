# Railsync 2.0 — Layer 0 Synthetic Data Generator Rules

## Purpose

This package creates synthetic Indian Railways-style infrastructure data for
the Railsync 2.0 SIH prototype because TMS/SMMS/TDMS operational systems are
internal and are not used here.

**All records are synthetic. They do not represent actual Indian Railways
assets, trains, maintenance records, failures, or operational schedules.**

---

## 1. Asset population

Exactly **50 asset segments** are generated across **2 divisions**:

- Agra
- Delhi

Asset domains:

- Track
- S&T
- Traction/OHE

Required segment attributes:

- `id`
- `division`
- `asset_type`
- `length_km`
- `age_years`
- `installation_year`
- `curve_gradient_class`
- `monsoon_exposure`
- `freight_density_class`

---

## 2. Observation window

Defect/failure observation period:

**2024-01-01 through 2025-12-31**

This provides 24 calendar months.

---

## 3. Causal hazard model

Each segment-day starts with an asset-type-specific baseline hazard.

The following multipliers are then applied.

### Rule A — Recent Grade-3 clustering

If a segment has **2 or more Grade-3 defects in the previous 90 days**:

`hazard × 8.0`

This is intended to model accelerating degradation / latent unresolved
condition following repeated critical defects.

### Rule B — Monsoon

For **Track** assets during:

- June
- July
- August
- September

apply:

`hazard × 1.5`

### Rule C — Freight + age

If both conditions hold:

- `freight_density_class == High`
- `age_years > 30`

apply:

`hazard × 2.0`

### Rule D — Overdue maintenance

Maintenance state is generated **before** defect events.

At every segment-day, an overdue task is active if its planned date has passed,
the task is flagged overdue, and its completion date has not yet occurred.

For each active overdue task:

`hazard × 1.5`

For numerical stability in this prototype, the compounded overdue multiplier is
capped after two active overdue tasks.

### Additional realism factors

- Age > 30: ×1.45
- High monsoon exposure: ×1.25
- High curve class: ×1.25
- Steep gradient: ×1.20

These are additional synthetic structural effects.

---

## 4. Defect severity

Defects are sampled as:

- Grade 1 → Minor
- Grade 2 → Major
- Grade 3 → Critical

A subset of Grade-3 events becomes `failure_event = 1`.

The generated defect table also records the causal state at the time of each
event, including recent Grade-3 count, active overdue tasks and applied
multipliers.

---

## 5. Causal audit trail

`hazard_audit.csv` contains a segment-day record of the hazard calculation.

It allows the model developer or SIH evaluator to inspect:

- base hazard
- Grade-3 count in previous 90 days
- active overdue tasks
- monsoon state
- freight + age state
- each causal multiplier
- total multiplier
- final daily failure hazard

This makes the synthetic causal process auditable rather than merely
documented in prose.

---

## 6. Maintenance tasks

Each segment receives multiple maintenance tasks.

Required fields:

- `task_id`
- `segment_id`
- `department`
- `type`
- `planned_duration_hrs`
- `actual_duration_hrs`
- `overdue_flag`

Additional useful fields:

- division
- planned_date
- completion_date
- overdue_days
- overrun_flag

Approximately **20%** of tasks are deliberately generated as overruns.

For overrun tasks:

`actual_duration ≈ 1.20–1.65 × planned_duration`

---

## 7. Timetable

The timetable includes:

- Passenger
- Express
- Superfast
- Freight

Passenger/Express/Superfast services are fixed.

Freight services are variable and receive day-specific schedule variation.

---

## 8. Corridor block generation

`corridor_blocks.csv` is derived from **actual timetable intervals**.

Process:

1. Determine trains running on a given date.
2. Apply variable timing shifts only to freight.
3. Sort occupied train intervals.
4. Merge overlapping train intervals.
5. Find gaps between occupied intervals.
6. Convert gaps of at least 2 hours into candidate maintenance windows.
7. Assign candidate windows to infrastructure segments.

Therefore block windows are not generated independently of the timetable.

---

## 9. Survival analysis and right censoring

`survival_outcomes.csv` contains exactly one time-to-event outcome per segment.

If a segment experiences a failure:

- `failure_event = 1`
- `right_censored = 0`
- `duration_days` = time from observation start to first failure

If a segment does not experience a failure during the entire observation period:

- `failure_event = 0`
- `right_censored = 1`
- `duration_days` = full observation duration

A non-failing segment is **never treated as a failure**.

The monthly panel is provided separately for downstream forecasting features.

---

## 10. Reproducibility

Random seeds:

- Python: `42`
- NumPy: `42`

---

## 11. Synthetic-data disclaimer

This dataset is a realistic prototype simulation, not a copy or reconstruction
of confidential Indian Railways TMS/SMMS/TDMS data.

No operational safety decision should be made from these records.
