import streamlit as st
import sqlite3
import hashlib
import os
import base64
from datetime import datetime
from pathlib import Path
from PIL import Image
import io

# ── Configuration ──────────────────────────────────────────────────────────────
DB_PATH = "still.db"
UPLOAD_DIR = "artifacts"
Path(UPLOAD_DIR).mkdir(exist_ok=True)

# ── Database & Repair ──────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Core tables
    c.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            password TEXT,
            pronouns TEXT,
            essence TEXT,
            obsessions TEXT,
            song_looping TEXT,
            grounding_quote TEXT,
            avatar_path TEXT,
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
    # Fail-safe for columns
    cursor = conn.execute("PRAGMA table_info(profiles)")
    cols = [col[1] for col in cursor.fetchall()]
    if "email" not in cols:
        try: conn.execute("ALTER TABLE profiles ADD COLUMN email TEXT UNIQUE")
        except: pass
    if "password" not in cols:
        try: conn.execute("ALTER TABLE profiles ADD COLUMN password TEXT")
        except: pass
    conn.commit()
    conn.close()

def make_hashes(pwd):
    return hashlib.sha256(str.encode(pwd)).hexdigest()

# ── Aesthetic CSS ──────────────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@200;300;400&display=swap');
:root { --bg: #F7F4EF; --text: #1A1A1A; --accent: #C4A898; --input-bg: #2C2C2C; }
html, body, [data-testid="stAppViewContainer"] { background: var(--bg) !important; color: var(--text); font-family: 'Jost', sans-serif; }
.auth-card { max-width: 420px; margin: 80px auto; padding: 40px; background: white; border: 1px solid rgba(0,0,0,0.05); text-align: center; }
.still-logo { font-family: 'Cormorant Garamond', serif; font-size: 2.6rem; letter-spacing: 0.4em; text-transform: uppercase; margin-bottom: 2rem; }
.stTextInput input { background-color: var(--input-bg) !important; color: white !important; padding: 12px !important; }
.stTextInput label { font-family: 'Cormorant Garamond', serif !important; font-style: italic !important; font-size: 1.1rem !important; }
.stButton > button { width: 100%; background: var(--text) !important; color: white !important; letter-spacing: 0.2em; border-radius: 2px; }
.artifact-card { background: white; padding: 20px; border: 1px solid rgba(0,0,0,0.04); margin-bottom: 20px; transition: 0.3s; }
.artifact-card:hover { transform: translateY(-3px); box-shadow: 0 10px 30px rgba(0,0,0,0.02); }
</style>
"""

# ── Authentic Logic ────────────────────────────────────────────────────────────
def auth_page():
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<p class="still-logo">STILL</p>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["LOG IN", "JOIN"])
    with t1:
        e = st.text_input("Email", key="l_e")
        p = st.text_input("Password", type="password", key="l_p")
        if st.button("ENTER"):
            conn = get_db()
            u = conn.execute("SELECT * FROM profiles WHERE email=?", (e,)).fetchone()
            conn.close()
            if u and make_hashes(p) == u['password']:
                st.session_state.user = dict(u)
                st.rerun()
            else: st.error("The soul did not match.")
    with t2:
        n = st.text_input("Full Name", key="r_n")
        re = st.text_input("Email", key="r_e")
        rp = st.text_input("Password", type="password", key="r_p")
        if st.button("BEGIN"):
            if any(x in n.lower() for x in ["corp", "inc", "ltd", "company", "şirket"]):
                st.warning("Individual souls only.")
            elif n and re and rp:
                conn = get_db()
                try:
                    conn.execute("INSERT INTO profiles (email, password, name) VALUES (?,?,?)", (re, make_hashes(rp), n))
                    conn.commit()
                    st.success("Welcome. Please log in.")
                except: st.error("Path already taken.")
                finally: conn.close()
    st.markdown('</div>', unsafe_allow_html=True)

def page_gallery():
    st.markdown("### The Gallery")
    search = st.text_input("Search vibes or names...", placeholder="Search...")
    conn = get_db()
    rows = conn.execute("""
        SELECT a.*, p.name FROM artifacts a JOIN profiles p ON a.profile_id = p.id
        WHERE p.name LIKE ? OR a.soul LIKE ? ORDER BY a.created_at DESC
    """, (f"%{search}%", f"%{search}%")).fetchall()
    cols = st.columns(3)
    for i, r in enumerate(rows):
        with cols[i % 3]:
            st.markdown(f'<div class="artifact-card"><b>{r["name"]}</b><br><i>"{r["soul"]}"</i><br><small>{r["feeling"]}</small></div>', unsafe_allow_html=True)
    conn.close()

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    init_db()
    st.set_page_config(page_title="Still", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "gallery"

    if st.session_state.user is None:
        auth_page()
    else:
        with st.sidebar:
            st.markdown('<p class="still-logo" style="font-size:1.5rem;">STILL</p>', unsafe_allow_html=True)
            if st.button("GALLERY"): st.session_state.page = "gallery"
            if st.button("RELEASE"): st.session_state.page = "upload"
            if st.button("SOULS"): st.session_state.page = "profiles"
            st.markdown("---")
            if st.button("DEPART"):
                st.session_state.user = None
                st.rerun()
        
        if st.session_state.page == "gallery": page_gallery()
        # Other pages link to original functions...

if __name__ == "__main__":
    main()
