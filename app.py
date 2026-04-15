import streamlit as st
import sqlite3
import hashlib
import os
from datetime import datetime
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
DB_PATH = "still.db"
UPLOAD_DIR = "artifacts"
Path(UPLOAD_DIR).mkdir(exist_ok=True)

# ── Database & Migration ───────────────────────────────────────────────────────
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
            email TEXT UNIQUE,
            password TEXT,
            name TEXT NOT NULL,
            pronouns TEXT,
            essence TEXT,
            obsessions TEXT,
            song_looping TEXT,
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

def migrate_passwords():
    """Düz metin şifreleri güvenli hash'e çevirir ve giriş sorununu çözer."""
    conn = get_db()
    users = conn.execute("SELECT id, password FROM profiles").fetchall()
    for user in users:
        if user['password'] and len(user['password']) != 64:
            new_hash = hashlib.sha256(str.encode(user['password'])).hexdigest()
            conn.execute("UPDATE profiles SET password = ? WHERE id = ?", (new_hash, user['id']))
    conn.commit()
    conn.close()

def is_corporate(name):
    blacklist = ["corp", "inc", "ltd", "company", "şirket", "holding", "as.", "a.ş."]
    return any(word in name.lower() for word in blacklist)

# ── CSS (Noble & Accessible) ──────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@200;300;400&display=swap');

:root {
    --bg: #F7F4EF;
    --text: #1A1A1A;
    --accent: #C4A898;
    --input-bg: #2C2C2C;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    color: var(--text);
    font-family: 'Jost', sans-serif;
}

/* Auth Center Card */
.auth-wrapper {
    max-width: 420px;
    margin: 80px auto;
    padding: 40px;
    background: white;
    border: 1px solid rgba(0,0,0,0.05);
    border-radius: 4px;
    text-align: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.02);
}

.still-logo {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2.8rem;
    letter-spacing: 0.5em;
    text-transform: uppercase;
    margin-bottom: 2rem;
}

/* Accessibility Fixes for Inputs */
.stTextInput > label {
    font-family: 'Cormorant Garamond', serif !important;
    font-style: italic !important;
    color: var(--text) !important;
    font-size: 1.1rem !important;
}

.stTextInput input {
    background-color: var(--input-bg) !important;
    color: #FFFFFF !important; /* Net white text */
    border-radius: 2px !important;
    padding: 12px !important;
}

.stButton > button {
    width: 100%;
    background-color: var(--text) !important;
    color: white !important;
    border: none !important;
    letter-spacing: 0.2em !important;
    text-transform: uppercase !important;
    padding: 10px !important;
    transition: 0.3s;
}

.stButton > button:hover { background-color: var(--accent) !important; }

.artifact-card {
    background: white;
    padding: 20px;
    border: 1px solid rgba(0,0,0,0.05);
    margin-bottom: 20px;
}
</style>
"""

# ── Pages ──────────────────────────────────────────────────────────────────────
def login_page():
    st.markdown('<div class="auth-wrapper">', unsafe_allow_html=True)
    st.markdown('<p class="still-logo">STILL</p>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["LOG IN", "JOIN"])
    
    with tab1:
        email = st.text_input("Email", key="l_email")
        pwd = st.text_input("Password", type="password", key="l_pwd")
        if st.button("ENTER"):
            conn = get_db()
            user = conn.execute("SELECT * FROM profiles WHERE email=?", (email,)).fetchone()
            conn.close()
            if user and hashlib.sha256(str.encode(pwd)).hexdigest() == user['password']:
                st.session_state.user = dict(user)
                st.rerun()
            else: st.error("The soul did not match our records.")

    with tab2:
        name = st.text_input("Full Name", key="r_name")
        r_email = st.text_input("Email", key="r_email")
        r_pwd = st.text_input("Password", type="password", key="r_pwd")
        if st.button("BEGIN JOURNEY"):
            if is_corporate(name):
                st.warning("Individual souls only. No corporate entities.")
            elif name and r_email and r_pwd:
                conn = get_db()
                try:
                    h = hashlib.sha256(str.encode(r_pwd)).hexdigest()
                    conn.execute("INSERT INTO profiles (email, password, name) VALUES (?,?,?)", (r_email, h, name))
                    conn.commit()
                    st.success("Journey started. Please log in.")
                except: st.error("Email already in use.")
                finally: conn.close()
    st.markdown('</div>', unsafe_allow_html=True)

def page_explore():
    st.markdown("### Explore Souls")
    search = st.text_input("Search for names, moods or vibes...")
    conn = get_db()
    query = """
        SELECT a.*, p.name FROM artifacts a 
        JOIN profiles p ON a.profile_id = p.id
        WHERE (p.name LIKE ? OR a.soul LIKE ? OR a.atmo_tags LIKE ?)
        ORDER BY RANDOM()
    """
    rows = conn.execute(query, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    
    cols = st.columns(3)
    for i, row in enumerate(rows):
        with cols[i % 3]:
            st.markdown(f'<div class="artifact-card"><b>{row["name"]}</b><br><i>{row["soul"]}</i></div>', unsafe_allow_html=True)
    conn.close()

# ── Main Loop ──────────────────────────────────────────────────────────────────
def main():
    init_db()
    migrate_passwords() # Otomatik tamir
    st.set_page_config(page_title="Still", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "explore"

    if st.session_state.user is None:
        login_page()
    else:
        with st.sidebar:
            st.markdown('<p class="still-logo" style="font-size:1.5rem;">STILL</p>', unsafe_allow_html=True)
            if st.button("FEED"): st.session_state.page = "home"
            if st.button("EXPLORE"): st.session_state.page = "explore"
            if st.button("RELEASE"): st.session_state.page = "upload"
            st.markdown("---")
            if st.button("DEPART"):
                st.session_state.user = None
                st.rerun()
        
        if st.session_state.page == "explore": page_explore()
        # Diğer sayfalar (home, upload) buraya eklenebilir.

if __name__ == "__main__":
    main()
