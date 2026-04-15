def apply_theme(mode):
    # Renk paleti
    if mode == "Dark":
        bg, text, input_bg, border = "#121212", "#FDFCFB", "#1E1E1E", "#444"
    else:
        bg, text, input_bg, border = "#FDFCFB", "#1A1A1A", "#FFFFFF", "#D1CDC7"
    
    st.markdown(f"""
    <style>
    /* Ana Arka Plan */
    .stApp {{ background-color: {bg} !important; }}

    /* Sidebar Butonları ve Yazıları */
    [data-testid="stSidebar"] {{ background-color: #1A1A1A !important; }}
    [data-testid="stSidebar"] button {{
        color: white !important; 
        background-color: transparent !important;
        border: 1px solid #333 !important;
        margin-bottom: 5px !important;
    }}
    [data-testid="stSidebar"] button:hover {{ border-color: #A89081 !important; }}
    
    /* Input ve Textarea (Yazı görünürlüğü garantisi) */
    div[data-baseweb="input"], div[data-baseweb="textarea"] {{
        background-color: {input_bg} !important;
        border: 1px solid {border} !important;
    }}
    input, textarea {{
        color: {text} !important;
        -webkit-text-fill-color: {text} !important;
    }}

    /* Release Butonu (Siyah kutu içinde siyah yazıyı engelleme) */
    div.stButton > button {{
        background-color: {text} !important; 
        color: {bg} !important;
        border: none !important;
        font-weight: 500 !important;
    }}
    
    /* Genel Yazı Tipi ve Rengi */
    h1, h2, h3, p, span, label {{ 
        color: {text} !important; 
        font-family: 'Jost', sans-serif !important; 
    }}
    </style>
    """, unsafe_allow_html=True)
