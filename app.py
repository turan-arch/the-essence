import streamlit as st
import sqlite3
import hashlib
import os
import base64
import json
from datetime import datetime
from pathlib import Path
import uuid

# ── Yapılandırma ──────────────────────────────────────────────────────────────
DB_PATH = "still_pro.db"
UPLOAD_DIR = "artifacts"
Path(UPLOAD_DIR).mkdir(exist_ok=True)

# ── Veritabanı Fonksiyonları ──────────────────────────────────────────────────
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
            essence TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            image_path TEXT,
            soul TEXT,
            feeling TEXT,
            atmo_tags TEXT,
            resonance_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(profile_id) REFERENCES profiles(id)
        );

        CREATE TABLE IF NOT EXISTS follows (
            follower_id INTEGER,
            followed_id INTEGER,
            PRIMARY KEY (follower_id, followed_id)
        );
    """)
    conn.commit()
    conn.close()

# ── Yardımcı Fonksiyonlar ─────────────────────────────────────────────────────
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def toast(message):
    st.markdown(f'<div class="still-toast">{message}</div>', unsafe_allow_html=True)

def is_corporate(name):
    # Kurumsal kelime filtresi
    blacklist = ["corp", "inc", "ltd", "company", "şirket", "holding", "llc", "as.", "a.ş.", "sanayi", "ticaret"]
    return any(word in name.lower() for word in blacklist)

# ── Gelişmiş Tasarım (CSS) ────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@200;300;400&display=swap');

:root {
    --bg: #F9F7F2;
    --card: #FFFFFF;
    --text: #1A1A1A;
    --accent: #7A6B5A;
    --muted: #9E9890;
    --border: rgba(0,0,0,0.08);
}

/* Genel Reset ve Erişilebilirlik */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    color: var(--text);
    font-family: 'Jost', sans-serif;
}

/* Ortalı Giriş/Kayıt Ekranı */
.auth-container {
    max-width: 400px;
    margin: 100px auto;
    padding: 40px;
    background: var(--card);
    border: 1px solid var(--border);
    box-shadow: 0 10px 30px rgba(0,0,0,0.03);
    border-radius: 4px;
    text-align: center;
}

.still-wordmark {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2.4rem;
    letter-spacing: 0.4em;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
    color: var(--text);
}

/* Modern Kart Yapısı */
.artifact-card {
    background: var(--card);
    border: 1px solid var(--border);
    padding: 20px;
    margin-bottom: 25px;
    transition: transform 0.3s ease;
}
.artifact-card:hover { transform: translateY(-5px); }

/* Toast Bildirimleri */
.still-toast {
    position: fixed;
    bottom: 30px;
    right: 30px;
    background: var(--text);
    color: white;
    padding: 12px 24px;
    border-radius: 2px;
    font-size: 0.8rem;
    letter-spacing: 0.1em;
    z-index: 10000;
    animation: slideIn 0.5s ease, fadeOut 0.5s ease 2.5s forwards;
}

@keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
@keyframes fadeOut { to { opacity: 0; visibility: hidden; } }

/* Form Elemanları */
.stButton>button {
    width: 100%;
    background-color: var(--text) !important;
    color: white !important;
    border: none !important;
    border-radius: 0px !important;
    letter-spacing: 0.2em;
    padding: 0.6rem !important;
}
</style>
"""

# ── Sayfa Fonksiyonları ────────────────────────────────────────────────────────
def login_page():
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown('<p class="still-wordmark">STILL</p>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["GİRİŞ", "KATIL"])
    
    with tab1:
        email = st.text_input("E-posta", key="login_email")
        password = st.text_input("Şifre", type="password", key="login_pwd")
        if st.button("ADIM AT"):
            conn = get_db()
            user = conn.execute("SELECT * FROM profiles WHERE email=?", (email,)).fetchone()
            conn.close()
            if user and check_hashes(password, user['password']):
                st.session_state.user = dict(user)
                st.rerun()
            else:
                st.error("Ruh eşleşmedi. Bilgileri kontrol et.")
                
    with tab2:
        new_name = st.text_input("İsim", key="reg_name", placeholder="Bireysel isminiz")
        new_email = st.text_input("E-posta", key="reg_email")
        new_pwd = st.text_input("Şifre", type="password", key="reg_pwd")
        if st.button("ALANA GİR"):
            if is_corporate(new_name):
                st.warning("Still sadece bireysel ruhlar içindir. Şirketleşmeye burada yer yok.")
            elif new_name and new_email and new_pwd:
                conn = get_db()
                try:
                    conn.execute("INSERT INTO profiles (email, password, name) VALUES (?,?,?)", 
                                 (new_email, make_hashes(new_pwd), new_name))
                    conn.commit()
                    st.success("Hoş geldin. Şimdi giriş yapabilirsin.")
                except:
                    st.error("Bu e-posta zaten bir yolculuğa dahil.")
                finally:
                    conn.close()
    st.markdown('</div>', unsafe_allow_html=True)

def page_home():
    st.markdown(f"### Merhaba, {st.session_state.user['name']}")
    st.write("Takip ettiğin kişilerin sessiz paylaşımları.")
    
    conn = get_db()
    rows = conn.execute("""
        SELECT a.*, p.name FROM artifacts a 
        JOIN profiles p ON a.profile_id = p.id
        WHERE a.profile_id IN (SELECT followed_id FROM follows WHERE follower_id = ?)
        ORDER BY a.created_at DESC
    """, (st.session_state.user['id'],)).fetchall()
    conn.close()
    
    if not rows:
        st.info("Burası şu an sessiz. Keşfet kısmından yeni insanlar bulabilirsin.")
    else:
        render_grid(rows)

def page_explore():
    search = st.text_input("Ara: İsim, his veya doku...", placeholder="Işık, yalnızlık, Duru...")
    
    conn = get_db()
    query = """
        SELECT a.*, p.name FROM artifacts a 
        JOIN profiles p ON a.profile_id = p.id
        WHERE (a.soul LIKE ? OR p.name LIKE ? OR a.atmo_tags LIKE ?)
        ORDER BY a.created_at DESC
    """
    rows = conn.execute(query, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    conn.close()
    render_grid(rows)

def render_grid(rows):
    cols = st.columns(3)
    for i, row in enumerate(rows):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="artifact-card">
                <p style="font-size:0.7rem; color:gray; letter-spacing:0.1em;">{row['name'].upper()}</p>
                <p style="font-family:'Cormorant Garamond'; font-style:italic; font-size:1.1rem;">"{row['soul']}"</p>
                <p style="font-size:0.8rem; color:var(--muted);">{row['feeling']}</p>
            </div>
            """, unsafe_allow_html=True)

# ── Ana Döngü ─────────────────────────────────────────────────────────────────
def main():
    init_db()
    st.set_page_config(page_title="Still", page_icon="○", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if "user" not in st.session_state:
        st.session_state.user = None
    if "page" not in st.session_state:
        st.session_state.page = "home"

    if st.session_state.user is None:
        login_page()
    else:
        with st.sidebar:
            st.markdown('<p class="still-wordmark">STILL</p>', unsafe_allow_html=True)
            if st.button("AKIS"): st.session_state.page = "home"
            if st.button("KESFET"): st.session_state.page = "explore"
            if st.button("BIRAK"): st.session_state.page = "upload"
            st.markdown("---")
            if st.button("CIKIS"):
                st.session_state.user = None
                st.rerun()
        
        if st.session_state.page == "home": page_home()
        elif st.session_state.page == "explore": page_explore()

if __name__ == "__main__":
    main()
