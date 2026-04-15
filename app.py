import streamlit as st
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# ── 1. DATABASE CONFIG ──────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "still_final_v7.db"

def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT, theme TEXT DEFAULT 'Light', bio TEXT DEFAULT 'A quiet soul.');
            CREATE TABLE IF NOT EXISTS artifacts (id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER, content TEXT, feeling TEXT, created_at TEXT DEFAULT (datetime('now')));
            CREATE TABLE IF NOT EXISTS follows (follower_id INTEGER, followed_id INTEGER, PRIMARY KEY (follower_id, followed_id));
        """)

# ── 2. BRUTE-FORCE CSS (The "Black Box" Killer) ─────────────────────────────
def apply_theme(mode):
    # Renk Paleti
    if mode == "Dark":
        bg, text, input_bg, border = "#121212", "#FDFCFB", "#252525", "#444"
    else:
        bg, text, input_bg, border = "#FDFCFB", "#1A1A1A", "#FFFFFF", "#E5E1DD"
    
    st.markdown(f"""
    <style>
    /* 1. Global Arka Plan */
    .stApp {{ background-color: {bg} !important; }}

    /* 2. INPUT & TEXTAREA - Bu kısım siyah kutu sorununu çözer */
    /* Streamlit'in iç içe geçmiş tüm input divlerini hedef alıyoruz */
    div[data-baseweb="base-input"], 
    div[data-baseweb="input"], 
    div[data-baseweb="textarea"],
    .stTextInput>div>div,
    .stTextArea>div>div {{
        background-color: {input_bg} !important;
        border: 1px solid {border} !important;
        color: {text} !important;
    }}

    /* Yazı rengini tarayıcı bazında zorlama */
    input, textarea {{
        color: {text} !important;
        -webkit-text-fill-color: {text} !important;
        background-color: transparent !important;
    }}

    /* Placeholder (ipucu yazısı) rengi */
    input::placeholder, textarea::placeholder {{
        color: #888 !important;
        -webkit-text-fill-color: #888 !important;
    }}

    /* 3. Butonlar - Siyah kutu içinde siyah yazı olmasını engeller */
    div.stButton > button {{
        background-color: {text} !important;
        color: {bg} !important;
        border: none !important;
        font-weight: bold !important;
        width: 100% !important;
    }}

    /* 4. Sidebar - Okunabilirlik Fix */
    [data-testid="stSidebar"] {{ background-color: #1A1A1A !important; }}
    [data-testid="stSidebar"] * {{ color: #FDFCFB !important; }}
    [data-testid="stSidebar"] button {{
        background-color: transparent !important;
        color: #FDFCFB !important;
        border: 1px solid #444 !important;
    }}

    /* 5. Genel Metinler */
    h1, h2, h3, p, span, label {{ 
        color: {text} !important; 
        font-family: 'Jost', sans-serif !important; 
    }}
    </style>
    """, unsafe_allow_html=True)

# ── 3. CORE LOGIC ───────────────────────────────────────────────────────────
def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

def auth_page():
    _, col, _ = st.columns([1, 1.8, 1])
    with col:
        st.markdown("<h1 style='text-align:center; margin-top:50px;'>STILL</h1>", unsafe_allow_html=True)
        tab_login, tab_join = st.tabs(["LOG IN", "JOIN"])
        
        with tab_login:
            with st.form("l_form"):
                e = st.text_input("Email")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("ENTER"):
                    with get_db() as conn:
                        u = conn.execute("SELECT * FROM profiles WHERE email=?", (e,)).fetchone()
                    if u and make_hash(p) == u['password']:
                        st.session_state.user = dict(u); st.rerun()
                    else: st.error("Soul not found.")

        with tab_join:
            n = st.text_input("Name")
            re = st.text_input("Email ")
            p1 = st.text_input("Password ", type="password")
            p2 = st.text_input("Verify ", type="password")
            
            if p1 and p2:
                if p1 == p2:
                    st.success("✔ Passwords match")
                    if st.button("BEGIN"):
                        try:
                            with get_db() as conn:
                                cur = conn.cursor()
                                cur.execute("INSERT INTO profiles (name, email, password) VALUES (?,?,?)", (n, re, make_hash(p1)))
                                conn.commit()
                                u = conn.execute("SELECT * FROM profiles WHERE id=?", (cur.lastrowid,)).fetchone()
                                st.session_state.user = dict(u); st.rerun()
                        except: st.error("Email taken.")
                else: st.error("✖ No match")

# ── 4. MAIN ──────────────────────────────────────────────────────────────────
def main():
    init_db()
    st.set_page_config(page_title="STILL", layout="centered")
    
    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "explore"

    apply_theme(st.session_state.user['theme'] if st.session_state.user else "Light")

    if st.session_state.user is None:
        auth_page()
    else:
        with st.sidebar:
            st.markdown("<h2>STILL</h2>", unsafe_allow_html=True)
            if st.button("🔍 Explore"): st.session_state.page = "explore"
            if st.button("👤 Profile"): st.session_state.page = "profile"
            st.divider()
            if st.button("Depart"): st.session_state.user = None; st.rerun()

        if st.session_state.page == "explore":
            st.markdown("<h2>EXPLORE</h2>", unsafe_allow_html=True)
            st.write("The path is yours.")
        elif st.session_state.page == "profile":
            st.markdown(f"<h2>{st.session_state.user['name'].upper()}</h2>", unsafe_allow_html=True)
            with st.form("release"):
                c = st.text_area("The Essence")
                f = st.text_input("Feeling")
                if st.form_submit_button("RELEASE"):
                    with get_db() as conn:
                        conn.execute("INSERT INTO artifacts (profile_id, content, feeling) VALUES (?,?,?)", (st.session_state.user['id'], c, f))
                        conn.commit()
                    st.success("Released.")

if __name__ == "__main__":
    main()
