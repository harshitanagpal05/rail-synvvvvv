# Railsync 2.0 — Layer 0 Final Dataset

## Contents

- `segments_master.csv` — exactly 50 assets.
- `maintenance_tasks.csv` — maintenance tasks with actual/planned duration,
  overdue status and ~20% overruns.
- `train_timetable.csv` — synthetic IR-style timetable.
- `corridor_blocks.csv` — timetable-derived candidate maintenance windows.
- `defect_events.csv` — 24 months of defects and failures.
- `hazard_audit.csv` — segment-day causal hazard calculation.
- `survival_outcomes.csv` — correct time-to-first-failure + right censoring.
- `segment_monthly_panel.csv` — 24-month ML/survival feature panel.
- `RULES.md` — complete causal generation rules.
- `VALIDATION.json` — automated validation summary.

## Main Layer 0 contract

1. 50 segments.
2. 2 divisions.
3. Track, S&T and Traction/OHE.
4. Required asset fields.
5. 24 months of defect events.
6. Explicit 8x Grade-3 clustering rule.
7. Explicit 1.5x Track monsoon rule.
8. Explicit 2x high-freight + age >30 rule.
9. Explicit 1.5x per active overdue task rule.
10. Correct right censoring.
11. Maintenance task overrun pattern ~20%.
12. Passenger timetable fixed.
13. Freight timetable variable.
14. Corridor windows derived from timetable intervals.
15. Separate RULES.md.
16. Causal audit trail for inspection.

## Reproducibility

Seed = 42.

## Disclaimer

All data are synthetic and intended for hackathon/prototype modelling only.
