import streamlit as st
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# ── 1. DATABASE CONFIGURATION ────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "still_v4.db"

def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, email TEXT UNIQUE, password TEXT,
                bio TEXT DEFAULT 'A quiet soul.', theme TEXT DEFAULT 'Light'
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER,
                content TEXT, feeling TEXT, created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS follows (follower_id INTEGER, followed_id INTEGER, PRIMARY KEY (follower_id, followed_id));
            CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, content TEXT, timestamp TEXT DEFAULT (datetime('now')));
        """)

# ── 2. DYNAMIC THEME ENGINE (CSS) ───────────────────────────────────────────
def apply_theme(mode):
    if mode == "Dark":
        bg, text, card_bg, border, input_bg = "#121212", "#FDFCFB", "#1E1E1E", "#333", "#252525"
    else:
        bg, text, card_bg, border, input_bg = "#FDFCFB", "#1A1A1A", "#FFFFFF", "#F0EBE6", "#FFFFFF"
    
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400&family=Jost:wght@200;300;400&display=swap');
    
    .stApp {{ background-color: {bg} !important; color: {text} !important; }}
    h1, h2, h3, p, span, label {{ color: {text} !important; font-family: 'Jost', sans-serif; }}
    h1, h2 {{ font-family: 'Cormorant Garamond', serif !important; letter-spacing: 3px; }}

    /* Input Fields */
    div[data-baseweb="input"], div[data-baseweb="textarea"], [data-testid="stFileUploader"] {{
        background-color: {input_bg} !important;
        border: 1px solid {border} !important;
    }}
    input, textarea {{ color: {text} !important; background-color: transparent !important; }}

    /* Cards */
    .artifact-card {{
        background: {card_bg}; padding: 25px; border: 1px solid {border};
        border-radius: 4px; margin-bottom: 20px;
    }}

    /* Buttons */
    .stButton > button {{
        background-color: {text} !important; color: {bg} !important;
        border: none !important; border-radius: 2px !important;
        transition: 0.3s all; letter-spacing: 2px; width: 100%;
    }}
    .stButton > button:hover {{ opacity: 0.8; transform: translateY(-1px); }}
    
    /* Tabs */
    button[data-baseweb="tab"] {{ color: #888 !important; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {text} !important; border-bottom-color: #A89081 !important; }}
    </style>
    """, unsafe_allow_html=True)

# ── 3. PAGE COMPONENTS ───────────────────────────────────────────────────────
def page_settings():
    st.markdown("<h2>SYSTEM SETTINGS</h2>", unsafe_allow_html=True)
    with st.form("settings_form"):
        new_bio = st.text_area("Update Bio", value=st.session_state.user['bio'])
        theme_choice = st.selectbox("Preferred Theme", ["Light", "Dark"], index=0 if st.session_state.user['theme'] == "Light" else 1)
        
        if st.form_submit_button("Save Preferences"):
            with get_db() as conn:
                conn.execute("UPDATE profiles SET bio=?, theme=? WHERE id=?", (new_bio, theme_choice, st.session_state.user['id']))
                conn.commit()
                # Update session state
                st.session_state.user['bio'] = new_bio
                st.session_state.user['theme'] = theme_choice
            st.success("Soul updated.")
            st.rerun()

def page_whispers():
    st.markdown("<h2>WHISPERS (DMs)</h2>", unsafe_allow_html=True)
    with get_db() as conn:
        users = conn.execute("SELECT * FROM profiles WHERE id != ?", (st.session_state.user['id'],)).fetchall()
    
    target = st.selectbox("Select a soul to whisper to:", users, format_func=lambda x: x['name'])
    if target:
        with get_db() as conn:
            msgs = conn.execute("""
                SELECT * FROM messages WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
                ORDER BY timestamp ASC""", (st.session_state.user['id'], target['id'], target['id'], st.session_state.user['id'])).fetchall()
        
        for m in msgs:
            align = "right" if m['sender_id'] == st.session_state.user['id'] else "left"
            color = "#A89081" if align == "right" else "#666"
            st.markdown(f"<div style='text-align:{align}; color:{color}; padding:5px;'><b>{m['content']}</b></div>", unsafe_allow_html=True)
        
        with st.form("msg_form", clear_on_submit=True):
            txt = st.text_input("Whisper something...")
            if st.form_submit_button("Send"):
                with get_db() as conn:
                    conn.execute("INSERT INTO messages (sender_id, receiver_id, content) VALUES (?,?,?)", (st.session_state.user['id'], target['id'], txt))
                    conn.commit()
                st.rerun()

# ── 4. AUTH & MAIN ───────────────────────────────────────────────────────────
def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

def main():
    init_db()
    st.set_page_config(page_title="STILL", page_icon="🌿", layout="centered")
    
    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "explore"

    # Theme Injection
    current_theme = st.session_state.user['theme'] if st.session_state.user else "Light"
    apply_theme(current_theme)

    if st.session_state.user is None:
        # Auth Page
        _, col, _ = st.columns([1, 1.5, 1])
        with col:
            st.markdown("<h1 style='text-align:center; margin-top:80px;'>STILL</h1>", unsafe_allow_html=True)
            t_l, t_j = st.tabs(["LOG IN", "JOIN"])
            with t_l:
                with st.form("login"):
                    e = st.text_input("Email")
                    p = st.text_input("Password", type="password")
                    if st.form_submit_button("ENTER"):
                        with get_db() as conn:
                            u = conn.execute("SELECT * FROM profiles WHERE email=?", (e,)).fetchone()
                        if u and make_hash(p) == u['password']:
                            st.session_state.user = dict(u); st.rerun()
                        else: st.error("Soul not found.")
            with t_j:
                with st.form("join"):
                    n = st.text_input("Name")
                    re = st.text_input("Email")
                    rp = st.text_input("Password", type="password")
                    if st.form_submit_button("BEGIN"):
                        try:
                            with get_db() as conn:
                                conn.execute("INSERT INTO profiles (name, email, password) VALUES (?,?,?)", (n, re, make_hash(rp)))
                                conn.commit()
                            st.success("Joined. Please Log In.")
                        except: st.error("Path taken.")
    else:
        # Sidebar
        with st.sidebar:
            st.markdown(f"<h2 style='color:white;'>STILL</h2>", unsafe_allow_html=True)
            st.write(f"Spirit: {st.session_state.user['name']}")
            if st.button("🏛 Stream"): st.session_state.page = "stream"
            if st.button("🔍 Explore"): st.session_state.page = "explore"
            if st.button("✉️ Whispers"): st.session_state.page = "whispers"
            if st.button("✨ Release"): st.session_state.page = "release"
            if st.button("⚙️ Settings"): st.session_state.page = "settings"
            st.divider()
            if st.button("Depart"): st.session_state.user = None; st.rerun()

        # Routing
        if st.session_state.page == "settings": page_settings()
        elif st.session_state.page == "whispers": page_whispers()
        elif st.session_state.page == "explore":
            st.markdown("<h2>EXPLORE</h2>", unsafe_allow_html=True)
            st.info("The gallery is open to your curiosity.")
        elif st.session_state.page == "release":
            with st.form("rel"):
                c = st.text_area("The Essence")
                f = st.text_input("Feeling")
                if st.form_submit_button("Release"):
                    with get_db() as conn:
                        conn.execute("INSERT INTO artifacts (profile_id, content, feeling) VALUES (?,?,?)", (st.session_state.user['id'], c, f))
                        conn.commit()
                    st.session_state.page = "explore"; st.rerun()

if __name__ == "__main__":
    main()
