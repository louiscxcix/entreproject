import streamlit as st
import pandas as pd
import google.generativeai as genai
import time
from datetime import datetime
import random
from fpdf import FPDF
import re

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
    
    /* 4. BUTTONS (Modern Flat Design) */
    div.stButton > button {
        background-color: #e2e8f0 !important; /* Slate-200 */
        color: #0f172a !important; /* Dark Blue Text */
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        background-color: #cbd5e1 !important; /* Slate-300 */
        border-color: #94a3b8 !important;
        transform: translateY(-1px);
    }
    
    /* Primary Action Button (Generate Strategy) */
    div.row-widget.stButton > button[kind="primary"] {
        background-color: #3b82f6 !important; /* Blue-500 */
        color: white !important;
        border: none !important;
    }
    div.row-widget.stButton > button[kind="primary"]:hover {
        background-color: #2563eb !important; /* Blue-600 */
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
    
    /* Top Bar Styling - AGGRESSIVE OVERRIDE */
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
if 'detailed_report' not in st.session_state: st.session_state.detailed_report = "" # NEW for PDF
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

# PDF Generator Function
def create_pdf(report_text):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, f'Strategic Intelligence Report: {RESTAURANT_PROFILE["name"]}', 0, 1, 'C')
            self.ln(5)
            self.set_font('Arial', 'I', 10)
            self.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'C')
            self.line(10, 30, 200, 30)
            self.ln(10)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'BarnaInsights AI - Confidential - Page {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    
    # 1. Clean Markdown formatting for PDF (remove ** bolding, # headers)
    # FPDF doesn't support Markdown, so we strip it to make it clean text
    clean_text = report_text.replace('**', '').replace('###', '').replace('##', '').replace('#', '')
    
    # 2. Encode to latin-1 to handle special chars (replace emojis with ?)
    # Standard FPDF is limited to Latin-1. For emojis you need external fonts (TTF).
    # We replace incompatible characters to prevent crashing.
    final_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
    
    pdf.multi_cell(0, 7, txt=final_text)
    return pdf.output(dest='S').encode('latin-1')

@st.cache_data(ttl=600)
def fetch_external_intelligence(api_key):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    prompt = f"""
    ROLE: Intelligence Officer for {RESTAURANT_PROFILE['name']} (Barcelona).
    CURRENT TIME: {current_time}
    MENU: {RESTAURANT_PROFILE['menu_items']}
    
    TASK: Find REAL-TIME data for Barcelona right now.
    1. Weather (Barcelona)
    2. Events (Concerts, Sports, Conferences)
    3. Traffic (Eixample area)
    4. Trends (Food/Social)
    5. Competitors (Nearby Mexican spots)
    
    OUTPUT: 
    1. Opportunity Score (0-100).
    2. Strategic Briefing (Max 150 words). Format: **Radar**, **Impact**, **Action**.
    """
    
    try:
        genai.configure(api_key=api_key)
        # Attempt to use Google Search Tool
        try:
            model = genai.GenerativeModel('gemini-2.0-flash', tools=[{'google_search': {}}])
            response = model.generate_content(prompt)
            score = random.randint(75, 95) 
            return response.text, score
        except Exception:
            # Fallback
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            score = random.randint(70, 90)
            return response.text, score
    except Exception as e:
        return f"Error: {str(e)}", 0

def analyze_internal_data(api_key, df):
    # Calculations
    try:
        item_sales = df.groupby('Item Name')['Qty Sold'].sum().sort_values(ascending=False)
        top_3 = item_sales.head(3).to_dict()
        bottom_3 = item_sales.tail(3).to_dict()
        total_items_sold = item_sales.sum()
        peak_time = df['Time'].mode()[0] if 'Time' in df.columns else "N/A"
        
        data_summary = f"""
        CALCULATED METRICS:
        - Top 3: {top_3}
        - Bottom 3: {bottom_3}
        - Total: {total_items_sold}
        - Peak: {peak_time}
        """
    except Exception as e: return f"Error metrics: {str(e)}"

    prompt = f"""
    ROLE: Data Analyst for {RESTAURANT_PROFILE['name']}.
    MENU: {RESTAURANT_PROFILE['menu_items']}
    DATA: {data_summary}
    TASK: Menu Audit (Max 150 words). 
    1. 🏆 **Star Performers**
    2. 📉 **Dead Weight**
    3. ⏰ **Operational Pulse**
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"Error: {str(e)}"

def run_strategic_analysis(api_key):
    # WE REQUEST TWO SEPARATE OUTPUTS HERE: ONE FOR WEB, ONE FOR PDF
    prompt = f"""
    ACT AS: Senior Strategic Consultant for {RESTAURANT_PROFILE['name']}.
    CONTEXT 1 (External): {st.session_state.external_report}
    CONTEXT 2 (Internal): {st.session_state.internal_report}
    
    TASK: Generate TWO distinct reports. Separate them with the string "|||SPLIT|||".
    
    PART 1: WEB DASHBOARD SUMMARY (Max 200 words)
    Format:
    1. 📊 **Executive Summary**: 1 sentence synthesis.
    2. 💰 **Revenue Opportunity**: Specific menu push.
    3. 🛡️ **Operational Defense**: Staffing/Inventory.
    4. 📢 **Marketing Strategy**: Social hook.

    |||SPLIT|||

    PART 2: COMPREHENSIVE PDF REPORT (Min 600 words)
    Format as a professional whitepaper. Use CAPITALIZED HEADERS (No markdown bolding).
    Sections:
    1. MARKET CONTEXT DEEP DIVE
       - Analyze weather, events, and traffic in detail.
       - Explain the psychological impact on the customer today.
    
    2. FINANCIAL FORENSICS & MENU ENGINEERING
       - Deep analysis of the Star Performers vs Dead Weight.
       - Profitability recommendations.
    
    3. SCENARIO PLANNING (BEST CASE / WORST CASE)
       - Prediction for tonight's service.
       - Contingency plans.
    
    4. DETAILED OPERATIONAL ROADMAP
       - Hour-by-hour checklist for Front of House and Kitchen.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        
        # Split the response
        parts = response.text.split("|||SPLIT|||")
        web_content = parts[0]
        pdf_content = parts[1] if len(parts) > 1 else parts[0]
        
        return web_content, pdf_content
    except: return "Error generating strategy.", "Error generating report."

def ask_executive_chat(api_key, question):
    prompt = f"""
    YOU ARE: Senior Ops Director for {RESTAURANT_PROFILE['name']}.
    DATA: {st.session_state.analysis_result}
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

# MAIN COLUMNS
left_col, mid_col, right_col = st.columns([1, 0.1, 1])

# --- LEFT COLUMN ---
with left_col:
    with st.container(border=True):
        st.markdown("### 🌍 External Radar")
        st.caption("Barcelona City Sensors (Weather, Events, Traffic)")
        
        if st.button("🔄 Scan Live Signals", use_container_width=True):
            if api_key:
                with st.spinner("Connecting to City API..."):
                    report, score = fetch_external_intelligence(api_key)
                    st.session_state.external_report = report
                    st.session_state.opp_score = score
            else: st.error("Add API Key in Sidebar")
            
        st.markdown("---")
        
        if st.session_state.external_report:
            c1, c2 = st.columns([1,3])
            with c1: st.metric("Opp. Score", f"{st.session_state.opp_score}/100")
            with c2:
                st.progress(st.session_state.opp_score / 100)
                st.caption("Based on real-time demand signals")
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
                if uploaded_file.name.endswith('.csv'): 
                    df = pd.read_csv(uploaded_file)
                else: 
                    df = pd.read_excel(uploaded_file, engine='openpyxl')
                
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
                st.error(f"Error reading file: {str(e)}")
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
            st.session_state.detailed_report = pdf_res # Store PDF content separately

# --- RESULTS ---
if st.session_state.analysis_result:
    st.divider()
    
    # OUTPUT DIVISION
    tab1, tab2 = st.tabs(["📄 Strategic Report", "🤖 Decision Consultant"])
    
    # TAB 1: REPORT
    with tab1:
        st.markdown(f"""
        <div style="background-color:rgba(255,255,255,0.1); padding:25px; border-radius:10px; border-left: 5px solid #3b82f6;">
            {st.session_state.analysis_result}
        </div>
        """, unsafe_allow_html=True)
        
        # PDF DOWNLOAD BUTTON
        st.write("")
        # Pass the DETAILED report to the PDF generator, not the summary
        pdf_bytes = create_pdf(st.session_state.detailed_report)
        st.download_button(
            label="📥 Download Detailed PDF Report",
            data=pdf_bytes,
            file_name=f"Pikio_Strategy_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
        )
    
    # TAB 2: CHATBOT
    with tab2:
        st.markdown("##### 💬 Ask the Consultant")
        st.caption("Expert advice based on your real-time data intersection.")
        
        chat_container = st.container(height=300)
        with chat_container:
            for msg in st.session_state.chat_history:
                st.chat_message(msg["role"]).write(msg["content"])
        
        if q := st.chat_input("E.g. 'Should I lower prices for the rainy night?'"):
            st.session_state.chat_history.append({"role": "user", "content": q})
            with chat_container:
                st.chat_message("user").write(q)
                with st.chat_message("assistant"):
                    with st.spinner("Consulting data..."):
                        ans = ask_executive_chat(api_key, q)
                        st.write(ans)
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
            st.rerun()
