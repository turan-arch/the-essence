import streamlit as st
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# ── 1. DATABASE CONFIG ──────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "still_v8.db"

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
            CREATE TABLE IF NOT EXISTS likes (profile_id INTEGER, artifact_id INTEGER, PRIMARY KEY (profile_id, artifact_id));
        """)

# ── 2. UTILS ────────────────────────────────────────────────────────────────
def get_vague_count(count):
    if count == 0: return "None"
    if count < 5: return "A few"
    if count < 20: return "Some"
    return "Many"

# ── 3. SOCIAL COMPONENTS ────────────────────────────────────────────────────
def render_artifact(art, current_user_id):
    with st.container():
        st.markdown(f"""
        <div style="background:white; padding:20px; border:1px solid #EEE; border-radius:4px; margin-bottom:15px;">
            <b style="color:#A89081;">{art['name']}</b>
            <p style="font-family:serif; font-style:italic; font-size:1.2rem; margin:10px 0;">"{art['content']}"</p>
            <div style="font-size:0.8rem; color:#888;">Feeling: {art['feeling']} | Presence: {art['tags']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if art['image_bytes']:
            st.image(art['image_bytes'], use_container_width=True)
        
        c1, c2, _ = st.columns([1, 1, 3])
        # Like System
        with get_db() as conn:
            liked = conn.execute("SELECT 1 FROM likes WHERE profile_id=? AND artifact_id=?", (current_user_id, art['id'])).fetchone()
        if c1.button("Resonate" if not liked else "Echoed", key=f"like_{art['id']}"):
            with get_db() as conn:
                if liked: conn.execute("DELETE FROM likes WHERE profile_id=? AND artifact_id=?", (current_user_id, art['id']))
                else: conn.execute("INSERT INTO likes VALUES (?,?)", (current_user_id, art['id']))
                conn.commit()
            st.rerun()

# ── 4. PAGES ────────────────────────────────────────────────────────────────
def page_home():
    st.markdown("<h2>THE STREAM</h2>", unsafe_allow_html=True)
    with get_db() as conn:
        arts = conn.execute("""
            SELECT a.*, p.name FROM artifacts a JOIN profiles p ON a.profile_id = p.id
            JOIN follows f ON a.profile_id = f.followed_id WHERE f.follower_id = ?
            ORDER BY a.created_at DESC""", (st.session_state.user['id'],)).fetchall()
    if not arts: st.info("Silence. Discover souls in Explore to fill your stream.")
    for a in arts: render_artifact(a, st.session_state.user['id'])

def page_explore():
    st.markdown("<h2>EXPLORE</h2>", unsafe_allow_html=True)
    search = st.text_input("Search souls, vibes or tags...", placeholder="Search...")
    with get_db() as conn:
        arts = conn.execute("""
            SELECT a.*, p.name FROM artifacts a JOIN profiles p ON a.profile_id = p.id
            WHERE p.name LIKE ? OR a.content LIKE ? OR a.tags LIKE ?
            ORDER BY a.created_at DESC""", (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    
    for a in arts:
        render_artifact(a, st.session_state.user['id'])
        if a['profile_id'] != st.session_state.user['id']:
            with get_db() as conn:
                is_f = conn.execute("SELECT 1 FROM follows WHERE follower_id=? AND followed_id=?", (st.session_state.user['id'], a['profile_id'])).fetchone()
            if st.button("Follow" if not is_f else "Unfollow", key=f"fol_{a['id']}"):
                with get_db() as conn:
                    if is_f: conn.execute("DELETE FROM follows WHERE follower_id=? AND followed_id=?", (st.session_state.user['id'], a['profile_id']))
                    else: conn.execute("INSERT INTO follows VALUES (?,?)", (st.session_state.user['id'], a['profile_id']))
                    conn.commit()
                st.rerun()

def page_profile():
    st.markdown(f"<h2>{st.session_state.user['name'].upper()}</h2>", unsafe_allow_html=True)
    
    with get_db() as conn:
        f_ing = conn.execute("SELECT COUNT(*) FROM follows WHERE follower_id=?", (st.session_state.user['id'],)).fetchone()[0]
        f_er = conn.execute("SELECT COUNT(*) FROM follows WHERE followed_id=?", (st.session_state.user['id'],)).fetchone()[0]
        my_arts = conn.execute("SELECT a.*, p.name FROM artifacts a JOIN profiles p ON a.profile_id = p.id WHERE a.profile_id=? ORDER BY a.created_at DESC", (st.session_state.user['id'],)).fetchall()
        liked_arts = conn.execute("""
            SELECT a.*, p.name FROM artifacts a 
            JOIN profiles p ON a.profile_id = p.id 
            JOIN likes l ON a.id = l.artifact_id 
            WHERE l.profile_id=? """, (st.session_state.user['id'],)).fetchall()

    st.markdown(f"*{st.session_state.user['bio']}*")
    st.markdown(f"<small>Following: {get_vague_count(f_ing)} souls | Presence: {get_vague_count(f_er)} resonances</small>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["MY RELEASES", "RESONATED"])
    with tab1:
        for a in my_arts: render_artifact(a, st.session_state.user['id'])
    with tab2:
        for a in liked_arts: render_artifact(a, st.session_state.user['id'])

def page_release():
    st.markdown("<h2>RELEASE</h2>", unsafe_allow_html=True)
    with st.form("release_form", clear_on_submit=True):
        content = st.text_area("What essence do you wish to share?")
        feeling = st.text_input("Current Feeling (Optional)")
        tags = st.text_input("Tags / Mentions (e.g. @soul, #peace)")
        img = st.file_uploader("Attach a fragment (Optional)", type=['png', 'jpg', 'jpeg'])
        
        if st.form_submit_button("RELEASE"):
            if content:
                img_b = img.getvalue() if img else None
                with get_db() as conn:
                    conn.execute("INSERT INTO artifacts (profile_id, content, feeling, tags, image_bytes) VALUES (?,?,?,?,?)",
                                 (st.session_state.user['id'], content, feeling, tags, img_b))
                    conn.commit()
                st.success("Released into the stream.")
            else: st.error("Content is required.")

# ── 5. MAIN EXECUTION ───────────────────────────────────────────────────────
def main():
    init_db()
    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "explore"

    # (Apply_Theme CSS buraya gelmeli - Renk fixleri dahil)

    if st.session_state.user is None:
        # Auth Page (Login/Join)
        pass 
    else:
        with st.sidebar:
            st.markdown("<h2>STILL</h2>", unsafe_allow_html=True)
            if st.button("Stream"): st.session_state.page = "home"
            if st.button("Explore"): st.session_state.page = "explore"
            if st.button("Profile"): st.session_state.page = "profile"
            if st.button("Release"): st.session_state.page = "release"
            st.divider()
            if st.button("Depart"): st.session_state.user = None; st.rerun()

        if st.session_state.page == "home": page_home()
        elif st.session_state.page == "explore": page_explore()
        elif st.session_state.page == "profile": page_profile()
        elif st.session_state.page == "release": page_release()

if __name__ == "__main__":
    main()
