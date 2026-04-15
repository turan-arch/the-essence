import streamlit as st
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# ── 1. DATABASE SETUP ────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "still_v3.db"

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
                bio TEXT DEFAULT 'A quiet soul.',
                avatar_index INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER,
                content TEXT,
                feeling TEXT,
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
                msg_text TEXT,
                timestamp TEXT DEFAULT (datetime('now'))
            );
        """)

# ── 2. ADVANCED UI/UX CSS (FIXED COLORS) ─────────────────────────────────────
STILL_STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400&family=Jost:wght@200;300;400&display=swap');

.stApp { background-color: #F8F5F2 !important; color: #2D2D2D !important; font-family: 'Jost', sans-serif !important; }

/* Input Fixes - No more dark-on-dark */
div[data-baseweb="input"], div[data-baseweb="textarea"] {
    background-color: #FFFFFF !important;
    border: 1px solid #D1CDC7 !important;
    border-radius: 2px !important;
}
input, textarea { color: #2D2D2D !important; background-color: transparent !important; }

/* Aesthetic Cards */
.artifact-card {
    background: white; padding: 20px; border: 1px solid #EEE;
    margin-bottom: 15px; border-radius: 4px;
}
.soul-name { font-family: 'Cormorant Garamond', serif; font-size: 1.2rem; font-weight: bold; color: #A89081; }
.message-bubble { padding: 10px 15px; border-radius: 15px; margin-bottom: 5px; max-width: 80%; }
.msg-sent { background: #E2DDD9; align-self: flex-end; margin-left: auto; }
.msg-received { background: white; border: 1px solid #EEE; }

/* Buttons */
.stButton > button {
    background-color: #2D2D2D !important; color: white !important;
    border-radius: 2px !important; width: 100%; transition: 0.3s;
}
.stButton > button:hover { background-color: #A89081 !important; border-color: #A89081 !important; }
</style>
"""

# ── 3. CORE FUNCTIONS ────────────────────────────────────────────────────────
def make_hash(pwd): return hashlib.sha256(str.encode(pwd)).hexdigest()

def toggle_follow(fid, tid):
    with get_db() as conn:
        existing = conn.execute("SELECT 1 FROM follows WHERE follower_id=? AND followed_id=?", (fid, tid)).fetchone()
        if existing: conn.execute("DELETE FROM follows WHERE follower_id=? AND followed_id=?", (fid, tid))
        else: conn.execute("INSERT INTO follows VALUES (?,?)", (fid, tid))
        conn.commit()

# ── 4. PAGES ─────────────────────────────────────────────────────────────────

def page_profile(user_id=None):
    target_id = user_id if user_id else st.session_state.user['id']
    with get_db() as conn:
        prof = conn.execute("SELECT * FROM profiles WHERE id=?", (target_id,)).fetchone()
        arts = conn.execute("SELECT * FROM artifacts WHERE profile_id=? ORDER BY created_at DESC", (target_id,)).fetchall()
        f_count = conn.execute("SELECT COUNT(*) FROM follows WHERE followed_id=?", (target_id,)).fetchone()[0]

    st.markdown(f"<h1 style='text-align:center;'>{prof['name']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; font-style:italic;'>{prof['bio']}</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:#A89081;'>{f_count} Resonances (Followers)</p>", unsafe_allow_html=True)
    
    if target_id != st.session_state.user['id']:
        if st.button("Message Soul"):
            st.session_state.chat_target = target_id
            st.session_state.page = "messages"
            st.rerun()

    st.divider()
    for a in arts:
        st.markdown(f"<div class='artifact-card'><i>{a['content']}</i><br><small>{a['feeling']}</small></div>", unsafe_allow_html=True)

def page_messages():
    st.title("Whispers (Messages)")
    with get_db() as conn:
        # Mesajlaşılan kişileri listele
        contacts = conn.execute("""
            SELECT DISTINCT p.id, p.name FROM profiles p
            JOIN messages m ON (p.id = m.sender_id OR p.id = m.receiver_id)
            WHERE (m.sender_id = ? OR m.receiver_id = ?) AND p.id != ?
        """, (st.session_state.user['id'], st.session_state.user['id'], st.session_state.user['id'])).fetchall()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Souls")
        for c in contacts:
            if st.button(c['name'], key=f"contact_{c['id']}"):
                st.session_state.chat_target = c['id']
        
    with col2:
        if "chat_target" in st.session_state:
            target = st.session_state.chat_target
            with get_db() as conn:
                msgs = conn.execute("""
                    SELECT * FROM messages WHERE 
                    (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
                    ORDER BY timestamp ASC
                """, (st.session_state.user['id'], target, target, st.session_state.user['id'])).fetchall()
            
            for m in msgs:
                cls = "msg-sent" if m['sender_id'] == st.session_state.user['id'] else "msg-received"
                st.markdown(f"<div class='message-bubble {cls}'>{m['msg_text']}</div>", unsafe_allow_html=True)
            
            with st.form("send_msg", clear_on_submit=True):
                txt = st.text_input("Send a whisper...")
                if st.form_submit_button("Send") and txt:
                    with get_db() as conn:
                        conn.execute("INSERT INTO messages (sender_id, receiver_id, msg_text) VALUES (?,?,?)",
                                     (st.session_state.user['id'], target, txt))
                        conn.commit()
                    st.rerun()

def page_explore():
    st.title("Explore Souls")
    search = st.text_input("Search names or vibes...")
    with get_db() as conn:
        users = conn.execute("SELECT * FROM profiles WHERE name LIKE ? AND id != ?", 
                            (f"%{search}%", st.session_state.user['id'])).fetchall()
    
    for u in users:
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"<span class='soul-name'>{u['name']}</span> - {u['bio']}", unsafe_allow_html=True)
        if c2.button("View Profile", key=f"view_{u['id']}"):
            st.session_state.viewing_profile = u['id']
            st.session_state.page = "profile"
            st.rerun()

# ── 5. MAIN ──────────────────────────────────────────────────────────────────
def main():
    init_db()
    st.set_page_config(page_title="STILL", layout="wide")
    st.markdown(STILL_STYLE, unsafe_allow_html=True)

    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "explore"

    if st.session_state.user is None:
        # Auth Page Logic (Daha önceki sade versiyon)
        from auth_module import auth_page # veya direkt buraya auth fonksiyonunu ekle
    else:
        with st.sidebar:
            st.title("STILL")
            if st.button("🏠 Home (Following)"): st.session_state.page = "home"
            if st.button("🔍 Explore"): st.session_state.page = "explore"
            if st.button("✉️ Whispers"): st.session_state.page = "messages"
            if st.button("👤 My Profile"): 
                st.session_state.page = "profile"
                st.session_state.viewing_profile = None
            if st.button("✨ Release Artifact"): st.session_state.page = "release"
            st.divider()
            if st.button("Depart"): st.session_state.user = None; st.rerun()

        if st.session_state.page == "profile": page_profile(st.session_state.get("viewing_profile"))
        elif st.session_state.page == "messages": page_messages()
        elif st.session_state.page == "explore": page_explore()
        # ... home ve release sayfaları

if __name__ == "__main__": main()
