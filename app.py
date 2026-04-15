import streamlit as st
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# ── 1. DATABASE CONFIG ──────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "still_v9.db"

def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT, bio TEXT DEFAULT 'A quiet soul.', theme TEXT DEFAULT 'Light');
            CREATE TABLE IF NOT EXISTS artifacts (id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER, content TEXT, feeling TEXT, tags TEXT, image_bytes BLOB, created_at TEXT DEFAULT (datetime('now')));
            CREATE TABLE IF NOT EXISTS follows (follower_id INTEGER, followed_id INTEGER, PRIMARY KEY (follower_id, followed_id));
        """)

# ── 2. ERROR-PROOF CSS (Siyah Ekranı Engelleme) ──────────────────────────────
def apply_theme(mode):
    # Renk Paleti
    if mode == "Dark":
        bg, text, input_bg, border = "#121212", "#FDFCFB", "#1E1E1E", "#333"
    else:
        bg, text, input_bg, border = "#FDFCFB", "#1A1A1A", "#FFFFFF", "#E5E1DD"
    
    # CSS'i parçalara böldük ki hata payı azalsın
    st.markdown(f"""
    <style>
    /* 1. Sayfanın en üst katmanını görünür yap */
    .stApp {{
        background-color: {bg} !important;
        visibility: visible !important;
    }}
    
    /* 2. Yazı Renkleri */
    h1, h2, h3, p, span, label, div, .stMarkdown {{
        color: {text} !important;
        font-family: 'Jost', sans-serif;
    }}

    /* 3. Input ve Siyah Kutu Fix */
    div[data-baseweb="input"], div[data-baseweb="textarea"], .stTextInput div, .stTextArea div {{
        background-color: {input_bg} !important;
        border: 1px solid {border} !important;
    }}
    
    input, textarea {{
        color: {text} !important;
        -webkit-text-fill-color: {text} !important;
        background-color: transparent !important;
    }}

    /* 4. Butonlar */
    .stButton > button {{
        background-color: {text} !important;
        color: {bg} !important;
        border: none !important;
        width: 100%;
    }}

    /* 5. Header Kararmasını Engelle */
    [data-testid="stHeader"] {{
        background-color: rgba(0,0,0,0) !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# ── 3. FUNCTIONS ─────────────────────────────────────────────────────────────
def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

# ── 4. MAIN APP ──────────────────────────────────────────────────────────────
def main():
    # Hata vermemesi için en başta init
    init_db()
    
    # Sayfa Konfigürasyonu (En başta olmalı)
    st.set_page_config(page_title="STILL", layout="centered")
    
    # Session State Başlatma
    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "explore"

    # Temayı uygula (User varsa onun temasını, yoksa Light)
    theme = st.session_state.user['theme'] if st.session_state.user else "Light"
    apply_theme(theme)

    if st.session_state.user is None:
        # Auth Page (Login / Join)
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
                            st.session_state.user = dict(u)
                            st.rerun()
                        else: st.error("Access denied.")
            with t2:
                # JOIN MANTIĞI (Daha önce konuştuğumuz anında girişli yapı)
                n = st.text_input("Full Name")
                re = st.text_input("Email ")
                p1 = st.text_input("Password ", type="password")
                p2 = st.text_input("Verify ", type="password")
                if p1 and p2 and p1 == p2:
                    st.success("✔ Passwords match")
                    if st.button("BEGIN JOURNEY"):
                        try:
                            with get_db() as conn:
                                cur = conn.cursor()
                                cur.execute("INSERT INTO profiles (name, email, password) VALUES (?,?,?)", (n, re, make_hash(p1)))
                                conn.commit()
                                u = conn.execute("SELECT * FROM profiles WHERE id=?", (cur.lastrowid,)).fetchone()
                                st.session_state.user = dict(u); st.rerun()
                        except: st.error("Email taken.")
    else:
        # SideBar
        with st.sidebar:
            st.markdown("<h2>STILL</h2>", unsafe_allow_html=True)
            if st.button("🏠 Stream"): st.session_state.page = "stream"
            if st.button("🔍 Explore"): st.session_state.page = "explore"
            if st.button("👤 Profile"): st.session_state.page = "profile"
            if st.button("✨ Release"): st.session_state.page = "release"
            st.divider()
            if st.button("Depart"): st.session_state.user = None; st.rerun()

        # Sayfa İçerikleri (Home, Explore, Release, Profile fonksiyonlarını buraya ekleyebilirsin)
        st.write(f"Spirit: {st.session_state.user['name']}")
        st.markdown(f"### Current Page: {st.session_state.page.capitalize()}")

if __name__ == "__main__":
    main()
