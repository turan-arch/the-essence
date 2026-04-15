import streamlit as st
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# ── 1. DATABASE CONFIG ──────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "still_master_final.db"

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

# ── 2. THEME ENGINE (AGGRESSIVE VISIBILITY FIX) ──────────────────────────────
def apply_theme(mode):
    # Renk Paleti
    if mode == "Dark":
        bg, text, input_bg, border, side_bg = "#121212", "#FDFCFB", "#1E1E1E", "#444", "#1A1A1A"
    else:
        bg, text, input_bg, border, side_bg = "#FDFCFB", "#1A1A1A", "#FFFFFF", "#D1CDC7", "#1A1A1A"
    
    st.markdown(f"""
    <style>
    /* Ana Ekran ve Yazı Renkleri */
    .stApp {{ background-color: {bg} !important; }}
    h1, h2, h3, p, span, label, .stMarkdown {{ color: {text} !important; font-family: 'Jost', sans-serif !important; }}

    /* Sidebar - Simsiyah Arka Plan, Bembeyaz Yazı */
    [data-testid="stSidebar"] {{ background-color: {side_bg} !important; }}
    [data-testid="stSidebar"] * {{ color: #FDFCFB !important; }}
    [data-testid="stSidebar"] button {{
        background-color: transparent !important;
        color: #FDFCFB !important;
        border: 1px solid #444 !important;
        width: 100%;
    }}

    /* Input Alanları - Görünürlük Garantisi */
    div[data-baseweb="input"], div[data-baseweb="textarea"] {{
        background-color: {input_bg} !important;
        border: 1px solid {border} !important;
    }}
    input, textarea {{
        color: {text} !important;
        -webkit-text-fill-color: {text} !important;
    }}

    /* Butonlar (Release vb.) - Okunabilir Kontrast */
    div.stButton > button {{
        background-color: {text} !important;
        color: {bg} !important;
        border: none !important;
        font-weight: bold !important;
    }}

    /* Sayfa Kararmasını Önleyen Fix */
    [data-testid="stHeader"] {{ background: transparent !important; }}
    </style>
    """, unsafe_allow_html=True)

# ── 3. CORE FUNCTIONS ────────────────────────────────────────────────────────
def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

# ── 4. PAGES ────────────────────────────────────────────────────────────────
def auth_page():
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("<h1 style='text-align:center; margin-top:50px;'>STILL</h1>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["LOG IN", "JOIN"])
        with t1:
            with st.form("l_form"):
                e = st.text_input("Email")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("ENTER"):
                    with get_db() as conn:
                        u = conn.execute("SELECT * FROM profiles WHERE email=?", (e,)).fetchone()
                    if u and make_hash(p) == u['password']:
                        st.session_state.user = dict(u); st.rerun()
                    else: st.error("Access denied.")
        with t2:
            n = st.text_input("Full Name")
            re = st.text_input("Email Address")
            p1 = st.text_input("Create Password", type="password")
            p2 = st.text_input("Verify Password", type="password")
            if p1 and p2 and p1 == p2:
                st.success("✔ Passwords match")
                if st.button("BEGIN JOURNEY"):
                    with get_db() as conn:
                        cur = conn.cursor()
                        cur.execute("INSERT INTO profiles (name, email, password) VALUES (?,?,?)", (n, re, make_hash(p1)))
                        conn.commit()
                        u = conn.execute("SELECT * FROM profiles WHERE id=?", (cur.lastrowid,)).fetchone()
                        st.session_state.user = dict(u); st.rerun()
            elif p1 and p2: st.error("✖ No match")

# ── 5. MAIN EXECUTION ───────────────────────────────────────────────────────
def main():
    init_db()
    st.set_page_config(page_title="STILL", layout="centered")
    
    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "explore"

    # Tema Uygulama
    apply_theme(st.session_state.user['theme'] if st.session_state.user else "Light")

    if st.session_state.user is None:
        auth_page()
    else:
        with st.sidebar:
            st.markdown("<h2>STILL</h2>", unsafe_allow_html=True)
            st.write(f"Spirit: {st.session_state.user['name']}")
            if st.button("🔍 Explore"): st.session_state.page = "explore"
            if st.button("👤 Profile"): st.session_state.page = "profile"
            st.divider()
            if st.button("Depart"): st.session_state.user = None; st.rerun()

        if st.session_state.page == "explore":
            st.markdown("<h2>EXPLORE</h2>", unsafe_allow_html=True)
            st.write("The gallery is open.")
        elif st.session_state.page == "profile":
            st.markdown(f"<h2>{st.session_state.user['name'].upper()}</h2>", unsafe_allow_html=True)
            with st.form("release"):
                c = st.text_area("What is the essence?")
                f = st.text_input("Feeling")
                if st.form_submit_button("RELEASE"):
                    with get_db() as conn:
                        conn.execute("INSERT INTO artifacts (profile_id, content, feeling) VALUES (?,?,?)", 
                                     (st.session_state.user['id'], c, f))
                        conn.commit()
                    st.success("Artifact released.")

if __name__ == "__main__":
    main()
