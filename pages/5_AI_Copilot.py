"""
CircuitSense — AI Co-pilot Chat Page
Conversational interface with board context injection and electronics domain expertise.
"""

import streamlit as st
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.gemini_client import chat_response

st.set_page_config(page_title="AI Co-pilot — CircuitSense", layout="wide", initial_sidebar_state="collapsed")

from nav import render_top_nav
render_top_nav()

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    .stApp { background-color: #FFFFFF; font-family: 'Inter', sans-serif; }
    
    h1, h2, h3, h4, h5, h6 { color: #0F172A !important; font-weight: 700 !important; letter-spacing: -0.5px; }
    p, span, div { color: #334155; }
    
    .stApp [data-testid="stMarkdownContainer"] h3,
    .stApp [data-testid="stMarkdownContainer"] h4 {
        margin-top: 1.5rem !important;
        margin-bottom: 0.5rem !important;
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
    
    [data-testid="block-container"] {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1240px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="top-header">
    <h1 class="page-title">AI Co-pilot</h1>
</div>
""", unsafe_allow_html=True)
st.markdown("Ask anything about your board, test strategy, failure diagnosis, or electronics testing best practices.")
st.markdown("<br>", unsafe_allow_html=True)

# Context indicator
has_board = "board_context" in st.session_state
has_anomaly = "anomaly_results" in st.session_state

if has_board or has_anomaly:
    pills_html = ""
    if has_board:
        comps = st.session_state["bom_data"]["summary"]["total_components"] if "bom_data" in st.session_state else "Loaded"
        pills_html += f'<span style="background-color: #E0E7FF; color: #3730A3; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; margin-right: 8px;">📎 BOM: {comps} Components</span>'
    if has_anomaly:
        anoms = st.session_state["anomaly_results"]["anomaly_count"]
        color = "#FEE2E2" if anoms > 0 else "#DCFCE7"
        text_color = "#991B1B" if anoms > 0 else "#166534"
        pills_html += f'<span style="background-color: {color}; color: {text_color}; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; margin-right: 8px;">📉 Anomalies: {anoms}</span>'
    if "correlation_results" in st.session_state and st.session_state["correlation_results"].get("linked_failures"):
        corrs = len(st.session_state["correlation_results"]["linked_failures"])
        pills_html += f'<span style="background-color: #F3E8FF; color: #6B21A8; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; margin-right: 8px;">🔗 Correlations: {corrs}</span>'
        
    st.markdown(f"""
    <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px 16px; border-radius: 8px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <div style="width: 8px; height: 8px; background-color: #3B82F6; border-radius: 50%;"></div>
            <span style="font-size: 0.9rem; color: #334155; font-weight: 500;">Active RAG Context:</span>
            <div style="margin-left: 8px;">{pills_html}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px 16px; border-radius: 8px; display: flex; align-items: center; gap: 8px; margin-bottom: 24px;">
        <span style="font-size: 0.9rem; color: #64748B;">Tip: Upload a BOM and test data on other pages for context-aware responses.</span>
    </div>
    """, unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": """**Hi! I'm CircuitSense**, your AI testing co-pilot.

I can help you with:
- **Test strategy** — "What should I test first on this board?"
- **Fault diagnosis** — "Why is my output voltage low?"
- **Data interpretation** — "What does this ripple pattern mean?"
- **Best practices** — "How should I set up my oscilloscope for ripple measurement?"

If you've uploaded a BOM or test data on other pages, I'll use that context automatically.

**What would you like to know?**"""
        }
    ]

# Display chat history
st.markdown("---")
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
prompt = st.chat_input("Ask me anything about electronics testing...")

# Suggested prompts
st.markdown("#### Suggested Questions")
suggestion_cols = st.columns(3)
suggestions = [
    "What should I test first on this board?",
    "What are common failure modes for voltage regulators?",
    "How do I measure ripple properly with an oscilloscope?",
    "What could cause intermittent resets in a microcontroller circuit?",
    "How do I calculate power dissipation for a linear regulator?",
    "What's the difference between linear and switching regulators?",
]

selected_suggestion = None
for i, suggestion in enumerate(suggestions):
    with suggestion_cols[i % 3]:
        if st.button(f"{suggestion[:50]}...", key=f"sug_{i}", use_container_width=True):
            selected_suggestion = suggestion

if selected_suggestion:
    prompt = selected_suggestion

if prompt:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get board context
    board_context = st.session_state.get("board_context", "")

    # Add anomaly context if available
    if has_anomaly:
        results = st.session_state["anomaly_results"]
        board_context += f"\n\nANOMALY DATA: {results['anomaly_count']} anomalies detected out of {results['total_points']} measurements using {results['method']}."

    # Generate response
    with st.chat_message("assistant"):
        with st.status("CircuitSense AI formulating response...", expanded=True) as status:
            time.sleep(0.5)
            if has_board or has_anomaly:
                status.update(label="Retrieving active session context...", state="running")
                st.write("✓ Loading Board Analysis & BOM framework...")
                time.sleep(0.8)
                if has_anomaly:
                    st.write("✓ Integrating Anomaly Detection telemetry...")
                    time.sleep(0.7)
            
            status.update(label="Querying electronics knowledge base...", state="running")
            st.write("✓ Synthesizing engineering insights...")
            
            response = chat_response(
                user_message=prompt,
                board_context=board_context,
                chat_history=st.session_state.messages[:-1],
            )
            status.update(label="Response generated", state="complete", expanded=False)
            
        st.markdown(response)

    # Add to history
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
