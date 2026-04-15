import streamlit as st
import sqlite3
import os
import base64
import json
from datetime import datetime
from pathlib import Path
import io

# ── Configuration ──────────────────────────────────────────────────────────────
DB_PATH = "still.db"
UPLOAD_DIR = "artifacts"
Path(UPLOAD_DIR).mkdir(exist_ok=True)

# ── Database ───────────────────────────────────────────────────────────────────
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
            pronouns TEXT,
            essence TEXT,
            obsessions TEXT,
            song_looping TEXT,
            grounding_quote TEXT,
            avatar_path TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            image_path TEXT,
            soul TEXT,
            feeling TEXT,
            atmo_tags TEXT,
            resonance_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(profile_id) REFERENCES profiles(id)
        );

        CREATE TABLE IF NOT EXISTS resonances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artifact_id INTEGER,
            session_id TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()

def seed_demo_data():
    """Seed with poetic demo data if DB is empty."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM profiles").fetchone()[0] > 0:
        conn.close()
        return

    profiles = [
        ("Elia Voss", "they/them", "I follow light across floors.",
         "moss, half-read books, the smell of old paper",
         "Weightless – Marconi Union",
         "To pay attention, this is our endless and proper work. — Mary Oliver",
         None),
        ("Seren Çelik", "she/her", "Colour before form. Always.",
         "indigo dye, fermentation, Anatolian kilim geometry",
         "Nuvole Bianche – Einaudi",
         "The eye is the first circle. — Emerson",
         None),
        ("Miro Nakai", "he/him", "Silence is also a composition.",
         "field recordings, wabi-sabi ceramics, untranslatable words",
         "Solitude Sometimes Is – Yo La Tengo",
         "Less is more. — Mies van der Rohe",
         None),
    ]

    for p in profiles:
        c.execute("""INSERT INTO profiles (name, pronouns, essence, obsessions, song_looping, grounding_quote, avatar_path)
                     VALUES (?,?,?,?,?,?,?)""", p)

    conn.commit()
    pid = [1, 2, 3]

    artifacts = [
        (pid[0], None, "The moment light folded into itself at 4 PM.",
         "Quietly grateful", '["Morning light", "Solitude"]', 7),
        (pid[0], None, "An unfinished gesture. Maybe it should stay that way.",
         "Uncertain, tender", '["In the shadows", "Unfinished"]', 3),
        (pid[1], None, "Indigo bleeding into ivory. I held my breath.",
         "Reverent", '["Deep water", "Yielding"]', 12),
        (pid[1], None, "The grid beneath the chaos. Always the grid.",
         "Focused, almost anxious", '["Seeking", "Structure"]', 5),
        (pid[2], None, "After three hours of silence, this emerged.",
         "Empty and full at once", '["Morning light", "Still"]', 9),
        (pid[2], None, "I cracked this on purpose. Kintsugi logic.",
         "Defiant, then at peace", '["Broken open", "Seeking"]', 14),
    ]

    for a in artifacts:
        c.execute("""INSERT INTO artifacts (profile_id, image_path, soul, feeling, atmo_tags, resonance_count)
                     VALUES (?,?,?,?,?,?)""", a)

    conn.commit()
    conn.close()

# ── Helpers ────────────────────────────────────────────────────────────────────
def save_image(uploaded_file):
    if uploaded_file is None:
        return None
    ext = uploaded_file.name.split(".")[-1]
    filename = f"{UPLOAD_DIR}/{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.{ext}"
    with open(filename, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return filename

def load_image_b64(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def get_placeholder_svg(seed=0):
    """Generate organic placeholder art."""
    palettes = [
        ["#C9B8A8", "#8C7B6E", "#E8DDD0"],
        ["#7B8C7A", "#4A5E4A", "#C4CDB5"],
        ["#8C7B8C", "#5E4A5E", "#CDB5CD"],
        ["#8C8C7B", "#5E5E4A", "#CDCDB5"],
        ["#7B8C8C", "#4A5E5E", "#B5CDCD"],
    ]
    p = palettes[seed % len(palettes)]
    shapes = ""
    import random
    rng = random.Random(seed)
    for _ in range(6):
        x = rng.randint(0, 300)
        y = rng.randint(0, 400)
        r = rng.randint(30, 120)
        op = rng.uniform(0.2, 0.6)
        c = rng.choice(p)
        shapes += f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}" opacity="{op:.2f}"/>\n'
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="300" height="400" viewBox="0 0 300 400">
        <rect width="300" height="400" fill="{p[2]}"/>
        {shapes}
    </svg>"""
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

def has_resonated(artifact_id):
    sid = st.session_state.get("session_id", "")
    conn = get_db()
    r = conn.execute("SELECT id FROM resonances WHERE artifact_id=? AND session_id=?",
                     (artifact_id, sid)).fetchone()
    conn.close()
    return r is not None

def toggle_resonance(artifact_id):
    sid = st.session_state.get("session_id", "anon")
    conn = get_db()
    if has_resonated(artifact_id):
        conn.execute("DELETE FROM resonances WHERE artifact_id=? AND session_id=?", (artifact_id, sid))
        conn.execute("UPDATE artifacts SET resonance_count = resonance_count - 1 WHERE id=?", (artifact_id,))
    else:
        conn.execute("INSERT INTO resonances (artifact_id, session_id) VALUES (?,?)", (artifact_id, sid))
        conn.execute("UPDATE artifacts SET resonance_count = resonance_count + 1 WHERE id=?", (artifact_id,))
    conn.commit()
    conn.close()

ATMOSPHERIC_TAGS = [
    "Morning light", "In the shadows", "Seeking", "Solitude",
    "Deep water", "Unfinished", "Still", "Yielding", "Broken open",
    "Before dawn", "After the storm", "Structure", "Dissolving",
    "Tender", "Held breath",
]

# ── CSS ────────────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&family=Jost:wght@300;400&display=swap');

:root {
    --parchment:   #F2EDE4;
    --ivory:       #EDE8DF;
    --warm-white:  #F7F4EF;
    --charcoal:    #2C2C2C;
    --ash:         #6B6560;
    --dust:        #9E9890;
    --earth:       #7A6B5A;
    --sage:        #7A8C7A;
    --blush:       #C4A898;
    --ink:         #1A1A18;
    --rule:        rgba(44,44,44,0.10);
    --serif:       'Cormorant Garamond', Georgia, serif;
    --sans:        'Jost', sans-serif;
    --radius:      2px;
    --shadow:      0 2px 20px rgba(44,44,44,0.07);
    --shadow-hover: 0 8px 40px rgba(44,44,44,0.13);
}

/* ── Reset ── */
html, body, [data-testid="stAppViewContainer"] {
    background: var(--warm-white) !important;
    color: var(--charcoal);
    font-family: var(--sans);
    font-weight: 300;
}

[data-testid="stSidebar"] {
    background: var(--parchment) !important;
    border-right: 1px solid var(--rule);
}

[data-testid="stSidebar"] * { color: var(--charcoal) !important; }

/* Hide Streamlit chrome */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }

/* ── Typography ── */
h1, h2, h3 {
    font-family: var(--serif) !important;
    font-weight: 300 !important;
    letter-spacing: 0.04em;
    color: var(--ink);
}

/* ── Wordmark ── */
.still-wordmark {
    font-family: var(--serif);
    font-size: 2.4rem;
    font-weight: 300;
    letter-spacing: 0.35em;
    color: var(--charcoal);
    text-transform: uppercase;
    margin: 0;
    padding: 2rem 0 0.3rem 0;
}

.still-tagline {
    font-family: var(--sans);
    font-size: 0.68rem;
    font-weight: 300;
    letter-spacing: 0.28em;
    color: var(--dust);
    text-transform: uppercase;
    margin: 0 0 2rem 0;
}

.still-divider {
    border: none;
    border-top: 1px solid var(--rule);
    margin: 1.5rem 0;
}

/* ── Nav pills ── */
.nav-item {
    font-family: var(--sans);
    font-size: 0.72rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ash);
    padding: 0.5rem 0;
    cursor: pointer;
    border: none;
    background: none;
    display: block;
    width: 100%;
    text-align: left;
    transition: color 0.3s ease;
}

/* ── Masonry Grid ── */
.masonry-grid {
    columns: 3;
    column-gap: 1.4rem;
    padding: 1rem 0;
}

@media (max-width: 1100px) { .masonry-grid { columns: 2; } }
@media (max-width: 700px)  { .masonry-grid { columns: 1; } }

.artifact-card {
    break-inside: avoid;
    background: var(--ivory);
    border: 1px solid rgba(44,44,44,0.07);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    margin-bottom: 1.4rem;
    overflow: hidden;
    transition: box-shadow 0.4s ease, transform 0.4s ease;
    display: inline-block;
    width: 100%;
}

.artifact-card:hover {
    box-shadow: var(--shadow-hover);
    transform: translateY(-3px);
}

.artifact-img {
    width: 100%;
    display: block;
    object-fit: cover;
}

.artifact-body {
    padding: 1.1rem 1.3rem 1rem 1.3rem;
}

.artifact-soul {
    font-family: var(--serif);
    font-size: 1.05rem;
    font-style: italic;
    font-weight: 300;
    color: var(--ink);
    line-height: 1.55;
    margin-bottom: 0.5rem;
}

.artifact-feeling {
    font-family: var(--sans);
    font-size: 0.72rem;
    font-weight: 300;
    letter-spacing: 0.08em;
    color: var(--dust);
    margin-bottom: 0.8rem;
}

.artifact-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-bottom: 0.85rem;
}

.atmo-tag {
    font-family: var(--sans);
    font-size: 0.62rem;
    font-weight: 300;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--earth);
    border: 1px solid rgba(122,107,90,0.3);
    padding: 0.15rem 0.55rem;
    border-radius: 20px;
    background: rgba(122,107,90,0.04);
}

.artifact-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 0.5rem;
    border-top: 1px solid var(--rule);
}

.creator-name {
    font-family: var(--serif);
    font-size: 0.85rem;
    font-weight: 400;
    color: var(--ash);
    letter-spacing: 0.05em;
}

.artifact-date {
    font-family: var(--sans);
    font-size: 0.62rem;
    color: var(--dust);
    letter-spacing: 0.1em;
}

/* ── Resonance button ── */
.resonate-btn {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.1rem;
    opacity: 0.5;
    transition: opacity 0.3s, transform 0.3s;
    padding: 0;
    line-height: 1;
}
.resonate-btn:hover { opacity: 1; transform: scale(1.2); }
.resonate-btn.resonated { opacity: 1; color: var(--blush); }

/* ── Profile card ── */
.profile-card {
    background: var(--ivory);
    border: 1px solid rgba(44,44,44,0.07);
    padding: 2rem 2.2rem;
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    margin-bottom: 2rem;
}

.profile-name {
    font-family: var(--serif);
    font-size: 2.2rem;
    font-weight: 300;
    color: var(--ink);
    margin: 0 0 0.1rem 0;
}

.profile-pronouns {
    font-family: var(--sans);
    font-size: 0.72rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--dust);
    margin-bottom: 0.8rem;
}

.profile-essence {
    font-family: var(--serif);
    font-size: 1.15rem;
    font-style: italic;
    color: var(--ash);
    line-height: 1.6;
    margin-bottom: 1.5rem;
    border-left: 2px solid var(--blush);
    padding-left: 1rem;
}

.curiosity-section {
    margin-top: 1.5rem;
}

.curiosity-label {
    font-family: var(--sans);
    font-size: 0.65rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--dust);
    margin-bottom: 0.35rem;
}

.curiosity-value {
    font-family: var(--serif);
    font-size: 1rem;
    color: var(--charcoal);
    font-weight: 300;
}

/* ── Upload form ── */
.upload-section {
    background: var(--ivory);
    border: 1px solid rgba(44,44,44,0.07);
    padding: 2rem 2.2rem;
    border-radius: var(--radius);
    box-shadow: var(--shadow);
}

.form-label {
    font-family: var(--serif);
    font-size: 1.05rem;
    font-style: italic;
    color: var(--charcoal);
    margin-bottom: 0.3rem;
    display: block;
}

/* ── Streamlit widget overrides ── */
.stTextInput > label,
.stTextArea > label,
.stSelectbox > label,
.stMultiSelect > label,
.stFileUploader > label {
    font-family: var(--serif) !important;
    font-style: italic !important;
    font-size: 1rem !important;
    color: var(--charcoal) !important;
    font-weight: 300 !important;
}

.stTextInput input,
.stTextArea textarea {
    background: var(--warm-white) !important;
    border: 1px solid rgba(44,44,44,0.12) !important;
    border-radius: var(--radius) !important;
    font-family: var(--sans) !important;
    font-weight: 300 !important;
    color: var(--charcoal) !important;
    box-shadow: none !important;
}

.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: rgba(122,107,90,0.4) !important;
    box-shadow: 0 0 0 2px rgba(122,107,90,0.08) !important;
}

.stButton > button {
    background: var(--charcoal) !important;
    color: var(--warm-white) !important;
    border: none !important;
    font-family: var(--sans) !important;
    font-size: 0.72rem !important;
    font-weight: 300 !important;
    letter-spacing: 0.2em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1.8rem !important;
    border-radius: var(--radius) !important;
    transition: background 0.3s !important;
}

.stButton > button:hover {
    background: var(--earth) !important;
}

.stMultiSelect [data-baseweb="tag"] {
    background: var(--parchment) !important;
    color: var(--earth) !important;
    border: 1px solid rgba(122,107,90,0.3) !important;
    font-family: var(--sans) !important;
    font-size: 0.7rem !important;
}

/* ── Section headers ── */
.section-header {
    font-family: var(--serif);
    font-size: 1.6rem;
    font-weight: 300;
    font-style: italic;
    color: var(--charcoal);
    letter-spacing: 0.04em;
    margin: 0 0 0.2rem 0;
}

.section-sub {
    font-family: var(--sans);
    font-size: 0.68rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--dust);
    margin-bottom: 1.5rem;
}

/* ── Resonance toast ── */
.resonate-toast {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    background: var(--charcoal);
    color: var(--warm-white);
    font-family: var(--sans);
    font-size: 0.72rem;
    letter-spacing: 0.15em;
    padding: 0.8rem 1.5rem;
    border-radius: var(--radius);
    opacity: 0;
    animation: fadeToast 2.5s ease forwards;
    z-index: 9999;
}

@keyframes fadeToast {
    0%   { opacity: 0; transform: translateY(8px); }
    15%  { opacity: 1; transform: translateY(0); }
    75%  { opacity: 1; }
    100% { opacity: 0; }
}

/* ── Page intro ── */
.page-intro {
    font-family: var(--serif);
    font-size: 1.25rem;
    font-style: italic;
    font-weight: 300;
    color: var(--ash);
    line-height: 1.7;
    max-width: 600px;
    margin-bottom: 2.5rem;
    border-left: 2px solid var(--blush);
    padding-left: 1.2rem;
}

/* ── Sidebar nav ── */
.sidebar-section {
    font-family: var(--sans);
    font-size: 0.6rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--dust);
    margin: 1.5rem 0 0.4rem 0;
}

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--dust);
}

.empty-state-icon { font-size: 2.5rem; margin-bottom: 1rem; }

.empty-state-text {
    font-family: var(--serif);
    font-style: italic;
    font-size: 1.1rem;
    line-height: 1.7;
}

/* Selectbox */
[data-baseweb="select"] > div {
    background: var(--warm-white) !important;
    border: 1px solid rgba(44,44,44,0.12) !important;
    border-radius: var(--radius) !important;
}

/* File uploader */
[data-testid="stFileUploader"] section {
    background: var(--warm-white) !important;
    border: 1px dashed rgba(44,44,44,0.2) !important;
    border-radius: var(--radius) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    gap: 0.5rem;
}

.stTabs [data-baseweb="tab"] {
    font-family: var(--sans) !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    font-weight: 300 !important;
    color: var(--dust) !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 1px solid transparent !important;
    padding: 0.5rem 1rem !important;
}

.stTabs [aria-selected="true"] {
    color: var(--charcoal) !important;
    border-bottom: 1px solid var(--charcoal) !important;
}

/* Success / info messages */
[data-testid="stAlert"] {
    background: var(--parchment) !important;
    border: 1px solid rgba(44,44,44,0.08) !important;
    color: var(--charcoal) !important;
    font-family: var(--sans) !important;
    font-weight: 300 !important;
    font-size: 0.85rem !important;
    border-radius: var(--radius) !important;
}
</style>
"""

# ── Pages ──────────────────────────────────────────────────────────────────────

def render_artifact_card(artifact, profile_name, show_resonate=True):
    aid = artifact["id"]
    soul = artifact["soul"] or ""
    feeling = artifact["feeling"] or ""
    img_path = artifact["image_path"]
    tags = json.loads(artifact["atmo_tags"]) if artifact["atmo_tags"] else []
    resonance = artifact["resonance_count"] or 0
    created = artifact["created_at"][:10] if artifact["created_at"] else ""

    # Build image
    if img_path and os.path.exists(img_path):
        b64 = load_image_b64(img_path)
        img_src = f"data:image/jpeg;base64,{b64}"
    else:
        img_src = get_placeholder_svg(seed=aid)

    tags_html = "".join(f'<span class="atmo-tag">{t}</span>' for t in tags)
    resonated = has_resonated(aid)
    resonate_sym = "◈" if resonated else "◇"
    resonate_label = f"{resonate_sym} {resonance}"

    card_html = f"""
    <div class="artifact-card">
        <img class="artifact-img" src="{img_src}" loading="lazy" />
        <div class="artifact-body">
            <p class="artifact-soul">"{soul}"</p>
            <p class="artifact-feeling">{feeling}</p>
            <div class="artifact-tags">{tags_html}</div>
            <div class="artifact-footer">
                <span class="creator-name">{profile_name}</span>
                <span class="artifact-date">{created}</span>
            </div>
        </div>
    </div>
    """
    return card_html, aid, resonate_label, resonated

def page_gallery():
    st.markdown('<p class="page-intro">A quiet room for things made with hands and heart.<br>No metrics. No performance. Only presence.</p>', unsafe_allow_html=True)

    conn = get_db()
    rows = conn.execute("""
        SELECT a.*, p.name as creator_name
        FROM artifacts a
        JOIN profiles p ON a.profile_id = p.id
        ORDER BY a.created_at DESC
    """).fetchall()
    conn.close()

    if not rows:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">○</div>
            <p class="empty-state-text">The gallery awaits its first artifact.<br>
            Leave something of yourself here.</p>
        </div>""", unsafe_allow_html=True)
        return

    # Render masonry with Streamlit columns (3-col approximation)
    cards_data = []
    for row in rows:
        card_html, aid, resonate_label, resonated = render_artifact_card(row, row["creator_name"])
        cards_data.append((card_html, aid, resonate_label, resonated))

    # Distribute into 3 columns
    cols = st.columns(3, gap="medium")
    for i, (card_html, aid, resonate_label, resonated) in enumerate(cards_data):
        col = cols[i % 3]
        with col:
            st.markdown(card_html, unsafe_allow_html=True)
            btn_type = "primary" if resonated else "secondary"
            if st.button(resonate_label, key=f"res_{aid}", help="Resonate with this work"):
                toggle_resonance(aid)
                st.rerun()

def page_upload():
    st.markdown('<p class="section-header">Leave an artifact</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">An offering, not a performance</p>', unsafe_allow_html=True)

    conn = get_db()
    profiles = conn.execute("SELECT id, name FROM profiles ORDER BY name").fetchall()
    conn.close()

    if not profiles:
        st.info("Create a profile first before leaving an artifact.")
        return

    profile_names = {p["name"]: p["id"] for p in profiles}

    st.markdown('<div class="upload-section">', unsafe_allow_html=True)

    creator = st.selectbox("Who is leaving this?", list(profile_names.keys()))
    image_file = st.file_uploader("An image, a sketch, a texture — or leave empty for an abstraction",
                                   type=["png", "jpg", "jpeg", "webp", "gif"])

    soul = st.text_area("What is the soul of this work?",
                         placeholder="The light that never quite reaches the floor...",
                         height=90)

    feeling = st.text_input("How did you feel while making this?",
                             placeholder="Hovering somewhere between grief and wonder")

    atmo_tags = st.multiselect("Atmospheric tags", ATMOSPHERIC_TAGS,
                                max_selections=4,
                                help="Choose up to 4 atmospheres that live in this work")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Place it here"):
        if not soul.strip():
            st.warning("Every artifact deserves a soul, however small.")
            return
        img_path = save_image(image_file) if image_file else None
        conn = get_db()
        conn.execute("""
            INSERT INTO artifacts (profile_id, image_path, soul, feeling, atmo_tags)
            VALUES (?,?,?,?,?)
        """, (profile_names[creator], img_path, soul.strip(),
              feeling.strip(), json.dumps(atmo_tags)))
        conn.commit()
        conn.close()
        st.success("It has found its place.")
        st.balloons()

def page_profiles():
    st.markdown('<p class="section-header">The people here</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">No titles. No metrics. Only essence.</p>', unsafe_allow_html=True)

    conn = get_db()
    profiles = conn.execute("SELECT * FROM profiles ORDER BY name").fetchall()
    conn.close()

    if not profiles:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">○</div>
            <p class="empty-state-text">No one has stepped through yet.<br>Be the first to arrive.</p>
        </div>""", unsafe_allow_html=True)
        return

    for p in profiles:
        conn = get_db()
        count = conn.execute("SELECT COUNT(*) FROM artifacts WHERE profile_id=?", (p["id"],)).fetchone()[0]
        conn.close()

        st.markdown(f"""
        <div class="profile-card">
            <p class="profile-name">{p['name']}</p>
            <p class="profile-pronouns">{p['pronouns'] or ''}</p>
            <p class="profile-essence">{p['essence'] or ''}</p>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:1.2rem; margin-top:1rem;">
                <div class="curiosity-section">
                    <p class="curiosity-label">Cabinet of curiosities</p>
                    <p class="curiosity-value">{p['obsessions'] or '—'}</p>
                </div>
                <div class="curiosity-section">
                    <p class="curiosity-label">Song on loop</p>
                    <p class="curiosity-value">{p['song_looping'] or '—'}</p>
                </div>
                <div class="curiosity-section" style="grid-column: span 2">
                    <p class="curiosity-label">What keeps me grounded</p>
                    <p class="curiosity-value" style="font-style:italic; font-family:'Cormorant Garamond',serif;">
                        {p['grounding_quote'] or '—'}
                    </p>
                </div>
                <div class="curiosity-section">
                    <p class="curiosity-label">Artifacts left here</p>
                    <p class="curiosity-value">{count}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def page_new_profile():
    st.markdown('<p class="section-header">Arrive</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Tell us who you are, not what you do</p>', unsafe_allow_html=True)

    st.markdown('<div class="upload-section">', unsafe_allow_html=True)

    name = st.text_input("Your name", placeholder="Elia Voss")
    pronouns = st.text_input("Pronouns (optional)", placeholder="they/them")
    essence = st.text_area("Your essence — one sentence, as honest as you can make it",
                            placeholder="I follow light across floors.",
                            height=80)
    obsessions = st.text_area("Your cabinet of curiosities — what are you obsessed with right now?",
                               placeholder="moss, half-read books, the smell of old paper",
                               height=80)
    song = st.text_input("The song you are looping", placeholder="Weightless – Marconi Union")
    quote = st.text_area("A quote that keeps you grounded",
                          placeholder="To pay attention, this is our endless and proper work.",
                          height=70)

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Step inside"):
        if not name.strip():
            st.warning("A name is the only thing we ask for.")
            return
        conn = get_db()
        conn.execute("""
            INSERT INTO profiles (name, pronouns, essence, obsessions, song_looping, grounding_quote)
            VALUES (?,?,?,?,?,?)
        """, (name.strip(), pronouns.strip(), essence.strip(),
              obsessions.strip(), song.strip(), quote.strip()))
        conn.commit()
        conn.close()
        st.success(f"Welcome, {name}. We're glad you're here.")

def page_about():
    st.markdown("""
    <div style="max-width:600px;">
        <p class="section-header">What is Still?</p>
        <p style="font-family:'Jost',sans-serif; font-weight:300; font-size:0.85rem; 
                  color:#6B6560; letter-spacing:0.05em; line-height:1.9; margin-bottom:2rem;">
            Still is a sanctuary for those who make things.<br><br>
            There are no follower counts here. No engagement metrics. 
            No achievement badges. No algorithm deciding what deserves to be seen.<br><br>
            What you find instead: space. Silence. The quiet company of others 
            who understand that making something — anything — is enough.<br><br>
            Resonance here is not applause. It is recognition. 
            The silent nod across a room that says: <em>I felt that too.</em>
        </p>

        <hr class="still-divider" />

        <p style="font-family:'Cormorant Garamond',serif; font-style:italic; 
                  font-size:1.1rem; color:#9E9890; line-height:1.8;">
            "The quiet ones make the most interesting things."
        </p>
    </div>
    """, unsafe_allow_html=True)

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Still",
        page_icon="○",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    init_db()
    seed_demo_data()

    # Session ID for resonance tracking
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())

    if "page" not in st.session_state:
        st.session_state.page = "gallery"

    # Inject CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown('<p class="still-wordmark">Still</p>', unsafe_allow_html=True)
        st.markdown('<p class="still-tagline">A place to simply be</p>', unsafe_allow_html=True)
        st.markdown('<hr class="still-divider" />', unsafe_allow_html=True)

        st.markdown('<p class="sidebar-section">Navigate</p>', unsafe_allow_html=True)

        pages = {
            "gallery":     ("○  The Gallery",    "Where artifacts rest"),
            "profiles":    ("◇  The People",     "Those who gather here"),
            "upload":      ("◈  Leave something","An offering of your own"),
            "new_profile": ("＋  Arrive",         "Step inside for the first time"),
            "about":       ("—  About Still",    "What this place is"),
        }

        for key, (label, sub) in pages.items():
            is_active = st.session_state.page == key
            style = "color: var(--charcoal);" if is_active else ""
            if st.button(label, key=f"nav_{key}", use_container_width=True,
                         help=sub, type="primary" if is_active else "secondary"):
                st.session_state.page = key
                st.rerun()

        st.markdown('<hr class="still-divider" />', unsafe_allow_html=True)

        conn = get_db()
        artifact_count = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
        profile_count  = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
        conn.close()

        st.markdown(f"""
        <div style="font-family:'Jost',sans-serif; font-size:0.68rem; 
                    letter-spacing:0.15em; color:var(--dust); line-height:2.2;">
            <span style="text-transform:uppercase;">{artifact_count} artifacts</span><br>
            <span style="text-transform:uppercase;">{profile_count} souls present</span>
        </div>
        """, unsafe_allow_html=True)

    # ── Main content ──
    page = st.session_state.page

    if page == "gallery":
        page_gallery()
    elif page == "upload":
        page_upload()
    elif page == "profiles":
        page_profiles()
    elif page == "new_profile":
        page_new_profile()
    elif page == "about":
        page_about()

if __name__ == "__main__":
    main()
