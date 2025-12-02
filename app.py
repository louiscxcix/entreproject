import streamlit as st
import pandas as pd
import google.generativeai as genai
import time
from datetime import datetime
import random
from fpdf import FPDF
from duckduckgo_search import DDGS

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(
    page_title="BarnaInsights: Pikio Taco",
    page_icon="🌮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .stApp { background-color: #0f172a; font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4, p, label, span, div { color: #f8fafc; }
    .header-card {
        background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px;
        padding: 2rem; margin-bottom: 2rem; text-align: center;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #f8fafc !important; border-radius: 16px; padding: 2rem !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] * { color: #1e293b !important; }
    div.stButton > button {
        background-color: #e2e8f0 !important; color: #0f172a !important; border: 1px solid #cbd5e1 !important;
    }
    div.row-widget.stButton > button[kind="primary"] {
        background-color: #3b82f6 !important; color: white !important; border: none !important;
    }
    .stTextInput input, .stFileUploader button { background-color: #ffffff !important; color: #1e293b !important; }
    .vertical-divider { border-left: 1px solid rgba(255, 255, 255, 0.2); height: 100%; min-height: 400px; margin: 0 auto; }
    div[data-testid="stDecoration"] { visibility: hidden; }
    header[data-testid="stHeader"] { background-color: #0f172a !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. RESTAURANT PROFILE ---
RESTAURANT_PROFILE = {
    "name": "Pikio Taco",
    "address": "Carrer de Còrsega, 376, L'Eixample",
    "neighborhood": "L'Eixample",
    "cuisine": "Mexican / Taqueria",
    "rating": "4.5",
    "menu_items": "TACOS (3.90€): Carnitas, Birria (Spicy), Campechano. ENTRANTES: Nachos Pikio (12.50€), Tostada (5€). QUESADILLAS (9.90€)."
}

# --- 3. STATE MANAGEMENT ---
if 'external_report' not in st.session_state: st.session_state.external_report = ""
if 'internal_report' not in st.session_state: st.session_state.internal_report = ""
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = ""
if 'pdf_content' not in st.session_state: st.session_state.pdf_content = ""
if 'chat_history' not in st.session_state: st.session_state.chat_history = [] 
if 'opp_score' not in st.session_state: st.session_state.opp_score = 50

# --- 4. CORE AI ENGINE (OPTIMIZED FOR COST) ---

def call_cheap_ai(api_key, prompt):
    """
    Uses 'gemini-1.5-flash'. This is the most cost-effective model (~$0.075/1M tokens).
    Does NOT use the expensive 'pro' model.
    """
    genai.configure(api_key=api_key)
    try:
        # 1. Try the cheapest model first
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model.generate_content(prompt).text
    except Exception as e:
        error_msg = str(e)
        # 2. Handle the "Not Found" error specifically
        if "404" in error_msg and "models/" in error_msg:
            return "❌ CRITICAL ERROR: Your google-generativeai library is too old. Please run: pip install -U google-generativeai"
        return f"AI Error: {error_msg}"

def get_real_world_data(query):
    """
    Uses DuckDuckGo (Free) instead of Google Search API (Paid).
    """
    try:
        # Search for max 3 results to keep prompt size small (saves money)
        results = DDGS().text(query, max_results=3)
        if not results: return "No data found."
        # Combine into a string
        evidence = ""
        for r in results:
            evidence += f"- {r['body']}\n"
        return evidence
    except Exception as e: 
        return f"Search Unavailable: {str(e)}"

# --- 5. REPORT GENERATORS ---

@st.cache_data(ttl=900) # Cache for 15 mins to save money on API calls
def fetch_external_intelligence(api_key):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 1. Get raw data from the web (Python does this, $0 cost)
    with st.spinner("🛰️ Scanning Free Web Signals..."):
        weather = get_real_world_data(f"current weather Barcelona {current_time} rain forecast")
        events = get_real_world_data(f"events Barcelona today {datetime.now().strftime('%Y-%m-%d')} concerts match")
        trends = get_real_world_data("Barcelona food trends popular restaurants this week")

    # 2. Send small prompt to Cheap AI
    prompt = f"""
    ROLE: Intelligence Officer for {RESTAURANT_PROFILE['name']}.
    DATA: 
    [WEATHER] {weather} 
    [EVENTS] {events} 
    [TRENDS] {trends}
    
    TASK: 
    1. Summarize the weather and major events (Max 100 words).
    2. END with "SCORE: X" (0-100).
       - Rain/Storm = High Score (Delivery demand).
       - Big Match/Concert = High Score (Footfall).
       - Quiet = Low Score.
    """
    
    text = call_cheap_ai(api_key, prompt)
    
    # Extract Score manually to save AI tokens
    score = 50 
    if "SCORE:" in text:
        try:
            score_part = text.split("SCORE:")[1].strip().split()[0]
            score = int(''.join(filter(str.isdigit, score_part)))
            text = text.split("SCORE:")[0] # Remove score from text display
        except: pass
    return text, score

def analyze_internal_data(api_key, df):
    # Limit rows to 1000 to prevent hitting paid token tiers
    csv_text = df.head(1000).to_csv(index=False)
    
    prompt = f"""
    ACT AS: Cost-Efficient Menu Engineer. 
    DATA (First 1000 rows): {csv_text}
    
    TASK: Audit the menu. Cite specific numbers.
    1. 🐂 **Plowhorses**: Highest volume items.
    2. 🐕 **Dogs**: Lowest volume items.
    3. 🧩 **The Gap**: What items are rarely bought together?
    4. ⏰ **Peak Warning**: Busiest hour.
    """
    return call_cheap_ai(api_key, prompt)

def run_strategic_analysis(api_key):
    prompt = f"""
    ACT AS: Strategy Consultant.
    CONTEXT: {st.session_state.external_report}
    INTERNAL: {st.session_state.internal_report}
    SCORE: {st.session_state.opp_score}/100
    
    TASK: Output 2 parts separated by |||SPLIT|||.
    
    PART 1: Mobile App Summary
    - 4 Emoji Bullet points (Exec Summary, Revenue, Ops, Marketing).
    
    PART 2: PDF Deep Dive (Professional)
    - Situation Analysis
    - Data Evidence (Cite the internal data)
    - Roadmap
    """
    text = call_cheap_ai(api_key, prompt)
    
    if "|||SPLIT|||" in text:
        parts = text.split("|||SPLIT|||")
        return parts[0].strip(), parts[1].strip()
    return text, text

def create_pdf(report_text):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 16)
            self.cell(0, 10, f'Pikio Taco Strategy', 0, 1, 'L')
            self.line(10, 20, 200, 20)
            self.ln(10)
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    
    # Clean text for PDF compatibility
    clean_text = report_text.replace("**", "").replace("##", "")
    replacements = {'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2013': '-', '€': 'EUR '}
    for k, v in replacements.items(): clean_text = clean_text.replace(k, v)
    
    pdf.multi_cell(0, 6, txt=clean_text.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

def ask_executive_chat(api_key, q):
    prompt = f"CONTEXT: {st.session_state.external_report} | {st.session_state.internal_report}. Q: {q}. Keep answer short."
    return call_cheap_ai(api_key, prompt)

# --- 6. LAYOUT & INTERFACE ---

st.markdown(f'<div class="header-card"><h1>🌮 BarnaInsights</h1><p>{RESTAURANT_PROFILE["name"]}</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Config")
    api_key = st.text_input("Gemini API Key", type="password")
    st.caption("Using Model: gemini-1.5-flash (Cost-Optimized)")
    
col1, _, col2 = st.columns([1, 0.1, 1])

# LEFT: External Data
with col1:
    with st.container(border=True):
        st.markdown("### 🌍 External Radar")
        if st.button("🔄 Scan Live Signals", use_container_width=True):
            if api_key:
                rep, sc = fetch_external_intelligence(api_key)
                st.session_state.external_report = rep
                st.session_state.opp_score = sc
            else: st.error("Need API Key")
        
        if st.session_state.external_report:
            st.metric("Opp Score", f"{st.session_state.opp_score}/100")
            st.info(st.session_state.external_report)

# RIGHT: Internal Data
with col2:
    st.markdown('<div class="vertical-divider"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("### 📊 Internal Audit")
        f = st.file_uploader("Upload CSV/XLSX", type=['csv', 'xlsx'], label_visibility="collapsed")
        if f:
            try:
                df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f, engine='openpyxl')
                if st.button("🔍 Run Audit", use_container_width=True):
                    if api_key:
                        with st.spinner("Auditing (Low Cost Mode)..."):
                            st.session_state.internal_report = analyze_internal_data(api_key, df)
                    else: st.error("Need API Key")
                if st.session_state.internal_report: st.success(st.session_state.internal_report)
            except Exception as e: st.error(str(e))

# CENTER: Strategy Generation
st.write("")
_, c, _ = st.columns([1,2,1])
with c:
    ready = st.session_state.external_report and st.session_state.internal_report
    if st.button("✨ GENERATE STRATEGY", type="primary", disabled=not ready, use_container_width=True):
        with st.spinner("Synthesizing..."):
            s, l = run_strategic_analysis(api_key)
            st.session_state.analysis_result = s
            st.session_state.pdf_content = l

# RESULTS TABS
if st.session_state.analysis_result:
    st.divider()
    t1, t2 = st.tabs(["📄 Strategy", "🤖 Chat"])
    
    with t1:
        st.markdown(f'<div style="background:rgba(255,255,255,0.1);padding:20px;border-radius:10px;">{st.session_state.analysis_result}</div>', unsafe_allow_html=True)
        if st.session_state.pdf_content:
            st.download_button("📥 Download PDF Report", create_pdf(st.session_state.pdf_content), "Pikio_Strategy.pdf", "application/pdf")
            
    with t2:
        for m in st.session_state.chat_history: st.chat_message(m["role"]).write(m["content"])
        if q := st.chat_input("Ask about the strategy..."):
            st.session_state.chat_history.append({"role":"user", "content":q})
            st.chat_message("user").write(q)
            ans = ask_executive_chat(api_key, q)
            st.chat_message("assistant").write(ans)
            st.session_state.chat_history.append({"role":"assistant", "content":ans})
