import streamlit as st
import sqlite3
import hashlib
from pathlib import Path

# ── Configuration & DB ────────────────────────────────────────────────────────
WORKING_DIR = Path(__file__).parent.absolute()
DB_PATH = WORKING_DIR / "still.db"

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
                password TEXT
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER,
                content TEXT,
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

# ── Business Logic ────────────────────────────────────────────────────────────
def follow_user(follower_id, followed_id):
    if follower_id == followed_id: return
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO follows VALUES (?,?)", (follower_id, followed_id))
        conn.commit()

def unfollow_user(follower_id, followed_id):
    with get_db() as conn:
        conn.execute("DELETE FROM follows WHERE follower_id=? AND followed_id=?", (follower_id, followed_id))
        conn.commit()

def is_following(follower_id, followed_id):
    with get_db() as conn:
        res = conn.execute("SELECT 1 FROM follows WHERE follower_id=? AND followed_id=?", (follower_id, followed_id)).fetchone()
        return True if res else False

# ── UI Components ─────────────────────────────────────────────────────────────
def artifact_card(art, current_user_id):
    """Her gönderi için ortak kart yapısı"""
    with st.container():
        st.markdown(f"""
        <div style="background:white; padding:20px; border:1px solid #eee; margin-bottom:10px; border-radius:5px;">
            <small style="color:#888;">{art['name'].upper()} • {art['created_at'][:16]}</small>
            <div style="font-family:serif; font-style:italic; font-size:1.2rem; margin:10px 0;">"{art['content']}"</div>
            <div style="font-size:0.8rem; color:#A89081;">Feeling: {art['feeling']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Fotoğraf varsa göster
        if art['image_bytes']:
            st.image(art['image_bytes'], use_container_width=True)
        
        # Takip Butonu Mantığı
        if art['profile_id'] != current_user_id:
            following = is_following(current_user_id, art['profile_id'])
            if following:
                if st.button(f"Unfollow {art['name']}", key=f"unfol_{art['id']}"):
                    unfollow_user(current_user_id, art['profile_id'])
                    st.rerun()
            else:
                if st.button(f"Follow {art['name']}", key=f"fol_{art['id']}"):
                    follow_user(current_user_id, art['profile_id'])
                    st.rerun()
        st.divider()

# ── Pages ─────────────────────────────────────────────────────────────────────
def page_home():
    """Sadece takip edilenlerin göründüğü Ana Sayfa"""
    st.title("Your Essence Stream")
    st.write("Fragments from the souls you follow.")
    
    with get_db() as conn:
        artifacts = conn.execute("""
            SELECT a.*, p.name FROM artifacts a
            JOIN profiles p ON a.profile_id = p.id
            JOIN follows f ON a.profile_id = f.followed_id
            WHERE f.follower_id = ?
            ORDER BY a.created_at DESC
        """, (st.session_state.user['id'],)).fetchall()
    
    if not artifacts:
        st.info("It's quiet here. Follow someone in 'Explore' to fill your stream.")
    else:
        for art in artifacts:
            artifact_card(art, st.session_state.user['id'])

def page_explore():
    """Arama ve genel keşfetme sayfası"""
    st.title("Explore")
    
    search_query = st.text_input("Search for souls or content...", placeholder="Type a name or a feeling...")
    
    with get_db() as conn:
        query = f"%{search_query}%"
        artifacts = conn.execute("""
            SELECT a.*, p.name FROM artifacts a
            JOIN profiles p ON a.profile_id = p.id
            WHERE p.name LIKE ? OR a.content LIKE ? OR a.feeling LIKE ?
            ORDER BY a.created_at DESC
        """, (query, query, query)).fetchall()
    
    for art in artifacts:
        artifact_card(art, st.session_state.user['id'])

# ── Registration (Şirket Engelli) ──────────────────────────────────────────────
def auth_page():
    st.markdown("<h1 style='text-align:center;'>STILL</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["LOG IN", "JOIN"])
    
    with t2:
        with st.form("reg"):
            new_name = st.text_input("Your Full Name")
            new_email = st.text_input("Email")
            new_pw = st.text_input("Password", type="password")
            if st.form_submit_button("BEGIN"):
                # Şirket kontrolü (Case-insensitive)
                forbidden = ["corp", "inc", "ltd", "company", "şirket", "holding", "pazarlama"]
                if any(word in new_name.lower() for word in forbidden):
                    st.error("This space is for individual souls only. Corporate entities are not permitted.")
                elif new_name and new_email and new_pw:
                    # Kayıt işlemi...
                    st.success("Welcome. Now please Log In.")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    init_db()
    if "user" not in st.session_state: st.session_state.user = None
    if "page" not in st.session_state: st.session_state.page = "home"

    if st.session_state.user is None:
        auth_page()
    else:
        with st.sidebar:
            st.markdown("### STILL")
            if st.button("🏠 HOME (Following)"): st.session_state.page = "home"
            if st.button("🔍 EXPLORE (Keşfet)"): st.session_state.page = "explore"
            if st.button("✨ RELEASE"): st.session_state.page = "release"
            if st.button("LOGOUT"):
                st.session_state.user = None
                st.rerun()
        
        if st.session_state.page == "home": page_home()
        elif st.session_state.page == "explore": page_explore()
        # release sayfası önceki koddaki gibi eklenebilir.

if __name__ == "__main__":
    main()
