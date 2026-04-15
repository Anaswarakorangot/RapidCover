# RapidCover ML Training Pipeline

This directory contains the ML training pipeline for RapidCover's three production models.

## Models

1. **Zone Risk Scorer** - XGBoost Regressor
   - Predicts risk score (0-100) for dark store zones
   - Features: rainfall, AQI, heat events, bandhs, suspensions, etc.
   - Current R²: 0.6731

2. **Premium Engine** - XGBoost/Gradient Boosting Regressor
   - Predicts weekly insurance premium
   - Features: city, zone risk, activity level, tier, loyalty, RIQI
   - Current R²: 0.9588

3. **Fraud Detector** - XGBoost Classifier
   - Binary classification: fraud vs legitimate
   - Features: GPS coherence, run count, device fingerprint, etc.
   - Current ROC AUC: 1.0000 (perfect on synthetic data)

## Directory Structure

```
ml_training/
├── README.md                    # This file
├── generate_training_data.py    # Generate synthetic training datasets
├── train_models.py              # Train all three models
└── data/                        # Training datasets (generated)
    ├── zone_risk_training.csv
    ├── premium_training.csv
    └── fraud_training.csv

ml_models/                       # Trained model artifacts
├── model_metadata.json          # Training metadata and metrics
├── zone_risk_model.pkl          # Trained zone risk model
├── zone_risk_city_encoder.pkl   # City label encoder
├── premium_model.pkl            # Trained premium model
├── premium_city_encoder.pkl     # City label encoder
├── premium_tier_encoder.pkl     # Tier label encoder
└── fraud_model.pkl              # Trained fraud model
```

## Usage

### Generate Training Data

```bash
cd backend/ml_training
python generate_training_data.py
```

This creates 3 CSV files in `ml_training/data/`:
- `zone_risk_training.csv` - 1,000 samples
- `premium_training.csv` - 1,000 samples
- `fraud_training.csv` - 2,000 samples (70% legitimate, 30% fraud)

### Train Models

```bash
cd backend/ml_training
python train_models.py
```

This will:
1. Load training data from `data/` directory
2. Train all three models using XGBoost (or GradientBoosting if XGBoost unavailable)
3. Save trained models to `../ml_models/`
4. Save training metadata and metrics to `model_metadata.json`

### Use Trained Models

The ML service (`app/services/ml_service.py`) automatically detects and loads trained models:

```python
from app.services.ml_service import zone_risk_model, premium_model, fraud_model

# Models are either TrainedZoneRiskModel (if trained models exist)
# or ZoneRiskModel (manual fallback)

# Usage is identical
risk_score = zone_risk_model.predict(zone_features)
premium_result = premium_model.predict(partner_features)
fraud_result = fraud_model.score(claim_features)
```

## Retraining Models

To retrain with new data:

1. **Option A: Replace synthetic data**
   - Modify `generate_training_data.py` to use real claim/partner data from database
   - Run data generation and training scripts

2. **Option B: Use real production data**
   - Export claims, partners, zones, and trigger events from database
   - Create training script that loads real data instead of synthetic
   - Run training pipeline

### Recommended Retraining Schedule

- **Weekly**: Fraud model (adapts to new fraud patterns)
- **Monthly**: Premium model (adjusts to seasonal trends)
- **Quarterly**: Zone risk model (incorporates new zone risk data)

## Model Versioning

The training pipeline saves metadata with each training run:

```json
{
  "training_date": "2026-04-15T11:44:01",
  "version": "1.0.0",
  "models": {
    "zone_risk": { "r2_score": 0.6731, ... },
    "premium": { "r2_score": 0.9588, ... },
    "fraud": { "roc_auc": 1.0000, ... }
  }
}
```

To deploy new model versions:
1. Train models with updated data
2. Review `model_metadata.json` metrics
3. If metrics are acceptable, the new models are automatically used on next app restart
4. Keep old models as backup in `ml_models/archive/`

## Fallback Behavior

If trained models are not available or fail to load, the system automatically falls back to manually calibrated models with the same interface. This ensures zero downtime during model updates.

## Dependencies

Required packages (already in `requirements.txt`):
- scikit-learn >= 1.3.0
- xgboost >= 2.0.0 (recommended, falls back to GradientBoosting if unavailable)
- pandas >= 2.0.0
- numpy >= 1.24.0
- joblib >= 1.3.0

## Performance Metrics

Current model performance (on synthetic data):

| Model | Metric | Score |
|-------|--------|-------|
| Zone Risk | R² | 0.6731 |
| Premium | R² | 0.9588 |
| Fraud | ROC AUC | 1.0000 |
| Fraud | Precision | 1.0000 |
| Fraud | Recall | 1.0000 |

Note: Fraud model shows perfect scores on synthetic data. Real-world performance will be lower and should be monitored.
