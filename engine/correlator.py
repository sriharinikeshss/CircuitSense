"""
Failure Correlation Engine for CircuitSense
Links related anomalies to common subsystem failures using rule-driven logic + statistical correlation.
"""

import pandas as pd
import numpy as np
from scipy import stats as scipy_stats


# Domain-specific correlation rules
# If these parameters are BOTH anomalous, they likely share a root cause
CORRELATION_RULES = [
    {
        "params": ["voltage_out", "ripple"],
        "keywords_a": ["voltage", "vout", "v_out", "output_v", "vo"],
        "keywords_b": ["ripple", "noise", "ac_noise", "vripple"],
        "diagnosis": "Cascading Regulator Stage Failure",
        "explanation": "Low output voltage AND high ripple strongly suggest the voltage regulator is failing or overloaded. The regulator cannot maintain stable output.",
        "next_steps": [
            "Measure regulator input voltage — is it within spec?",
            "Check regulator temperature — is it overheating?",
            "If input is fine and regulator is hot → regulator is likely damaged or undersized for the load",
            "If input is also low → problem is upstream (power source or input protection)",
        ],
    },
    {
        "params": ["voltage_out", "current"],
        "keywords_a": ["voltage", "vout", "v_out", "output_v", "vo"],
        "keywords_b": ["current", "iout", "i_out", "load_current", "io", "amps"],
        "diagnosis": "Load-dependent Regulation Failure (Overcurrent/Thermal Limit)",
        "explanation": "Low voltage with abnormal current suggests the load is drawing too much current, causing the regulator to enter current limiting or thermal shutdown.",
        "next_steps": [
            "Disconnect load and measure voltage — does it recover?",
            "If yes → load circuit has a short or excessive draw",
            "If no → regulator itself is damaged",
            "Check for shorted components downstream (especially capacitors and ICs)",
        ],
    },
    {
        "params": ["temperature", "voltage_out"],
        "keywords_a": ["temp", "temperature", "thermal", "heat", "tj"],
        "keywords_b": ["voltage", "vout", "v_out", "output_v", "vo"],
        "diagnosis": "Sustained Thermal Stress causing Regulation Drift",
        "explanation": "High temperature correlating with voltage drift indicates thermal stress is affecting regulator performance. This can indicate inadequate heatsinking or sustained overload.",
        "next_steps": [
            "Check if thermal shutdown is activating (output drops then recovers cyclically)",
            "Improve heatsinking or airflow",
            "Consider derating the load or using a higher-rated regulator",
        ],
    },
    {
        "params": ["clock_freq", "signal_level"],
        "keywords_a": ["clock", "freq", "frequency", "clk", "osc"],
        "keywords_b": ["signal", "level", "amplitude", "vpp", "logic"],
        "diagnosis": "Clock/Signal Integrity Degradation via Power Coupling",
        "explanation": "Unstable clock frequency with abnormal signal levels suggests power supply noise is affecting the oscillator or crystal, or the clock circuit has a component fault.",
        "next_steps": [
            "Check power supply to the oscillator/crystal circuit",
            "Verify crystal load capacitors are correct value",
            "Check for nearby noise sources (switching regulators, high-current traces)",
        ],
    },
]


def find_correlations(df: pd.DataFrame, anomaly_indices: list, numeric_cols: list = None) -> dict:
    """
    Find correlations between test parameters, especially among anomalous readings.

    Args:
        df: Test measurement DataFrame
        anomaly_indices: List of row indices flagged as anomalous
        numeric_cols: Numeric columns to analyze

    Returns:
        dict with:
            - rule_matches: domain-specific correlation matches
            - statistical_correlations: significant parameter correlations
            - linked_failures: grouped anomalies with shared root causes
    """
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if len(numeric_cols) < 2:
        return {
            "rule_matches": [],
            "statistical_correlations": [],
            "linked_failures": [],
            "message": "Need at least 2 numeric columns for correlation analysis.",
        }

    # 1. Rule-based correlation matching
    rule_matches = _match_correlation_rules(df, anomaly_indices, numeric_cols)

    # 2. Statistical correlation (Pearson)
    stat_correlations = _compute_statistical_correlations(df, numeric_cols)

    # 3. Group linked failures
    linked_failures = _group_linked_failures(rule_matches, stat_correlations, anomaly_indices)

    return {
        "rule_matches": rule_matches,
        "statistical_correlations": stat_correlations,
        "linked_failures": linked_failures,
    }


def _match_correlation_rules(df: pd.DataFrame, anomaly_indices: list, numeric_cols: list) -> list:
    """Match anomalous parameters against domain-specific correlation rules."""
    matches = []
    cols_lower = {col: col.lower().strip() for col in numeric_cols}

    for rule in CORRELATION_RULES:
        # Find columns matching each parameter group
        matched_a = [col for col, cl in cols_lower.items()
                     if any(kw in cl for kw in rule["keywords_a"])]
        matched_b = [col for col, cl in cols_lower.items()
                     if any(kw in cl for kw in rule["keywords_b"])]

        if not matched_a or not matched_b:
            continue

        # Check if both parameter groups have anomalies in the same rows
        for col_a in matched_a:
            for col_b in matched_b:
                if col_a == col_b:
                    continue

                # Check if these columns are both anomalous at the same data points
                both_anomalous = _are_both_anomalous(df, col_a, col_b, anomaly_indices)

                if both_anomalous:
                    matches.append({
                        "param_a": col_a,
                        "param_b": col_b,
                        "diagnosis": rule["diagnosis"],
                        "explanation": rule["explanation"],
                        "next_steps": rule["next_steps"],
                        "confidence": "HIGH",
                        "source": "🔗 Correlated (rule-based)",
                        "affected_rows": both_anomalous,
                    })

    return matches


def _are_both_anomalous(df: pd.DataFrame, col_a: str, col_b: str, anomaly_indices: list) -> list:
    """Check if both columns have abnormal values at the same row indices."""
    if not anomaly_indices:
        return []

    # Use z-score to check if values are abnormal in each column
    both = []
    mean_a, std_a = df[col_a].mean(), df[col_a].std()
    mean_b, std_b = df[col_b].mean(), df[col_b].std()

    if std_a == 0 or std_b == 0:
        return []

    for idx in anomaly_indices:
        if idx not in df.index:
            continue
        z_a = abs((df.loc[idx, col_a] - mean_a) / std_a)
        z_b = abs((df.loc[idx, col_b] - mean_b) / std_b)
        if z_a > 1.5 and z_b > 1.5:
            both.append(idx)

    return both


def _compute_statistical_correlations(df: pd.DataFrame, numeric_cols: list) -> list:
    """Compute pairwise correlations (Pearson for linear, Spearman for monotonic)."""
    correlations = []

    for i, col_a in enumerate(numeric_cols):
        for col_b in numeric_cols[i + 1:]:
            try:
                clean = df[[col_a, col_b]].dropna()
                n_samples = len(clean)
                if n_samples < 5:
                    continue
                
                corr, p_value = scipy_stats.pearsonr(clean[col_a], clean[col_b])
                
                # Check Spearman for monotonic (non-linear) relationships like thermal drift
                spearman_corr, spearman_p = 0, 1
                if n_samples >= 8:
                    spearman_corr, spearman_p = scipy_stats.spearmanr(clean[col_a], clean[col_b])

                # Linear dominates
                if abs(corr) > 0.7 and p_value < 0.05:
                    direction = "positive" if corr > 0 else "negative"
                    correlations.append({
                        "param_a": col_a,
                        "param_b": col_b,
                        "correlation": round(float(corr), 3),
                        "p_value": round(float(p_value), 4),
                        "direction": direction,
                        "strength": "Strong" if abs(corr) > 0.85 else "Moderate",
                        "interpretation": f"{col_a} and {col_b} are strongly {direction}ly correlated (r={corr:.3f}). Changes in one reliably predict linear changes in the other.",
                        "source": "🔗 Correlated (Pearson Linear)",
                    })
                # Check if it's statistically significant but strictly non-linear
                elif abs(spearman_corr) > 0.7 and spearman_p < 0.05 and abs(corr) <= 0.7:
                     direction = "positive" if spearman_corr > 0 else "negative"
                     correlations.append({
                        "param_a": col_a,
                        "param_b": col_b,
                        "correlation": round(float(spearman_corr), 3),
                        "p_value": round(float(spearman_p), 4),
                        "direction": direction,
                        "strength": "Strong (Monotonic)" if abs(spearman_corr) > 0.85 else "Moderate (Monotonic)",
                        "interpretation": f"Non-linear correlation detected (ρ={spearman_corr:.3f}). Signals a monotonic drift, common in thermal load or saturation failures.",
                        "source": "🔗 Correlated (Spearman Rank)",
                    })
            except Exception:
                continue

    return correlations


def _group_linked_failures(rule_matches: list, stat_correlations: list, anomaly_indices: list) -> list:
    """Group related anomalies into linked failure clusters."""
    groups_dict = {}

    # Each rule match is a failure group
    for match in rule_matches:
        diag = match["diagnosis"]
        if diag not in groups_dict:
            groups_dict[diag] = {
                "type": diag,
                "linked_parameters": [match["param_a"], match["param_b"]],
                "affected_rows": set(match["affected_rows"]),
                "explanation": match["explanation"],
                "next_steps": match["next_steps"],
                "confidence": match["confidence"],
                "source": match["source"],
            }
        else:
            if match["param_a"] not in groups_dict[diag]["linked_parameters"]:
                groups_dict[diag]["linked_parameters"].append(match["param_a"])
            if match["param_b"] not in groups_dict[diag]["linked_parameters"]:
                groups_dict[diag]["linked_parameters"].append(match["param_b"])
            groups_dict[diag]["affected_rows"].update(match["affected_rows"])

    groups = []
    for diag, data in groups_dict.items():
        data["affected_rows"] = list(data["affected_rows"])
        groups.append(data)

    # Add statistically correlated pairs that aren't already covered by rules
    rule_pairs = {(m["param_a"], m["param_b"]) for m in rule_matches}
    for corr in stat_correlations:
        pair = (corr["param_a"], corr["param_b"])
        if pair not in rule_pairs and (pair[1], pair[0]) not in rule_pairs:
            groups.append({
                "type": f"Statistical link: {corr['param_a']} ↔ {corr['param_b']}",
                "linked_parameters": [corr["param_a"], corr["param_b"]],
                "affected_rows": anomaly_indices,
                "explanation": corr["interpretation"],
                "next_steps": [
                    f"Investigate why {corr['param_a']} and {corr['param_b']} move together",
                    "Check if they share a common power or signal source",
                    "Look for a single component feeding both subsystems",
                ],
                "confidence": "MEDIUM",
                "source": corr["source"],
            })

    return groups
