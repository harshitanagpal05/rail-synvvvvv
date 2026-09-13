
#!/usr/bin/env python3
"""
Railsync 2.0 — Layer 1: Failure Forecasting
Designed for Google Colab or local Python.

Input: Layer 0 CSVs
Output:
  layer1_outputs/segment_failure_forecasts.csv
  layer1_outputs/metrics.json
  layer1_outputs/calibration_curve.csv
  layer1_outputs/feature_importance.csv
  layer1_outputs/weibull_hazard_ratios.csv
  layer1_outputs/models/*.json
"""

from pathlib import Path
import json, warnings, joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.metrics import (
    brier_score_loss, precision_score, mean_absolute_error, mean_squared_error,
    roc_auc_score
)
from sklearn.calibration import calibration_curve
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier, XGBRegressor
from lifelines import WeibullAFTFitter
from lifelines.utils import concordance_index

warnings.filterwarnings("ignore")
SEED = 42

# -----------------------------
# Configuration
# -----------------------------
DATA_DIR = Path("data")
OUT_DIR = Path("layer1_outputs")
MODEL_DIR = OUT_DIR / "models"
TRAIN_LAST_MONTH = 18
HISTORY_DAYS_COLD_START = 60

for d in [OUT_DIR, MODEL_DIR]:
    d.mkdir(parents=True, exist_ok=True)

REQUIRED = [
    "segments_master.csv", "segment_monthly_panel.csv",
    "survival_outcomes.csv", "defect_events.csv", "maintenance_tasks.csv"
]

def read_inputs():
    missing = [f for f in REQUIRED if not (DATA_DIR / f).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing Layer 0 files: {missing}. Put all Layer 0 CSVs in {DATA_DIR.resolve()}"
        )
    seg = pd.read_csv(DATA_DIR / "segments_master.csv")
    panel = pd.read_csv(DATA_DIR / "segment_monthly_panel.csv", parse_dates=["month"])
    outcomes = pd.read_csv(DATA_DIR / "survival_outcomes.csv",
                           parse_dates=["observation_start", "observation_end", "observed_end"])
    defects = pd.read_csv(DATA_DIR / "defect_events.csv", parse_dates=["event_date"])
    tasks = pd.read_csv(DATA_DIR / "maintenance_tasks.csv",
                         parse_dates=["planned_date", "completion_date"])
    return seg, panel, outcomes, defects, tasks

# -----------------------------
# Feature engineering
# -----------------------------
def build_monthly_features(seg, panel, tasks):
    p = panel.copy().sort_values(["segment_id", "month"])
    p["defect_count_prev_month"] = (
        p.groupby("segment_id")["defect_count_month"].shift(1).fillna(0)
    )

    # Reconstruct active overdue state from Layer 0 maintenance dates.
    # This is preferable to treating future/current task completion as a feature.
    rows = []
    for _, r in p.iterrows():
        sid, m = r["segment_id"], r["month"]
        month_start = pd.Timestamp(m).normalize()
        active = tasks[
            (tasks.segment_id == sid) &
            (tasks.planned_date < month_start) &
            (tasks.completion_date >= month_start)
        ]
        # Include tasks planned before month start with missing completion dates.
        active = tasks[
            (tasks.segment_id == sid) &
            (tasks.planned_date < month_start) &
            (tasks.overdue_flag == 1) &
            ((tasks.completion_date.isna()) | (tasks.completion_date >= month_start))
        ]
        rows.append({
            "segment_id": sid,
            "month": m,
            "overdue_tasks_active": int(len(active)),
            "overdue_days_max": float(active["overdue_days"].max()) if len(active) else 0.0
        })
    overdue = pd.DataFrame(rows)
    p = p.merge(overdue, on=["segment_id", "month"], how="left")

    # Attach all master attributes.
    p = p.drop(columns=["division", "asset_type"], errors="ignore").merge(
        seg, left_on="segment_id", right_on="id", how="left"
    )
    p = p.drop(columns=["id"], errors="ignore")

    # Avoid look-ahead from the current month's defect total.
    # Grade-3 previous-90d is already lagged by Layer 0's causal construction.
    p["defect_count_prev_month"] = p["defect_count_prev_month"].clip(lower=0)
    p["overdue_tasks_active"] = p["overdue_tasks_active"].clip(lower=0)

    return p

def add_daily_labels(monthly, defects):
    """Expand each segment-month to daily rows and place failure on its actual event date."""
    daily_parts = []
    failure_dates = (
        defects.loc[defects["failure_event"].eq(1)]
        .sort_values("event_date")
        .groupby("segment_id")["event_date"].first()
        .to_dict()
    )

    for _, r in monthly.iterrows():
        month_start = pd.Timestamp(r["month"]).normalize()
        month_end = month_start + pd.offsets.MonthEnd(1)
        dates = pd.date_range(month_start, month_end, freq="D")
        x = pd.DataFrame({"date": dates})
        for c, v in r.items():
            if c != "month":
                x[c] = v
        x["failure_event_daily"] = 0
        fdate = failure_dates.get(r["segment_id"])
        if fdate is not None:
            x.loc[x["date"].eq(pd.Timestamp(fdate)), "failure_event_daily"] = 1
            # Once failure occurs, the segment leaves the risk set.
            x = x[x["date"] <= pd.Timestamp(fdate)]
        daily_parts.append(x)

    return pd.concat(daily_parts, ignore_index=True)

# -----------------------------
# Encoding / monotonic XGBoost
# -----------------------------
BASE_FEATURES = [
    "age_years", "length_km", "grade3_defects_previous_90d",
    "defect_count_prev_month", "overdue_tasks_active", "overdue_days_max",
    "monsoon_month", "monsoon_exposure", "freight_density_class",
    "curve_gradient_class", "asset_type", "division"
]

def encode_features(df, columns=None):
    x = df[BASE_FEATURES].copy()
    categorical = [
        "monsoon_exposure", "freight_density_class",
        "curve_gradient_class", "asset_type", "division"
    ]
    x = pd.get_dummies(x, columns=categorical, dtype=float)
    if columns is not None:
        x = x.reindex(columns=columns, fill_value=0)
    return x

def monotone_constraints(columns):
    # Required: hazard non-decreasing in defect counts, age, overdue.
    positive = {
        "age_years", "grade3_defects_previous_90d",
        "defect_count_prev_month", "overdue_tasks_active", "overdue_days_max"
    }
    return tuple(1 if c in positive else 0 for c in columns)

# -----------------------------
# Train discrete-time survival model
# -----------------------------
def train_discrete_survival(daily):
    train = daily[daily["month"] <= pd.Timestamp("2025-06-01")].copy()
    test = daily[daily["month"] >= pd.Timestamp("2025-07-01")].copy()

    Xtr = encode_features(train)
    Xte = encode_features(test, Xtr.columns)
    ytr, yte = train["failure_event_daily"].astype(int), test["failure_event_daily"].astype(int)

    model = XGBClassifier(
        objective="binary:logistic",
        n_estimators=350,
        max_depth=4,
        learning_rate=0.035,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=2.0,
        min_child_weight=3,
        eval_metric="logloss",
        tree_method="hist",
        random_state=SEED,
        n_jobs=-1,
        monotone_constraints=monotone_constraints(Xtr.columns)
    )
    model.fit(Xtr, ytr)
    return model, Xtr.columns.tolist(), train, test

def predict_daily_hazard(model, columns, df):
    X = encode_features(df, columns)
    return np.clip(model.predict_proba(X)[:, 1], 1e-8, 1 - 1e-8)

def survival_curve_from_hazards(h):
    return np.cumprod(1.0 - np.asarray(h))

# -----------------------------
# Weibull AFT baseline
# -----------------------------
def build_segment_training_table(monthly, outcomes):
    train_months = monthly[monthly["month"] <= pd.Timestamp("2025-06-01")]
    # Use only information available in the first 18 months.
    agg = train_months.groupby("segment_id").agg(
        age_years=("age_years", "first"),
        grade3_defects_previous_90d=("grade3_defects_previous_90d", "mean"),
        defect_count_prev_month=("defect_count_prev_month", "mean"),
        overdue_tasks_active=("overdue_tasks_active", "mean"),
        monsoon_month=("monsoon_month", "mean")
    ).reset_index()
    agg = agg.merge(
        monthly[["segment_id", "asset_type", "division"]].drop_duplicates("segment_id"),
        on="segment_id"
    )
    out = outcomes[["segment_id", "duration_days", "failure_event"]].merge(agg, on="segment_id")
    return out

def fit_weibull_baseline(segment_train):
    w = segment_train.copy()
    cats = ["asset_type", "division"]
    w = pd.get_dummies(w, columns=cats, dtype=float)
    w["event"] = w["failure_event"].astype(int)
    w = w.drop(columns=["segment_id", "failure_event"])
    aft = WeibullAFTFitter(penalizer=0.10)
    aft.fit(w, duration_col="duration_days", event_col="event")
    return aft, w.columns.tolist()

def weibull_hazard_ratios(aft):
    """For a Weibull AFT with constant rho, HR = exp(-rho * beta_lambda)."""
    coefs = aft.params_.loc["lambda_"].copy()
    rho = float(np.exp(aft.params_.loc["rho_"].iloc[0]))
    hrs = np.exp(-rho * coefs)
    return pd.DataFrame({
        "feature": coefs.index,
        "aft_coefficient": coefs.values,
        "approx_hazard_ratio": hrs.values
    }).sort_values("approx_hazard_ratio")

# -----------------------------
# Cold-start Weibull priors
# -----------------------------
def fit_weibull_priors(seg, outcomes):
    df = outcomes.merge(seg[["id", "asset_type", "age_years"]],
                        left_on="segment_id", right_on="id")
    df["age_bucket"] = pd.cut(
        df["age_years"], [-1, 10, 20, 30, 40, np.inf],
        labels=["<=10", "11-20", "21-30", "31-40", ">40"]
    )
    priors = {}
    global_w = __import__("lifelines").WeibullFitter()
    global_w.fit(df.duration_days, event_observed=df.failure_event)
    priors[("GLOBAL", "GLOBAL")] = global_w

    for (asset, ageb), g in df.groupby(["asset_type", "age_bucket"], observed=True):
        if len(g) >= 3 and g.failure_event.sum() >= 1:
            wf = __import__("lifelines").WeibullFitter()
            wf.fit(g.duration_days, event_observed=g.failure_event)
            priors[(asset, str(ageb))] = wf

    for asset, g in df.groupby("asset_type"):
        if len(g) >= 4 and g.failure_event.sum() >= 1:
            wf = __import__("lifelines").WeibullFitter()
            wf.fit(g.duration_days, event_observed=g.failure_event)
            priors[(asset, "GLOBAL")] = wf
    return priors

def prior_30d_risk(priors, asset_type, age_years):
    ageb = str(pd.cut([age_years], [-1,10,20,30,40,np.inf],
                      labels=["<=10","11-20","21-30","31-40",">40"])[0])
    wf = priors.get((asset_type, ageb),
         priors.get((asset_type, "GLOBAL"),
         priors[("GLOBAL", "GLOBAL")]))
    s0 = float(wf.survival_function_at_times(0).iloc[0])
    s30 = float(wf.survival_function_at_times(30).iloc[0])
    return float(np.clip(1 - s30 / max(s0, 1e-12), 0, 1))

# -----------------------------
# Duration / overrun head
# -----------------------------
DURATION_FEATURES = [
    "planned_duration_hrs", "overdue_days", "overdue_flag",
    "asset_type", "division", "department", "type"
]

def task_features(tasks, seg):
    t = tasks.merge(
        seg[["id", "asset_type", "age_years", "length_km"]],
        left_on="segment_id", right_on="id", how="left"
    )
    return t

def encode_duration(df, columns=None):
    x = df[DURATION_FEATURES].copy()
    cats = ["asset_type", "division", "department", "type"]
    x = pd.get_dummies(x, columns=cats, dtype=float)
    if columns is not None:
        x = x.reindex(columns=columns, fill_value=0)
    return x

def train_duration_heads(tasks, seg):
    t = task_features(tasks, seg)
    # Chronological split, not random split.
    t = t.sort_values("planned_date")
    cut = t["planned_date"].quantile(0.75)
    tr, te = t[t.planned_date <= cut], t[t.planned_date > cut]

    Xtr = encode_duration(tr)
    Xte = encode_duration(te, Xtr.columns)

    reg = XGBRegressor(
        objective="reg:squarederror", n_estimators=250, max_depth=4,
        learning_rate=0.04, subsample=0.9, colsample_bytree=0.9,
        reg_lambda=2.0, random_state=SEED, n_jobs=-1
    )
    reg.fit(Xtr, tr["actual_duration_hrs"])

    clf = XGBClassifier(
        objective="binary:logistic", n_estimators=250, max_depth=4,
        learning_rate=0.04, subsample=0.9, colsample_bytree=0.9,
        eval_metric="logloss", random_state=SEED, n_jobs=-1
    )
    clf.fit(Xtr, tr["overrun_flag"].astype(int))

    pred = reg.predict(Xte)
    metrics = {
        "duration_test_mae_hrs": float(mean_absolute_error(te.actual_duration_hrs, pred)),
        "duration_test_rmse_hrs": float(mean_squared_error(te.actual_duration_hrs, pred, squared=False)),
        "overrun_test_auc": float(roc_auc_score(
            te.overrun_flag, clf.predict_proba(Xte)[:,1]
        )) if te.overrun_flag.nunique() > 1 else None
    }
    return reg, clf, Xtr.columns.tolist(), metrics

# -----------------------------
# Evaluation
# -----------------------------
def make_anchor_predictions(model, columns, test_daily, anchor_date):
    at = test_daily[
        (test_daily["date"] >= pd.Timestamp(anchor_date)) &
        (test_daily["date"] < pd.Timestamp(anchor_date) + pd.Timedelta(days=30))
    ].copy()
    if at.empty:
        return pd.DataFrame()
    at["hazard"] = predict_daily_hazard(model, columns, at)
    out = []
    for sid, g in at.groupby("segment_id"):
        g = g.sort_values("date")
        # If a failure occurs before day 30, survival is zero after that date.
        risk = 1 - np.prod(1 - g["hazard"].values)
        out.append({"segment_id": sid, "anchor": anchor_date, "risk_30d": risk})
    return pd.DataFrame(out)

def evaluate(model, columns, daily, outcomes):
    test = daily[daily["month"] >= pd.Timestamp("2025-07-01")].copy()

    # Test risk set = segments alive at start of test period.
    test_start = pd.Timestamp("2025-07-01")
    failed_before = set(
        outcomes.loc[
            (outcomes.failure_event == 1) &
            (outcomes.observed_end < test_start), "segment_id"
        ]
    )
    eligible = [s for s in daily.segment_id.unique() if s not in failed_before]

    # 30-day Brier + calibration across monthly test anchors.
    anchors = pd.date_range("2025-07-01", "2025-12-01", freq="MS")
    rows = []
    failure_dates = (
        outcomes[outcomes.failure_event == 1]
        .set_index("segment_id")["observed_end"].to_dict()
    )
    for anchor in anchors:
        for sid in eligible:
            g = test[
                (test.segment_id == sid) &
                (test.date >= anchor) &
                (test.date < anchor + pd.Timedelta(days=30))
            ]
            if len(g) == 0:
                continue
            hz = predict_daily_hazard(model, columns, g)
            risk = 1 - np.prod(1 - hz)
            fd = failure_dates.get(sid)
            y = int(fd is not None and anchor <= fd < anchor + pd.Timedelta(days=30))
            rows.append({"segment_id": sid, "anchor": anchor, "risk_30d": risk, "y": y})

    ev = pd.DataFrame(rows)
    brier = float(brier_score_loss(ev.y, ev.risk_30d))
    prob_true, prob_pred = calibration_curve(ev.y, ev.risk_30d, n_bins=5, strategy="quantile")
    cal = pd.DataFrame({"predicted": prob_pred, "observed": prob_true})

    # Top-20 precision on the first test anchor, with base-rate comparison.
    first = ev[ev.anchor == pd.Timestamp("2025-07-01")].copy()
    first = first.sort_values("risk_30d", ascending=False)
    k = min(20, len(first))
    top20_precision = float(first.head(k).y.mean()) if k else None
    base_rate = float(first.y.mean()) if len(first) else None

    # C-index: time from 2025-07-01 to event/end of test.
    times, events, risks = [], [], []
    test_end = pd.Timestamp("2025-12-31")
    for sid in eligible:
        o = outcomes[outcomes.segment_id == sid].iloc[0]
        observed = pd.Timestamp(o.observed_end)
        end = min(observed, test_end)
        times.append(max((end - test_start).days, 1))
        events.append(int(o.failure_event == 1 and observed >= test_start and observed <= test_end))
        r = first.loc[first.segment_id == sid, "risk_30d"]
        risks.append(float(r.iloc[0]) if len(r) else 0.0)
    cidx = float(concordance_index(times, -np.asarray(risks), events))

    metrics = {
        "timeline_split": "months 1-18 train; months 19-24 test",
        "test_at_risk_segments": len(eligible),
        "c_index": cidx,
        "brier_score_30d": brier,
        "top20_precision": top20_precision,
        "base_rate": base_rate,
        "top20_lift_vs_base_rate": (
            top20_precision / base_rate if base_rate and top20_precision is not None else None
        ),
        "n_30d_anchor_rows": int(len(ev))
    }
    return metrics, cal, ev

# -----------------------------
# Final segment forecasts
# -----------------------------
def final_forecasts(seg, panel, daily, model, columns, priors, duration_reg, duration_clf, dur_cols):
    final_month = panel["month"].max()
    latest = panel[panel.month == final_month].copy()
    # Reconstruct final feature frame from monthly pipeline fields.
    # Rebuild overdue values by using the same function is cleaner than relying on panel.
    # Caller passes already engineered daily data, so use final daily rows.
    d = daily[daily["month"] == final_month].copy()
    d["hazard"] = predict_daily_hazard(model, columns, d)

    duration_tasks = task_features(
        pd.read_csv(DATA_DIR / "maintenance_tasks.csv", parse_dates=["planned_date","completion_date"]),
        seg
    )
    latest_task = duration_tasks.sort_values("planned_date").groupby("segment_id").tail(1).copy()
    if latest_task.empty:
        latest_task = pd.DataFrame({"segment_id": seg.id})

    rows = []
    for sid, g in d.groupby("segment_id"):
        g = g.sort_values("date")
        risk = 1 - np.prod(1 - g["hazard"].values[:30])
        hist_days = int((g["date"].max() - g["date"].min()).days + 1)

        srow = seg[seg.id == sid].iloc[0]
        cold = hist_days < HISTORY_DAYS_COLD_START
        if cold:
            risk = prior_30d_risk(priors, srow.asset_type, srow.age_years)
            confidence = "low"
        else:
            # Confidence based on history + number of failures/defects.
            defect_count = int((d[d.segment_id == sid]["defect_count_prev_month"] > 0).sum())
            confidence = "high" if hist_days >= 180 and defect_count >= 2 else "medium"

        lt = latest_task[latest_task.segment_id == sid]
        if len(lt):
            t = lt.iloc[0].copy()
            tx = encode_duration(pd.DataFrame([t]), dur_cols)
            pred_dur = float(max(0.5, duration_reg.predict(tx)[0]))
            overrun_p = float(duration_clf.predict_proba(tx)[0,1])
        else:
            pred_dur = 6.0
            overrun_p = 0.2

        # Synthetic Layer-0 repair-duration prior from defect events.
        repair = pd.read_csv(DATA_DIR / "defect_events.csv")
        repair = repair[repair.segment_id == sid]
        if len(repair):
            repair_days = float(repair.days_to_repair.mean())
        else:
            repair_days = float(pd.read_csv(DATA_DIR / "defect_events.csv").days_to_repair.median())
        expected_downtime = float(risk * repair_days)

        rows.append({
            "segment_id": sid,
            "division": srow.division,
            "asset_type": srow.asset_type,
            "risk_30d": round(float(risk), 6),
            "expected_downtime_days": round(expected_downtime, 3),
            "preventive_block_duration_hrs": round(pred_dur, 2),
            "overrun_probability": round(overrun_p, 4),
            "confidence": confidence,
            "cold_start_fallback": bool(cold),
            "forecast_as_of": str(final_month.date())
        })
    return pd.DataFrame(rows)

# -----------------------------
# Main
# -----------------------------
def main():
    seg, panel, outcomes, defects, tasks = read_inputs()
    monthly = build_monthly_features(seg, panel, tasks)
    daily = add_daily_labels(monthly, defects)

    model, feature_cols, train_daily, test_daily = train_discrete_survival(daily)
    joblib.dump(model, MODEL_DIR / "discrete_survival_xgboost.joblib")
    with open(MODEL_DIR / "feature_columns.json", "w") as f:
        json.dump(feature_cols, f, indent=2)

    metrics, cal, eval_rows = evaluate(model, feature_cols, daily, outcomes)
    cal.to_csv(OUT_DIR / "calibration_curve.csv", index=False)
    eval_rows.to_csv(OUT_DIR / "evaluation_anchor_predictions.csv", index=False)

    segment_train = build_segment_training_table(monthly, outcomes)
    aft, aft_cols = fit_weibull_baseline(segment_train)
    aft.print_summary()
    joblib.dump(aft, MODEL_DIR / "weibull_aft.joblib")
    hrs = weibull_hazard_ratios(aft)
    hrs.to_csv(OUT_DIR / "weibull_hazard_ratios.csv", index=False)

    priors = fit_weibull_priors(seg, outcomes)

    duration_reg, duration_clf, dur_cols, dur_metrics = train_duration_heads(tasks, seg)
    joblib.dump(duration_reg, MODEL_DIR / "duration_xgb_regressor.joblib")
    joblib.dump(duration_clf, MODEL_DIR / "overrun_xgb_classifier.joblib")

    forecasts = final_forecasts(
        seg, panel, daily, model, feature_cols, priors,
        duration_reg, duration_clf, dur_cols
    )
    forecasts.to_csv(OUT_DIR / "segment_failure_forecasts.csv", index=False)

    # Feature importance with monotonic features visible.
    fi = pd.DataFrame({
        "feature": feature_cols,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)
    fi.to_csv(OUT_DIR / "feature_importance.csv", index=False)

    metrics.update(dur_metrics)
    metrics["n_daily_rows"] = int(len(daily))
    metrics["n_train_daily_rows"] = int(len(train_daily))
    metrics["n_test_daily_rows"] = int(len(test_daily))
    metrics["monotonic_features"] = [
        c for c, v in zip(feature_cols, monotone_constraints(feature_cols)) if v == 1
    ]
    metrics["model_contract"] = {
        "primary": "XGBoost discrete-time daily hazard",
        "baseline": "Weibull AFT",
        "duration_head": "XGBoost actual-duration regressor + overrun classifier",
        "cold_start": "Weibull prior by asset_type + age bucket",
        "timeline_split": "2024-01 through 2025-06 train; 2025-07 through 2025-12 test"
    }
    with open(OUT_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Plots
    plt.figure(figsize=(6,5))
    plt.plot(cal["predicted"], cal["observed"], marker="o", label="Model")
    plt.plot([0,1], [0,1], linestyle="--", label="Perfect calibration")
    plt.xlabel("Predicted 30-day risk")
    plt.ylabel("Observed 30-day rate")
    plt.title("Layer 1 Calibration")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "calibration_curve.png", dpi=160)
    plt.close()

    print("\n=== Railsync 2.0 Layer 1 Metrics ===")
    for k, v in metrics.items():
        print(f"{k}: {v}")
    print("\n=== Top 20 segment forecasts ===")
    print(forecasts.sort_values("risk_30d", ascending=False).head(20).to_string(index=False))
    print(f"\nOutputs saved to: {OUT_DIR.resolve()}")

if __name__ == "__main__":
    main()
