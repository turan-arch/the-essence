import streamlit as st
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# ── 1. DATABASE CONFIG ──────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "still_master_v5.db"

def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, email TEXT UNIQUE, password TEXT,
                bio TEXT DEFAULT 'A quiet soul.', theme TEXT DEFAULT 'Light'
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER,
                content TEXT, feeling TEXT, created_at TEXT DEFAULT (datetime('now'))
            );
        """)

# ── 2. DYNAMIC THEME & VISIBILITY CSS ───────────────────────────────────────
def apply_theme(mode):
    if mode == "Dark":
        bg, text, card_bg, border, input_bg = "#121212", "#FDFCFB", "#1E1E1E", "#333", "#252525"
    else:
        bg, text, card_bg, border, input_bg = "#FDFCFB", "#1A1A1A", "#FFFFFF", "#E5E1DD", "#FFFFFF"
    
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400&family=Jost:wght@200;300;400&display=swap');
    
    /* Background Force */
    .stApp, [data-testid="stHeader"] {{ background-color: {bg} !important; color: {text} !important; }}
    
    /* Global Text Visibility Fix */
    p, span, label, h1, h2, h3, .stMarkdown {{ color: {text} !important; font-family: 'Jost', sans-serif; }}
    
    /* Input Visibility Fix (The Black on Black Issue) */
    div[data-baseweb="input"], div[data-baseweb="textarea"] {{
        background-color: {input_bg} !important;
        border: 1px solid {border} !important;
    }}
    input, textarea {{
        color: {text} !important;
        background-color: transparent !important;
        -webkit-text-fill-color: {text} !important; /* Critical fix for browsers */
    }}

    /* Tabs Styling */
    button[data-baseweb="tab"] {{ color: #888 !important; border: none !important; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {text} !important; border-bottom: 2px solid #A89081 !important; }}

    /* Button Styling */
    .stButton > button {{
        background-color: {text} !important; color: {bg} !important;
        border-radius: 2px !important; width: 100% !important; border: none !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# ── 3. AUTH LOGIC ───────────────────────────────────────────────────────────
def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

def auth_page():
    _, col, _ = st.columns([1, 1.8, 1])
    with col:
        st.markdown("<h1 style='text-align:center; margin-top:60px;'>STILL</h1>", unsafe_allow_html=True)
        tab_login, tab_join = st.tabs(["LOG IN", "JOIN THE PATH"])
        
        with tab_login:
            with st.form("l_form"):
                e = st.text_input("Email")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("ENTER"):
                    with get_db() as conn:
                        u = conn.execute("SELECT * FROM profiles WHERE email=?", (e,)).fetchone()
                    if u and make_hash(p) == u['password']:
                        st.session_state.user = dict(u); st.rerun()
                    else: st.error("Soul not found or incorrect password.")

        with tab_join:
            n = st.text_input("Full Name", placeholder="e.g. John Doe")
            re = st.text_input("Email Address", placeholder="soul@domain.com")
            
            # Password Verification System
            p1 = st.text_input("Create Password", type="password", key="p1")
            p2 = st.text_input("Verify Password", type="password", key="p2")
            
            pass_match = False
            if p1 and p2:
                if p1 == p2:
                    st.markdown("<span style='color: #4CAF50;'>✔ Passwords match</span>", unsafe_allow_html=True)
                    pass_match = True
                else:
                    st.markdown("<span style='color: #FF5252;'>✖ Passwords do not match</span>", unsafe_allow_html=True)
            
            if st.button("BEGIN JOURNEY"):
                if not pass_match:
                    st.error("Please ensure passwords match before proceeding.")
                elif any(x in n.lower() for x in ["corp", "inc", "ltd", "company", "şirket"]):
                    st.warning("Only individuals may join.")
                elif n and re and p1:
                    try:
                        with get_db() as conn:
                            cur = conn.cursor()
                            cur.execute("INSERT INTO profiles (name, email, password) VALUES (?,?,?)", (n, re, make_hash(p1)))
                            conn.commit()
                            # AUTO LOGIN: Get the newly created user
                            u = conn.execute("SELECT * FROM profiles WHERE id=?", (cur.lastrowid,)).fetchone()
                            st.session_state.user = dict(u)
                            st.success("Welcome aboard.")
                            st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("This email is already in use.")

# ── 4. APP FLOW ──────────────────────────────────────────────────────────────
def main():
    init_db()
    st.set_page_config(page_title="STILL", page_icon="🌿", layout="centered")
    
    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "explore"

    # Apply Theme based on user preference or default
    current_theme = st.session_state.user['theme'] if st.session_state.user else "Light"
    apply_theme(current_theme)

    if st.session_state.user is None:
        auth_page()
    else:
        # Sidebar & Content
        with st.sidebar:
            st.markdown(f"<h2>STILL</h2>", unsafe_allow_html=True)
            st.write(f"Spirit: {st.session_state.user['name']}")
            if st.button("🔍 Explore"): st.session_state.page = "explore"
            if st.button("⚙️ Settings"): st.session_state.page = "settings"
            st.divider()
            if st.button("Depart"): st.session_state.user = None; st.rerun()

        if st.session_state.page == "settings":
            st.markdown("<h2>SETTINGS</h2>", unsafe_allow_html=True)
            theme_choice = st.selectbox("Theme", ["Light", "Dark"], index=0 if current_theme=="Light" else 1)
            if st.button("Save Changes"):
                with get_db() as conn:
                    conn.execute("UPDATE profiles SET theme=? WHERE id=?", (theme_choice, st.session_state.user['id']))
                    conn.commit()
                st.session_state.user['theme'] = theme_choice
                st.rerun()
        else:
            st.markdown(f"<h2>WELCOME, {st.session_state.user['name'].upper()}</h2>", unsafe_allow_html=True)
            st.write("You are now part of the essence.")

if __name__ == "__main__":
    main()
