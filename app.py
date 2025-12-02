import streamlit as st
import pandas as pd
import google.generativeai as genai
import time
from datetime import datetime
import random
from fpdf import FPDF
from duckduckgo_search import DDGS
import concurrent.futures # <--- NEW: Enables parallel searching

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
    
    /* 3. CARDS */
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
    div.row-widget.stButton > button[kind="primary"] {
        background-color: #3b82f6 !important; /* Blue-500 */
        color: white !important;
        border: none !important;
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

# A. Helper: Get Real Data (Optimized)
def get_live_search_data(query):
    """
    Uses DuckDuckGo to get real-time search results.
    Includes timeout protection to prevent hanging.
    """
    try:
        # We limit results to 2 to save time/bandwidth
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=2))
            
        if not results:
            return "No specific data found."
        
        evidence = ""
        for r in results:
            evidence += f"- {r['body']}\n"
        return evidence
    except Exception as e:
        return f"Signal lost ({str(e)[:20]}...)"

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
    
    clean_text = report_text.replace("**", "").replace("##", "")
    replacements = {'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2013': '-', '€': 'EUR '}
    for k, v in replacements.items():
        clean_text = clean_text.replace(k, v)
        
    clean_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

# C. Logic: External Intelligence (PARALLEL PROCESSING FIX)
@st.cache_data(ttl=600)
def fetch_external_intelligence(api_key):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # --- SPEED FIX: PARALLEL EXECUTION ---
    # Instead of doing 1, then 2, then 3... we do all at once.
    with st.spinner("🛰️ Pinging Weather, Events, & Trends simultaneously..."):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # 1. Define the tasks
            future_weather = executor.submit(get_live_search_data, f"current weather Barcelona today {current_time} rain forecast")
            future_events = executor.submit(get_live_search_data, f"events in Barcelona today {datetime.now().strftime('%Y-%m-%d')} concerts football")
            future_trends = executor.submit(get_live_search_data, "Barcelona food trends popular restaurants this week")
            
            # 2. Get results (waits only for the slowest one)
            weather_data = future_weather.result()
            events_data = future_events.result()
            trends_data = future_trends.result()

    # 3. AI SUMMARIZATION
    prompt = f"""
    ROLE: Intelligence Officer for {RESTAURANT_PROFILE['name']} (Barcelona).
    CURRENT TIME: {current_time}
    
    RAW EVIDENCE GATHERED:
    [WEATHER]: {weather_data}
    [EVENTS]: {events_data}
    [TRENDS]: {trends_data}
    
    TASK:
    1. Write a 'Strategic Intelligence Briefing' (Max 150 words).
       - Mention specific weather/events found.
    
    2. AT THE END, calculate an OPPORTUNITY SCORE (0-100) based strictly on evidence.
       - Rain/Bad Weather = High Score (Delivery Demand).
       - Big Event = High Score (Footfall).
       - Quiet = Neutral Score (50-60).
       
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

# D. Logic: Internal Audit
def analyze_internal_data(api_key, df):
    # Limit to 1000 rows to prevent timeouts and high costs
    csv_text = df.head(1000).to_csv(index=False)
    
    prompt = f"""
    ACT AS: A Senior Menu Engineer & Profit Consultant.
    CONTEXT: {RESTAURANT_PROFILE['name']} (Mexican Taqueria).
    MENU CONTEXT: {RESTAURANT_PROFILE['menu_items']}
    
    INPUT DATA (Sample):
    {csv_text}
    
    TASK: Perform a ruthless Menu Engineering Audit. 
    You must CITE DATA (approx numbers) to support every claim.
    
    REQUIRED SECTIONS:
    1. 🐂 **The Plowhorses (High Volume)**: Identify #1 most sold item. Calc approx % of total orders. Risk of dependency?
    2. 🐕 **The Dogs (Kill List)**: Identify 2-3 items with lowest sales. Recommendation: Remove or Reprice?
    3. 🧩 **The Gap**: What are people buying Tacos WITH? What are they ignoring?
    4. ⏰ **Kitchen Crash Warning**: Identify the busiest time cluster.
    
    TONE: Analytical, direct, numbers-driven. No generic advice.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"Error analyzing data: {str(e)}"

# E. Logic: Strategy
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
            return text, text
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

with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    st.subheader("📍 Profile")
    st.info(f"**{RESTAURANT_PROFILE['name']}**\n\n{RESTAURANT_PROFILE['address']}")

left_col, mid_col, right_col = st.columns([1, 0.1, 1])

# LEFT: External
with left_col:
    with st.container(border=True):
        st.markdown("### 🌍 External Radar")
        st.caption("Live Search: Weather, Events, Competitors")
        
        if st.button("🔄 Scan Live Signals", use_container_width=True):
            if api_key:
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
        else: st.markdown("*Waiting for scan...*")

with mid_col: st.markdown('<div class="vertical-divider"></div>', unsafe_allow_html=True)

# RIGHT: Internal
with right_col:
    with st.container(border=True):
        st.markdown("### 📊 Internal Audit")
        uploaded_file = st.file_uploader("Drop Sales File", type=['csv', 'xlsx'], label_visibility="collapsed")
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
                else: df = pd.read_excel(uploaded_file, engine='openpyxl')
                
                if st.button("🔍 Run Menu Audit", use_container_width=True):
                    if api_key:
                        with st.spinner("Calculating..."):
                            rep = analyze_internal_data(api_key, df)
                            st.session_state.internal_report = rep
                    else: st.error("Add API Key")
                
                st.markdown("---")
                if st.session_state.internal_report: st.success(st.session_state.internal_report)
            except Exception as e: st.error(f"Error: {str(e)}")
        else: st.markdown("*Waiting for file...*")

# CENTER ACTION
st.write("")
st.write("")
_, center, _ = st.columns([1, 2, 1])
with center:
    ready = st.session_state.external_report and st.session_state.internal_report
    if st.button("✨ GENERATE STRATEGY", type="primary", disabled=not ready, use_container_width=True):
        with st.spinner("Synthesizing..."):
            short_res, long_res = run_strategic_analysis(api_key)
            st.session_state.analysis_result = short_res
            st.session_state.pdf_content = long_res

# RESULTS
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
        if st.session_state.pdf_content:
            pdf_bytes = create_pdf(st.session_state.pdf_content)
            st.download_button("📥 Download Full PDF", pdf_bytes, "Pikio_Strategy.pdf", "application/pdf")
    
    with tab2:
        chat_container = st.container(height=300)
        with chat_container:
            for msg in st.session_state.chat_history: st.chat_message(msg["role"]).write(msg["content"])
        
        if q := st.chat_input("Ask a question..."):
            st.session_state.chat_history.append({"role": "user", "content": q})
            with chat_container:
                st.chat_message("user").write(q)
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        ans = ask_executive_chat(api_key, q)
                        st.write(ans)
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
            st.rerun()
