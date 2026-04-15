import streamlit as st
import sqlite3
import hashlib
from pathlib import Path

# ── Configuration & DB ────────────────────────────────────────────────────────
DB_PATH = "still.db"
UPLOAD_DIR = "artifacts"
Path(UPLOAD_DIR).mkdir(exist_ok=True)

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
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            password TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            soul TEXT,
            feeling TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(profile_id) REFERENCES profiles(id)
        );
    """)
    conn.commit()
    conn.close()

def make_hashes(pwd):
    return hashlib.sha256(str.encode(pwd)).hexdigest()

# ── Enhanced Aesthetic CSS ───────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;1,300&family=Jost:wght@300;400&display=swap');

:root {
    --bg: #FDFCFB;
    --text: #2D2D2D;
    --accent: #A89081;
    --input-border: #E0E0E0;
}

/* Genel Tipografi ve Arka Plan */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    color: var(--text);
    font-family: 'Jost', sans-serif;
}

/* Kart Yapısı */
.auth-card {
    max-width: 450px;
    margin: 2rem auto;
    padding: 3rem;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.03);
    border: 1px solid rgba(0,0,0,0.05);
}

.still-logo {
    font-family: 'Cormorant Garamond', serif;
    font-size: 3rem;
    letter-spacing: 0.5em;
    text-align: center;
    color: var(--text);
    margin-bottom: 1rem;
}

/* Input ve Erişilebilirlik Düzenlemeleri */
.stTextInput input {
    background-color: #ffffff !important;
    color: #333 !important;
    border: 1px solid var(--input-border) !important;
    border-radius: 4px !important;
    padding: 10px !important;
}

.stTextInput label {
    color: var(--text) !important;
    font-family: 'Jost', sans-serif !important;
    font-weight: 400 !important;
}

/* Buton İyileştirmesi */
.stButton > button {
    width: 100%;
    background: var(--text) !important;
    color: white !important;
    border: none !important;
    padding: 0.6rem !important;
    font-weight: 300;
    letter-spacing: 0.1em;
    transition: 0.4s ease;
}

.stButton > button:hover {
    background: var(--accent) !important;
    color: white !important;
}

/* Gallery Kartları */
.artifact-card {
    background: white;
    padding: 25px;
    border-radius: 4px;
    border: 1px solid #F0F0F0;
    margin-bottom: 20px;
}
</style>
"""

# ── Auth Logic (Fixing the "Join-Login" Loop) ──────────────────────────────────
def auth_page():
    # Sayfayı ortalamak için boş kolonlar
    _, mid, _ = st.columns([1, 2, 1])
    
    with mid:
        st.markdown('<p class="still-logo">STILL</p>', unsafe_allow_html=True)
        
        # Session state ile hangi sekmede olduğumuzu takip edelim
        if 'auth_tab' not in st.session_state:
            st.session_state.auth_tab = 0

        tab_titles = ["LOG IN", "JOIN"]
        active_tab = st.tabs(tab_titles)

        with active_tab[0]:
            with st.form("login_form"):
                le = st.text_input("Email")
                lp = st.text_input("Password", type="password")
                submit_l = st.form_submit_button("ENTER")
                
                if submit_l:
                    conn = get_db()
                    u = conn.execute("SELECT * FROM profiles WHERE email=?", (le,)).fetchone()
                    conn.close()
                    if u and make_hashes(lp) == u['password']:
                        st.session_state.user = dict(u)
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")

        with active_tab[1]:
            with st.form("join_form"):
                rn = st.text_input("Full Name")
                re = st.text_input("Email")
                rp = st.text_input("Password", type="password")
                submit_j = st.form_submit_button("BEGIN JOURNEY")
                
                if submit_j:
                    if not (rn and re and rp):
                        st.warning("Please fill all fields.")
                    elif any(x in rn.lower() for x in ["corp", "inc", "şirket"]):
                        st.warning("Human souls only.")
                    else:
                        conn = get_db()
                        try:
                            conn.execute("INSERT INTO profiles (email, password, name) VALUES (?,?,?)", 
                                         (re, make_hashes(rp), rn))
                            conn.commit()
                            st.success("Welcome! Now you can Log In.")
                            # Burada rerun yaparak formu temizliyoruz, kullanıcı artık Login'e geçebilir.
                        except sqlite3.IntegrityError:
                            st.error("This email is already registered.")
                        finally:
                            conn.close()

# ── App Logic ──────────────────────────────────────────────────────────────────
def main():
    init_db()
    st.set_page_config(page_title="STILL", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        auth_page()
    else:
        # Sidebar Navigation
        with st.sidebar:
            st.markdown('<p class="still-logo" style="font-size:1.8rem; letter-spacing:0.2em;">STILL</p>', unsafe_allow_html=True)
            st.write(f"Welcome, {st.session_state.user['name']}")
            if st.button("LOGOUT"):
                st.session_state.user = None
                st.rerun()
        
        st.title("The Gallery")
        st.write("Quietly observing the essence of others.")

if __name__ == "__main__":
    main()
