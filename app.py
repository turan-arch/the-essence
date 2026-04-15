import streamlit as st
import sqlite3
import hashlib
import os
import base64
from datetime import datetime
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
DB_PATH = "still_v4.db"
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

# ── Logic Helpers ──────────────────────────────────────────────────────────────
def is_corporate(name):
    """Protects the individual nature of the platform."""
    blacklist = ["corp", "inc", "ltd", "company", "holding", "llc", "as.", "a.ş.", "industrial"]
    return any(word in name.lower() for word in blacklist)

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# ── Aesthetics (CSS) ───────────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@200;300;400&display=swap');

:root {
    --bg: #F7F4EF;
    --charcoal: #2C2C2C;
    --dust: #9E9890;
    --ivory: #EDE8DF;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    color: var(--charcoal);
    font-family: 'Jost', sans-serif;
}

/* Centered Auth Box */
.auth-wrapper {
    max-width: 450px;
    margin: 80px auto;
    padding: 50px;
    background: white;
    border: 1px solid rgba(0,0,0,0.05);
    text-align: center;
}

.still-logo {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2.8rem;
    letter-spacing: 0.5em;
    text-transform: uppercase;
    margin-bottom: 2rem;
}

.artifact-card {
    background: white;
    padding: 25px;
    border: 1px solid rgba(0,0,0,0.04);
    margin-bottom: 20px;
}

.still-divider { border: 0; height: 1px; background: rgba(0,0,0,0.1); margin: 2rem 0; }
</style>
"""

# ── Pages ──────────────────────────────────────────────────────────────────────
def auth_page():
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
            if user and check_hashes(pwd, user['password']):
                st.session_state.user = dict(user)
                st.rerun()
            else: st.error("The soul did not match our records.")

    with tab2:
        name = st.text_input("Full Name", key="r_name", placeholder="Individual name only")
        r_email = st.text_input("Email", key="r_email")
        r_pwd = st.text_input("Password", type="password", key="r_pwd")
        if st.button("BEGIN JOURNEY"):
            if is_corporate(name):
                st.warning("Still is reserved for individual souls. Corporate entities are not permitted.")
            elif name and r_email and r_pwd:
                conn = get_db()
                try:
                    conn.execute("INSERT INTO profiles (email, password, name) VALUES (?,?,?)", 
                                 (r_email, make_hashes(r_pwd), name))
                    conn.commit()
                    st.success("Welcome. You may now log in.")
                except: st.error("This path is already taken.")
                finally: conn.close()
    st.markdown('</div>', unsafe_allow_html=True)

def page_home():
    st.markdown(f"### Welcome, {st.session_state.user['name']}")
    st.write("A quiet stream of those you follow.")
    # Logic for following feed...
    st.info("Your feed is silent. Explore to find connections.")

def page_explore():
    search = st.text_input("Search", placeholder="Search by name, essence, or atmosphere...")
    st.markdown("---")
    # Logic for search and random discovery...
    st.write("Discovery mode active.")

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    init_db()
    st.set_page_config(page_title="Still", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "home"

    if st.session_state.user is None:
        auth_page()
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

        if st.session_state.page == "home": page_home()
        elif st.session_state.page == "explore": page_explore()

if __name__ == "__main__":
    main()
