import streamlit as st
import sqlite3
import hashlib
from pathlib import Path

# ── 1. DATABASE SETUP ────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "still_v2.db"

def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ── 2. ULTIMATE UI/UX & ACCESSIBILITY CSS ────────────────────────────────────
STILL_STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400&family=Jost:wght@200;300;400&display=swap');

/* Arka Plan ve Ana Font */
.stApp {
    background-color: #F8F5F2 !important; 
    color: #2D2D2D !important;
    font-family: 'Jost', sans-serif !important;
}

/* Giriş Alanları (Inputs) - Tam Uyumluluk */
div[data-baseweb="input"] {
    background-color: #FFFFFF !important;
    border: 1px solid #D1CDC7 !important;
    border-radius: 4px !important;
}

input {
    color: #2D2D2D !important; /* Yazı rengi siyah/füme */
    background-color: transparent !important;
}

/* Tab (Sekme) Renkleri */
button[data-baseweb="tab"] {
    color: #888 !important;
    font-family: 'Jost', sans-serif !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #2D2D2D !important;
    border-bottom-color: #A89081 !important;
}

/* Buton Tasarımı */
.stButton > button {
    background-color: #2D2D2D !important;
    color: #F8F5F2 !important;
    border: none !important;
    border-radius: 2px !important;
    letter-spacing: 2px !important;
    transition: 0.3s ease all !important;
    width: 100% !important;
}

.stButton > button:hover {
    background-color: #A89081 !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
}

/* Kartlar ve Yazı Tipleri */
h1 { font-family: 'Cormorant Garamond', serif !important; font-weight: 300 !important; letter-spacing: 6px !important; }
label { color: #4A4A4A !important; font-weight: 300 !important; }

/* Hata ve Başarı Mesajları İçin Sadeleştirme */
.stAlert { border-radius: 2px !important; border: none !important; }
</style>
"""

# ── 3. AUTH LOGIC ────────────────────────────────────────────────────────────
def make_hash(pwd): return hashlib.sha256(str.encode(pwd)).hexdigest()

def auth_page():
    # Sayfa ortalama
    _, col, _ = st.columns([1, 2, 1])
    
    with col:
        st.markdown("<h1 style='text-align:center; margin-top:50px;'>STILL</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; font-style:italic; margin-bottom:40px;'>Individual souls only.</p>", unsafe_allow_html=True)
        
        tab_login, tab_join = st.tabs(["LOG IN", "JOIN"])
        
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("ENTER")
                
                if submitted:
                    with get_db() as conn:
                        user = conn.execute("SELECT * FROM profiles WHERE email=?", (email,)).fetchone()
                    if user and make_hash(password) == user['password']:
                        st.session_state.user = dict(user)
                        st.rerun()
                    else:
                        st.error("Credential mismatch.")

        with tab_join:
            with st.form("join_form"):
                name = st.text_input("Full Name")
                new_email = st.text_input("Email Address")
                new_password = st.text_input("Secure Password", type="password")
                join_btn = st.form_submit_button("BEGIN JOURNEY")
                
                if join_btn:
                    # Şirket Filtresi
                    corps = ["corp", "inc", "ltd", "company", "şirket", "holding", "pazarlama"]
                    if any(x in name.lower() for x in corps):
                        st.warning("Corporate entities are not permitted here.")
                    elif name and new_email and new_password:
                        try:
                            with get_db() as conn:
                                conn.execute("INSERT INTO profiles (name, email, password) VALUES (?,?,?)", 
                                             (name, new_email, make_hash(new_password)))
                                conn.commit()
                            st.success("Soul registered. Please switch to 'LOG IN'.")
                        except:
                            st.error("This path is already taken.")

# ── 4. APP MAIN ──────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="STILL", layout="wide")
    st.markdown(STILL_STYLE, unsafe_allow_html=True)

    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        auth_page()
    else:
        # Uygulamanın geri kalanı (Home, Explore vb.) buraya gelecek
        st.sidebar.markdown("### STILL")
        st.write(f"Welcome, {st.session_state.user['name']}")
        if st.sidebar.button("LOGOUT"):
            st.session_state.user = None
            st.rerun()

if __name__ == "__main__":
    main()
