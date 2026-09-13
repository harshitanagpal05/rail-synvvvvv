"""RailSync 2.0 — Layer 1 trainer.

Primary failure head: Weibull AFT (lifelines) with conditional 30-day survival
probabilities. Duration/overrun heads remain XGBoost.

Run:
    python scripts/layer1_train.py --data Railsync_2.0_Layer_0_FINAL \\
        --out Railsync_Layer1_Complete --seed 42
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lifelines import WeibullAFTFitter, WeibullFitter
from lifelines.utils import concordance_index
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, mean_absolute_error, mean_squared_error, roc_auc_score
from xgboost import XGBClassifier, XGBRegressor

warnings.filterwarnings("ignore")
SEED = 42
HISTORY_DAYS_COLD_START = 60
TRAIN_CUTOFF = pd.Timestamp("2025-06-01")
TEST_START = pd.Timestamp("2025-07-01")

AFT_CATEGORICAL = ["asset_type", "division"]
DURATION_FEATURES = [
    "planned_duration_hrs", "overdue_days", "overdue_flag",
    "asset_type", "division", "department", "type",
]


def build_monthly_panel(panel: pd.DataFrame, seg: pd.DataFrame, tasks: pd.DataFrame) -> pd.DataFrame:
    p = panel.copy()
    p["month"] = pd.to_datetime(p["month"])
    p["defect_count_prev_month"] = (
        p.groupby("segment_id")["defect_count_month"].shift(1).fillna(0)
    )
    overdue_rows = []
    for _, r in p.iterrows():
        sid, m = r["segment_id"], r["month"]
        m_start = pd.Timestamp(m).normalize()
        active = tasks[
            (tasks.segment_id == sid)
            & (tasks.planned_date < m_start)
            & (tasks.overdue_flag == 1)
            & ((tasks.completion_date.isna()) | (tasks.completion_date >= m_start))
        ]
        overdue_rows.append({
            "segment_id": sid, "month": m,
            "overdue_tasks_active": int(len(active)),
            "overdue_days_max": float(active["overdue_days"].max()) if len(active) else 0.0,
        })
    overdue = pd.DataFrame(overdue_rows)
    p = p.drop(columns=["overdue_tasks_active", "overdue_days_max"], errors="ignore").merge(
        overdue, on=["segment_id", "month"], how="left"
    )
    overlap = ["age_years", "freight_density_class", "monsoon_exposure", "division", "asset_type"]
    p = p.drop(columns=[c for c in overlap if c in p.columns], errors="ignore").merge(
        seg, left_on="segment_id", right_on="id", how="left"
    )
    p = p.drop(columns=["id"], errors="ignore")
    p["overdue_tasks_active"] = p["overdue_tasks_active"].clip(lower=0)
    p["overdue_days_max"] = p["overdue_days_max"].fillna(0.0)
    return p


def expand_to_daily(monthly: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    oc = outcomes.copy()
    oc["observed_end"] = pd.to_datetime(oc["observed_end"])
    failure_dates = (
        oc.loc[oc["failure_event"].eq(1)]
        .set_index("segment_id")["observed_end"]
        .to_dict()
    )
    parts = []
    for _, r in monthly.iterrows():
        m_start = pd.Timestamp(r["month"]).normalize()
        m_end = m_start + pd.offsets.MonthEnd(1)
        dates = pd.date_range(m_start, m_end, freq="D")
        x = pd.DataFrame({"date": dates})
        for c, v in r.items():
            if c != "month":
                x[c] = v
        x["failure_event_daily"] = 0
        fdate = failure_dates.get(r["segment_id"])
        if fdate is not None:
            x.loc[x["date"].eq(pd.Timestamp(fdate)), "failure_event_daily"] = 1
            x = x[x["date"] <= pd.Timestamp(fdate)]
        parts.append(x)
    return pd.concat(parts, ignore_index=True).reset_index(drop=True)


def build_segment_training_table(monthly: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    train_months = monthly[monthly["month"] <= TRAIN_CUTOFF]
    agg = train_months.groupby("segment_id").agg(
        age_years=("age_years", "first"),
        grade3_defects_previous_90d=("grade3_defects_previous_90d", "mean"),
        defect_count_prev_month=("defect_count_prev_month", "mean"),
        overdue_tasks_active=("overdue_tasks_active", "mean"),
        monsoon_month=("monsoon_month", "mean"),
    ).reset_index()
    agg = agg.merge(
        monthly[["segment_id", "asset_type", "division"]].drop_duplicates("segment_id"),
        on="segment_id",
    )
    return outcomes[["segment_id", "duration_days", "failure_event"]].merge(agg, on="segment_id")


def build_segment_covariates(monthly: pd.DataFrame, segment_id: str, as_of_month) -> dict | None:
    hist = monthly[
        (monthly.segment_id == segment_id) &
        (monthly.month <= pd.Timestamp(as_of_month))
    ]
    if hist.empty:
        return None
    return {
        "segment_id": segment_id,
        "age_years": float(hist["age_years"].iloc[0]),
        "grade3_defects_previous_90d": float(hist["grade3_defects_previous_90d"].mean()),
        "defect_count_prev_month": float(hist["defect_count_prev_month"].mean()),
        "overdue_tasks_active": float(hist["overdue_tasks_active"].mean()),
        "monsoon_month": float(hist["monsoon_month"].mean()),
        "asset_type": hist["asset_type"].iloc[-1],
        "division": hist["division"].iloc[-1],
    }


def encode_aft_features(rows, covariate_cols):
    df = pd.DataFrame(rows)
    df = pd.get_dummies(df, columns=AFT_CATEGORICAL, dtype=float)
    return df.reindex(columns=covariate_cols, fill_value=0)


def fit_weibull_baseline(segment_train: pd.DataFrame):
    w = segment_train.copy()
    w = pd.get_dummies(w, columns=AFT_CATEGORICAL, dtype=float)
    w["event"] = w["failure_event"].astype(int)
    w = w.drop(columns=["segment_id", "failure_event"])
    aft = WeibullAFTFitter(penalizer=0.10)
    aft.fit(w, duration_col="duration_days", event_col="event")
    covariate_cols = [c for c in w.columns if c not in ("duration_days", "event")]
    return aft, covariate_cols


def weibull_hazard_ratios(aft):
    coefs = aft.params_.loc["lambda_"].copy()
    rho = float(np.exp(aft.params_.loc["rho_"].iloc[0]))
    hrs = np.exp(-rho * coefs)
    return pd.DataFrame({
        "feature": coefs.index,
        "aft_coefficient": coefs.values,
        "approx_hazard_ratio": hrs.values,
    }).sort_values("approx_hazard_ratio")


def weibull_risk_30d(aft, covariates, elapsed_days):
    t0 = max(float(elapsed_days), 0.0)
    sf = aft.predict_survival_function(covariates, times=[t0, t0 + 30])
    s0 = float(sf.iloc[0, 0])
    s30 = float(sf.iloc[1, 0])
    if s0 <= 1e-12:
        return 1.0
    return float(np.clip(1.0 - s30 / s0, 0.0, 1.0))


def weibull_survival_curve(aft, covariates, elapsed_days, horizon_days=30):
    t0 = max(float(elapsed_days), 0.0)
    rel_days = np.arange(1, horizon_days + 1, dtype=float)
    times = t0 + rel_days
    sf = aft.predict_survival_function(covariates, times=[t0] + times.tolist())
    s0 = float(sf.iloc[0, 0])
    if s0 <= 1e-12:
        return rel_days, np.zeros(horizon_days)
    return rel_days, np.clip(sf.iloc[1:, 0].values / s0, 0.0, 1.0)


def fit_weibull_priors(seg, outcomes):
    df = outcomes.merge(seg[["id", "asset_type", "age_years"]], left_on="segment_id", right_on="id")
    df["age_bucket"] = pd.cut(
        df["age_years"], [-1, 10, 20, 30, 40, np.inf],
        labels=["<=10", "11-20", "21-30", "31-40", ">40"],
    )
    priors = {}
    global_w = WeibullFitter()
    global_w.fit(df.duration_days, event_observed=df.failure_event)
    priors[("GLOBAL", "GLOBAL")] = global_w
    for (asset, ageb), g in df.groupby(["asset_type", "age_bucket"], observed=True):
        if len(g) >= 3 and g.failure_event.sum() >= 1:
            wf = WeibullFitter()
            wf.fit(g.duration_days, event_observed=g.failure_event)
            priors[(asset, str(ageb))] = wf
    for asset, g in df.groupby("asset_type"):
        if len(g) >= 4 and g.failure_event.sum() >= 1:
            wf = WeibullFitter()
            wf.fit(g.duration_days, event_observed=g.failure_event)
            priors[(asset, "GLOBAL")] = wf
    return priors


def prior_30d_risk(priors, asset_type, age_years):
    ageb = str(pd.cut([age_years], [-1, 10, 20, 30, 40, np.inf],
                      labels=["<=10", "11-20", "21-30", "31-40", ">40"])[0])
    wf = priors.get((asset_type, ageb), priors.get((asset_type, "GLOBAL"), priors[("GLOBAL", "GLOBAL")]))
    s0 = float(wf.survival_function_at_times(0).iloc[0])
    s30 = float(wf.survival_function_at_times(30).iloc[0])
    return float(np.clip(1 - s30 / max(s0, 1e-12), 0, 1))


def encode_duration(df, columns=None):
    x = df[DURATION_FEATURES].copy()
    cats = ["asset_type", "division", "department", "type"]
    x = pd.get_dummies(x, columns=cats, dtype=float)
    if columns is not None:
        x = x.reindex(columns=columns, fill_value=0)
    return x


def task_features(tasks, seg):
    return tasks.merge(
        seg[["id", "asset_type", "age_years", "length_km"]],
        left_on="segment_id", right_on="id", how="left",
    )


def train_duration_heads(tasks, seg):
    t = task_features(tasks, seg)
    t = t.sort_values("planned_date")
    cut = pd.Timestamp("2025-06-30")
    tr, te = t[t.planned_date <= cut], t[t.planned_date > cut]
    if tr.empty or te.empty:
        return None, None, [], {}

    Xtr = encode_duration(tr)
    Xte = encode_duration(te, Xtr.columns)
    reg = XGBRegressor(
        objective="reg:squarederror", n_estimators=250, max_depth=4,
        learning_rate=0.04, subsample=0.9, colsample_bytree=0.9,
        reg_lambda=2.0, random_state=SEED, n_jobs=-1,
    )
    reg.fit(Xtr, tr["actual_duration_hrs"])
    clf = XGBClassifier(
        objective="binary:logistic", n_estimators=250, max_depth=4,
        learning_rate=0.04, subsample=0.9, colsample_bytree=0.9,
        eval_metric="logloss", random_state=SEED, n_jobs=-1,
    )
    clf.fit(Xtr, tr["overrun_flag"].astype(int))
    metrics = {
        "duration_test_mae_hrs": float(mean_absolute_error(te.actual_duration_hrs, reg.predict(Xte))),
        "duration_test_rmse_hrs": float(np.sqrt(mean_squared_error(te.actual_duration_hrs, reg.predict(Xte)))),
        "overrun_test_auc": float(roc_auc_score(te.overrun_flag, clf.predict_proba(Xte)[:, 1]))
        if te.overrun_flag.nunique() > 1 else None,
    }
    return reg, clf, Xtr.columns.tolist(), metrics


def evaluate(aft, covariate_cols, monthly, outcomes):
    outcomes = outcomes.copy()
    outcomes["observed_end"] = pd.to_datetime(outcomes["observed_end"])
    obs_start = pd.to_datetime(outcomes["observation_start"].iloc[0])
    failed_before = set(
        outcomes.loc[
            (outcomes.failure_event == 1) & (outcomes.observed_end < TEST_START), "segment_id"
        ]
    )
    eligible = [s for s in monthly.segment_id.unique() if s not in failed_before]
    failure_dates = outcomes[outcomes.failure_event == 1].set_index("segment_id")["observed_end"].to_dict()

    rows = []
    for anchor in pd.date_range(TEST_START, "2025-12-01", freq="MS"):
        as_of_month = pd.Timestamp(anchor).to_period("M").to_timestamp()
        for sid in eligible:
            cov_row = build_segment_covariates(monthly, sid, as_of_month)
            if cov_row is None:
                continue
            X = encode_aft_features([cov_row], covariate_cols)
            elapsed = (pd.Timestamp(anchor) - obs_start).days
            risk = weibull_risk_30d(aft, X, elapsed)
            fd = failure_dates.get(sid)
            y = int(fd is not None and anchor <= fd < anchor + pd.Timedelta(days=30))
            rows.append({"segment_id": sid, "anchor": anchor, "risk_30d": risk, "y": y})

    ev = pd.DataFrame(rows)
    brier = float(brier_score_loss(ev.y, ev.risk_30d))
    if ev.y.nunique() >= 2:
        prob_true, prob_pred = calibration_curve(ev.y, ev.risk_30d, n_bins=5, strategy="quantile")
        cal = pd.DataFrame({"predicted": prob_pred, "observed": prob_true})
    else:
        cal = pd.DataFrame({"predicted": [], "observed": []})

    first = ev[ev.anchor == TEST_START].sort_values("risk_30d", ascending=False)
    k = min(20, len(first))
    top20_precision = float(first.head(k).y.mean()) if k else None
    base_rate = float(first.y.mean()) if len(first) else None

    times, events, risks = [], [], []
    test_end = pd.Timestamp("2025-12-31")
    for sid in eligible:
        o = outcomes[outcomes.segment_id == sid].iloc[0]
        observed = pd.Timestamp(o.observed_end)
        end = min(observed, test_end)
        times.append(max((end - TEST_START).days, 1))
        events.append(int(o.failure_event == 1 and observed >= TEST_START and observed <= test_end))
        r = first.loc[first.segment_id == sid, "risk_30d"]
        risks.append(float(r.iloc[0]) if len(r) else 0.0)

    return {
        "brier_score_30d": brier,
        "c_index": float(concordance_index(times, -np.asarray(risks), events)),
        "top20_precision": top20_precision,
        "base_rate": base_rate,
        "top20_lift_vs_base_rate": top20_precision / base_rate if base_rate and top20_precision is not None else None,
        "test_at_risk_segments": len(eligible),
        "n_30d_anchor_rows": int(len(ev)),
    }, cal, ev


def build_final_forecasts(seg, monthly, daily, defects, tasks, outcomes, aft, covariate_cols, priors,
                          duration_reg, duration_clf, dur_cols):
    final_month = monthly["month"].max()
    obs_start = pd.to_datetime(outcomes["observation_start"].iloc[0])
    anchor = pd.Timestamp(final_month)
    duration_tasks = task_features(tasks, seg)
    latest_task = duration_tasks.sort_values("planned_date").groupby("segment_id").tail(1) if not duration_tasks.empty else pd.DataFrame()

    rows = []
    for sid in seg.id:
        history = daily[daily.segment_id == sid]
        hist_days = int((history["date"].max() - history["date"].min()).days + 1) if len(history) else 0
        srow = seg[seg.id == sid].iloc[0]
        cold = hist_days < HISTORY_DAYS_COLD_START
        if cold:
            risk = prior_30d_risk(priors, srow.asset_type, srow.age_years)
            confidence = "low"
        else:
            cov_row = build_segment_covariates(monthly, sid, final_month)
            if cov_row is None:
                cov_row = {
                    "segment_id": sid, "age_years": float(srow.age_years),
                    "grade3_defects_previous_90d": 0.0, "defect_count_prev_month": 0.0,
                    "overdue_tasks_active": 0.0, "monsoon_month": 0.0,
                    "asset_type": srow.asset_type, "division": srow.division,
                }
            X = encode_aft_features([cov_row], covariate_cols)
            risk = weibull_risk_30d(aft, X, (anchor - obs_start).days)
            defect_count = int(monthly.loc[(monthly.segment_id == sid) & (monthly.month == final_month),
                                           "defect_count_prev_month"].fillna(0).gt(0).sum())
            confidence = "high" if hist_days >= 180 and defect_count >= 2 else "medium"

        lt = latest_task[latest_task.segment_id == sid] if not latest_task.empty else pd.DataFrame()
        if len(lt) and duration_reg is not None:
            tx = encode_duration(pd.DataFrame([lt.iloc[0]]), dur_cols)
            pred_dur = float(max(0.5, duration_reg.predict(tx)[0]))
            overrun_p = float(duration_clf.predict_proba(tx)[0, 1])
        else:
            pred_dur, overrun_p = 6.0, 0.2

        repair = defects[defects.segment_id == sid]
        repair_days = float(repair.days_to_repair.mean()) if len(repair) else float(defects.days_to_repair.median())
        rows.append({
            "segment_id": sid,
            "division": srow.division,
            "asset_type": srow.asset_type,
            "risk_30d": round(float(risk), 6),
            "expected_downtime_days": round(float(risk * repair_days), 3),
            "preventive_block_duration_hrs": round(pred_dur, 2),
            "overrun_probability": round(overrun_p, 4),
            "confidence": confidence,
            "cold_start_fallback": bool(cold),
            "forecast_as_of": str(final_month.date()),
        })
    return pd.DataFrame(rows)


def build_survival_curves(monthly, outcomes, aft, covariate_cols, horizon_days=30):
    final_month = monthly["month"].max()
    obs_start = pd.to_datetime(outcomes["observation_start"].iloc[0])
    anchor = pd.Timestamp(final_month)
    elapsed = (anchor - obs_start).days
    rows = []
    for sid in monthly.segment_id.unique():
        cov_row = build_segment_covariates(monthly, sid, final_month)
        if cov_row is None:
            continue
        X = encode_aft_features([cov_row], covariate_cols)
        days, survival = weibull_survival_curve(aft, X, elapsed, horizon_days)
        for day_idx, s in zip(days.astype(int), survival):
            rows.append({
                "segment_id": sid,
                "forecast_day": int(day_idx),
                "survival_probability": round(float(s), 6),
                "cumulative_failure_probability": round(float(1.0 - s), 6),
            })
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="Railsync_2.0_Layer_0_FINAL")
    ap.add_argument("--out", default="Railsync_Layer1_Complete")
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()

    data_dir = Path(args.data)
    out_dir = Path(args.out)
    model_dir = out_dir / "models"
    out_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading Layer 0 from {data_dir}/")
    seg = pd.read_csv(data_dir / "segments_master.csv")
    panel = pd.read_csv(data_dir / "segment_monthly_panel.csv")
    outcomes = pd.read_csv(data_dir / "survival_outcomes.csv")
    defects = pd.read_csv(data_dir / "defect_events.csv")
    tasks = pd.read_csv(data_dir / "maintenance_tasks.csv")
    for col in ("planned_date", "completion_date"):
        if col in tasks.columns:
            tasks[col] = pd.to_datetime(tasks[col], errors="coerce")

    print(f"  segments={len(seg)}  failures={int(outcomes['failure_event'].sum())}")
    monthly = build_monthly_panel(panel, seg, tasks)
    daily = expand_to_daily(monthly, outcomes)

    print("Fitting Weibull AFT primary model...")
    segment_train = build_segment_training_table(monthly, outcomes)
    aft, covariate_cols = fit_weibull_baseline(segment_train)
    joblib.dump(aft, model_dir / "weibull_aft.joblib")
    (model_dir / "weibull_covariate_columns.json").write_text(json.dumps(covariate_cols, indent=2))
    hrs = weibull_hazard_ratios(aft)
    hrs.to_csv(out_dir / "weibull_hazard_ratios.csv", index=False)

    print("Evaluating 30-day conditional risks...")
    metrics, cal, ev = evaluate(aft, covariate_cols, monthly, outcomes)
    cal.to_csv(out_dir / "calibration_curve.csv", index=False)
    ev.to_csv(out_dir / "brier_30d_predictions.csv", index=False)

    priors = fit_weibull_priors(seg, outcomes)
    duration_reg, duration_clf, dur_cols, dur_metrics = train_duration_heads(tasks, seg)
    if duration_reg is not None:
        joblib.dump(duration_reg, model_dir / "duration_xgb_regressor.joblib")
        joblib.dump(duration_clf, model_dir / "overrun_xgb_classifier.joblib")
    metrics.update(dur_metrics or {})

    forecasts = build_final_forecasts(
        seg, monthly, daily, defects, tasks, outcomes,
        aft, covariate_cols, priors, duration_reg, duration_clf, dur_cols,
    )
    forecasts.to_csv(out_dir / "final_failure_forecasts.csv", index=False)
    forecasts.to_csv(out_dir / "segment_failure_forecasts.csv", index=False)

    surv = build_survival_curves(monthly, outcomes, aft, covariate_cols)
    surv.to_csv(out_dir / "segment_survival_curves.csv", index=False)

    fi = hrs.copy()
    fi["importance"] = fi["approx_hazard_ratio"].abs()
    fi[["feature", "aft_coefficient", "approx_hazard_ratio", "importance"]].to_csv(
        out_dir / "feature_importance.csv", index=False
    )

    metrics["model_contract"] = {
        "primary": "Weibull AFT conditional 30-day survival",
        "duration_head": "XGBoost actual-duration regressor + overrun classifier",
        "cold_start": "Weibull prior by asset_type + age bucket",
    }
    metrics["weibull_shape_rho"] = float(np.exp(aft.params_.loc["rho_"].iloc[0]))
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    pd.DataFrame([metrics]).to_csv(out_dir / "metrics.csv", index=False)

    print("\n=== Top 20 segment forecasts ===")
    print(forecasts.sort_values("risk_30d", ascending=False).head(20).to_string(index=False))
    print(f"\nMetrics: {metrics}")
    print(f"Done. Outputs in {out_dir.resolve()}")


if __name__ == "__main__":
    main()
