import streamlit as st
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# ── 1. DATABASE CONFIGURATION ────────────────────────────────────────────────
WORKING_DIR = Path(__file__).parent.absolute()
DB_PATH = WORKING_DIR / "still_v2.db"

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
        """)

# ── 2. AESTHETIC & ACCESSIBILITY CSS ──────────────────────────────────────────
STILL_STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;1,300&family=Jost:wght@200;300;400&display=swap');

:root {
    --bg-color: #FDFCFB;
    --text-color: #1A1A1A;
    --accent: #A89081;
}

.stApp { background-color: var(--bg-color); color: var(--text-color); font-family: 'Jost', sans-serif; }

/* Custom Typography */
h1, h2, h3 { font-family: 'Cormorant Garamond', serif !important; letter-spacing: 2px; }
.artifact-card {
    background: white; padding: 25px; border: 1px solid #F0F0F0;
    border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.02);
}
.soul-quote { font-family: 'Cormorant Garamond', serif; font-style: italic; font-size: 1.5rem; color: #333; }

/* Accessible Inputs */
.stTextInput input, .stTextArea textarea {
    background-color: white !important;
    border: 1px solid #D1D1D1 !important;
    color: #1A1A1A !important;
}

/* Sidebar Styling */
[data-testid="stSidebar"] { background-color: #1A1A1A !important; }
[data-testid="stSidebar"] * { color: #E0E0E0 !important; }
</style>
"""

# ── 3. CORE LOGIC FUNCTIONS ──────────────────────────────────────────────────
def make_hash(pwd): return hashlib.sha256(str.encode(pwd)).hexdigest()

def follow_user(fid, tid):
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO follows VALUES (?,?)", (fid, tid))
        conn.commit()

def unfollow_user(fid, tid):
    with get_db() as conn:
        conn.execute("DELETE FROM follows WHERE follower_id=? AND followed_id=?", (fid, tid))
        conn.commit()

# ── 4. UI COMPONENTS ─────────────────────────────────────────────────────────
def render_artifact(art, current_user_id):
    with st.container():
        st.markdown(f"""
        <div class="artifact-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                <span style="font-weight:300; font-size:0.9rem; color:var(--accent); text-transform:uppercase;">{art['name']}</span>
                <span style="font-size:0.7rem; color:#AAA;">{art['created_at'][:16]}</span>
            </div>
            <div class="soul-quote">"{art['content']}"</div>
            <div style="margin-top:10px; font-size:0.85rem; color:#666;">Feeling: {art['feeling']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if art['image_bytes']:
            st.image(art['image_bytes'], use_container_width=True)
        
        # Interaction Row
        if art['profile_id'] != current_user_id:
            with get_db() as conn:
                is_fol = conn.execute("SELECT 1 FROM follows WHERE follower_id=? AND followed_id=?", 
                                     (current_user_id, art['profile_id'])).fetchone()
            
            col_btn, _ = st.columns([1, 3])
            if is_fol:
                if col_btn.button("Unfollow Soul", key=f"unf_{art['id']}", type="secondary"):
                    unfollow_user(current_user_id, art['profile_id'])
                    st.rerun()
            else:
                if col_btn.button("Follow Soul", key=f"fol_{art['id']}", type="primary"):
                    follow_user(current_user_id, art['profile_id'])
                    st.rerun()
        st.divider()

# ── 5. PAGES ─────────────────────────────────────────────────────────────────
def auth_page():
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown("<h1 style='text-align:center;'>STILL</h1>", unsafe_allow_html=True)
        tab_l, tab_j = st.tabs(["LOG IN", "JOIN"])
        
        with tab_l:
            with st.form("login"):
                e = st.text_input("Email")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("ENTER"):
                    with get_db() as conn:
                        user = conn.execute("SELECT * FROM profiles WHERE email=?", (e,)).fetchone()
                    if user and make_hash(p) == user['password']:
                        st.session_state.user = dict(user)
                        st.rerun()
                    else: st.error("Soul not found.")

        with tab_j:
            with st.form("join"):
                n = st.text_input("Human Name")
                re = st.text_input("Email")
                rp = st.text_input("Password", type="password")
                if st.form_submit_button("BEGIN JOURNEY"):
                    corps = ["corp", "inc", "ltd", "company", "şirket", "holding", "pazarlama"]
                    if any(x in n.lower() for x in corps):
                        st.warning("Only individual souls may enter. No corporations.")
                    elif n and re and rp:
                        try:
                            with get_db() as conn:
                                conn.execute("INSERT INTO profiles (name, email, password) VALUES (?,?,?)", 
                                             (n, re, make_hash(rp)))
                                conn.commit()
                            st.success("Welcome. Please switch to Log In.")
                        except: st.error("Path already taken.")

def page_home():
    st.markdown("## Your Stream")
    st.write("Fragments from the souls you follow.")
    with get_db() as conn:
        arts = conn.execute("""
            SELECT a.*, p.name FROM artifacts a JOIN profiles p ON a.profile_id = p.id
            JOIN follows f ON a.profile_id = f.followed_id
            WHERE f.follower_id = ? ORDER BY a.created_at DESC
        """, (st.session_state.user['id'],)).fetchall()
    
    if not arts: st.info("Silent here. Find someone to follow in Explore.")
    for a in arts: render_artifact(a, st.session_state.user['id'])

def page_explore():
    st.markdown("## Explore")
    search = st.text_input("Search vibes, feelings, or names...", placeholder="e.g. Serenity")
    with get_db() as conn:
        q = f"%{search}%"
        arts = conn.execute("""
            SELECT a.*, p.name FROM artifacts a JOIN profiles p ON a.profile_id = p.id
            WHERE p.name LIKE ? OR a.content LIKE ? OR a.feeling LIKE ?
            ORDER BY a.created_at DESC
        """, (q, q, q)).fetchall()
    for a in arts: render_artifact(a, st.session_state.user['id'])

def page_release():
    st.markdown("## Release Artifact")
    with st.form("release"):
        c = st.text_area("The Essence", placeholder="Share a thought...")
        f = st.text_input("Feeling")
        img = st.file_uploader("Visual fragment", type=['jpg', 'png'])
        if st.form_submit_button("RELEASE"):
            if c:
                img_b = img.getvalue() if img else None
                with get_db() as conn:
                    conn.execute("INSERT INTO artifacts (profile_id, content, feeling, image_bytes) VALUES (?,?,?,?)",
                                 (st.session_state.user['id'], c, f, img_b))
                    conn.commit()
                st.session_state.page = "home"
                st.rerun()

# ── 6. MAIN APP ──────────────────────────────────────────────────────────────
def main():
    init_db()
    st.set_page_config(page_title="STILL", page_icon="🌿", layout="centered")
    st.markdown(STILL_STYLE, unsafe_allow_html=True)

    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "home"

    if st.session_state.user is None:
        auth_page()
    else:
        with st.sidebar:
            st.markdown("<h2 style='color:white;'>STILL</h2>", unsafe_allow_html=True)
            if st.button("🏠 Home Stream"): st.session_state.page = "home"
            if st.button("🔍 Explore Souls"): st.session_state.page = "explore"
            if st.button("✨ Release New"): st.session_state.page = "release"
            st.divider()
            if st.button("Depart"):
                st.session_state.user = None
                st.rerun()

        if st.session_state.page == "home": page_home()
        elif st.session_state.page == "explore": page_explore()
        elif st.session_state.page == "release": page_release()

if __name__ == "__main__":
    main()
