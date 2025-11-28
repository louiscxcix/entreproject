import streamlit as st
import pandas as pd
import google.generativeai as genai
import time

# --- 1. Page Config ---
st.set_page_config(
    page_title="BarnaInsights: Pikio Taco",
    page_icon="🌮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. THEME & CSS ---
st.markdown("""
    <style>
    /* GLOBAL SETTINGS */
    .stApp {
        background-color: #053371;
    }
    
    /* --- INTEGRATED TOP BAR --- */
    /* Match the top header bar to the app background */
    header[data-testid="stHeader"] {
        background-color: #053371 !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1); /* Subtle separator */
    }
    
    /* Force icons (Hamburger, Deploy, Github) to be white */
    header[data-testid="stHeader"] button, 
    header[data-testid="stHeader"] svg, 
    header[data-testid="stHeader"] a {
        color: #ffffff !important;
        fill: #ffffff !important;
    }
    
    /* Hide the default multi-colored decoration line at the top */
    div[data-testid="stDecoration"] {
        visibility: hidden;
    }
    /* -------------------------- */
    
    /* HEADER BANNER STYLE */
    .header-banner {
        background-color: #022c5e; /* Darker blue for separation */
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        border-left: 6px solid #3b82f6; /* Accent border */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    
    /* Global Text - White by default for Blue background */
    h1, h2, h3, h4, p, span, div, label {
        color: #ffffff;
    }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #042451;
        border-right: 1px solid #4b5563;
    }
    
    /* SILVER BOXES (Targeting Streamlit Containers with Borders) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(135deg, #f3f4f6 0%, #d1d5db 100%);
        border: 2px solid #9ca3af !important; /* Thicker border for "Big Box" feel */
        border-radius: 16px;
        box-shadow: 0 6px 12px -2px rgba(0, 0, 0, 0.2);
        padding: 1.5rem; /* Increased padding */
    }
    
    /* FORCE DARK TEXT INSIDE SILVER BOXES */
    div[data-testid="stVerticalBlockBorderWrapper"] * {
        color: #1f2937 !important;
    }
    
    /* EXCEPTIONS: Success/Error messages inside Silver Boxes need their own colors */
    div[data-testid="stVerticalBlockBorderWrapper"] .stAlert * {
        color: inherit !important; /* Let alert text color stick */
    }

    /* INPUT FIELDS */
    .stTextInput input, .stFileUploader button {
        background-color: #ffffff !important;
        color: #1f2937 !important;
        border: 1px solid #d1d5db;
    }
    
    /* BUTTONS - Silver/Metallic Style */
    .stButton > button {
        background: linear-gradient(to bottom, #ffffff, #e5e7eb);
        color: #000000 !important; /* CHANGED: Black text as requested */
        font-weight: 800;
        border: 1px solid #9ca3af;
        border-radius: 8px;
        transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        border-color: #ffffff;
    }
    
    /* CHAT BUBBLES */
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: white !important;
    }
    
    /* Remove top padding for compact look */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. HARDCODED DATABASE ---
RESTAURANT_PROFILE = {
    "name": "Pikio Taco",
    "address": "Carrer de Còrsega, 376, L'Eixample",
    "neighborhood": "L'Eixample",
    "cuisine": "Mexican / Taqueria",
    "price_range": "€10–20",
    "rating": "4.5",
    "vibe": "Snug taqueria, cool vibe",
    "services": ["Dine-in", "Takeaway", "Delivery"],
    "menu_items": """
    TACOS (3.90€/unit):
    - Carnitas: Pork confit Quiroga style, onion, coriander, radish.
    - Birria (Spicy): Beef in dried chili marinade, red pickled onion.
    - Campechano: Grilled skirt steak, chorizo, onion, nopal.
    - Tijuana (Spiced): Spiced chicken, mozzarella, guacamole, salsa Valentina.
    - Alambre Veggie: Sauteed cauliflower w/ curcuma, sesame seeds.
    
    ENTRANTES:
    - Nachos Pikio (12.50€): Homemade chips, cheddar, guacamole, jalapenos (Add meat/beans).
    - Tostada de Pollo/Setas (5.00€): Crunchy corn tortilla, beans, feta, crispy onion.
    
    QUESADILLAS (9.90€):
    - 20cm flour tortilla w/ mozzarella + Choice of: Chicken, Beef, Sausage, Mushrooms.
    
    DESSERTS (5.00€): Homemade daily options.
    """
}

# --- 4. SESSION STATE ---
if 'external_report' not in st.session_state: st.session_state.external_report = ""
if 'internal_report' not in st.session_state: st.session_state.internal_report = ""
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = ""
if 'chat_history' not in st.session_state: st.session_state.chat_history = [] 

# --- 5. SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3268/3268897.png", width=60)
    st.title("📍 Active Profile")
    st.markdown("---")
    st.subheader(f"🌮 {RESTAURANT_PROFILE['name']}")
    st.caption(RESTAURANT_PROFILE['address'])
    
    col_a, col_b = st.columns(2)
    with col_a: st.metric("Rating", RESTAURANT_PROFILE['rating'])
    with col_b: st.caption(f"**Zone:**\n{RESTAURANT_PROFILE['neighborhood']}")
    
    with st.expander("📖 View Menu Data"):
        st.text(RESTAURANT_PROFILE["menu_items"])
        
    st.markdown("---")
    api_key = st.text_input("🔑 Gemini API Key", type="password")
    if not api_key:
        st.warning("Enter Key to Start")

# --- 6. CORE LOGIC ---

def fetch_external_intelligence(api_key):
    if not api_key: return st.error("Missing API Key")
    prompt = f"""
    ROLE: Intelligence Officer for {RESTAURANT_PROFILE['name']} in Barcelona.
    MENU: {RESTAURANT_PROFILE['menu_items']}
    RAW DATA (Simulated Còrsega 376):
    - EVENTS: Heavy Rain tonight. Corporate event Casa Fuster (20:00).
    - COMPETITORS: "La Taqueria" fully booked.
    - TRENDS: High search "Comfort food delivery" & "Spicy".
    TASK: 5-point 'External Reality Report' with Emojis. Link trends to specific menu items.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        with st.spinner("📡 Scanning city sensors..."):
            response = model.generate_content(prompt)
            st.session_state.external_report = response.text
    except Exception as e:
        st.error(f"Error: {e}")

def analyze_internal_data(api_key, df):
    if not api_key: return st.error("Missing API Key")
    csv_text = df.to_csv(index=False)
    prompt = f"""
    ROLE: Data Analyst for {RESTAURANT_PROFILE['name']}.
    MENU: {RESTAURANT_PROFILE['menu_items']}
    INPUT DATA: {csv_text[:15000]}
    TASK: Health Check. 1. Star Performers, 2. Dead Weight, 3. Peak Times, 4. Financial Health.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        with st.spinner("🔍 Auditing records..."):
            response = model.generate_content(prompt)
            st.session_state.internal_report = response.text
    except Exception as e:
        st.error(f"Error: {e}")

def run_strategic_analysis(api_key):
    if not api_key: return
    prompt = f"""
    ACT AS: Strategic Consultant for {RESTAURANT_PROFILE['name']}.
    MENU: {RESTAURANT_PROFILE['menu_items']}
    CONTEXT 1 (External): {st.session_state.external_report}
    CONTEXT 2 (Internal): {st.session_state.internal_report}
    TASK: 4-point Decision Plan (Money Move, Shield, Menu Pivot, Marketing Hook).
    CRITICAL: Cite specific menu items (e.g. "Promote Carnitas").
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        with st.spinner("🚀 Generating Strategy..."):
            response = model.generate_content(prompt)
            st.session_state.analysis_result = response.text
    except Exception as e:
        st.error(f"Error: {e}")

def ask_executive_chat(api_key, question):
    if not api_key: return "Please enter API Key."
    prompt = f"""
    YOU ARE: Ops Director for {RESTAURANT_PROFILE['name']}.
    MENU: {RESTAURANT_PROFILE['menu_items']}
    DATA: 
    1. External: {st.session_state.external_report}
    2. Internal: {st.session_state.internal_report}
    3. Strategy: {st.session_state.analysis_result}
    USER QUESTION: "{question}"
    TASK: Concise, evidence-based answer. Be specific.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Error: {e}"

# --- 7. MAIN UI LAYOUT ---

# HEADER SECTION
st.markdown(f"""
<div class="header-banner">
    <h1 style="margin:0; padding-bottom:10px;">🌮 BarnaInsights: {RESTAURANT_PROFILE['name']}</h1>
    <p style="font-size: 1.1rem; color: #cbd5e1; margin:0;">Real-time Intelligence for {RESTAURANT_PROFILE['address']}</p>
</div>
""", unsafe_allow_html=True)

# SPLIT LAYOUT (Responsive Columns)
col_left, col_right = st.columns([1, 1], gap="large")

# === LEFT BOX: EXTERNAL ===
with col_left:
    # Everything inside this container gets the "Silver Box" style + border
    with st.container(border=True):
        st.markdown("### 🌍 External Radar")
        st.caption("City Events, Weather, Competitors")
        
        if st.button("🔄 Scan City Data", use_container_width=True):
            fetch_external_intelligence(api_key)
        
        st.markdown("---")
        
        if st.session_state.external_report:
            st.markdown(st.session_state.external_report)
        else:
            st.info("System Ready. Click Scan to fetch live data.")

# === RIGHT BOX: INTERNAL ===
with col_right:
    # Everything inside this container gets the "Silver Box" style + border
    with st.container(border=True):
        st.markdown("### 📊 Internal Audit")
        st.caption("Sales Logs, POS Data, Inventory")
        
        uploaded_file = st.file_uploader("Upload Excel/CSV", type=['csv', 'xlsx'])
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
                else: df = pd.read_excel(uploaded_file)
                st.success(f"✅ Loaded {len(df)} rows")
                
                if st.button("🔍 Scan Internal Data", use_container_width=True):
                    analyze_internal_data(api_key, df)
            except:
                st.error("Invalid file format")
        
        st.markdown("---")
        
        if st.session_state.internal_report:
            st.markdown(st.session_state.internal_report)
        else:
            st.markdown("*Upload data to uncover Top Sellers.*")

# === MERGE STRATEGY ===
st.write("") # Spacer
_, col_center, _ = st.columns([1, 2, 1])
with col_center:
    ready = st.session_state.external_report and st.session_state.internal_report and api_key
    if st.button("⚡ GENERATE UNIFIED STRATEGY", type="primary", disabled=not ready, use_container_width=True):
        run_strategic_analysis(api_key)

# === RESULTS ===
if st.session_state.analysis_result:
    st.write("")
    with st.container(border=True):
        st.subheader("🚀 Strategic Action Plan")
        st.markdown(st.session_state.analysis_result)

    # === EXECUTIVE CHAT ===
    st.write("")
    st.markdown("### 💬 Executive Chat")
    
    # Chat container
    chat_container = st.container(height=400, border=True)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
    # Input
    if q := st.chat_input("Ask Ops Director (e.g., 'How do I handle the delivery surge?')"):
        st.session_state.chat_history.append({"role": "user", "content": q})
        with chat_container:
            with st.chat_message("user"): st.markdown(q)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    ans = ask_executive_chat(api_key, q)
                    st.markdown(ans)
        st.session_state.chat_history.append({"role": "assistant", "content": ans})
        st.rerun()
