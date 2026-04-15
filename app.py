import streamlit as st
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# ── 1. CORE CONFIGURATION ───────────────────────────────────────────────────
WORKING_DIR = Path(__file__).parent.absolute()
DB_PATH = WORKING_DIR / "still_final.db"

def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                password TEXT,
                bio TEXT DEFAULT 'A silent observer of the world.',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER,
                content TEXT NOT NULL,
                feeling TEXT,
                image_bytes BLOB,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(profile_id) REFERENCES profiles(id)
            );
            CREATE TABLE IF NOT EXISTS follows (
                follower_id INTEGER,
                followed_id INTEGER,
                PRIMARY KEY (follower_id, followed_id)
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER,
                receiver_id INTEGER,
                content TEXT,
                timestamp TEXT DEFAULT (datetime('now'))
            );
        """)

# ── 2. ELITE CSS (Accessibility & Interaction) ─────────────────────────────
FINAL_STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@200;300;400&display=swap');

/* Global Reset */
.stApp { background-color: #FDFCFB !important; color: #1A1A1A !important; font-family: 'Jost', sans-serif !important; }

/* Input Fields - Pure Visibility */
div[data-baseweb="input"], div[data-baseweb="textarea"] {
    background-color: white !important;
    border: 1px solid #E0DCD8 !important;
    border-radius: 2px !important;
}
input, textarea { color: #1A1A1A !important; font-weight: 400 !important; }

/* Typography */
h1, h2, h3 { font-family: 'Cormorant Garamond', serif !important; font-weight: 300 !important; letter-spacing: 4px; }
.artifact-card {
    background: white; padding: 2rem; border-radius: 4px; border: 1px solid #F0EBE6;
    margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.02);
}
.soul-quote { font-family: 'Cormorant Garamond', serif; font-style: italic; font-size: 1.6rem; margin: 1.5rem 0; color: #2D2D2D; }

/* Sidebar & Buttons */
[data-testid="stSidebar"] { background-color: #1A1A1A !important; }
[data-testid="stSidebar"] * { color: #FDFCFB !important; }
.stButton > button {
    background-color: #1A1A1A !important; color: #FDFCFB !important;
    border-radius: 2px !important; border: none !important; width: 100%;
    transition: 0.4s ease; letter-spacing: 2px;
}
.stButton > button:hover { background-color: #A89081 !important; color: white !important; }

/* Tabs Navigation */
button[data-baseweb="tab"] { font-family: 'Jost', sans-serif !important; letter-spacing: 1px; color: #888 !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #1A1A1A !important; border-bottom-color: #A89081 !important; }
</style>
"""

# ── 3. AUTHENTICATION LOGIC ──────────────────────────────────────────────────
def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

def auth_page():
    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        st.markdown("<h1 style='text-align:center; margin-top:100px;'>STILL</h1>", unsafe_allow_html=True)
        tab_l, tab_j = st.tabs(["LOG IN", "JOIN"])
        
        with tab_l:
            with st.form("l_form"):
                e = st.text_input("Email")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("ENTER"):
                    with get_db() as conn:
                        user = conn.execute("SELECT * FROM profiles WHERE email=?", (e,)).fetchone()
                    if user and make_hash(p) == user['password']:
                        st.session_state.user = dict(user)
                        st.rerun()
                    else: st.error("No such soul exists.")

        with tab_j:
            with st.form("j_form"):
                n = st.text_input("Human Name")
                re = st.text_input("Email")
                rp = st.text_input("Password", type="password")
                if st.form_submit_button("BEGIN"):
                    corps = ["corp", "inc", "ltd", "company", "şirket", "holding", "pazarlama"]
                    if any(x in n.lower() for x in corps):
                        st.warning("Only individuals may join.")
                    elif n and re and rp:
                        try:
                            with get_db() as conn:
                                conn.execute("INSERT INTO profiles (name, email, password) VALUES (?,?,?)", (n, re, make_hash(rp)))
                                conn.commit()
                            st.success("Soul Registered. Proceed to Log In.")
                        except: st.error("Path already taken.")

# ── 4. CONTENT & INTERACTION ────────────────────────────────────────────────
def render_artifact(art):
    st.markdown(f"""
    <div class="artifact-card">
        <small style="color:#A89081; letter-spacing:2px; text-transform:uppercase;">{art['name']}</small>
        <div class="soul-quote">"{art['content']}"</div>
        <small style="color:#888;">Mood: {art['feeling']} | {art['created_at'][:16]}</small>
    </div>
    """, unsafe_allow_html=True)
    if art['image_bytes']: st.image(art['image_bytes'], use_container_width=True)
    
    # Interaction Buttons
    if art['profile_id'] != st.session_state.user['id']:
        c1, c2, _ = st.columns([1, 1, 2])
        with get_db() as conn:
            is_fol = conn.execute("SELECT 1 FROM follows WHERE follower_id=? AND followed_id=?", (st.session_state.user['id'], art['profile_id'])).fetchone()
        
        if c1.button("Follow" if not is_fol else "Unfollow", key=f"f_{art['id']}"):
            with get_db() as conn:
                if is_fol: conn.execute("DELETE FROM follows WHERE follower_id=? AND followed_id=?", (st.session_state.user['id'], art['profile_id']))
                else: conn.execute("INSERT INTO follows VALUES (?,?)", (st.session_state.user['id'], art['profile_id']))
                conn.commit()
            st.rerun()
        if c2.button("Profile", key=f"p_{art['id']}"):
            st.session_state.view_target = art['profile_id']
            st.session_state.page = "profile"
            st.rerun()
    st.divider()

# ── 5. MAIN PAGES ────────────────────────────────────────────────────────────
def page_home():
    st.markdown("<h2>YOUR STREAM</h2>", unsafe_allow_html=True)
    with get_db() as conn:
        arts = conn.execute("""
            SELECT a.*, p.name FROM artifacts a JOIN profiles p ON a.profile_id = p.id
            JOIN follows f ON a.profile_id = f.followed_id WHERE f.follower_id = ?
            ORDER BY a.created_at DESC
        """, (st.session_state.user['id'],)).fetchall()
    if not arts: st.info("Silence. Follow someone in Explore.")
    for a in arts: render_artifact(a)

def page_explore():
    st.markdown("<h2>EXPLORE SOULS</h2>", unsafe_allow_html=True)
    query = st.text_input("Search names or vibes...")
    with get_db() as conn:
        arts = conn.execute("""
            SELECT a.*, p.name FROM artifacts a JOIN profiles p ON a.profile_id = p.id
            WHERE p.name LIKE ? OR a.content LIKE ? OR a.feeling LIKE ?
            ORDER BY a.created_at DESC
        """, (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
    for a in arts: render_artifact(a)

def page_whispers():
    st.markdown("<h2>WHISPERS</h2>", unsafe_allow_html=True)
    # This is a simplified direct messaging interface
    with get_db() as conn:
        users = conn.execute("SELECT * FROM profiles WHERE id != ?", (st.session_state.user['id'],)).fetchall()
    
    target = st.selectbox("Send whisper to:", users, format_func=lambda x: x['name'])
    if target:
        with get_db() as conn:
            msgs = conn.execute("SELECT * FROM messages WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?) ORDER BY timestamp", 
                                (st.session_state.user['id'], target['id'], target['id'], st.session_state.user['id'])).fetchall()
        for m in msgs:
            align = "right" if m['sender_id'] == st.session_state.user['id'] else "left"
            st.markdown(f"<div style='text-align:{align}; background:#f0f0f0; padding:10px; margin:5px; border-radius:10px;'>{m['content']}</div>", unsafe_allow_html=True)
        
        with st.form("msg_form", clear_on_submit=True):
            txt = st.text_input("Your message...")
            if st.form_submit_button("Send") and txt:
                with get_db() as conn:
                    conn.execute("INSERT INTO messages (sender_id, receiver_id, content) VALUES (?,?,?)", (st.session_state.user['id'], target['id'], txt))
                    conn.commit()
                st.rerun()

# ── 6. EXECUTION ─────────────────────────────────────────────────────────────
def main():
    init_db()
    st.set_page_config(page_title="STILL", page_icon="🌿", layout="centered")
    st.markdown(FINAL_STYLE, unsafe_allow_html=True)

    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "explore"

    if st.session_state.user is None:
        auth_page()
    else:
        with st.sidebar:
            st.markdown("<h1 style='color:white;'>STILL</h1>", unsafe_allow_html=True)
            if st.button("🏛 Stream"): st.session_state.page = "home"
            if st.button("🔍 Explore"): st.session_state.page = "explore"
            if st.button("✉️ Whispers"): st.session_state.page = "whispers"
            if st.button("✨ Release"): st.session_state.page = "release"
            st.divider()
            if st.button("Depart"): st.session_state.user = None; st.rerun()

        if st.session_state.page == "home": page_home()
        elif st.session_state.page == "explore": page_explore()
        elif st.session_state.page == "whispers": page_whispers()
        elif st.session_state.page == "release":
            with st.form("rel_form"):
                content = st.text_area("What is the essence?")
                feeling = st.text_input("Feeling")
                img = st.file_uploader("Visual (Optional)", type=['png', 'jpg'])
                if st.form_submit_button("Release"):
                    img_b = img.getvalue() if img else None
                    with get_db() as conn:
                        conn.execute("INSERT INTO artifacts (profile_id, content, feeling, image_bytes) VALUES (?,?,?,?)",
                                     (st.session_state.user['id'], content, feeling, img_b))
                        conn.commit()
                    st.session_state.page = "explore"
                    st.rerun()

if __name__ == "__main__":
    main()
