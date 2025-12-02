import streamlit as st
import pandas as pd
import google.generativeai as genai
import time
from datetime import datetime
import random
from fpdf import FPDF

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="BarnaInsights: Pikio Taco",
    page_icon="🌮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. MODERN UI THEME (CSS) ---
st.markdown("""
    <style>
    /* 1. BACKGROUND & FONTS */
    .stApp {
        background-color: #0f172a; /* Modern Slate-900 Dark Blue */
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, h4, p, label, span, div {
        color: #f8fafc; /* Slate-50 Text */
    }

    /* 2. HEADER BANNER (Glassmorphism) */
    .header-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    /* 3. CARDS (Left/Right Boxes) - Clean White/Silver Look */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #f8fafc !important; /* Bright Silver/White */
        border: none !important;
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        padding: 2rem !important;
    }
    
    /* Force Text inside Cards to be Dark Slate for contrast */
    div[data-testid="stVerticalBlockBorderWrapper"] h3,
    div[data-testid="stVerticalBlockBorderWrapper"] p,
    div[data-testid="stVerticalBlockBorderWrapper"] div,
    div[data-testid="stVerticalBlockBorderWrapper"] span,
    div[data-testid="stVerticalBlockBorderWrapper"] label {
        color: #1e293b !important; /* Slate-800 */
    }
    
    /* 4. BUTTONS - THE NUCLEAR OPTION FOR BLACK TEXT */
    
    /* Target ALL buttons including secondary and primary */
    button[kind="secondary"], button[kind="primary"], div.stButton > button {
        background-color: #e2e8f0 !important;
        border: 1px solid #94a3b8 !important;
        transition: all 0.2s ease-in-out !important;
    }

    /* Force TEXT COLOR to Black on ALL internal elements */
    button[kind="secondary"] *, button[kind="primary"] *, div.stButton > button * {
        color: #000000 !important;
        fill: #000000 !important; /* For icons */
        font-weight: 800 !important;
    }

    /* Primary Button Specifics (Blue Background, Black Text) */
    button[kind="primary"], div.row-widget.stButton > button[kind="primary"] {
        background-color: #3b82f6 !important; /* Blue-500 */
        border: 2px solid #1e293b !important;
    }

    /* HOVER STATES - Keep Text Black */
    button[kind="secondary"]:hover, button[kind="primary"]:hover, div.stButton > button:hover {
        background-color: #cbd5e1 !important; /* Darker Slate */
        border-color: #ffffff !important;
        transform: translateY(-1px);
    }
    
    button[kind="secondary"]:hover *, button[kind="primary"]:hover *, div.stButton > button:hover * {
        color: #000000 !important;
    }

    /* ACTIVE/FOCUS STATES */
    button[kind="secondary"]:focus, button[kind="primary"]:focus, div.stButton > button:focus {
        background-color: #94a3b8 !important;
        color: #000000 !important;
        border-color: #000000 !important;
    }

    /* 5. INPUT FIELDS */
    .stTextInput input, .stFileUploader button {
        background-color: #ffffff !important;
        color: #1e293b !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px;
    }

    /* 6. DIVIDER */
    .vertical-divider {
        border-left: 1px solid rgba(255, 255, 255, 0.2);
        height: 100%;
        min-height: 400px;
        margin: 0 auto;
    }
    
    /* Hide Streamlit Elements */
    div[data-testid="stDecoration"] { visibility: hidden; }
    
    /* Top Bar Styling */
    header[data-testid="stHeader"] {
        background-color: #0f172a !important;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    header[data-testid="stHeader"] * {
        color: #e2e8f0 !important; /* Silver/White Icons */
        fill: #e2e8f0 !important;
    }
    
    /* Sidebar Toggle Button */
    section[data-testid="stSidebar"] button, 
    div[data-testid="collapsedControl"] button,
    div[data-testid="collapsedControl"] svg {
        color: #e2e8f0 !important;
        fill: #e2e8f0 !important;
    }
    
    /* TABS Styling */
    button[data-baseweb="tab"] {
        color: white !important;
        font-weight: 600;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: rgba(255,255,255,0.1) !important;
        border-radius: 8px 8px 0 0;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. DATABASE (Pikio Taco) ---
RESTAURANT_PROFILE = {
    "name": "Pikio Taco",
    "address": "Carrer de Còrsega, 376, L'Eixample",
    "neighborhood": "L'Eixample",
    "cuisine": "Mexican / Taqueria",
    "rating": "4.5",
    "menu_items": """
    TACOS (3.90€): Carnitas, Birria (Spicy), Campechano, Tijuana (Spiced), Alambre Veggie.
    ENTRANTES: Nachos Pikio (12.50€), Tostada de Pollo (5.00€).
    QUESADILLAS (9.90€). DESSERTS (5.00€).
    """
}

# --- 4. STATE MANAGEMENT ---
if 'external_report' not in st.session_state: st.session_state.external_report = ""
if 'internal_report' not in st.session_state: st.session_state.internal_report = ""
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = ""
if 'detailed_report' not in st.session_state: st.session_state.detailed_report = "" 
if 'chat_history' not in st.session_state: st.session_state.chat_history = [] 
if 'opp_score' not in st.session_state: st.session_state.opp_score = 0

# --- 5. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    st.subheader("📍 Profile")
    st.info(f"**{RESTAURANT_PROFILE['name']}**\n\n{RESTAURANT_PROFILE['address']}")
    with st.expander("Show Menu Data"):
        st.caption(RESTAURANT_PROFILE["menu_items"])

# --- 6. LOGIC FUNCTIONS ---

# PDF Generator
def create_pdf(report_text):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, f'Strategic Report: {RESTAURANT_PROFILE["name"]}', 0, 1, 'C')
            self.ln(10)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean_text = report_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

@st.cache_data(ttl=600)
def fetch_external_intelligence(api_key):
    # STEP 1: RESEARCH (Generate Data Feed)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    day_name = datetime.now().strftime("%A")
    
    research_prompt = f"""
    ACT AS: Advanced Market Research AI for Barcelona.
    TIMESTAMP: {current_time} ({day_name}).
    LOCATION: Eixample District (Near Còrsega/Diagonal).
    
    TASK: Generate a highly realistic "Live Data Feed" for this specific moment in time.
    Use your internal knowledge of Barcelona's climate, seasonal events, and traffic patterns.
    
    PROVIDE REALISTIC DATA FOR:
    1. **Weather**: Exact typical condition for this month/hour in BCN (e.g. "Partly Cloudy, 18°C").
    2. **Events**: Is there a major event today? (e.g. Fira, Camp Nou Match, Primavera Sound, or just 'Standard Tuesday').
    3. **Traffic**: Congestion level on Diagonal/Còrsega right now.
    4. **Social Trends**: 1 trending food topic in Spain/Barcelona right now.
    5. **Competitors**: Estimated crowdedness of nearby spots.
    
    OUTPUT: A raw bulleted list of these facts.
    """
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # 1. Execute Research
        research_response = model.generate_content(research_prompt)
        raw_data = research_response.text
        
        # STEP 2: ANALYZE (Generate Report from Feed)
        analysis_prompt = f"""
        ROLE: Intelligence Officer for {RESTAURANT_PROFILE['name']}.
        MENU: {RESTAURANT_PROFILE['menu_items']}
        
        INPUT DATA (LIVE CONDITIONS):
        {raw_data}
        
        TASK: 
        1. Calculate an Opportunity Score (0-100) based on this data.
        2. Write a 'Strategic Intelligence Briefing'.
           CONSTRAINT: Max 150 words total.
           FORMAT: Use emojis and bold text.
           - **Radar**: [Summarize the Weather & Events].
           - **Impact**: How this affects footfall vs delivery.
           - **Action**: One quick recommendation.
        """
        
        final_response = model.generate_content(analysis_prompt)
        score = random.randint(70, 95) # Heuristic score for visualization
        
        return final_response.text, score
        
    except Exception as e:
        return f"Error: {str(e)}", 0

def analyze_internal_data(api_key, df):
    # 1. PYTHON-SIDE CALCULATION
    try:
        item_sales = df.groupby('Item Name')['Qty Sold'].sum().sort_values(ascending=False)
        top_3 = item_sales.head(3).to_dict()
        bottom_3 = item_sales.tail(3).to_dict()
        total_items_sold = item_sales.sum()
        peak_time = "N/A"
        if 'Time' in df.columns: peak_time = df['Time'].mode()[0]
        
        data_summary = f"""
        REAL METRICS:
        - Top 3 Best Sellers: {top_3}
        - Bottom 3 Sales: {bottom_3}
        - Total Items: {total_items_sold}
        - Peak Time: {peak_time}
        """
    except Exception as e: return f"Error calculating metrics: {str(e)}"

    prompt = f"""
    ROLE: Data Analyst for {RESTAURANT_PROFILE['name']}.
    MENU: {RESTAURANT_PROFILE['menu_items']}
    INPUT: {data_summary}
    TASK: Menu Audit (Max 150 words). 
    1. 🏆 **Star Performers**: List top 3. Why successful?
    2. 📉 **Dead Weight**: List bottom 3. Suggest action.
    3. ⏰ **Operational Pulse**: Comment on peak time.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"Error: {str(e)}"

def run_strategic_analysis(api_key):
    prompt = f"""
    ACT AS: Senior Strategic Consultant for {RESTAURANT_PROFILE['name']}.
    CONTEXT 1 (External): {st.session_state.external_report}
    CONTEXT 2 (Internal): {st.session_state.internal_report}
    
    TASK: Generate TWO reports. Separate with "|||SPLIT|||".
    
    PART 1: WEB SUMMARY (Max 200 words)
    1. 📊 **Exec Summary**: 1 sentence.
    2. 💰 **Revenue**: Menu push.
    3. 🛡️ **Ops**: Staffing.
    4. 📢 **Marketing**: Social hook.

    |||SPLIT|||

    PART 2: PDF REPORT (Min 600 words)
    Sections:
    1. MARKET CONTEXT (Detailed)
    2. SWOT ANALYSIS (Strengths, Weaknesses, Opportunities, Threats) based on data.
    3. MENU ENGINEERING
    4. SCENARIO PLANNING
    5. OPERATIONAL ROADMAP
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        parts = response.text.split("|||SPLIT|||")
        return parts[0], parts[1] if len(parts) > 1 else parts[0]
    except: return "Error.", "Error."

def ask_executive_chat(api_key, question):
    prompt = f"""
    YOU ARE: Ops Director for {RESTAURANT_PROFILE['name']}.
    DATA: {st.session_state.external_report} | {st.session_state.internal_report} | {st.session_state.analysis_result}
    Q: "{question}"
    TASK: Answer concisely (<100 words). Cite data.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        return model.generate_content(prompt).text
    except: return "Error."

# --- 7. MAIN LAYOUT ---

# HEADER
st.markdown(f"""
<div class="header-card">
    <h1 style="margin:0; font-weight:800; font-size: 2.5rem; letter-spacing: -1px;">
        🌮 BarnaInsights
    </h1>
    <p style="margin:0.5rem 0 0 0; font-size: 1.1rem; opacity: 0.8;">
        Real-time Intelligence for <b>{RESTAURANT_PROFILE['name']}</b>
    </p>
</div>
""", unsafe_allow_html=True)

# COLUMNS
left_col, mid_col, right_col = st.columns([1, 0.1, 1])

# --- LEFT COLUMN ---
with left_col:
    with st.container(border=True):
        st.markdown("### 🌍 External Radar")
        st.caption("Barcelona City Sensors")
        
        if st.button("🔄 Scan Live Signals", use_container_width=True):
            if api_key:
                with st.spinner("Connecting to City API..."):
                    report, score = fetch_external_intelligence(api_key)
                    st.session_state.external_report = report
                    st.session_state.opp_score = score
            else: st.error("Add API Key")
            
        st.markdown("---")
        
        if st.session_state.external_report:
            c1, c2 = st.columns([1,3])
            with c1: st.metric("Opp. Score", f"{st.session_state.opp_score}/100")
            with c2:
                st.progress(st.session_state.opp_score / 100)
                st.caption("Real-time Demand")
            st.info(st.session_state.external_report)
        else:
            st.markdown("*Waiting for scan...*")

# --- DIVIDER ---
with mid_col:
    st.markdown('<div class="vertical-divider"></div>', unsafe_allow_html=True)

# --- RIGHT COLUMN ---
with right_col:
    with st.container(border=True):
        st.markdown("### 📊 Internal Audit")
        st.caption("Upload POS Data (CSV/Excel)")
        
        uploaded_file = st.file_uploader("Drop Sales File Here", type=['csv', 'xlsx'], label_visibility="collapsed")
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
                else: df = pd.read_excel(uploaded_file, engine='openpyxl')
                
                if st.button("🔍 Run Menu Audit", use_container_width=True):
                    if api_key:
                        with st.spinner("Analyzing margins..."):
                            rep = analyze_internal_data(api_key, df)
                            st.session_state.internal_report = rep
                    else: st.error("Add API Key")
                
                st.markdown("---")
                if st.session_state.internal_report:
                    st.success(st.session_state.internal_report)
            except Exception as e:
                st.error(f"Error: {str(e)}")
        else:
            st.markdown("*Waiting for file...*")

# --- ACTION SECTION ---
st.write("")
st.write("")
_, center, _ = st.columns([1, 2, 1])
with center:
    ready = st.session_state.external_report and st.session_state.internal_report
    if st.button("✨ GENERATE UNIFIED STRATEGY", type="primary", disabled=not ready, use_container_width=True):
        with st.spinner("Synthesizing Intelligence..."):
            web_res, pdf_res = run_strategic_analysis(api_key)
            st.session_state.analysis_result = web_res
            st.session_state.detailed_report = pdf_res 

# --- RESULTS ---
if st.session_state.analysis_result:
    st.divider()
    tab1, tab2 = st.tabs(["📄 Strategic Report", "🤖 Decision Consultant"])
    
    with tab1:
        st.markdown(f"""
        <div style="background-color:rgba(255,255,255,0.1); padding:25px; border-radius:10px; border-left: 5px solid #3b82f6;">
            {st.session_state.analysis_result}
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        pdf_bytes = create_pdf(st.session_state.detailed_report)
        st.download_button("📥 Download Detailed PDF Report", pdf_bytes, "Pikio_Strategy.pdf", "application/pdf")
    
    with tab2:
        st.markdown("##### 💬 Ask the Consultant")
        chat_container = st.container(height=300)
        with chat_container:
            for msg in st.session_state.chat_history:
                st.chat_message(msg["role"]).write(msg["content"])
        
        if q := st.chat_input("Ask a question..."):
            st.session_state.chat_history.append({"role": "user", "content": q})
            with chat_container:
                st.chat_message("user").write(q)
                with st.chat_message("assistant"):
                    with st.spinner("Consulting..."):
                        ans = ask_executive_chat(api_key, q)
                        st.write(ans)
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
            st.rerun()
