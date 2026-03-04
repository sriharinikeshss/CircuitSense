"""
Isolation Forest Anomaly Detection for CircuitSense
Detects multivariate outliers in test measurement data.
Falls back to threshold-based detection for small datasets.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


def detect_anomalies(df: pd.DataFrame, numeric_cols: list = None, contamination="auto") -> dict:
    """
    Detect anomalies in test measurement data.

    Args:
        df: DataFrame with test measurements
        numeric_cols: List of numeric column names to analyze. If None, auto-detect.
        contamination: Expected proportion of anomalies (0.01 to 0.5) or "auto"

    Returns:
        dict with:
            - anomaly_mask: boolean array (True = anomaly)
            - anomaly_scores: float array (lower = more anomalous)
            - anomaly_indices: list of row indices flagged
            - method: 'isolation_forest' or 'threshold'
            - feature_contributions: dict showing which features contributed most
            - stats: per-column statistics
    """
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if len(numeric_cols) == 0:
        return {
            "anomaly_mask": np.array([]),
            "anomaly_scores": np.array([]),
            "anomaly_indices": [],
            "method": "none",
            "feature_contributions": {},
            "stats": {},
            "error": "No numeric columns found in data.",
        }

    # Extract numeric data
    data = df[numeric_cols].dropna()

    if len(data) < 5:
        return {
            "anomaly_mask": np.array([]),
            "anomaly_scores": np.array([]),
            "anomaly_indices": [],
            "method": "none",
            "feature_contributions": {},
            "stats": {},
            "error": "Too few data points (need at least 5 rows).",
        }

    # Calculate per-column statistics
    stats = {}
    for col in numeric_cols:
        col_data = data[col]
        stats[col] = {
            "mean": float(col_data.mean()),
            "std": float(col_data.std()),
            "min": float(col_data.min()),
            "max": float(col_data.max()),
            "median": float(col_data.median()),
            "q1": float(col_data.quantile(0.25)),
            "q3": float(col_data.quantile(0.75)),
        }

    # Choose method based on data size and dimensionality
    if len(numeric_cols) >= 3 and len(data) >= 20:
        return _isolation_forest_detect(data, numeric_cols, contamination, stats)
    else:
        return _threshold_detect(data, numeric_cols, stats)


def _isolation_forest_detect(data: pd.DataFrame, numeric_cols: list,
                              contamination, stats: dict) -> dict:
    """Use Isolation Forest for multivariate anomaly detection."""
    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data)

    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100,
    )
    predictions = model.fit_predict(data_scaled)
    scores = model.decision_function(data_scaled)

    anomaly_mask = predictions == -1
    
    # --- Post-processing: Sanity check for pristine data ---
    # Isolation Forest will force some points below 0 decision function if contamination='auto' 
    # even in a perfectly normal distribution.
    # We apply a strict reality check: Gaussian tail population testing.
    # In a true normal distribution, P(|Z| > 3) ≈ 0.0027 (0.27%).
    # We only accept IF's anomalies if the actual tail population exceeds logical expectations.
    z_scores = np.abs((data - data.mean()) / data.std().replace(0, 1))
    
    # 1. Identify points stretching into the theoretical 3-sigma tail
    tail_mask = (z_scores > 3.0).any(axis=1)
    
    # 2. Calculate observed vs expected tail fraction
    observed_tail_fraction = tail_mask.mean()
    
    # 3. Adjust expected tail rate for multi-dimensionality (Probability of at least one feature > 3-sigma)
    p_univariate_tail = 0.0027 
    expected_multivariate_tail_rate = 1.0 - (1.0 - p_univariate_tail) ** data.shape[1]
    
    # 4. Engineering Margin (Allow up to 2x the multivariate expected noise before declaring anomalous)
    allowed_multiplier = 2.0 
    
    if observed_tail_fraction <= (expected_multivariate_tail_rate * allowed_multiplier):
        anomaly_mask[:] = False # Suppress false positives for clean datasets

    anomaly_indices = data.index[anomaly_mask].tolist()

    # Calculate feature contributions for anomalies
    feature_contributions = _compute_feature_contributions(data, data_scaled, anomaly_mask, numeric_cols)

    return {
        "anomaly_mask": anomaly_mask,
        "anomaly_scores": scores,
        "anomaly_indices": anomaly_indices,
        "anomaly_count": int(anomaly_mask.sum()),
        "total_points": len(data),
        "method": "isolation_forest",
        "source": "📊 ML-detected (Isolation Forest)",
        "feature_contributions": feature_contributions,
        "stats": stats,
        "error": None,
    }


def _threshold_detect(data: pd.DataFrame, numeric_cols: list, stats: dict) -> dict:
    """Fallback: z-score based threshold detection for small datasets."""
    z_scores = np.abs((data - data.mean()) / data.std().replace(0, 1))

    # A point is anomalous if any column has z-score > 2.5
    anomaly_mask = (z_scores > 2.5).any(axis=1)
    anomaly_indices = data.index[anomaly_mask].tolist()

    # Max z-score per row as "anomaly score" (inverted so lower = more anomalous)
    max_z = z_scores.max(axis=1)
    scores = -max_z  # Invert to match Isolation Forest convention

    # Feature contributions: which columns had high z-scores
    feature_contributions = {}
    for idx in anomaly_indices:
        row_z = z_scores.loc[idx]
        top_features = row_z.nlargest(3)
        feature_contributions[idx] = {
            col: float(z_val) for col, z_val in top_features.items() if z_val > 2.0
        }

    return {
        "anomaly_mask": anomaly_mask,
        "anomaly_scores": scores.values,
        "anomaly_indices": anomaly_indices,
        "anomaly_count": int(anomaly_mask.sum()),
        "total_points": len(data),
        "method": "threshold (z-score > 2.5)",
        "source": "📊 ML-detected (statistical threshold)",
        "feature_contributions": feature_contributions,
        "stats": stats,
        "error": None,
    }


def _compute_feature_contributions(data: pd.DataFrame, data_scaled: np.ndarray,
                                    anomaly_mask: np.ndarray, numeric_cols: list) -> dict:
    """For each anomaly, determine which features contributed most."""
    contributions = {}

    # Use absolute deviation from mean as a proxy for feature contribution
    mean_scaled = data_scaled.mean(axis=0)

    for idx in data.index[anomaly_mask]:
        row_idx = data.index.get_loc(idx)
        deviations = np.abs(data_scaled[row_idx] - mean_scaled)
        top_indices = np.argsort(deviations)[::-1][:3]

        contributions[idx] = {
            numeric_cols[i]: {
                "deviation": float(deviations[i]),
                "actual_value": float(data.loc[idx, numeric_cols[i]]),
                "mean": float(data[numeric_cols[i]].mean()),
            }
            for i in top_indices if deviations[i] > 1.0
        }

    return contributions
