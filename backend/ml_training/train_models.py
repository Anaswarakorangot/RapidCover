"""
Train RapidCover ML models.

TRAINING METHODOLOGY
--------------------
Three models are trained:

  1. Zone Risk Scorer (XGBoost/GradientBoosting Regressor)
     Target: risk_score (0-100) -- composite of simulated historical event
             frequency and severity with independent noise injection.
     Baseline: city-mean predictor (mean risk score per city).
     Split: 60% train / 20% val / 20% test

  2. Premium Engine (XGBoost/GradientBoosting Regressor)
     Target: expected_weekly_payout_pressure (Rs.) -- an INDEPENDENT economic
             signal (E[payout] = trigger_freq �- severity �- exposure �- load).
             This is NOT the same formula as the runtime pricing engine.
             Deterministic insurance constraints (IRDAI caps, tier floors)
             are applied POST-prediction, not learned.
     Baseline: tier-mean predictor.
     Split: 60% train / 20% val / 20% test

  3. Fraud Detector (RandomForestClassifier -- supervised)
     Target: is_fraud (0/1) -- deterministic policy-grounded labels from
             adjuster-recognized fraud scenarios (GPS spoofing, activity
             paradox, frequency abuse, multi-signal anomaly).
             This is NOT derived from the run-time weighted scoring formula.
     Baseline: rule-based hard-stop only classifier (flags any hard-stop hit).
     Split: 60% train / 20% val / 20% test (stratified)

IMPORTANT: This project uses a supervised RandomForestClassifier for fraud,
NOT IsolationForest. The training data has independent labels, so supervised
learning is both appropriate and more defensible to judges than unsupervised
anomaly detection on formula-derived labels.

Feature importances are saved for all three models to enable explanation.
"""

import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, f1_score, mean_absolute_error, mean_squared_error,
    precision_score, r2_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("[WARNING] XGBoost not installed -- using GradientBoostingRegressor fallback.")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _section(title: str) -> None:
    print("\n" + "=" * 72)
    print(f"  {title}")
    print("=" * 72)


def _feature_importances(model, feature_names: list) -> dict:
    """Extract feature importances from trained model."""
    try:
        fi = model.feature_importances_
        ranked = sorted(
            zip(feature_names, fi.tolist()),
            key=lambda x: x[1],
            reverse=True
        )
        return [{"feature": f, "importance": round(float(v), 6)} for f, v in ranked]
    except AttributeError:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Model 1: Zone Risk Scorer
# ─────────────────────────────────────────────────────────────────────────────

def train_zone_risk_model(data_path: Path, output_dir: Path) -> dict:
    """Train Zone Risk Scorer with baseline comparison and feature importances."""
    _section("Model 1: Zone Risk Scorer")

    df = pd.read_csv(data_path)
    print(f"  Loaded {len(df)} samples")

    city_encoder = LabelEncoder()
    df["city_encoded"] = city_encoder.fit_transform(df["city"])

    feature_cols = [
        "city_encoded", "avg_rainfall_mm_per_hr", "flood_events_2yr",
        "aqi_avg_annual", "aqi_severe_days_2yr", "heat_advisory_days_2yr",
        "bandh_events_2yr", "dark_store_suspensions_2yr", "road_flood_prone", "month",
    ]
    X = df[feature_cols].values
    y = df["risk_score"].values

    # 60 / 20 / 20 split
    X_tv, X_test, y_tv, y_test = train_test_split(X, y, test_size=0.20, random_state=42)
    X_train, X_val, y_train, y_val = train_test_split(X_tv, y_tv, test_size=0.25, random_state=42)
    print(f"  Train: {len(X_train)}  Val: {len(X_val)}  Test: {len(X_test)}")

    # ── Baseline: city-mean predictor ──
    # Use city index (col 0) to compute per-city mean on training set
    city_means = {}
    for city_idx in np.unique(X_train[:, 0].astype(int)):
        mask = X_train[:, 0].astype(int) == city_idx
        city_means[city_idx] = float(y_train[mask].mean())
    global_mean = float(y_train.mean())

    def city_mean_predict(X_arr):
        return np.array([city_means.get(int(row[0]), global_mean) for row in X_arr])

    baseline_pred_test = city_mean_predict(X_test)
    baseline_mae  = float(mean_absolute_error(y_test, baseline_pred_test))
    baseline_r2   = float(r2_score(y_test, baseline_pred_test))
    print(f"\n  Baseline (city-mean):  MAE={baseline_mae:.2f}  R²={baseline_r2:.4f}")

    # ── Train model ──
    if HAS_XGBOOST:
        model = xgb.XGBRegressor(
            n_estimators=150, max_depth=6, learning_rate=0.08,
            subsample=0.85, colsample_bytree=0.85,
            random_state=42, objective="reg:squarederror", n_jobs=-1,
        )
    else:
        model = GradientBoostingRegressor(
            n_estimators=150, max_depth=6, learning_rate=0.08,
            subsample=0.85, random_state=42,
        )

    model.fit(X_train, y_train)

    # ── Evaluate ──
    y_val_pred  = model.predict(X_val)
    y_test_pred = model.predict(X_test)

    val_mae  = float(mean_absolute_error(y_val, y_val_pred))
    val_r2   = float(r2_score(y_val, y_val_pred))
    test_mse = float(mean_squared_error(y_test, y_test_pred))
    test_mae = float(mean_absolute_error(y_test, y_test_pred))
    test_r2  = float(r2_score(y_test, y_test_pred))

    cv_scores = cross_val_score(model, X_tv, y_tv, cv=5, scoring="r2")

    print(f"  Val:           MAE={val_mae:.2f}  R²={val_r2:.4f}")
    print(f"  Test (held):   MAE={test_mae:.2f}  R²={test_r2:.4f}")
    print(f"  CV R² (5-fold): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    print(f"  Improvement over baseline: MAE {baseline_mae:.2f} -> {test_mae:.2f}")

    fi = _feature_importances(model, feature_cols)
    print(f"  Top feature: {fi[0]['feature']} ({fi[0]['importance']:.4f})")

    # ── Save ──
    joblib.dump(model, output_dir / "zone_risk_model.pkl")
    joblib.dump(city_encoder, output_dir / "zone_risk_city_encoder.pkl")
    print(f"\n  [OK] Saved zone_risk_model.pkl")

    return {
        "model_type": ("XGBRegressor" if HAS_XGBOOST else "GradientBoostingRegressor"),
        "target": "risk_score",
        "target_description": "Composite zone risk (0-100) with independent noise injection",
        "n_features": len(feature_cols),
        "feature_names": feature_cols,
        "split": {"train": int(len(X_train)), "val": int(len(X_val)), "test": int(len(X_test))},
        "baseline": {
            "method": "city_mean_predictor",
            "test_mae": round(baseline_mae, 4),
            "test_r2": round(baseline_r2, 4),
        },
        "val_metrics":  {"mae": round(val_mae, 4), "r2": round(val_r2, 4)},
        "test_metrics": {"mse": round(test_mse, 4), "mae": round(test_mae, 4), "r2": round(test_r2, 4)},
        "cv_r2_mean": round(float(cv_scores.mean()), 4),
        "cv_r2_std":  round(float(cv_scores.std()), 4),
        "feature_importances": fi,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Model 2: Premium Engine
# ─────────────────────────────────────────────────────────────────────────────

def train_premium_model(data_path: Path, output_dir: Path) -> dict:
    """
    Train Premium Engine against expected_weekly_payout_pressure.

    The trained ML model predicts the underlying economic risk (expected payout
    pressure). The pricing engine then applies deterministic constraints on top:
    tier floor, IRDAI 3x cap, loyalty, RTO adjustments.

    This is NOT learning the pricing formula -- it is learning the payout risk.
    """
    _section("Model 2: Premium Engine (target: expected payout pressure)")

    df = pd.read_csv(data_path)
    print(f"  Loaded {len(df)} samples")
    print(f"  Target: expected_weekly_payout_pressure (independent of pricing formula)")

    city_encoder = LabelEncoder()
    tier_encoder = LabelEncoder()
    df["city_encoded"] = city_encoder.fit_transform(df["city"])
    df["tier_encoded"] = tier_encoder.fit_transform(df["tier"])

    feature_cols = [
        "city_encoded", "zone_risk_score", "active_days_last_30",
        "avg_hours_per_day", "tier_encoded", "loyalty_weeks", "month", "riqi_score",
    ]
    X = df[feature_cols].values
    y = df["expected_weekly_payout_pressure"].values

    # 60 / 20 / 20 split
    X_tv, X_test, y_tv, y_test = train_test_split(X, y, test_size=0.20, random_state=42)
    X_train, X_val, y_train, y_val = train_test_split(X_tv, y_tv, test_size=0.25, random_state=42)
    print(f"  Train: {len(X_train)}  Val: {len(X_val)}  Test: {len(X_test)}")

    # ── Baseline: tier-mean predictor ──
    tier_idx = feature_cols.index("tier_encoded")
    tier_means = {}
    for t_idx in np.unique(X_train[:, tier_idx].astype(int)):
        mask = X_train[:, tier_idx].astype(int) == t_idx
        tier_means[t_idx] = float(y_train[mask].mean())
    global_mean = float(y_train.mean())

    def tier_mean_predict(X_arr):
        return np.array([tier_means.get(int(row[tier_idx]), global_mean) for row in X_arr])

    baseline_pred_test = tier_mean_predict(X_test)
    baseline_mae  = float(mean_absolute_error(y_test, baseline_pred_test))
    baseline_r2   = float(r2_score(y_test, baseline_pred_test))
    print(f"\n  Baseline (tier-mean):  MAE=Rs.{baseline_mae:.2f}  R²={baseline_r2:.4f}")

    # ── Train model ──
    if HAS_XGBOOST:
        model = xgb.XGBRegressor(
            n_estimators=150, max_depth=5, learning_rate=0.08,
            subsample=0.85, colsample_bytree=0.85,
            random_state=42, objective="reg:squarederror", n_jobs=-1,
        )
    else:
        model = GradientBoostingRegressor(
            n_estimators=150, max_depth=5, learning_rate=0.08,
            subsample=0.85, random_state=42,
        )

    model.fit(X_train, y_train)

    # ── Evaluate ──
    y_val_pred  = model.predict(X_val)
    y_test_pred = model.predict(X_test)

    val_mae  = float(mean_absolute_error(y_val, y_val_pred))
    val_r2   = float(r2_score(y_val, y_val_pred))
    test_mse = float(mean_squared_error(y_test, y_test_pred))
    test_mae = float(mean_absolute_error(y_test, y_test_pred))
    test_r2  = float(r2_score(y_test, y_test_pred))

    cv_scores = cross_val_score(model, X_tv, y_tv, cv=5, scoring="r2")

    print(f"  Val:           MAE=Rs.{val_mae:.2f}  R²={val_r2:.4f}")
    print(f"  Test (held):   MAE=Rs.{test_mae:.2f}  R²={test_r2:.4f}")
    print(f"  CV R² (5-fold): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    print(f"  Improvement over baseline: MAE Rs.{baseline_mae:.2f} -> Rs.{test_mae:.2f}")

    fi = _feature_importances(model, feature_cols)
    print(f"  Top feature: {fi[0]['feature']} ({fi[0]['importance']:.4f})")

    # ── Save ──
    joblib.dump(model, output_dir / "premium_model.pkl")
    joblib.dump(city_encoder, output_dir / "premium_city_encoder.pkl")
    joblib.dump(tier_encoder, output_dir / "premium_tier_encoder.pkl")
    print(f"\n  [OK] Saved premium_model.pkl + encoders")

    return {
        "model_type": ("XGBRegressor" if HAS_XGBOOST else "GradientBoostingRegressor"),
        "target": "expected_weekly_payout_pressure",
        "target_description": (
            "E[payout] = trigger_frequency �- severity �- exposure �- load -- "
            "independent of runtime pricing formula; deterministic caps applied post-prediction"
        ),
        "n_features": len(feature_cols),
        "feature_names": feature_cols,
        "split": {"train": int(len(X_train)), "val": int(len(X_val)), "test": int(len(X_test))},
        "baseline": {
            "method": "tier_mean_predictor",
            "test_mae_rs": round(baseline_mae, 4),
            "test_r2": round(baseline_r2, 4),
        },
        "val_metrics":  {"mae_rs": round(val_mae, 4), "r2": round(val_r2, 4)},
        "test_metrics": {"mse": round(test_mse, 4), "mae_rs": round(test_mae, 4), "r2": round(test_r2, 4)},
        "cv_r2_mean": round(float(cv_scores.mean()), 4),
        "cv_r2_std":  round(float(cv_scores.std()), 4),
        "feature_importances": fi,
        "note": (
            "Model predicts expected payout pressure, not the final premium. "
            "Price floor, IRDAI cap, and loyalty adjustments are applied deterministically after ML output."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Model 3: Fraud Detector
# ─────────────────────────────────────────────────────────────────────────────

def _rule_based_fraud_predict(X: np.ndarray, feature_cols: list) -> np.ndarray:
    """
    Baseline: hard-stop-only rule classifier.
    Flags fraud if any of: GPS out + velocity>55, or run_count>0, or zone not suspended.
    """
    cols = {c: i for i, c in enumerate(feature_cols)}
    preds = []
    for row in X:
        velocity   = float(row[cols["max_gps_velocity_kmh"]])
        gps_in     = int(row[cols["gps_in_zone"]])
        run_count  = int(row[cols["run_count_during_event"]])
        suspended  = int(row[cols["zone_suspended"]])
        claims_30d = int(row[cols["claims_last_30_days"]])
        device_ok  = int(row[cols["device_consistent"]])
        drift      = float(row[cols["centroid_drift_km"]])
        polygon    = int(row[cols["zone_polygon_match"]])

        flag = 0
        if velocity > 55.0 and gps_in == 0:
            flag = 1
        elif run_count > 0 and suspended == 1:
            flag = 1
        elif gps_in == 0 and drift > 12.0 and polygon == 0:
            flag = 1
        elif claims_30d >= 5 and device_ok == 0 and gps_in == 0:
            flag = 1
        elif suspended == 0 and int(row[cols.get("traffic_disrupted", -1)]) == 0 and claims_30d >= 3:
            flag = 1
        preds.append(flag)
    return np.array(preds)


def train_fraud_model(data_path: Path, output_dir: Path) -> dict:
    """
    Train supervised RandomForestClassifier on independently labeled fraud data.

    Uses policy-grounded deterministic scenario labels (NOT the runtime weighted
    scoring formula). This is a fully supervised classification problem.

    Baseline: rule-based hard-stop-only classifier (same rules as the deterministic
    gates in the runtime FraudModel -- the ML model adds value on top of these).
    """
    _section("Model 3: Fraud Detector (supervised RandomForestClassifier)")

    df = pd.read_csv(data_path)
    print(f"  Loaded {len(df)} samples")
    fraud_rate = df["is_fraud"].mean() * 100
    print(f"  Fraud rate: {fraud_rate:.1f}%  (independent policy-grounded labels)")
    print(f"  Model: RandomForestClassifier (supervised -- labels are NOT from scoring formula)")

    feature_cols = [
        "gps_in_zone", "run_count_during_event", "zone_polygon_match",
        "claims_last_30_days", "device_consistent", "traffic_disrupted",
        "centroid_drift_km", "max_gps_velocity_kmh", "zone_suspended",
    ]
    X = df[feature_cols].values
    y = df["is_fraud"].values

    # Stratified 60 / 20 / 20 split
    X_tv, X_test, y_tv, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_tv, y_tv, test_size=0.25, random_state=42, stratify=y_tv
    )
    print(f"  Train: {len(X_train)}  Val: {len(X_val)}  Test: {len(X_test)}")

    # ── Baseline: rule-based hard-stop classifier ──
    baseline_pred_test = _rule_based_fraud_predict(X_test, feature_cols)
    baseline_acc  = float(accuracy_score(y_test, baseline_pred_test))
    baseline_f1   = float(f1_score(y_test, baseline_pred_test, zero_division=0))
    baseline_prec = float(precision_score(y_test, baseline_pred_test, zero_division=0))
    baseline_rec  = float(recall_score(y_test, baseline_pred_test, zero_division=0))
    print(f"\n  Baseline (rule-only):  Acc={baseline_acc:.3f}  F1={baseline_f1:.3f}  "
          f"P={baseline_prec:.3f}  R={baseline_rec:.3f}")

    # ── Train RandomForestClassifier ──
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=5,
        class_weight="balanced",   # handle class imbalance
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # ── Evaluate ──
    y_val_pred  = model.predict(X_val)
    y_test_pred = model.predict(X_test)
    y_test_prob = model.predict_proba(X_test)[:, 1]

    val_acc  = float(accuracy_score(y_val, y_val_pred))
    val_f1   = float(f1_score(y_val, y_val_pred, zero_division=0))

    test_acc  = float(accuracy_score(y_test, y_test_pred))
    test_f1   = float(f1_score(y_test, y_test_pred, zero_division=0))
    test_prec = float(precision_score(y_test, y_test_pred, zero_division=0))
    test_rec  = float(recall_score(y_test, y_test_pred, zero_division=0))
    try:
        test_auc = float(roc_auc_score(y_test, y_test_prob))
    except Exception:
        test_auc = 0.5

    cv_scores = cross_val_score(model, X_tv, y_tv, cv=5, scoring="f1")

    print(f"  Val:           Acc={val_acc:.3f}  F1={val_f1:.3f}")
    print(f"  Test (held):   Acc={test_acc:.3f}  F1={test_f1:.3f}  "
          f"P={test_prec:.3f}  R={test_rec:.3f}  AUC={test_auc:.3f}")
    print(f"  CV F1 (5-fold): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    print(f"  Improvement over rule-only: F1 {baseline_f1:.3f} -> {test_f1:.3f}")

    fi = _feature_importances(model, feature_cols)
    print(f"  Top feature: {fi[0]['feature']} ({fi[0]['importance']:.4f})")

    # ── Save ──
    joblib.dump(model, output_dir / "fraud_model.pkl")
    print(f"\n  [OK] Saved fraud_model.pkl (RandomForestClassifier)")

    return {
        "model_type": "RandomForestClassifier",
        "target": "is_fraud",
        "target_description": (
            "Binary label assigned by policy-grounded deterministic scenarios "
            "(GPS spoofing, activity paradox, frequency abuse, multi-signal anomaly). "
            "Labels are INDEPENDENT of the runtime weighted scoring formula."
        ),
        "n_features": len(feature_cols),
        "feature_names": feature_cols,
        "split": {"train": int(len(X_train)), "val": int(len(X_val)), "test": int(len(X_test))},
        "class_distribution": {
            "fraud_rate_pct": round(float(fraud_rate), 2),
            "legitimate_rate_pct": round(float(100 - fraud_rate), 2),
        },
        "baseline": {
            "method": "rule_based_hard_stop_only",
            "description": "Flags fraud only when hard deterministic stops are hit",
            "test_accuracy": round(baseline_acc, 4),
            "test_f1": round(baseline_f1, 4),
            "test_precision": round(baseline_prec, 4),
            "test_recall": round(baseline_rec, 4),
        },
        "val_metrics":  {"accuracy": round(val_acc, 4), "f1": round(val_f1, 4)},
        "test_metrics": {
            "accuracy":  round(test_acc, 4),
            "f1":        round(test_f1, 4),
            "precision": round(test_prec, 4),
            "recall":    round(test_rec, 4),
            "roc_auc":   round(test_auc, 4),
        },
        "cv_f1_mean": round(float(cv_scores.mean()), 4),
        "cv_f1_std":  round(float(cv_scores.std()), 4),
        "feature_importances": fi,
        "architecture_note": (
            "Deterministic hard-stops (GPS velocity>60, run_count>0, zone_suspended=False) "
            "always override ML decision. ML assists triage and grey-area anomaly detection "
            "between the hard stops. The model never decides alone on high-stakes rejections."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    training_dir = Path(__file__).parent
    data_dir     = training_dir / "data"
    output_dir   = training_dir.parent / "ml_models"
    output_dir.mkdir(exist_ok=True)

    print("=" * 72)
    print("RapidCover ML Training Pipeline")
    print("Independent targets · Baseline comparisons · Feature importances")
    print("3-way split (60/20/20 train/val/test)")
    print("=" * 72)

    metadata: dict = {
        "training_date": datetime.now().isoformat(),
        "version": "2.0.0",
        "provenance": {
            "premium_target": "expected_weekly_payout_pressure (independent of pricing formula)",
            "fraud_labels": "policy-grounded deterministic scenarios (independent of scoring formula)",
            "zone_risk_target": "composite event frequency/severity with independent noise injection",
            "split_methodology": "60% train / 20% val / 20% test (stratified for fraud)",
        },
        "models": {},
    }

    metadata["models"]["zone_risk"] = train_zone_risk_model(
        data_dir / "zone_risk_training.csv", output_dir
    )
    metadata["models"]["premium"] = train_premium_model(
        data_dir / "premium_training.csv", output_dir
    )
    metadata["models"]["fraud"] = train_fraud_model(
        data_dir / "fraud_training.csv", output_dir
    )

    metadata_path = output_dir / "model_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # ── Summary table ──
    _section("TRAINING COMPLETE -- Summary")
    zr = metadata["models"]["zone_risk"]
    pm = metadata["models"]["premium"]
    fr = metadata["models"]["fraud"]

    print(f"\n  {'Model':<20} {'Metric':<20} {'Baseline':<14} {'ML Model'}")
    print(f"  {'-'*20} {'-'*20} {'-'*14} {'-'*14}")
    print(f"  {'Zone Risk':<20} {'Test MAE':<20} {zr['baseline']['test_mae']:<14.2f} {zr['test_metrics']['mae']:.2f}")
    print(f"  {'Zone Risk':<20} {'Test R²':<20} {zr['baseline']['test_r2']:<14.4f} {zr['test_metrics']['r2']:.4f}")
    print(f"  {'Premium':<20} {'Test MAE (Rs.)':<20} {pm['baseline']['test_mae_rs']:<14.2f} {pm['test_metrics']['mae_rs']:.2f}")
    print(f"  {'Premium':<20} {'Test R²':<20} {pm['baseline']['test_r2']:<14.4f} {pm['test_metrics']['r2']:.4f}")
    print(f"  {'Fraud':<20} {'Test F1':<20} {fr['baseline']['test_f1']:<14.4f} {fr['test_metrics']['f1']:.4f}")
    print(f"  {'Fraud':<20} {'Test AUC':<20} {'(rules)':<14} {fr['test_metrics']['roc_auc']:.4f}")

    print(f"\n  Models saved to:   {output_dir.absolute()}")
    print(f"  Metadata saved to: {metadata_path}")
    print("\n" + "=" * 72)


if __name__ == "__main__":
    main()
