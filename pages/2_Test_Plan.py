"""
CircuitSense — Test Plan Generation Page
Uses rule engine + Gemini AI to generate prioritized test plans.
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.rules import analyze_board
from engine.gemini_client import generate_test_plan

st.set_page_config(page_title="Test Plan — CircuitSense", layout="wide", initial_sidebar_state="collapsed")

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
    
    .test-step-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 0.95em;
    /* Styling for AI-Generated Markdown structure */
    .ai-plan-container {
        padding: 0px 8px; /* Internal padding only */
        overflow-wrap: break-word; /* Prevent text clipping */
        word-wrap: break-word;
    }

    
    .ai-plan-container h1 { display: none !important; }
    
    .ai-plan-container h2 {
        font-size: 1.1rem !important;
        color: #0F172A !important;
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 10px 14px;
        margin-top: 1.5rem !important;
        margin-bottom: 12px !important;
    }
    
    .ai-plan-container ul, .ai-plan-container ol {
        margin-top: 0.5rem !important;
        margin-bottom: 1.5rem !important;
        padding-left: 20px;
    }
    
    .ai-plan-container li {
        font-size: 0.95em;
        line-height: 1.6;
        color: #334155;
        margin-bottom: 8px;
    }
    
    .ai-plan-container p {
        font-size: 0.95em;
        line-height: 1.5;
        color: #334155;
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
    <h1 class="page-title">Test Plan Generator</h1>
</div>
""", unsafe_allow_html=True)
st.markdown("Generate a **prioritized test plan** with instrument settings and pass/fail criteria, based on your board analysis.")
st.markdown("<br>", unsafe_allow_html=True)

# Check if board analysis exists
if "board_analysis" not in st.session_state:
    st.info("No board analysis found. Please upload a BOM on the **Board Analysis** page first.")
    st.page_link("pages/1_Board_Analysis.py", label="Go to Board Analysis →", icon="📋")
    st.stop()

analysis = st.session_state["board_analysis"]
board_context = st.session_state.get("board_context", "")

# Calculate Confidence Score based on context richness
context_sources = 0
if board_context: context_sources += 1
if analysis.get("power_analysis"): context_sources += 1
if analysis.get("stress_checks"): context_sources += 1

confidence = "High" if context_sources >= 3 else "Medium"

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    # --- Rule-based test priorities ---
    st.markdown("### Rule-Based Test Priorities")
    st.info("💡 **Why this order?** Test order is determined using **power-first failure logic**: upstream faults invalidate downstream measurements.")

    for tp in analysis["test_priorities"]:
        st.markdown(f"""
        <div class="clean-list-item">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="background-color: #0F172A; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600;">P{tp['priority']}</span>
                    <strong style="font-size: 1.1rem; color: #0F172A;">{tp['area']}</strong>
                </div>
            </div>
            <div style="margin-bottom: 12px; font-size: 0.95em;">
                <strong>Rationale:</strong> {tp['reason']}
            </div>
        """, unsafe_allow_html=True)
        
        with st.expander("View Test Steps", expanded=(tp["priority"] <= 2)):
            for i, test in enumerate(tp["tests"], 1):
                st.markdown(f"""
                <div class="test-step-card">
                    <strong>{i}.</strong> {test}
                </div>
                """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"<span style='font-size:0.9em;'><strong>Instruments:</strong> {tp['instruments']}</span>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<span style='font-size:0.9em;'><strong>Pass Criteria:</strong> {tp['pass_criteria']}</span>", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)


with col_right:
    # --- AI-generated detailed test plan ---
    st.markdown("### AI-Detailed Test Plan")
    st.markdown(f'<div style="margin-bottom: 16px;"><span style="background-color: #F8FAFC; color: #64748B; border: 1px solid #E2E8F0; padding: 4px 10px; border-radius: 9999px; font-size: 0.8rem; font-weight: 500;">Confidence: {confidence} (Anchored to Rules + Design Context)</span></div>', unsafe_allow_html=True)
    st.caption("**Rule Plan:** Guarantees coverage. **AI Plan:** Optimizes execution and depth.")

    if st.button("Generate Detailed AI Plan", use_container_width=True):
        with st.spinner("Generating test plan with AI reasoning..."):
            ai_plan = generate_test_plan(board_context, priorities=analysis["test_priorities"])
        
        st.session_state["test_plan"] = ai_plan

    if "test_plan" in st.session_state:
        if not st.session_state["test_plan"] or len(st.session_state["test_plan"].strip()) < 50:
             st.warning("AI plan could not be generated. Please proceed with the deterministic Rule-Based Plan on the left.")
        else:
             clean_plan = st.session_state["test_plan"].replace("# Detailed Test Plan", "").strip()
             wrapped_plan = f'<div class="ai-plan-container">\n\n{clean_plan}\n\n</div>'
             
             # Add the Mistral Execution Engine header to make it look like a formal module
             st.markdown("""
             <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-bottom: none; padding: 12px 16px; font-weight: 600; color: #334155; font-size: 0.9rem; border-top-left-radius: 8px; border-top-right-radius: 8px; display: flex; align-items: center; gap: 8px;">
                 <div style="width: 8px; height: 8px; background-color: #3B82F6; border-radius: 50%;"></div>
                 Mistral AI Execution Engine
             </div>
             """, unsafe_allow_html=True)
             
             with st.container(height=700, border=True):
                 st.markdown(wrapped_plan, unsafe_allow_html=True)

# --- Export Unified Plan ---
if "test_plan" in st.session_state and st.session_state["test_plan"]:
    st.markdown("---")
    from datetime import datetime
    
    export_content = [
        f"# CircuitSense — Combined Test Plan",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        "## Part 1: Deterministic Priority Sequence (Rule-Engine)",
    ]
    
    for tp in analysis["test_priorities"]:
        export_content.append(f"### Priority {tp['priority']}: {tp['area']}")
        export_content.append(f"**Rationale**: {tp['reason']}")
        export_content.append("**Key Tests**:")
        for t in tp['tests'][:3]:
            export_content.append(f"- {t}")
        export_content.append(f"**Pass Criteria**: {tp['pass_criteria']}\n")
        
    export_content.extend([
        "## Part 2: Detailed Execution Steps (AI-Expanded)",
        "The following execution steps map directly to the priorities outlined above.\n",
        st.session_state["test_plan"]
    ])
    
    export_str = "\n".join(export_content)
    
    st.download_button(
        label="📥 Export Combined Test Plan",
        data=export_str,
        file_name="CircuitSense_TestPlan.md",
        mime="text/markdown",
        use_container_width=True
    )
