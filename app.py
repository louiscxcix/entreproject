import streamlit as st
import pandas as pd
import google.generativeai as genai
import time
from datetime import datetime
import random
from fpdf import FPDF
from duckduckgo_search import DDGS

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
        background-color: #0f172a; /* Slate-900 */
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3, h4, p, label, span, div {
        color: #f8fafc; /* Slate-50 */
    }

    /* 2. HEADER BANNER */
    .header-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    /* 3. CARDS (Silver/White Look) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #f8fafc !important; 
        border: none !important;
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        padding: 2rem !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] * {
        color: #1e293b !important; /* Dark Text inside cards */
    }
    
    /* 4. BUTTONS */
    div.stButton > button {
        background-color: #e2e8f0 !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    div.stButton > button:hover {
        background-color: #cbd5e1 !important;
        transform: translateY(-1px);
    }
    /* Primary Action Button */
    div.row-widget.stButton > button[kind="primary"] {
        background-color: #3b82f6 !important; /* Blue-500 */
        color: white !important;
        border: none !important;
    }
    div.row-widget.stButton > button[kind="primary"]:hover {
        background-color: #2563eb !important;
    }

    /* 5. INPUTS & DIVIDERS */
    .stTextInput input, .stFileUploader button {
        background-color: #ffffff !important;
        color: #1e293b !important;
    }
    .vertical-divider {
        border-left: 1px solid rgba(255, 255, 255, 0.2);
        height: 100%;
        min-height: 400px;
        margin: 0 auto;
    }
    
    /* Hide Streamlit Decorations */
    div[data-testid="stDecoration"] { visibility: hidden; }
    header[data-testid="stHeader"] { background-color: #0f172a !important; }
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
if 'pdf_content' not in st.session_state: st.session_state.pdf_content = ""
if 'chat_history' not in st.session_state: st.session_state.chat_history = [] 
if 'opp_score' not in st.session_state: st.session_state.opp_score = 50

# --- 5. LOGIC FUNCTIONS ---

# A. Helper: Get Real Data (DuckDuckGo)
def get_live_search_data(query):
    """
    Uses DuckDuckGo to get real-time search results (No Hallucinations).
    """
    try:
        # Simple text search, returning top 3 results
        results = DDGS().text(query, max_results=3)
        if not results:
            return "No specific data found."
        
        evidence = ""
        for r in results:
            evidence += f"- {r['body']}\n"
        return evidence
    except Exception as e:
        return f"Search Signal Weak ({str(e)})"

# B. Helper: Create PDF
def create_pdf(report_text):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 20)
            self.cell(0, 10, f'Pikio Taco: Intelligence Report', 0, 1, 'L')
            self.set_font('Arial', 'I', 10)
            self.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'L')
            self.line(10, 30, 200, 30)
            self.ln(10)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'BarnaInsights AI - Page {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Strategic Deep Dive & Execution Plan", 0, 1)
    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    
    # Text Cleanup for FPDF (Latin-1 handling)
    clean_text = report_text.replace("**", "").replace("##", "")
    # Replace common smart quotes that break PDF generation
    replacements = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', 
        '\u2013': '-', '\u2014': '-', '€': 'EUR '
    }
    for k, v in replacements.items():
        clean_text = clean_text.replace(k, v)
        
    clean_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

# C. Logic: External Intelligence (RAG)
@st.cache_data(ttl=600)
def fetch_external_intelligence(api_key):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 1. SEARCH REALITY (Python Only)
    with st.spinner("🛰️ Pinging Weather Satellites & Event Feeds..."):
        weather_data = get_live_search_data(f"current weather Barcelona today {current_time} rain forecast")
        events_data = get_live_search_data(f"events in Barcelona today {datetime.now().strftime('%Y-%m-%d')} concerts football festivals")
        trends_data = get_live_search_data("Barcelona food trends popular restaurants this week")

    # 2. AI SUMMARIZATION (No Lying Allowed)
    prompt = f"""
    ROLE: Intelligence Officer for {RESTAURANT_PROFILE['name']} (Barcelona).
    CURRENT TIME: {current_time}
    
    RAW EVIDENCE GATHERED (Use ONLY this):
    [WEATHER]: {weather_data}
    [EVENTS]: {events_data}
    [TRENDS]: {trends_data}
    
    TASK:
    1. Write a 'Strategic Intelligence Briefing' (Max 150 words).
       - Be concise. Mention the specific weather and any specific events found.
    
    2. AT THE END, calculate an OPPORTUNITY SCORE (0-100) based strictly on evidence.
       - Rain/Bad Weather = High Score (Delivery Demand).
       - Big Event (Concert/Match) = High Score (Footfall).
       - Quiet/Nice Day = Neutral Score (50-60).
       
    OUTPUT FORMAT:
    [Your Briefing]
    SCORE: [Number]
    """
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text_response = response.text
        
        # Parse Score
        score = 50 
        if "SCORE:" in text_response:
            try:
                score_part = text_response.split("SCORE:")[1].strip().split()[0]
                score = int(''.join(filter(str.isdigit, score_part)))
                text_response = text_response.split("SCORE:")[0]
            except: pass
                
        return text_response, score

    except Exception as e:
        return f"Error connecting to AI: {str(e)}", 0

# D. Logic: Internal Audit (Ruthless Menu Engineer)
def analyze_internal_data(api_key, df):
    csv_text = df.head(1500).to_csv(index=False)
    
    prompt = f"""
    ACT AS: A Senior Menu Engineer & Profit Consultant.
    CONTEXT: {RESTAURANT_PROFILE['name']} (Mexican Taqueria).
    MENU CONTEXT: {RESTAURANT_PROFILE['menu_items']}
    
    INPUT DATA (First 1500 rows of POS data):
    {csv_text}
    
    TASK: Perform a ruthless Menu Engineering Audit. 
    You must CITE DATA (approx numbers) to support every claim.
    
    REQUIRED SECTIONS:
    1. 🐂 **The Plowhorses (High Volume)**: Identify #1 most sold item. Calc approx % of total orders. Risk of dependency?
    2. 🐕 **The Dogs (Kill List)**: Identify 2-3 items with lowest sales. Recommendation: Remove or Reprice?
    3. 🧩 **The Gap**: What are people buying Tacos WITH? What are they ignoring? (e.g. "High Tacos, Low Drinks").
    4. ⏰ **Kitchen Crash Warning**: Identify the busiest time cluster in the data. One operational tip for that hour.
    
    TONE: Analytical, direct, numbers-driven. No generic advice.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"Error analyzing data: {str(e)}"

# E. Logic: Strategy (Split Output)
def run_strategic_analysis(api_key):
    prompt = f"""
    ACT AS: Senior Strategic Consultant for {RESTAURANT_PROFILE['name']}.
    CONTEXT 1 (External): {st.session_state.external_report}
    CONTEXT 2 (Internal): {st.session_state.internal_report}
    CONTEXT 3 (Opp Score): {st.session_state.opp_score}/100
    
    TASK: Generate a Strategic Response in TWO PARTS.
    
    --- PART 1: APP SUMMARY (Mobile View) ---
    Format: 4 Bullet Points (Exec Summary, Revenue Opp, Ops Defense, Marketing).
    Constraint: Concise, emoji-heavy, under 200 words.
    
    --- PART 2: DETAILED PDF REPORT (Download) ---
    Format: Professional Business Memo.
    Structure:
    1. **Situation Analysis**: Why weather/events today create a specific market condition.
    2. **Data Evidence**: Cite numbers from the Internal Audit (Context 2).
    3. **Implementation Roadmap**: Step-by-step for staff tonight.
    4. **Financial Projection**: Estimated impact.
    Constraint: Professional, detailed, NO emojis, approx 500 words.
    
    REQUIRED OUTPUT FORMAT:
    [Insert Part 1 Content]
    |||SPLIT|||
    [Insert Part 2 Content]
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text
        
        if "|||SPLIT|||" in text:
            parts = text.split("|||SPLIT|||")
            return parts[0].strip(), parts[1].strip()
        else:
            return text, text # Fallback
    except Exception as e: return "Error.", f"Error: {str(e)}"

def ask_executive_chat(api_key, question):
    prompt = f"""
    YOU ARE: Ops Director for {RESTAURANT_PROFILE['name']}.
    DATA:
    [EXTERNAL]: {st.session_state.external_report}
    [INTERNAL]: {st.session_state.internal_report}
    [SCORE]: {st.session_state.opp_score}
    USER ASKED: "{question}"
    Answer strictly based on the data provided. Keep it short.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model.generate_content(prompt).text
    except: return "Error."

# --- 6. MAIN LAYOUT ---

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

# SIDEBAR
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    st.subheader("📍 Profile")
    st.info(f"**{RESTAURANT_PROFILE['name']}**\n\n{RESTAURANT_PROFILE['address']}")
    with st.expander("Show Menu Data"):
        st.caption(RESTAURANT_PROFILE["menu_items"])

# MAIN COLUMNS
left_col, mid_col, right_col = st.columns([1, 0.1, 1])

# --- LEFT COLUMN (EXTERNAL) ---
with left_col:
    with st.container(border=True):
        st.markdown("### 🌍 External Radar")
        st.caption("Live Search: Weather, Events, Competitors")
        
        if st.button("🔄 Scan Live Signals", use_container_width=True):
            if api_key:
                report, score = fetch_external_intelligence(api_key)
                st.session_state.external_report = report
                st.session_state.opp_score = score
            else: st.error("Add API Key in Sidebar")
            
        st.markdown("---")
        
        if st.session_state.external_report:
            c1, c2 = st.columns([1,3])
            with c1: 
                st.metric("Opp. Score", f"{st.session_state.opp_score}/100")
            with c2:
                st.progress(st.session_state.opp_score / 100)
                st.caption("Real-time Demand Potential")
            st.info(st.session_state.external_report)
        else:
            st.markdown("*Waiting for scan...*")

# --- DIVIDER ---
with mid_col:
    st.markdown('<div class="vertical-divider"></div>', unsafe_allow_html=True)

# --- RIGHT COLUMN (INTERNAL) ---
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
                        with st.spinner("Calculating Margins & Trends..."):
                            rep = analyze_internal_data(api_key, df)
                            st.session_state.internal_report = rep
                    else: st.error("Add API Key")
                
                st.markdown("---")
                if st.session_state.internal_report:
                    st.success(st.session_state.internal_report)
            except Exception as e:
                st.error(f"File Error: {str(e)}")
        else:
            st.markdown("*Waiting for file...*")

# --- ACTION SECTION ---
st.write("")
st.write("")
_, center, _ = st.columns([1, 2, 1])
with center:
    ready = st.session_state.external_report and st.session_state.internal_report
    if st.button("✨ GENERATE UNIFIED STRATEGY", type="primary", disabled=not ready, use_container_width=True):
        with st.spinner("Synthesizing Intelligence (Drafting Brief & Full Report)..."):
            short_res, long_res = run_strategic_analysis(api_key)
            st.session_state.analysis_result = short_res
            st.session_state.pdf_content = long_res

# --- RESULTS ---
if st.session_state.analysis_result:
    st.divider()
    
    tab1, tab2 = st.tabs(["📄 Strategic Report", "🤖 Decision Consultant"])
    
    with tab1:
        # 1. SCREEN VERSION
        st.markdown(f"""
        <div style="background-color:rgba(255,255,255,0.1); padding:25px; border-radius:10px; border-left: 5px solid #3b82f6;">
            {st.session_state.analysis_result}
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        
        # 2. PDF VERSION (LONG)
        if st.session_state.pdf_content:
            pdf_bytes = create_pdf(st.session_state.pdf_content)
            st.download_button(
                label="📥 Download Full Executive Report (PDF)",
                data=pdf_bytes,
                file_name=f"Pikio_Strategy_DeepDive_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
            )
    
    with tab2:
        st.markdown("##### 💬 Ask the Consultant")
        chat_container = st.container(height=300)
        with chat_container:
            for msg in st.session_state.chat_history:
                st.chat_message(msg["role"]).write(msg["content"])
        
        if q := st.chat_input("Ex: 'How do I execute the marketing idea?'"):
            st.session_state.chat_history.append({"role": "user", "content": q})
            with chat_container:
                st.chat_message("user").write(q)
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        ans = ask_executive_chat(api_key, q)
                        st.write(ans)
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
            st.rerun()
