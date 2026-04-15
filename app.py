import streamlit as st
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# ── 1. DATABASE CONFIG ──────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "still_master_final.db"

def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT, theme TEXT DEFAULT 'Light', bio TEXT DEFAULT 'A quiet soul.');
            CREATE TABLE IF NOT EXISTS artifacts (id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER, content TEXT, feeling TEXT, created_at TEXT DEFAULT (datetime('now')));
            CREATE TABLE IF NOT EXISTS follows (follower_id INTEGER, followed_id INTEGER, PRIMARY KEY (follower_id, followed_id));
        """)

# ── 2. AGGRESSIVE VISIBILITY CSS ─────────────────────────────────────────────
def apply_theme(mode):
    bg, text, input_bg, border = ("#121212", "#FDFCFB", "#252525", "#333") if mode == "Dark" else ("#FDFCFB", "#1A1A1A", "#FFFFFF", "#E5E1DD")
    st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg} !important; }}
    input, textarea, label, p, span, h1, h2, h3, .stMarkdown {{ color: {text} !important; font-family: 'Jost', sans-serif !important; }}
    
    /* Anti-Black Box Hack */
    input, textarea {{ background-color: {input_bg} !important; -webkit-text-fill-color: {text} !important; }}
    input:-webkit-autofill {{ -webkit-box-shadow: 0 0 0px 1000px {input_bg} inset !important; -webkit-text-fill-color: {text} !important; }}
    div[data-baseweb="input"], div[data-baseweb="textarea"] {{ background-color: {input_bg} !important; border: 1px solid {border} !important; }}

    .artifact-card {{ background: {input_bg}; padding: 20px; border: 1px solid {border}; border-radius: 4px; margin-bottom: 20px; }}
    .stButton > button {{ background-color: {text} !important; color: {bg} !important; border-radius: 2px !important; width: 100%; }}
    </style>
    """, unsafe_allow_html=True) 
    
    /* Anti-Black Box Hack */
    input, textarea {{ background-color: {input_bg} !important; -webkit-text-fill-color: {text} !important; }}
    input:-webkit-autofill {{ -webkit-box-shadow: 0 0 0px 1000px {input_bg} inset !important; -webkit-text-fill-color: {text} !important; }}
    div[data-baseweb="input"], div[data-baseweb="textarea"] {{ background-color: {input_bg} !important; border: 1px solid {border} !important; }}


# ── 3. SOCIAL LOGIC ─────────────────────────────────────────────────────────
def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

def toggle_follow(tid):
    fid = st.session_state.user['id']
    with get_db() as conn:
        is_f = conn.execute("SELECT 1 FROM follows WHERE follower_id=? AND followed_id=?", (fid, tid)).fetchone()
        if is_f: conn.execute("DELETE FROM follows WHERE follower_id=? AND followed_id=?", (fid, tid))
        else: conn.execute("INSERT INTO follows VALUES (?,?)", (fid, tid))
        conn.commit()

# ── 4. PAGES ────────────────────────────────────────────────────────────────
def render_artifact(art):
    st.markdown(f"""<div class="artifact-card">
        <b style="color:#A89081;">{art['name'].upper()}</b><br>
        <i style="font-size:1.2rem; display:block; margin:10px 0;">"{art['content']}"</i>
        <small>Feeling: {art['feeling']}</small>
    </div>""", unsafe_allow_html=True)
    if art['profile_id'] != st.session_state.user['id']:
        with get_db() as conn:
            is_f = conn.execute("SELECT 1 FROM follows WHERE follower_id=? AND followed_id=?", (st.session_state.user['id'], art['profile_id'])).fetchone()
        if st.button("Unfollow" if is_f else "Follow", key=f"btn_{art['id']}"):
            toggle_follow(art['profile_id']); st.rerun()

def page_home():
    st.markdown("<h2>YOUR STREAM</h2>", unsafe_allow_html=True)
    with get_db() as conn:
        arts = conn.execute("SELECT a.*, p.name FROM artifacts a JOIN profiles p ON a.profile_id = p.id JOIN follows f ON a.profile_id = f.followed_id WHERE f.follower_id = ? ORDER BY a.created_at DESC", (st.session_state.user['id'],)).fetchall()
    if not arts: st.info("Stream is empty. Follow souls in Explore.")
    for a in arts: render_artifact(a)

def page_explore():
    st.markdown("<h2>EXPLORE</h2>", unsafe_allow_html=True)
    q = st.text_input("Search vibes...")
    with get_db() as conn:
        arts = conn.execute("SELECT a.*, p.name FROM artifacts a JOIN profiles p ON a.profile_id = p.id WHERE p.name LIKE ? OR a.content LIKE ? ORDER BY a.created_at DESC", (f"%{q}%", f"%{q}%")).fetchall()
    for a in arts: render_artifact(a)

def page_profile():
    st.markdown(f"<h2>{st.session_state.user['name'].upper()}</h2>", unsafe_allow_html=True)
    with get_db() as conn:
        f_ing = conn.execute("SELECT COUNT(*) FROM follows WHERE follower_id=?", (st.session_state.user['id'],)).fetchone()[0]
        f_er = conn.execute("SELECT COUNT(*) FROM follows WHERE followed_id=?", (st.session_state.user['id'],)).fetchone()[0]
    st.write(f"Following: {f_ing} | Followers: {f_er}")
    
    with st.form("release"):
        c = st.text_area("Release an artifact...")
        f = st.text_input("Feeling")
        if st.form_submit_button("RELEASE"):
            if c:
                with get_db() as conn: conn.execute("INSERT INTO artifacts (profile_id, content, feeling) VALUES (?,?,?)", (st.session_state.user['id'], c, f)); conn.commit()
                st.rerun()

# ── 5. MAIN EXECUTION ───────────────────────────────────────────────────────
def main():
    init_db()
    st.set_page_config(page_title="STILL", layout="centered")
    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "explore"
    
    apply_theme(st.session_state.user['theme'] if st.session_state.user else "Light")

    if st.session_state.user is None:
        # Auth (Login/Join with 2-Password check & Auto-Login)
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.markdown("<h1 style='text-align:center; margin-top:50px;'>STILL</h1>", unsafe_allow_html=True)
            t1, t2 = st.tabs(["LOG IN", "JOIN"])
            with t1:
                with st.form("l"):
                    e, p = st.text_input("Email"), st.text_input("Password", type="password")
                    if st.form_submit_button("ENTER"):
                        with get_db() as conn: u = conn.execute("SELECT * FROM profiles WHERE email=?", (e,)).fetchone()
                        if u and make_hash(p) == u['password']: st.session_state.user = dict(u); st.rerun()
                        else: st.error("Soul not found.")
            with t2:
                n, re = st.text_input("Name"), st.text_input("Email ")
                p1, p2 = st.text_input("Password ", type="password"), st.text_input("Verify", type="password")
                if p1 and p2 and p1 == p2:
                    st.success("✔ Match")
                    if st.button("BEGIN JOURNEY"):
                        with get_db() as conn:
                            cur = conn.cursor(); cur.execute("INSERT INTO profiles (name, email, password) VALUES (?,?,?)", (n, re, make_hash(p1))); conn.commit()
                            u = conn.execute("SELECT * FROM profiles WHERE id=?", (cur.lastrowid,)).fetchone()
                            st.session_state.user = dict(u); st.rerun()
                elif p1 and p2: st.error("✖ No match")
    else:
        with st.sidebar:
            st.title("STILL")
            if st.button("Stream"): st.session_state.page = "home"
            if st.button("Explore"): st.session_state.page = "explore"
            if st.button("Profile"): st.session_state.page = "profile"
            if st.button("Logout"): st.session_state.user = None; st.rerun()
        
        if st.session_state.page == "home": page_home()
        elif st.session_state.page == "explore": page_explore()
        elif st.session_state.page == "profile": page_profile()

if __name__ == "__main__": main()
