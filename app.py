"""
CircuitSense — AI-Based Electronics Testing Assistant
Main Streamlit dashboard and entry point.
"""

import streamlit as st
import streamlit_shadcn_ui as ui
import sys
import os
import pandas as pd
import numpy as np

# Use absolute path to ensure engine can be found regardless of where we run this
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Page configuration
st.set_page_config(
    page_title="Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for Shadcn pristine look and Top Nav
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    .stApp {
        background-color: #FFFFFF;
        font-family: 'Inter', sans-serif;
    }

    /* Hide sidebar */
    [data-testid="collapsedControl"] { display: none !important; }
    [data-testid="stSidebar"] { display: none !important; }

    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #0F172A !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
    }

    .stApp [data-testid="stMarkdownContainer"] h3 {
        margin-top: 1rem !important;
        margin-bottom: 0.5rem !important;
        font-size: 1.5rem !important;
    }

    p, span, div {
        color: #334155;
    }
    
    /* Top Header Bar Layout */
    .top-header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 12px;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 24px;
        margin-top: -24px;
    }
    
    .logo-container {
        display: flex;
        align-items: center;
        gap: 12px;
        font-weight: 600;
        font-size: 1rem;
        color: #0F172A;
    }
    
    .nav-links-center {
        display: flex;
        gap: 24px;
        align-items: center;
        justify-content: center;
        flex: 1;
    }

    .dashboard-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        margin: 0;
    }

    [data-testid="block-container"] {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 1240px;
    }
    
    .footer-text {
        text-align: center;
        color: #94A3B8;
        font-size: 0.85rem;
        padding-top: 40px;
        border-top: 1px solid #F1F5F9;
        margin-top: 40px;
    }
    
    /* Make page links look like native text links */
    .stPageLink a {
        text-decoration: none !important;
        color: #64748B !important;
        font-weight: 500 !important;
    }
    .stPageLink a:hover {
        color: #0F172A !important;
    }
</style>
""", unsafe_allow_html=True)


# ── Top Navigation (Matches Reference Image) ───────────
from nav import render_top_nav
render_top_nav()


# ── Title Area ───────────
st.markdown("""
<div style="margin-bottom: 24px;">
    <h1 class="dashboard-title">Dashboard</h1>
    <p style="color: #64748B; font-size: 1.05rem; margin-top: 6px;">CircuitSense aggregates design intent (BOM), observed behavior (test data), and inferred relationships (correlation) into a unified board health view.</p>
</div>
""", unsafe_allow_html=True)

has_board = "board_analysis" in st.session_state
has_anomaly = "anomaly_results" in st.session_state

# ── Tabs ──────────────

tabs = ui.tabs(options=['Overview', 'Analytics', 'System State', 'Getting Started'], default_value='Overview', key="main_tabs")

if tabs == 'Overview':
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 4-Card Top Row like Shadcn
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        if has_board:
            total_comps = st.session_state["bom_data"]["summary"]["total_components"]
            ui.metric_card(title="Total Components", content=str(total_comps), description="Analyzed in BOM", key="dash_ov1")
        else:
            ui.metric_card(title="Total Components", content="0", description="Upload BOM", key="dash_ov1_empty")
            
    with m2:
        if has_board:
            risk = st.session_state["board_analysis"]["power_analysis"]["risk_level"]
            ui.metric_card(title="Design Risk", content=risk, description="Power Topology", key="dash_ov2")
        else:
            ui.metric_card(title="Design Risk", content="—", description="Pending", key="dash_ov2_empty")

    with m3:
        if has_anomaly:
            anoms = st.session_state["anomaly_results"]["anomaly_count"]
            ui.metric_card(title="Anomalies", content=str(anoms), description="Detected via ML", key="dash_ov3")
        else:
            ui.metric_card(title="Anomalies", content="0", description="Upload Test Data", key="dash_ov3_empty")

    with m4:
        if has_anomaly:
            corrs = len(st.session_state["correlation_results"].get("linked_failures", []))
            ui.metric_card(title="Correlations", content=str(corrs), description="Linked failures", key="dash_ov4")
        else:
            ui.metric_card(title="Correlations", content="0", description="Requires telemetry", key="dash_ov4_empty")

    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Bottom Layout: Chart on Left, List on Right
    left_col, right_col = st.columns([2, 1], gap="large")
    
    with left_col:
        st.markdown("### Processed Telemetry")
        if has_anomaly:
            import plotly.graph_objects as go
            import numpy as np
            df = st.session_state["test_df"]
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if len(num_cols) > 0:
                # Interactive multiselect for plotting
                selected_cols = st.multiselect(
                    "Select parameters to display",
                    options=num_cols,
                    default=[num_cols[0]],
                    label_visibility="collapsed"
                )
                
                if not selected_cols:
                    st.info("Select at least one parameter to view the telemetry.")
                 
                if selected_cols:
                    fig = go.Figure()
                    
                    colors = ['#0F172A', '#3B82F6', '#10B981', '#F59E0B', '#8B5CF6']
                    
                    for i, col_name in enumerate(selected_cols):
                        trace_color = colors[i % len(colors)]
                        
                        # Normal Line
                        fig.add_trace(go.Scatter(
                            y=df[col_name],
                            mode='lines+markers',
                            line=dict(color=trace_color, width=2),
                            marker=dict(color=trace_color, size=6, opacity=0.7),
                            name=col_name
                        ))
                        
                        # Red Anomalies Overlay for this specific column
                        anom_mask = st.session_state["anomaly_results"]["anomaly_mask"]
                        if anom_mask.any():
                            fig.add_trace(go.Scatter(
                                x=df.index[anom_mask],
                                y=df[col_name][anom_mask],
                                mode='markers',
                                marker=dict(color='#EF4444', size=10, symbol='x', line=dict(width=1, color='#EF4444')),
                                name=f"{col_name} (Anomaly)",
                                showlegend=False # Hide anomaly legends to keep it clean, the red X is universal
                            ))
                    
                    fig.update_layout(
                        template="plotly_white",
                        margin=dict(l=0, r=0, t=10, b=0),
                        height=350,
                        xaxis=dict(showgrid=False, zeroline=False),
                        yaxis=dict(showgrid=True, gridcolor='#F1F5F9', zeroline=False),
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Dynamic Trace Statistics
                    stats_cols = st.columns(len(selected_cols))
                    for i, col_name in enumerate(selected_cols):
                        with stats_cols[i]:
                            trace_mean = df[col_name].mean()
                            trace_max = df[col_name].max()
                            trace_min = df[col_name].min()
                            st.markdown(f"""
                            <div style="border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px; font-size: 0.82rem; background-color: #F8FAFC; margin-top: 4px;">
                                <div style="font-weight: 600; color: #0F172A; margin-bottom: 4px;">{col_name}</div>
                                <span style="color: #64748B;">Min:</span> {trace_min:.2f} &nbsp;|&nbsp; 
                                <span style="color: #64748B;">Max:</span> {trace_max:.2f} &nbsp;|&nbsp; 
                                <span style="color: #64748B;">Mean:</span> {trace_mean:.2f}
                            </div>
                            """, unsafe_allow_html=True)
            else:
                st.info("No numeric data found in telemetry to plot.")
        else:
            st.info("No test data loaded. Go to the Anomaly Detection page to upload test logs.")

    with right_col:
        st.markdown("### Recent Activity")
        activities = []
        if has_board:
            total_comps = st.session_state["bom_data"]["summary"]["total_components"]
            activities.append(("🟢", f"Parsed BOM ({total_comps} components)"))
            activities.append(("🟡", "Generated power verification plan"))
        if has_anomaly:
            anoms = st.session_state["anomaly_results"]["anomaly_count"]
            activities.append(("🟢", f"Scanned {len(st.session_state['test_df'])} test logs"))
            if anoms > 0:
                activities.append(("🔴", f"Isolated {anoms} anomalies"))
            else:
                activities.append(("🟢", "Telemetry verified clean"))
        if "last_diagnosis" in st.session_state:
            activities.append(("🟣", "Synthesized root-cause diagnosis"))
            
        if not activities:
            st.write("System idle. Awaiting data input.")
        else:
            for icon, act in activities:
                st.markdown(f"""
                <div style="padding: 12px 0; border-bottom: 1px solid #F1F5F9; display: flex; align-items: center;">
                    <div style="width: 32px; height: 32px; border-radius: 50%; background-color: #F8FAFC; border: 1px solid #E2E8F0; margin-right: 12px; display: flex; align-items: center; justify-content: center; font-size: 16px; color: #0F172A;">{icon}</div>
                    <span style="font-size: 0.9em; font-weight: 500; color: #0F172A;">{act}</span>
                </div>
                """, unsafe_allow_html=True)
                



elif tabs == 'Analytics':
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Deep Dive Analytics")
    import plotly.express as px
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**BOM Composition**")
        if has_board:
            # Generate actual pie chart based on real BOM components
            comps = st.session_state["bom_data"]["components"]
            cat_counts = {}
            for c in comps:
                cat = c.get("category", "Other")
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
                
            fig_pie = px.pie(names=list(cat_counts.keys()), values=list(cat_counts.values()), template="plotly_white", hole=0.5)
            fig_pie.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Upload BOM to view composition analytics.")
            
    with c2:
        st.markdown("**Telemetry Correlation Matrix**")
        if has_anomaly:
            df = st.session_state["test_df"]
            num_cols = df.select_dtypes(include=[np.number]).columns
            if len(num_cols) >= 2:
                exclude_anom = st.checkbox("Exclude anomalies from calculation", value=False)
                if exclude_anom:
                    anom_mask = st.session_state["anomaly_results"]["anomaly_mask"]
                    calc_df = df[~anom_mask]
                else:
                    calc_df = df
                    
                corr_matrix = calc_df[num_cols].corr()
                fig_heat = px.imshow(
                    corr_matrix,
                    color_continuous_scale="RdBu",
                    zmin=-1, zmax=1,
                    template="plotly_white"
                )
                fig_heat.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.info("Need at least two numeric parameters to compute correlations.")
        else:
            st.info("Upload test data on the Anomaly Detection page to unlock telemetry analytics.")

elif tabs == 'System State':
    st.markdown("<br>", unsafe_allow_html=True)
    if has_board or has_anomaly:
        health_cols = st.columns(3, gap="medium")
        with health_cols[0]:
            risk_val = st.session_state["board_analysis"]["power_analysis"]["risk_level"] if has_board else "Pending"
            ui.card(title="Design Risk", content=risk_val, description="Based on component analysis", key="hs_c1").render()
        with health_cols[1]:
            if has_anomaly:
                anom_count = st.session_state["anomaly_results"]["anomaly_count"]
                health_status = "Clean" if anom_count == 0 else f"{anom_count} Anomalies"
            else:
                health_status = "Pending"
            ui.card(title="Telemetry Health", content=health_status, description="Based on ML detection", key="hs_c2").render()
        with health_cols[2]:
            diag_val = "Complete" if "last_diagnosis" in st.session_state else "Pending"
            ui.card(title="Root Cause Analysis", content=diag_val, description="Diagnostic chain status", key="hs_c3").render()
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### System Health Summary (Derived Metrics)", help="Scores are derived from rule-based analysis and test data, not direct measurements.")
        import plotly.express as px
        
        # Calculate derived metrics 0-100
        power_score = 50
        if has_board:
            risk = st.session_state["board_analysis"]["power_analysis"]["risk_level"]
            power_score = 90 if risk == "LOW" else 70 if risk == "MEDIUM" else 40
            
        prot_score = 50
        if has_board:
            has_prot = st.session_state["board_analysis"]["power_analysis"]["has_input_protection"]
            prot_score = 95 if has_prot else 30
            
        anom_score = 50
        if has_anomaly:
            anoms = st.session_state["anomaly_results"]["anomaly_count"]
            total = len(st.session_state["test_df"])
            anom_pct = min(anoms / max(total, 1), 1.0)
            anom_score = int(100 - (anom_pct * 100))
            if anom_score < 20: anom_score = 20
        elif has_board:
            anom_score = 50 # Pending
            
        corr_score = 50
        if has_anomaly:
            corrs = len(st.session_state["correlation_results"].get("linked_failures", []))
            corr_score = max(100 - (corrs * 15), 20)
            
        df_radar = pd.DataFrame(dict(
            r=[power_score, prot_score, anom_score, corr_score],
            theta=['Power Stability', 'Protection Level', 'Telemetry Cleanliness', 'Correlation Risk']
        ))
        
        fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True, template="plotly_white")
        fig_radar.update_traces(fill='toself', line_color='#3B82F6', fillcolor='rgba(59, 130, 246, 0.2)')
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
            margin=dict(l=40, r=40, t=30, b=30),
            height=400
        )
        st.plotly_chart(fig_radar, use_container_width=True)
            
    else:
        st.info("No data available to assess system state.")

elif tabs == 'Getting Started':
    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns(3, gap="medium")
    with cols[0]:
        ui.card(title="1. Upload Design", content="BOM", description="Upload BOM (CSV) to analyze.", key="qs1").render()
    with cols[1]:
        ui.card(title="2. Analyze Data", content="Telemetry", description="Upload measurements (CSV) to scan.", key="qs2").render()
    with cols[2]:
        ui.card(title="3. Diagnostics", content="Root Cause", description="Describe symptoms to get chains.", key="qs3").render()


st.markdown("""
<div class="footer-text">
    CircuitSense
</div>
""", unsafe_allow_html=True)
