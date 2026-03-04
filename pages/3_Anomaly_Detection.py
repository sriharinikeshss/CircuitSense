"""
CircuitSense — Anomaly Detection Page
Upload test log CSV → Isolation Forest / threshold detection → Plotly charts with anomaly overlay + correlation.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.anomaly import detect_anomalies
from engine.correlator import find_correlations

st.set_page_config(page_title="Anomaly Detection — CircuitSense", layout="wide", initial_sidebar_state="collapsed")

from nav import render_top_nav
render_top_nav()

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    .stApp { background-color: #FFFFFF; font-family: 'Inter', sans-serif; }
    
    h1, h2, h3, h4, h5, h6 { color: #0F172A !important; font-weight: 700 !important; letter-spacing: -0.5px; }
    p, span, div { color: #334155; }
    
    .stApp [data-testid="stMarkdownContainer"] h3 {
        margin-top: 1.5rem !important;
        margin-bottom: 0.5rem !important;
        font-size: 1.3rem !important;
    }
    
    .top-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        margin-top: -16px;
    }
    .page-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        margin: 0;
    }
    
    [data-testid="stHorizontalBlock"] { gap: 16px !important; }
    
    .clean-list-item {
        padding: 16px 20px;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        margin-bottom: 12px;
        background-color: #FFFFFF;
    }
    
    [data-testid="block-container"] {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1240px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="top-header">
    <h1 class="page-title">Anomaly Detection</h1>
</div>
""", unsafe_allow_html=True)
st.markdown("Upload test measurement data to detect anomalies using **ML (Isolation Forest)** and find **correlated failures** across parameters.")
st.info("💡 **Note:** Anomalies indicate statistically unusual behavior compared to other boards, not necessarily specification violations.")
st.markdown("<br>", unsafe_allow_html=True)

if "uploader_key_ad" not in st.session_state:
    st.session_state["uploader_key_ad"] = 0

# File upload
col_upload, col_clear = st.columns([4, 1])
with col_upload:
    uploaded_file = st.file_uploader("Upload Test Log CSV", type=["csv"], key=f"testlog_upload_{st.session_state['uploader_key_ad']}", label_visibility="collapsed")
with col_clear:
    clear_data = st.button("Clear Data", use_container_width=True)

if clear_data:
    st.session_state["uploader_key_ad"] += 1
    for key in ["anomaly_results", "correlation_results", "test_df", "testlog_source"]:
        st.session_state.pop(key, None)
    st.rerun()

# Load data
df = None
testlog_source = None
fresh_upload = False

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    testlog_source = f"{uploaded_file.name} ({len(df)} rows)"
    fresh_upload = True
elif "test_df" in st.session_state:
    df = st.session_state["test_df"]
    testlog_source = st.session_state.get("testlog_source", "Previously loaded test log")

if df is not None:
    st.success(f"Loaded: **{testlog_source}**")
    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("Raw Data Preview", expanded=False):
        st.dataframe(df, use_container_width=True, height=200)

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        st.error("No numeric columns found in the data.")
        st.stop()

    with st.sidebar:
        st.markdown("### ⚙️ Detection Settings")
        auto_contamination = st.checkbox("Auto-detect anomaly rate", value=True)
        if not auto_contamination:
            contamination = st.slider("Expected anomaly rate (manual)", 0.01, 0.3, 0.1, 0.01)
        else:
            contamination = "auto"
        selected_cols = st.multiselect("Columns to analyze", numeric_cols, default=numeric_cols)

    if not selected_cols:
        st.warning("Select at least one column to analyze.")
        st.stop()
    elif len(selected_cols) == 1:
        st.info("Single-parameter analysis: anomalies are detected using univariate behavior only.")

    prev_contamination = st.session_state.get("_prev_contamination", None)
    prev_cols = st.session_state.get("_prev_selected_cols", None)
    # Check if we need to force re-run based on changed params or new data
    settings_changed = (prev_contamination != contamination or prev_cols != selected_cols)
    force_run = fresh_upload or ("anomaly_results" not in st.session_state) or settings_changed

    if force_run:
        results = detect_anomalies(df, numeric_cols=selected_cols, contamination=contamination)
        if "error" in results and results["error"]:
            st.error(results["error"])
            st.stop()
        correlations = find_correlations(df, results["anomaly_indices"], numeric_cols=selected_cols)
        st.session_state["_prev_contamination"] = contamination
        st.session_state["_prev_selected_cols"] = selected_cols
    else:
        results = st.session_state["anomaly_results"]
        correlations = st.session_state["correlation_results"]

    st.session_state["anomaly_results"] = results
    st.session_state["correlation_results"] = correlations
    st.session_state["test_df"] = df
    st.session_state["testlog_source"] = testlog_source

    # --- Summary metrics ---
    st.markdown("### Detection Summary")
    
    def custom_metric(label, value, caption, delta_color="gray"):
        color = "#10B981" if delta_color == "normal" else "#EF4444" if delta_color == "inverse" else "#64748B"
        return f"""
        <div style="padding: 4px 2px; display: flex; flex-direction: column; justify-content: space-between; height: 130px;">
            <div>
                <div style="color: #64748B; font-size: 0.85rem; margin-bottom: 4px;">{label}</div>
                <div style="color: #0F172A; font-size: 1.3rem; font-weight: 600; line-height: 1.2; margin-bottom: 8px;">{value}</div>
            </div>
            <div style="margin-top: auto;">
                <div style="color: {color}; font-size: 0.75rem; background-color: {color}15; display: inline-block; padding: 2px 6px; border-radius: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;">↑ {caption}</div>
            </div>
        </div>
        """

    m1, m2, m3, m4 = st.columns(4)
    anom_pct = f"{results['anomaly_count']/results['total_points']*100:.1f}%"
    linked = len(correlations.get("linked_failures", []))
    
    with m1:
        with st.container(border=True):
            st.markdown(custom_metric("Total Points", str(results["total_points"]), "Data points analyzed"), unsafe_allow_html=True)
    with m2:
        with st.container(border=True):
            st.markdown(custom_metric("Anomalies Found", str(results["anomaly_count"]), f"{anom_pct} of total", "inverse"), unsafe_allow_html=True)
    with m3:
        with st.container(border=True):
            st.markdown(custom_metric("Method", results["method"].split("(")[0].strip(), "Detection algorithm"), unsafe_allow_html=True)
    with m4:
        with st.container(border=True):
            st.markdown(custom_metric("Correlated Failures", str(linked), "Linked groups", "inverse"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Anomaly hero chart ---
    st.markdown("### Measurement Trace & Anomalies")
    st.caption("Anomalies are detected at the row (board) level using multivariate analysis. A board may appear normal on one parameter but anomalous in combination with others.")
    
    # Interactive multiselect for the hero plotting
    hero_selected_cols = st.multiselect(
        "Select parameters to display on main chart",
        options=selected_cols,
        default=[selected_cols[0]] if selected_cols else [],
        label_visibility="collapsed"
    )
    
    if not hero_selected_cols:
        st.info("Select at least one parameter to view the telemetry.")
     
    if hero_selected_cols:
        fig_hero = go.Figure()
        
        colors = ['#0F172A', '#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#14B8A6']
        
        for i, col_name in enumerate(hero_selected_cols):
            trace_color = colors[i % len(colors)]
            
            # Normal Line
            fig_hero.add_trace(go.Scatter(
                y=df[col_name],
                mode='lines+markers',
                line=dict(color=trace_color, width=2),
                marker=dict(color=trace_color, size=6, opacity=0.7),
                name=col_name
            ))
            
            # Red Anomalies Overlay for this specific column
            anom_mask = results["anomaly_mask"]
            if anom_mask.any():
                fig_hero.add_trace(go.Scatter(
                    x=df.index[anom_mask],
                    y=df[col_name][anom_mask],
                    mode='markers',
                    marker=dict(color='#EF4444', size=10, symbol='x', line=dict(width=1, color='#EF4444')),
                    name=f"{col_name} (Anomaly)",
                    showlegend=False # Hide anomaly legends to keep it clean
                ))
        
        fig_hero.update_layout(
            template="plotly_white",
            margin=dict(l=0, r=0, t=10, b=0),
            height=400,
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=True, gridcolor='#F1F5F9', zeroline=False),
            plot_bgcolor='white',
            paper_bgcolor='white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_hero, use_container_width=True)
        
        # Dynamic Trace Statistics
        stats_cols = st.columns(len(hero_selected_cols))
        for i, col_name in enumerate(hero_selected_cols):
            with stats_cols[i]:
                trace_mean = df[col_name].mean()
                trace_max = df[col_name].max()
                trace_min = df[col_name].min()
                st.markdown(f"""
                <div style="border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px; font-size: 0.85rem; background-color: #F8FAFC; margin-top: 4px; margin-bottom: 24px;">
                    <div style="font-weight: 600; color: #0F172A; margin-bottom: 4px;">{col_name}</div>
                    <span style="color: #64748B;">Min:</span> {trace_min:.2f} &nbsp;|&nbsp; 
                    <span style="color: #64748B;">Max:</span> {trace_max:.2f} &nbsp;|&nbsp; 
                    <span style="color: #64748B;">Mean:</span> {trace_mean:.2f}
                </div>
                """, unsafe_allow_html=True)

    with st.expander("Expand for Isolated Parameter Views (Grid)", expanded=False):
        st.markdown("Individual isolation plots with $\pm2.5\sigma$ reference lines.")
        n_cols = len(selected_cols)
        fig_grid = make_subplots(
            rows=(n_cols + 1) // 2, cols=2,
            subplot_titles=selected_cols,
            vertical_spacing=0.12,
            horizontal_spacing=0.08,
        )

        for i, col in enumerate(selected_cols):
            row = i // 2 + 1
            col_idx = i % 2 + 1

            normal_mask = ~results["anomaly_mask"]
            
            # Crisp Shadcn-like plotting
            fig_grid.add_trace(
                go.Scatter(
                    x=df.index[normal_mask],
                    y=df[col][normal_mask],
                    mode="markers",
                    marker=dict(color="#0F172A", size=5, opacity=0.8),
                    name=f"{col} (normal)",
                    showlegend=(i == 0),
                ),
                row=row, col=col_idx,
            )

            fig_grid.add_trace(
                go.Scatter(
                    x=df.index[results["anomaly_mask"]],
                    y=df[col][results["anomaly_mask"]],
                    mode="markers",
                    marker=dict(color="#EF4444", size=10, symbol="x", line=dict(width=2, color="#EF4444")),
                    name=f"{col} (anomaly)",
                    showlegend=(i == 0),
                ),
                row=row, col=col_idx,
            )

            mean = df[col].mean()
            std = df[col].std()
            fig_grid.add_hline(y=mean + 2.5 * std, line_dash="dash", line_color="#94A3B8",
                          opacity=0.6, row=row, col=col_idx, annotation_text="+2.5σ (Reference)", annotation_position="top left")
            fig_grid.add_hline(y=mean - 2.5 * std, line_dash="dash", line_color="#94A3B8",
                          opacity=0.6, row=row, col=col_idx, annotation_text="-2.5σ (Reference)", annotation_position="bottom left")

        fig_grid.update_layout(
            template="plotly_white",
            height=340 * ((n_cols + 1) // 2),
            plot_bgcolor='white',
            paper_bgcolor='white',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1),
            margin=dict(l=24, r=24, t=40, b=24),
            font=dict(family='Inter, sans-serif', color="#0F172A"),
        )
        fig_grid.update_xaxes(showgrid=False, zeroline=False)
        fig_grid.update_yaxes(showgrid=True, gridcolor='#F1F5F9', zeroline=False)
        
        st.plotly_chart(fig_grid, use_container_width=True)

    # --- Anomaly details ---
    if results["anomaly_count"] == 0:
        st.success("All Clear: All measurements are within normal operating bounds. No anomalies detected.")
    else:
        col_details, col_corr = st.columns([1, 1], gap="large")
        
        with col_details:
            st.markdown("### Anomaly Details")
            # Native HTML replacement for Shadcn secondary badge
            st.markdown(f'<div style="margin-bottom: 16px;"><span style="background-color: #F1F5F9; color: #334155; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 500;">{results["source"]}</span></div>', unsafe_allow_html=True)
            
            anomaly_df = df.loc[results["anomaly_indices"]]
            st.dataframe(anomaly_df, use_container_width=True, hide_index=True)

            if results["feature_contributions"]:
                st.markdown("#### Feature Contributions")
                
                # Build a clean dataframe for the contributions instead of nested expanders
                contribution_data = []
                for idx, contributions in results["feature_contributions"].items():
                    if contributions:
                        board_label = str(idx)
                        for col_name in ["Board_ID", "board_id", "ID", "Sample"]:
                            if col_name in df.columns:
                                board_label = str(df.loc[idx, col_name])
                                break
                        
                        for feat, info in contributions.items():
                            if isinstance(info, dict):
                                dev = info.get("deviation", 0)
                                entry = {
                                    "Board / Row": board_label,
                                    "Primary Factor": feat,
                                    "Deviation (σ)": round(dev, 2),
                                    "Actual Value": round(info.get("actual_value", 0), 4)
                                }
                            else:
                                entry = {
                                    "Board / Row": board_label,
                                    "Primary Factor": feat,
                                    "Deviation (σ)": round(info, 2),
                                    "Actual Value": "N/A"
                                }
                            contribution_data.append(entry)
                
                if contribution_data:
                    contrib_df = pd.DataFrame(contribution_data)
                    st.dataframe(contrib_df, hide_index=True, use_container_width=True, height=200)

        with col_corr:
            if correlations.get("linked_failures"):
                st.markdown("### Correlated Failures")
                st.caption("Anomalies that likely share a common root cause.")

                for gi, group in enumerate(correlations["linked_failures"]):
                    with st.expander(f"🚨 {group['type']} ({len(group['affected_rows'])} boards)", expanded=(gi == 0)):
                        st.markdown(f"**Linked parameters:** `{', '.join(group['linked_parameters'])}`")
                        st.markdown(f"**Explanation:** {group['explanation']}")
                        
                        if group.get("next_steps"):
                            st.markdown("**Recommended Next Steps:**")
                            for i, step in enumerate(group["next_steps"], 1):
                                st.markdown(f"{i}. {step}")

            # Statistical correlations
            if correlations.get("statistical_correlations"):
                with st.expander("📊 All Statistical Links", expanded=False):
                    for corr in correlations["statistical_correlations"]:
                        st.markdown(f"""
                        - **{corr['param_a']}** ↔ **{corr['param_b']}**: r = {corr['correlation']} ({corr['strength']})  
                          *{corr['interpretation']}*
                        """)

    # Correlation heatmap
    if len(selected_cols) >= 2:
        st.markdown("---")
        st.markdown("### Correlation Heatmap")
        
        exclude_anomalies = st.checkbox("Exclude anomalous rows from heatmap calculation", value=False)
        heatmap_df = df[~results["anomaly_mask"]] if exclude_anomalies else df
        corr_matrix = heatmap_df[selected_cols].corr()
        fig_heat = px.imshow(
            corr_matrix,
            color_continuous_scale="RdBu",
            zmin=-1, zmax=1,
            labels=dict(color="Correlation"),
        )
        fig_heat.update_layout(
            template="plotly_white",
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=420,
            margin=dict(l=24, r=24, t=32, b=24),
            font=dict(family='Inter, sans-serif', color="#0F172A"),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

else:
    st.info("Upload a test log CSV to get started.")
    st.markdown("""
    **Expected CSV format:**
    | Board_ID | Voltage_Out | Ripple_mV | Current_mA | Temperature_C |
    |---|---|---|---|---|
    | B001 | 5.02 | 12 | 145 | 42 |
    
    Each row = one board/sample. Numeric columns will be analyzed for anomalies.
    """)
