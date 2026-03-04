"""
CircuitSense — Board Analysis Page
Upload BOM CSV → Parse → Rule Engine Analysis → Risk Flags
"""

import streamlit as st
import pandas as pd
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parsers.bom_parser import parse_bom
from engine.rules import analyze_board, get_context_for_ai

st.set_page_config(page_title="Board Analysis — CircuitSense", layout="wide", initial_sidebar_state="collapsed")

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
    
    .power-chain-step { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 16px; margin: 8px 0; color: #0F172A; }
    
    .clean-list-item {
        padding: 12px 0;
        border-bottom: 1px solid #F1F5F9;
        display: flex;
        align-items: flex-start;
    }
    
    .clean-list-icon {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        margin-right: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        color: #0F172A;
        flex-shrink: 0;
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
    <h1 class="page-title">Board Analysis</h1>
</div>
""", unsafe_allow_html=True)
st.markdown("Upload your **Bill of Materials (BOM)** CSV to get instant component analysis, power subsystem assessment, and risk flags.")
st.markdown("<br>", unsafe_allow_html=True)

if "uploader_key_ba" not in st.session_state:
    st.session_state["uploader_key_ba"] = 0

# File upload
col_upload, col_clear = st.columns([4, 1])
with col_upload:
    uploaded_file = st.file_uploader("Upload BOM CSV", type=["csv"], key=f"bom_upload_{st.session_state['uploader_key_ba']}", label_visibility="collapsed")
with col_clear:
    clear_data = st.button("Clear Data", use_container_width=True)

if clear_data:
    st.session_state["uploader_key_ba"] += 1
    for key in ["bom_data", "board_analysis", "board_context", "bom_source"]:
        st.session_state.pop(key, None)
    st.rerun()

# Load data — new upload takes priority, then fall back to session state
bom_data = None
bom_source = None

if uploaded_file is not None:
    bom_data = parse_bom(uploaded_file)
    bom_source = uploaded_file.name
elif "bom_data" in st.session_state:
    # Restore from session state (user navigated away and came back)
    bom_data = st.session_state["bom_data"]
    bom_source = st.session_state.get("bom_source", "Previously loaded BOM")

if bom_data is not None:
    # Run rule engine analysis
    analysis = analyze_board(bom_data)

    # Store in session state for persistence + other pages
    st.session_state["bom_data"] = bom_data
    st.session_state["board_analysis"] = analysis
    st.session_state["board_context"] = get_context_for_ai(bom_data, analysis)
    st.session_state["bom_source"] = bom_source

    st.success(f"Loaded: **{bom_source}**")
    st.markdown("<br>", unsafe_allow_html=True)

    # --- System State Overview (Board Health Summary) ---
    st.markdown("### System State Overview")
    summary = bom_data["summary"]
    comp_risk = analysis["composite_risk"]
    
    # Check if there is anomaly data in session state
    if "anomaly_results" in st.session_state:
        ar = st.session_state["anomaly_results"]
        measurement_health = f"⚠️ {ar['anomaly_count']} Anomalies Detected" if ar['anomaly_count'] > 0 else "✅ All Clear"
    else:
        measurement_health = "⚪ Not Available — Upload Test Data"
        
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
    with m1:
        with st.container(border=True):
            status_icon = "🔴" if comp_risk == "HIGH" else "🟡" if comp_risk == "MEDIUM" else "🟢"
            st.markdown(custom_metric("Board Status", f"{status_icon} {'Degraded' if comp_risk != 'LOW' else 'Nominal'}", "Based on rules engine"), unsafe_allow_html=True)
    with m2:
        with st.container(border=True):
            st.markdown(custom_metric("Design Risk", comp_risk, "Structural + Power flaws", "inverse" if comp_risk=="HIGH" else "gray"), unsafe_allow_html=True)
    with m3:
        with st.container(border=True):
            val = measurement_health.split(" ", 1)[1] if " " in measurement_health.split(" ", 1)[1] else measurement_health.split(" ", 1)[1]
            cap = measurement_health.split(" ")[0]
            st.markdown(custom_metric("Measurement Health", val, cap, "inverse" if "⚠️" in measurement_health else "normal"), unsafe_allow_html=True)
    with m4:
        with st.container(border=True):
            st.markdown(custom_metric("Top Action", analysis["top_action"], "Priority recommendation"), unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- Component Metrics ---
    st.markdown("### Component Breakdown")
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
             st.metric("Total Components", str(summary["total_components"]), "All physical parts")
    with c2:
        with st.container(border=True):
             st.metric("Categories", str(len(summary["categories"])), "Unique component types")
    with c3:
        with st.container(border=True):
             st.metric("Power-Critical", str(summary["power_critical_count"]), "In the main power path")

    st.markdown("<br>", unsafe_allow_html=True)

    # Category distribution chart and Power Chain
    col_chart, col_power = st.columns([2, 1], gap="large")

    with col_chart:
        st.markdown("### Category Distribution")
        import plotly.express as px
        cat_df = pd.DataFrame(list(summary["category_counts"].items()), columns=["Category", "Count"])
        fig = px.bar(cat_df, x="Category", y="Count")
        
        # Shadcn pristine bar styling: black bars, no grid, rounded top corners
        fig.update_traces(
            marker_color='#0F172A', 
            marker_line_color='#0F172A', 
            marker_line_width=0, 
            opacity=0.9,
            marker_cornerradius=4
        )
        fig.update_layout(
            template="plotly_white",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=20, b=0),
            showlegend=False,
            height=320,
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=True, gridcolor='#F1F5F9', zeroline=False),
            font=dict(family='Inter, sans-serif', color="#0F172A"),
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # --- Component Impact Ranking ---
        st.markdown("#### Top 3 Most Impactful Components")
        st.caption("Priority Bench Focus (Impact = Power Relevance × Quantity)")
        for ic in analysis["impactful_components"]:
            st.markdown(f"""
            <div class="clean-list-item" style="padding: 12px 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div><strong>{ic['reference']}</strong> ({ic['value']})</div>
                    <div style="background-color: #F1F5F9; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; color: #475569;">Score: {ic['score']}</div>
                </div>
                <div style="font-size: 0.85rem; color: #64748B;">{ic['category']}</div>
            </div>
            """, unsafe_allow_html=True)

    with col_power:
        st.markdown("### Power Subsystem")
        pa = analysis["power_analysis"]
        st.markdown(f"**Topology:** {pa['topology']}")
        st.markdown(f"**Regulators:** {pa['regulator_count']}")

        st.markdown("**Power Chain:**")
        
        # Build the visual chain blocks
        chain_html = '<div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 12px; margin-bottom: 16px;">'
        
        for idx, step in enumerate(pa["power_chain"]):
            status_icon = "🟢" if "✅" in step["status"] else "🟡" if "⚠️" in step["status"] else "⚪"
            components = ", ".join(step["components"]) if step["components"] else "—"
            
            # The Stage Block
            chain_html += f"""
            <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px 12px; display: flex; flex-direction: column; min-width: 120px;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #0F172A; margin-bottom: 4px; display: flex; justify-content: space-between;">
                    <span>{step['stage']}</span>
                    <span>{status_icon}</span>
                </div>
                <div style="font-size: 0.7rem; color: #64748B; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{components}</div>
            </div>
            """
            
            # The Arrow (unless it's the last item)
            if idx < len(pa["power_chain"]) - 1:
                chain_html += '<div style="color: #94A3B8; font-weight: 800; font-size: 1.2rem;">➔</div>'
                
        chain_html += '</div>'
        st.markdown(chain_html, unsafe_allow_html=True)
            
        st.info("💡 **Why this matters:** Power chain vulnerabilities propagate to all downstream components. Instability here will invalidate signal-level tests and cause intermittent failures.", icon="⚡")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Bottom Layout
    col_flags, col_tests = st.columns([1, 1], gap="large")
    
    with col_flags:
        # --- Risk Flags ---
        st.markdown("### Risk Flags")
        if bom_data["risk_flags"]:
            for i, flag in enumerate(bom_data["risk_flags"]):
                components = ", ".join(flag["components"]) if flag["components"] else ""
                comp_text = f" | Components: **{components}**" if components else ""
                icon = "✕" if flag['severity'] == "HIGH" else "!"
                color = "#EF4444" if flag['severity'] == "HIGH" else "#F59E0B" if flag['severity'] == "MEDIUM" else "#3B82F6"
                
                st.markdown(f"""
                <div class="clean-list-item">
                    <div class="clean-list-icon" style="color: {color}; border-color: {color}40; background-color: {color}10;">{icon}</div>
                    <div>
                        <div style="margin-bottom: 4px; color: #0F172A;"><strong>[{flag['severity']}] {flag['type']}</strong>{comp_text}</div>
                        <div style="font-size: 0.9em; margin-bottom: 8px;">{flag['message']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f'<div style="margin-bottom: 24px;"><span style="background-color: #F8FAFC; color: #64748B; border: 1px solid #E2E8F0; padding: 2px 8px; border-radius: 9999px; font-size: 0.7rem; font-weight: 500;">{flag["source"]}</span></div>', unsafe_allow_html=True)
        else:
            st.write("No risk flags identified. Board design looks well-structured.")

        # --- Stress Checks ---
        if analysis["stress_checks"]:
            st.markdown("### Component Stress Checks")
            for j, sc in enumerate(analysis["stress_checks"]):
                icon = "!"
                color = "#F59E0B"
                st.markdown(f"""
                <div class="clean-list-item">
                    <div class="clean-list-icon" style="color: {color}; border-color: {color}40; background-color: {color}10;">{icon}</div>
                    <div>
                        <div style="margin-bottom: 4px; color: #0F172A;"><strong>{sc['component']}</strong>: {sc['issue']}</div>
                        <div style="font-size: 0.9em; margin-bottom: 8px;"><em>Recommendation:</em> {sc['recommendation']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f'<div style="margin-bottom: 24px;"><span style="background-color: #F8FAFC; color: #64748B; border: 1px solid #E2E8F0; padding: 2px 8px; border-radius: 9999px; font-size: 0.7rem; font-weight: 500;">{sc["source"]}</span></div>', unsafe_allow_html=True)

    with col_tests:
        # --- Component table ---
        st.markdown("### Component Breakdown")
        comp_df = pd.DataFrame(bom_data["components"])
        display_cols = ["reference", "value", "category", "power_relevance"]
        st.dataframe(comp_df[display_cols], use_container_width=True, height=250, hide_index=True)

        # --- Test Priorities Preview ---
        st.markdown("### Recommended Test Priorities")
        st.caption("Full test plan available on the Test Plan page →")
        for tp in analysis["test_priorities"][:3]:
            st.markdown(f"""
            <div class="clean-list-item">
                <div class="clean-list-icon">⚡</div>
                <div>
                    <div style="margin-bottom: 4px; color: #0F172A;"><strong>Priority {tp['priority']}: {tp['area']}</strong></div>
                    <div style="font-size: 0.9em; margin-bottom: 4px;"><strong>Why:</strong> {tp['reason']}</div>
                    <div style="font-size: 0.9em;"><strong>Tests:</strong> {", ".join(tp['tests'][:2])}...</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    # --- Export Report ---
    st.markdown("---")
    from datetime import datetime
    
    report_lines = [
        f"# CircuitSense — Board Analysis Report",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Source BOM**: {bom_source}\n",
        
        "## Board Summary",
        f"- **Total Components**: {summary['total_components']}",
        f"- **Power-Critical Components**: {summary['power_critical_count']}",
        f"- **Overall Design Risk**: {comp_risk}\n",
        
        "## Power Subsystem Assessment",
        f"- **Topology**: {analysis['power_analysis']['topology']}",
        f"- **Regulator Count**: {analysis['power_analysis']['regulator_count']}\n",
    ]
    
    if bom_data["risk_flags"]:
        report_lines.append("## Risk Flags")
        for flag in bom_data["risk_flags"]:
            comps = f" ({', '.join(flag['components'])})" if flag['components'] else ""
            report_lines.append(f"- **[{flag['severity']}]** {flag['type']}{comps}: {flag['message']}")
        report_lines.append("")
        
    if analysis["stress_checks"]:
        report_lines.append("## Component Stress Checks")
        for sc in analysis["stress_checks"]:
            report_lines.append(f"- **{sc['component']}**: {sc['issue']}")
            report_lines.append(f"  - *Recommendation*: {sc['recommendation']}")
        report_lines.append("")
        
    report_lines.append("## Recommended Test Priorities")
    for tp in analysis["test_priorities"]:
        report_lines.append(f"### Priority {tp['priority']}: {tp['area']}")
        report_lines.append(f"**Rationale**: {tp['reason']}\n**Tests**:")
        for t in tp["tests"]:
            report_lines.append(f"- {t}")
        report_lines.append(f"\n**Instruments**: {tp['instruments']}")
        report_lines.append(f"**Pass Criteria**: {tp['pass_criteria']}\n")
        
    report_lines.append("---\n*Report generated by CircuitSense AI Test Co-pilot*")
    
    st.download_button(
        "Export Full Report",
        data="\n".join(report_lines),
        file_name=f"circuitsense_board_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
        use_container_width=True,
    )

else:
    st.info("Upload a BOM CSV file to get started.")
    st.markdown("""
    **Expected CSV format:**
    | Reference | Value | Description | Quantity | Package | Manufacturer |
    |---|---|---|---|---|---|
    | U1 | LM7805 | 5V Voltage Regulator | 1 | TO-220 | Texas Instruments |
    | C1 | 100uF | Electrolytic Capacitor | 1 | Radial | Nichicon |
    """)
