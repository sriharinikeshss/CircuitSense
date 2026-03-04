import streamlit as st
import streamlit_shadcn_ui as ui

def render_top_nav():
    """Renders the top navigation header to replace the sidebar, matching the Shadcn Dashboard reference."""
    st.markdown("""
    <style>
        /* Hide sidebar */
        [data-testid="collapsedControl"] { display: none !important; }
        [data-testid="stSidebar"] { display: none !important; }
        
        .logo-container {
            display: flex;
            align-items: center;
            gap: 12px;
            font-weight: 700;
            font-size: 1.25rem;
            color: #0F172A;
            margin-bottom: 0;
            padding-top: 5px;
        }
        
        .stPageLink a {
            text-decoration: none !important;
            color: #64748B !important;
            font-weight: 500 !important;
        }
        .stPageLink a:hover {
            color: #0F172A !important;
        }
        
        /* Adjust gap for columns */
        [data-testid="column"] {
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        /* Remove top padding without pushing content off-screen */
        .stApp [data-testid="block-container"], 
        .stApp [data-testid="stMainBlockContainer"] {
            padding-top: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        
        /* Hide the default Streamlit top header decoration and toolbar */
        header[data-testid="stHeader"], 
        div[data-testid="stToolbar"] {
            display: none !important;
            visibility: hidden !important;
            height: 0px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    nav_cols = st.columns([2, 6, 2], vertical_alignment="center")
    with nav_cols[0]:
        st.markdown("""
        <div class="logo-container">
            <div style="width: 28px; height: 28px; border-radius: 50%; background: #0F172A; color: white; display: flex; align-items: center; justify-content: center; font-size: 13px;">CS</div>
            CircuitSense
        </div>
        """, unsafe_allow_html=True)
    with nav_cols[1]:
        cl1, cl2, cl3, cl4, cl5, cl6 = st.columns(6)
        with cl1: st.page_link("app.py", label="Overview")
        with cl2: st.page_link("pages/1_Board_Analysis.py", label="Analysis")
        with cl3: st.page_link("pages/2_Test_Plan.py", label="Test Plan")
        with cl4: st.page_link("pages/3_Anomaly_Detection.py", label="Anomalies")
        with cl5: st.page_link("pages/4_Fault_Diagnosis.py", label="Diagnostics")
        with cl6: st.page_link("pages/5_AI_Copilot.py", label="AI Chat")
    with nav_cols[2]:
        pass

    st.markdown("<div style='border-bottom: 1px solid #E2E8F0; margin-top: 8px; margin-bottom: 32px;'></div>", unsafe_allow_html=True)
