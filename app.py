import streamlit as st
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# ── 1. DATABASE CONFIG ──────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "still_master_v6.db"

def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, email TEXT UNIQUE, password TEXT,
                bio TEXT DEFAULT 'A quiet soul.', theme TEXT DEFAULT 'Light'
            );
        """)

# ── 2. BRUTE FORCE CSS (Fixes the "Black Box" once and for all) ──────────────
def apply_theme(mode):
    # Renk paleti tanımları
    if mode == "Dark":
        bg, text, input_bg, border = "#121212", "#FDFCFB", "#252525", "#333333"
    else:
        bg, text, input_bg, border = "#FDFCFB", "#1A1A1A", "#FFFFFF", "#E5E1DD"
    
    st.markdown(f"""
    <style>
    /* 1. Global Reset */
    .stApp {{ background-color: {bg} !important; }}
    
    /* 2. Input Alanlarını Kökten Düzeltme (En Önemli Kısım) */
    /* Streamlit'in tüm input bileşenlerini hedef alıyoruz */
    div[data-baseweb="input"], div[data-baseweb="textarea"], [data-testid="stTextValue"] {{
        background-color: {input_bg} !important;
        border: 1px solid {border} !important;
        color: {text} !important;
    }}
    
    /* Tarayıcıların "Otomatik Doldurma" (Autofill) rengini ezme */
    input:-webkit-autofill,
    input:-webkit-autofill:hover, 
    input:-webkit-autofill:focus {{
        -webkit-text-fill-color: {text} !important;
        -webkit-box-shadow: 0 0 0px 1000px {input_bg} inset !important;
        transition: background-color 5000s ease-in-out 0s;
    }}

    /* Yazı rengini her koşulda zorlama */
    input, textarea, label, p, span, h1, h2, h3 {{
        color: {text} !important;
        font-family: 'Jost', sans-serif !important;
    }}

    /* 3. Butonlar */
    .stButton > button {{
        background-color: {text} !important;
        color: {bg} !important;
        border: none !important;
        width: 100% !important;
        border-radius: 2px !important;
    }}

    /* 4. Tablar (Login/Join) */
    button[data-baseweb="tab"] {{ color: #888 !important; }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {text} !important;
        border-bottom-color: #A89081 !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# ── 3. AUTH LOGIC (Direct Entry & Verification) ──────────────────────────────
def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

def auth_page():
    _, col, _ = st.columns([1, 1.8, 1])
    with col:
        st.markdown(f"<h1 style='text-align:center; margin-top:50px;'>STILL</h1>", unsafe_allow_html=True)
        t_login, t_join = st.tabs(["LOG IN", "JOIN THE PATH"])
        
        with t_login:
            with st.form("l_form"):
                e = st.text_input("Email", key="login_email")
                p = st.text_input("Password", type="password", key="login_pass")
                if st.form_submit_button("ENTER"):
                    with get_db() as conn:
                        u = conn.execute("SELECT * FROM profiles WHERE email=?", (e,)).fetchone()
                    if u and make_hash(p) == u['password']:
                        st.session_state.user = dict(u); st.rerun()
                    else: st.error("Soul not found.")

        with t_join:
            # Form yerine manuel kontrol (Daha iyi etkileşim için)
            name = st.text_input("Full Name", key="j_name")
            email = st.text_input("Email Address", key="j_email")
            p1 = st.text_input("Create Password", type="password", key="j_p1")
            p2 = st.text_input("Verify Password", type="password", key="j_p2")
            
            if p1 and p2:
                if p1 == p2:
                    st.success("✔ Passwords match")
                    if st.button("BEGIN JOURNEY"):
                        if name and email:
                            try:
                                with get_db() as conn:
                                    cur = conn.cursor()
                                    cur.execute("INSERT INTO profiles (name, email, password) VALUES (?,?,?)", (name, email, make_hash(p1)))
                                    conn.commit()
                                    # OTOMATİK GİRİŞ
                                    u = conn.execute("SELECT * FROM profiles WHERE id=?", (cur.lastrowid,)).fetchone()
                                    st.session_state.user = dict(u); st.rerun()
                            except: st.error("Email path already taken.")
                else:
                    st.error("✖ Passwords do not match")

# ── 4. MAIN ──────────────────────────────────────────────────────────────────
def main():
    init_db()
    st.set_page_config(page_title="STILL", layout="centered")
    
    if "user" not in st.session_state: st.session_state.user = None
    
    # Temayı uygula
    theme = st.session_state.user['theme'] if st.session_state.user else "Light"
    apply_theme(theme)

    if st.session_state.user is None:
        auth_page()
    else:
        # SideBar & Settings
        with st.sidebar:
            st.title("STILL")
            st.write(f"Spirit: {st.session_state.user['name']}")
            mode = st.selectbox("Theme", ["Light", "Dark"], index=0 if theme=="Light" else 1)
            if st.button("Save Theme"):
                with get_db() as conn:
                    conn.execute("UPDATE profiles SET theme=? WHERE id=?", (mode, st.session_state.user['id']))
                    conn.commit()
                st.session_state.user['theme'] = mode; st.rerun()
            st.divider()
            if st.button("Depart"): st.session_state.user = None; st.rerun()
            
        st.markdown(f"<h2>WELCOME, {st.session_state.user['name'].upper()}</h2>", unsafe_allow_html=True)
        st.write("The path is yours to walk.")

if __name__ == "__main__":
    main()
