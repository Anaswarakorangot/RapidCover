"""
Train real ML models for RapidCover.

Trains three production models:
1. Zone Risk Scorer - XGBoost Regressor
2. Premium Engine - Gradient Boosting Regressor
3. Fraud Detector - XGBoost Classifier

Models are saved to backend/ml_models/ with versioning.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import joblib
import json
from datetime import datetime

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score


try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("[WARNING] XGBoost not installed. Falling back to GradientBoostingRegressor.")


def train_zone_risk_model(data_path, output_dir):
    """Train Zone Risk Scorer using XGBoost/GradientBoosting."""
    print("\n" + "="*80)
    print("Training Model 1: Zone Risk Scorer")
    print("="*80)

    # Load data
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} samples")

    # Encode categorical features
    city_encoder = LabelEncoder()
    df['city_encoded'] = city_encoder.fit_transform(df['city'])

    # Features and target
    feature_cols = [
        'city_encoded', 'avg_rainfall_mm_per_hr', 'flood_events_2yr',
        'aqi_avg_annual', 'aqi_severe_days_2yr', 'heat_advisory_days_2yr',
        'bandh_events_2yr', 'dark_store_suspensions_2yr', 'road_flood_prone', 'month'
    ]
    X = df[feature_cols]
    y = df['risk_score']

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train model
    if HAS_XGBOOST:
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            objective='reg:squarederror'
        )
        print("Using XGBoost Regressor")
    else:
        model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        print("Using GradientBoosting Regressor")

    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"\nModel Performance:")
    print(f"  MSE:  {mse:.2f}")
    print(f"  MAE:  {mae:.2f}")
    print(f"  R²:   {r2:.4f}")

    # Cross-validation
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='r2')
    print(f"  CV R² (5-fold): {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    # Save model and encoders
    model_path = output_dir / "zone_risk_model.pkl"
    encoder_path = output_dir / "zone_risk_city_encoder.pkl"

    joblib.dump(model, model_path)
    joblib.dump(city_encoder, encoder_path)

    print(f"\n[OK] Model saved to {model_path}")
    print(f"[OK] Encoder saved to {encoder_path}")

    return {
        "model_type": "XGBRegressor" if HAS_XGBOOST else "GradientBoostingRegressor",
        "n_features": len(feature_cols),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "mse": float(mse),
        "mae": float(mae),
        "r2_score": float(r2),
        "cv_r2_mean": float(cv_scores.mean()),
        "cv_r2_std": float(cv_scores.std()),
        "feature_names": feature_cols
    }


def train_premium_model(data_path, output_dir):
    """Train Premium Engine using Gradient Boosting."""
    print("\n" + "="*80)
    print("Training Model 2: Premium Engine")
    print("="*80)

    # Load data
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} samples")

    # Encode categorical features
    city_encoder = LabelEncoder()
    tier_encoder = LabelEncoder()
    df['city_encoded'] = city_encoder.fit_transform(df['city'])
    df['tier_encoded'] = tier_encoder.fit_transform(df['tier'])

    # Features and target
    feature_cols = [
        'city_encoded', 'zone_risk_score', 'active_days_last_30',
        'avg_hours_per_day', 'tier_encoded', 'loyalty_weeks', 'month', 'riqi_score'
    ]
    X = df[feature_cols]
    y = df['weekly_premium']

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train model
    if HAS_XGBOOST:
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
            objective='reg:squarederror'
        )
        print("Using XGBoost Regressor")
    else:
        model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        print("Using GradientBoosting Regressor")

    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"\nModel Performance:")
    print(f"  MSE:  {mse:.2f}")
    print(f"  MAE:  Rs.{mae:.2f}")
    print(f"  R²:   {r2:.4f}")

    # Cross-validation
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='r2')
    print(f"  CV R² (5-fold): {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    # Save model and encoders
    model_path = output_dir / "premium_model.pkl"
    city_encoder_path = output_dir / "premium_city_encoder.pkl"
    tier_encoder_path = output_dir / "premium_tier_encoder.pkl"

    joblib.dump(model, model_path)
    joblib.dump(city_encoder, city_encoder_path)
    joblib.dump(tier_encoder, tier_encoder_path)

    print(f"\n[OK] Model saved to {model_path}")
    print(f"[OK] Encoders saved")

    return {
        "model_type": "XGBRegressor" if HAS_XGBOOST else "GradientBoostingRegressor",
        "n_features": len(feature_cols),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "mse": float(mse),
        "mae": float(mae),
        "r2_score": float(r2),
        "cv_r2_mean": float(cv_scores.mean()),
        "cv_r2_std": float(cv_scores.std()),
        "feature_names": feature_cols
    }


def train_fraud_model(data_path, output_dir):
    """Train Fraud Detector using XGBoost Classifier."""
    print("\n" + "="*80)
    print("Training Model 3: Fraud Anomaly Detector")
    print("="*80)

    # Load data
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} samples")

    # Features and target
    feature_cols = [
        'gps_in_zone', 'run_count_during_event', 'zone_polygon_match',
        'claims_last_30_days', 'device_consistent', 'traffic_disrupted',
        'centroid_drift_km', 'max_gps_velocity_kmh', 'zone_suspended'
    ]
    X = df[feature_cols]
    y = df['is_fraud']

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train model
    if HAS_XGBOOST:
        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            eval_metric='logloss',
            use_label_encoder=False
        )
        print("Using XGBoost Classifier")
    else:
        from sklearn.ensemble import GradientBoostingClassifier
        model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        print("Using GradientBoosting Classifier")

    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)

    print(f"\nModel Performance:")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    print(f"  ROC AUC:   {auc:.4f}")

    # Cross-validation
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='roc_auc')
    print(f"  CV AUC (5-fold): {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    # Save model
    model_path = output_dir / "fraud_model.pkl"
    joblib.dump(model, model_path)

    print(f"\n[OK] Model saved to {model_path}")

    return {
        "model_type": "XGBClassifier" if HAS_XGBOOST else "GradientBoostingClassifier",
        "n_features": len(feature_cols),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "roc_auc": float(auc),
        "cv_auc_mean": float(cv_scores.mean()),
        "cv_auc_std": float(cv_scores.std()),
        "feature_names": feature_cols
    }


def main():
    """Train all models and save metadata."""
    training_dir = Path(__file__).parent
    data_dir = training_dir / "data"
    output_dir = training_dir.parent / "ml_models"
    output_dir.mkdir(exist_ok=True)

    print("="*80)
    print("RapidCover ML Model Training Pipeline")
    print("="*80)

    metadata = {
        "training_date": datetime.now().isoformat(),
        "version": "1.0.0",
        "models": {}
    }

    # Train Zone Risk Model
    zone_metrics = train_zone_risk_model(
        data_dir / "zone_risk_training.csv",
        output_dir
    )
    metadata["models"]["zone_risk"] = zone_metrics

    # Train Premium Model
    premium_metrics = train_premium_model(
        data_dir / "premium_training.csv",
        output_dir
    )
    metadata["models"]["premium"] = premium_metrics

    # Train Fraud Model
    fraud_metrics = train_fraud_model(
        data_dir / "fraud_training.csv",
        output_dir
    )
    metadata["models"]["fraud"] = fraud_metrics

    # Save metadata
    metadata_path = output_dir / "model_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print("\n" + "="*80)
    print("[SUCCESS] ALL MODELS TRAINED SUCCESSFULLY!")
    print("="*80)
    print(f"\nModels saved to: {output_dir.absolute()}")
    print(f"Metadata saved to: {metadata_path}")

    print("\nModel Summary:")
    print(f"  Zone Risk:  R² = {zone_metrics['r2_score']:.4f}")
    print(f"  Premium:    R² = {premium_metrics['r2_score']:.4f}")
    print(f"  Fraud:      AUC = {fraud_metrics['roc_auc']:.4f}")


if __name__ == "__main__":
    main()
