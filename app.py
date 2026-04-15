import streamlit as st
import sqlite3
import hashlib
import os
import base64
from datetime import datetime
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
DB_PATH = "still_safe.db"
UPLOAD_DIR = "artifacts"
Path(UPLOAD_DIR).mkdir(exist_ok=True)

# ── Database ───────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()

# ── Helpers ────────────────────────────────────────────────────────────────────
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# ── CSS (Orijinal Tasarım Korundu, UX İyileştirildi) ──────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@200;300;400&display=swap');

:root {
    --bg: #F9F7F2; /* Biraz daha sıcak kemik rengi */
    --card: #FFFFFF;
    --text: #1A1A1A; /* Net okunabilir metin */
    --accent: #C4A898; /* Senin asil blush rengin */
    --border: rgba(0,0,0,0.06);
    --input-bg: #2C2C2C; /* Koyu input zemini baki */
    --serif: 'Cormorant Garamond', serif;
    --sans: 'Jost', sans-serif;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    color: var(--text);
    font-family: var(--sans);
}

/* Ortalı Login Kartı */
.auth-wrapper {
    max-width: 420px;
    margin: 100px auto;
    padding: 50px;
    background: var(--card);
    border: 1px solid var(--border);
    box-shadow: 0 10px 40px rgba(0,0,0,0.03);
    border-radius: 4px;
    text-align: center;
}

.still-logo {
    font-family: var(--serif);
    font-size: 2.6rem;
    letter-spacing: 0.4em;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
    color: var(--text);
}

.still-sub {
    font-family: var(--sans);
    font-size: 0.68rem;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: var(--dust);
    margin-bottom: 2.5rem;
}

/* Input Etiketleri ve UX Düzeltmesi */
.stTextInput > label,
.stTextArea > label {
    font-family: var(--serif) !important;
    font-style: italic !important;
    font-size: 1rem !important;
    color: var(--text) !important; /* Net OKUNABİLİR etiketler */
    margin-bottom: 0.3rem !important;
}

.stTextInput input,
.stTextArea textarea {
    background: var(--input-bg) !important; /* Koyu zemin baki */
    border: 1px solid var(--input-bg) !important;
    border-radius: 2px !important;
    font-family: var(--sans) !important;
    font-weight: 300 !important;
    color: #FFFFFF !important; /* İçindeki metin METNİN RENGİ NET BEYAZ */
    padding: 1rem !important;
}

/* Odaklanma Efekti (UX Feedback) */
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--accent) !important; /* Blush rengi çerçeve */
    box-shadow: 0 0 0 2px rgba(196,168,152,0.15) !important;
}

/* Standartların Üstünde Butonlar */
.stButton > button {
    width: 100%;
    background-color: var(--text) !important; /* Siyah baki */
    color: #FFFFFF !important;
    border: none !important;
    font-family: var(--sans) !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.2em !important;
    text-transform: uppercase !important;
    padding: 0.8rem !important;
    border-radius: 2px !important;
    transition: 0.3s ease !important;
}

.stButton > button:hover {
    background-color: var(--accent) !important; /* Blush rengi hover */
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; }
.stTabs [data-baseweb="tab"] { font-size: 0.75rem !important; letter-spacing: 0.15em !important; }

</style>
"""

# ── Pages ──────────────────────────────────────────────────────────────────────
def auth_page():
    st.markdown('<div class="auth-wrapper">', unsafe_allow_html=True)
    st.markdown('<p class="still-logo">STILL</p>', unsafe_allow_html=True)
    st.markdown('<p class="still-sub">A room to simply be</p>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["LOG IN", "JOIN"])
    
    with tab1:
        email = st.text_input("Enter your Email", key="l_email", placeholder="elia.voss@still.app")
        pwd = st.text_input("Enter your Password", type="password", key="l_pwd")
        st.markdown("<br>", unsafe_allow_html=True) # Boşluk UX
        if st.button("ENTER"):
            conn = get_db()
            user = conn.execute("SELECT * FROM profiles WHERE email=?", (email,)).fetchone()
            conn.close()
            if user and check_hashes(pwd, user['password']):
                st.session_state.user = dict(user)
                st.rerun()
            else: st.error("The soul did not match our records.")

    with tab2:
        name = st.text_input("Full Individual Name", key="r_name", placeholder="Elia Voss")
        r_email = st.text_input("Email Address", key="r_email", placeholder="elia@proton.me")
        r_pwd = st.text_input("Password", type="password", key="r_pwd")
        st.markdown("<br>", unsafe_allow_html=True) # Boşluk UX
        if st.button("BEGIN JOURNEY"):
            # DB kayıt işlemleri...
            st.success("Welcome. Please login.")

    st.markdown('</div>', unsafe_allow_html=True)

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    init_db()
    st.set_page_config(page_title="Still", page_icon="○", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if "user" not in st.session_state: st.session_state.user = None
    
    if st.session_state.user is None:
        auth_page()
    else:
        # Ana içerik...
        pass

if __name__ == "__main__":
    main()
