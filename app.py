import streamlit as st
import sqlite3
import hashlib
import os
import base64
import json
from datetime import datetime
from pathlib import Path
import io
import uuid

# ── Configuration ──────────────────────────────────────────────────────────────
DB_PATH = "still_v3.db" # Veritabanı yapısı değiştiği için v3 yaptık
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
            PRIMARY KEY (follower_id, followed_id),
            FOREIGN KEY(follower_id) REFERENCES profiles(id),
            FOREIGN KEY(followed_id) REFERENCES profiles(id)
        );

        CREATE TABLE IF NOT EXISTS resonances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artifact_id INTEGER,
            session_id TEXT
        );
    """)
    conn.commit()
    conn.close()

# ── Logic Helpers ──────────────────────────────────────────────────────────────
def is_corporate(name):
    """Şirketleşmeyi engelleyen basit ama etkili filtre."""
    blacklist = ["corp", "inc", "ltd", "company", "şirket", "holding", "llc", "as.", "a.ş."]
    return any(word in name.lower() for word in blacklist)

def toggle_follow(followed_id):
    me = st.session_state.user['id']
    conn = get_db()
    exists = conn.execute("SELECT 1 FROM follows WHERE follower_id=? AND followed_id=?", (me, followed_id)).fetchone()
    if exists:
        conn.execute("DELETE FROM follows WHERE follower_id=? AND followed_id=?", (me, followed_id))
        toast("Path diverged.")
    else:
        conn.execute("INSERT INTO follows (follower_id, followed_id) VALUES (?,?)", (me, followed_id))
        toast("Paths crossed.")
    conn.commit()
    conn.close()

def toast(message):
    st.markdown(f'<div class="resonate-toast">{message}</div>', unsafe_allow_html=True)

# ── CSS (Orijinal 'Still' Estetiği) ───────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@300;400&display=swap');
:root { --warm-white: #F7F4EF; --charcoal: #2C2C2C; --dust: #9E9890; --ivory: #EDE8DF; --serif: 'Cormorant Garamond', serif; --sans: 'Jost', sans-serif; }
html, body, [data-testid="stAppViewContainer"] { background: var(--warm-white) !important; color: var(--charcoal); font-family: var(--sans); }
.still-wordmark { font-family: var(--serif); font-size: 2rem; letter-spacing: 0.3em; text-transform: uppercase; padding: 1.5rem 0; text-align: center; }
.resonate-toast { position: fixed; bottom: 2rem; right: 2rem; background: var(--charcoal); color: white; padding: 0.8rem 1.5rem; z-index: 9999; animation: fade 3s forwards; }
@keyframes fade { 0%, 100% {opacity:0} 10%, 90% {opacity:1} }
.artifact-card { background: var(--ivory); margin-bottom: 1.5rem; padding: 0.5rem; border-radius: 2px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); }
</style>
"""

# ── Pages ──────────────────────────────────────────────────────────────────────
def page_home():
    st.markdown('<p class="still-wordmark">Home</p>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; color:gray; font-style:italic;">Your followed paths</p>', unsafe_allow_html=True)
    conn = get_db()
    # Sadece takip edilenlerin gönderileri
    rows = conn.execute("""
        SELECT a.*, p.name FROM artifacts a 
        JOIN profiles p ON a.profile_id = p.id
        WHERE a.profile_id IN (SELECT followed_id FROM follows WHERE follower_id = ?)
        ORDER BY a.created_at DESC
    """, (st.session_state.user['id'],)).fetchall()
    
    if not rows:
        st.info("Your feed is quiet. Explore to find people to follow.")
    else:
        render_grid(rows)
    conn.close()

def page_explore():
    st.markdown('<p class="still-wordmark">Explore</p>', unsafe_allow_html=True)
    search_query = st.text_input("Search for souls, names or atmospheres...", placeholder="Light, Elia, Still...")
    
    conn = get_db()
    query = """
        SELECT a.*, p.name FROM artifacts a 
        JOIN profiles p ON a.profile_id = p.id
        WHERE (a.soul LIKE ? OR p.name LIKE ? OR a.atmo_tags LIKE ?)
        ORDER BY RANDOM()
    """
    param = f"%{search_query}%"
    rows = conn.execute(query, (param, param, param)).fetchall()
    render_grid(rows)
    conn.close()

def render_grid(rows):
    cols = st.columns(3)
    for i, row in enumerate(rows):
        with cols[i % 3]:
            st.markdown(f'<div class="artifact-card"><b>{row["name"]}</b><br><i>"{row["soul"]}"</i></div>', unsafe_allow_html=True)
            if st.button(f"◈ {row['resonance_count']}", key=f"res_{row['id']}"):
                # Resonance logic here...
                pass

def page_people():
    st.markdown('<p class="still-wordmark">The People</p>', unsafe_allow_html=True)
    conn = get_db()
    users = conn.execute("SELECT * FROM profiles WHERE id != ?", (st.session_state.user['id'],)).fetchall()
    for u in users:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### {u['name']}\n*{u['essence']}*")
        with col2:
            is_following = conn.execute("SELECT 1 FROM follows WHERE follower_id=? AND followed_id=?", 
                                         (st.session_state.user['id'], u['id'])).fetchone()
            label = "Following" if is_following else "Follow"
            if st.button(label, key=f"fol_{u['id']}"):
                toggle_follow(u['id'])
                st.rerun()
    conn.close()

# ── Auth & Entry ──────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="Still", page_icon="○", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    init_db()

    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "explore"

    if st.session_state.user is None:
        auth_section()
    else:
        sidebar_nav()
        if st.session_state.page == "home": page_home()
        elif st.session_state.page == "explore": page_explore()
        elif st.session_state.page == "people": page_people()
        # Diğer sayfalar...

def auth_section():
    st.markdown('<p class="still-wordmark">Still</p>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab2:
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        if st.button("Arrive"):
            if is_corporate(name):
                st.error("Still is for individual souls only. No corporate entities.")
            else:
                # DB kayıt işlemi...
                st.success("Welcome. Please login.")

def sidebar_nav():
    with st.sidebar:
        st.markdown('<p class="still-wordmark">Still</p>', unsafe_allow_html=True)
        if st.button("Home (Following)"): st.session_state.page = "home"
        if st.button("Explore (Discover)"): st.session_state.page = "explore"
        if st.button("The People"): st.session_state.page = "people"
        if st.button("Logout"): 
            st.session_state.user = None
            st.rerun()

if __name__ == "__main__":
    main()
