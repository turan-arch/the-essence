"""
Still — A sanctuary for individuals. Not companies, not brands. People.
"""

import streamlit as st
import sqlite3
import os
import base64
import json
import hashlib
import uuid
from datetime import datetime
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
DB_PATH    = "still.db"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "avatars").mkdir(exist_ok=True)
(UPLOAD_DIR / "media").mkdir(exist_ok=True)

ATMO_TAGS = [
    "Sabah ışığı", "Gölgede", "Arıyorum", "Yalnızlık",
    "Derin su", "Yarım kalmış", "Sessizlik", "Teslim olmak",
    "Kırılmak", "Şafaktan önce", "Fırtınadan sonra", "Yapı",
    "Çözülmek", "Narin", "Tutulan nefes", "Merak",
    "Özlem", "Huzur", "Karmaşa", "Yeniden başlamak",
]

FEELINGS = [
    "Sakin", "Hüzünlü", "Umutlu", "Kaygılı", "Minnettar",
    "Şaşkın", "Yorgun", "Dingin", "Öfkeli", "Meraklı",
    "Nostaljik", "Hafif", "Ağır", "Kayıp", "Burada",
]

# ── Database ────────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        username     TEXT    UNIQUE NOT NULL,
        email        TEXT    UNIQUE NOT NULL,
        password     TEXT    NOT NULL,
        display_name TEXT    NOT NULL,
        pronouns     TEXT,
        bio          TEXT,
        essence      TEXT,
        obsessions   TEXT,
        song         TEXT,
        quote        TEXT,
        avatar_path  TEXT,
        created_at   TEXT    DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS follows (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        follower_id INTEGER NOT NULL,
        followed_id INTEGER NOT NULL,
        created_at  TEXT    DEFAULT (datetime('now')),
        UNIQUE(follower_id, followed_id),
        FOREIGN KEY(follower_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(followed_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS posts (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        text_content    TEXT,
        soul            TEXT,
        feeling         TEXT,
        atmo_tags       TEXT    DEFAULT '[]',
        media_path      TEXT,
        media_type      TEXT,
        is_sensitive    INTEGER DEFAULT 0,
        resonance_count INTEGER DEFAULT 0,
        created_at      TEXT    DEFAULT (datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS resonances (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id    INTEGER NOT NULL,
        user_id    INTEGER NOT NULL,
        created_at TEXT    DEFAULT (datetime('now')),
        UNIQUE(post_id, user_id),
        FOREIGN KEY(post_id) REFERENCES posts(id)  ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id)  ON DELETE CASCADE
    );
    """)
    conn.commit()
    _seed_demo(conn)
    conn.close()

def _seed_demo(conn):
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        return
    demo_users = [
        ("elia",  "elia@still.here",  _hash("demo"),  "Elia Voss",   "they/them",
         "Işığı takip ederim. Hep ederdim.",
         "Yerde uzanan ışık dikdörtgenleri, yarı okunmuş kitaplar, eski kağıt kokusu",
         "Weightless – Marconi Union",
         "Dikkat etmek; bu bizim sonsuz ve gerçek işimiz. — Mary Oliver"),
        ("seren", "seren@still.here", _hash("demo"),  "Seren Çelik", "she/her",
         "Biçimden önce renk. Her zaman.",
         "İndigo boya, fermantasyon, Anadolu kilim geometrisi",
         "Nuvole Bianche – Einaudi",
         "Göz ilk çemberdir. — Emerson"),
        ("miro",  "miro@still.here",  _hash("demo"),  "Miro Nakai",  "he/him",
         "Sessizlik de bir beste.",
         "Saha kayıtları, wabi-sabi seramik, çevrilemeyen kelimeler",
         "Solitude Sometimes Is – Yo La Tengo",
         "Az, çoktur. — Mies van der Rohe"),
    ]
    ids = []
    for u in demo_users:
        cur = conn.execute(
            "INSERT INTO users (username,email,password,display_name,pronouns,essence,obsessions,song,quote) VALUES (?,?,?,?,?,?,?,?,?)",
            u)
        ids.append(cur.lastrowid)
    pairs = [(ids[0],ids[1]),(ids[1],ids[0]),(ids[1],ids[2]),(ids[2],ids[1]),(ids[2],ids[0]),(ids[0],ids[2])]
    for f,t in pairs:
        conn.execute("INSERT OR IGNORE INTO follows (follower_id,followed_id) VALUES (?,?)",(f,t))
    posts = [
        (ids[0], None, "Öğleden sonra 16:00'da ışık kendine katlandığı an.", "Sessizce minnettarım",  '["Sabah ışığı","Yalnızlık"]', 0),
        (ids[0], None, "Yarım kalan bir jest. Belki öyle kalmalıydı.",       "Kararsız, narin",        '["Gölgede","Yarım kalmış"]',  0),
        (ids[1], None, "İndigo fildişine karıştı. Nefesimi tuttum.",          "Saygıyla",               '["Derin su","Teslim olmak"]',  0),
        (ids[1], None, "Kaosun altındaki ızgara. Her zaman ızgara.",          "Odaklanmış, neredeyse kaygılı", '["Yapı","Arıyorum"]',   0),
        (ids[2], None, "Üç saat sessizlikten sonra bu çıktı.",                "Hem boş hem dolu",       '["Sabah ışığı","Sessizlik"]',  0),
        (ids[2], None, "Bunu kasıtlı kırdım. Kintsugi mantığı.",              "Asi, sonra huzurlu",     '["Kırılmak","Arıyorum"]',     1),
    ]
    for p in posts:
        conn.execute(
            "INSERT INTO posts (user_id,media_path,soul,feeling,atmo_tags,is_sensitive) VALUES (?,?,?,?,?,?)",
            p)
    conn.commit()

def _hash(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ── Auth helpers ────────────────────────────────────────────────────────────────
def login_user(identifier, password):
    conn = get_db()
    u = conn.execute(
        "SELECT * FROM users WHERE (username=? OR email=?) AND password=?",
        (identifier, identifier, _hash(password))
    ).fetchone()
    conn.close()
    return dict(u) if u else None

def register_user(username, email, password, display_name, pronouns):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username,email,password,display_name,pronouns) VALUES (?,?,?,?,?)",
            (username.strip().lower(), email.strip().lower(), _hash(password),
             display_name.strip(), pronouns.strip())
        )
        conn.commit()
        u = conn.execute("SELECT * FROM users WHERE username=?", (username.strip().lower(),)).fetchone()
        conn.close()
        return dict(u), None
    except sqlite3.IntegrityError as e:
        conn.close()
        if "username" in str(e): return None, "Bu kullanıcı adı alınmış."
        if "email"    in str(e): return None, "Bu e-posta zaten kayıtlı."
        return None, "Kayıt başarısız."

def get_user_by_id(uid):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return dict(u) if u else None

def get_user_by_username(username):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(u) if u else None

def update_profile(uid, **kwargs):
    fields = {k: v for k, v in kwargs.items()
              if k in ("display_name","pronouns","bio","essence","obsessions","song","quote","avatar_path")}
    if not fields: return
    conn = get_db()
    conn.execute(
        f"UPDATE users SET {', '.join(f'{k}=?' for k in fields)} WHERE id=?",
        list(fields.values()) + [uid]
    )
    conn.commit()
    conn.close()

# ── Follow helpers ──────────────────────────────────────────────────────────────
def is_following(follower_id, followed_id):
    conn = get_db()
    r = conn.execute("SELECT id FROM follows WHERE follower_id=? AND followed_id=?",
                     (follower_id, followed_id)).fetchone()
    conn.close()
    return r is not None

def toggle_follow(follower_id, followed_id):
    conn = get_db()
    if is_following(follower_id, followed_id):
        conn.execute("DELETE FROM follows WHERE follower_id=? AND followed_id=?", (follower_id, followed_id))
    else:
        conn.execute("INSERT OR IGNORE INTO follows (follower_id,followed_id) VALUES (?,?)", (follower_id, followed_id))
    conn.commit()
    conn.close()

def get_following_ids(uid):
    conn = get_db()
    rows = conn.execute("SELECT followed_id FROM follows WHERE follower_id=?", (uid,)).fetchall()
    conn.close()
    return [r["followed_id"] for r in rows]

def get_follower_count(uid):
    conn = get_db()
    c = conn.execute("SELECT COUNT(*) FROM follows WHERE followed_id=?", (uid,)).fetchone()[0]
    conn.close()
    return c

def get_following_count(uid):
    conn = get_db()
    c = conn.execute("SELECT COUNT(*) FROM follows WHERE follower_id=?", (uid,)).fetchone()[0]
    conn.close()
    return c

# ── Post helpers ────────────────────────────────────────────────────────────────
def create_post(user_id, text_content=None, soul=None, feeling=None,
                atmo_tags=None, media_path=None, media_type=None, is_sensitive=0):
    conn = get_db()
    conn.execute(
        "INSERT INTO posts (user_id,text_content,soul,feeling,atmo_tags,media_path,media_type,is_sensitive) VALUES (?,?,?,?,?,?,?,?)",
        (user_id, text_content, soul, feeling, json.dumps(atmo_tags or []), media_path, media_type, int(is_sensitive))
    )
    conn.commit()
    conn.close()

def _post_query(where_clause, params, limit=30):
    conn = get_db()
    rows = conn.execute(f"""
        SELECT p.*, u.display_name, u.username, u.avatar_path, u.pronouns
        FROM posts p JOIN users u ON p.user_id=u.id
        WHERE {where_clause}
        ORDER BY p.created_at DESC LIMIT ?
    """, params + [limit]).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_feed_posts(uid, limit=30):
    ids = get_following_ids(uid) + [uid]
    ph  = ",".join("?" * len(ids))
    return _post_query(f"p.user_id IN ({ph})", ids, limit)

def get_discover_posts(uid, limit=30):
    ids = get_following_ids(uid) + [uid]
    ph  = ",".join("?" * len(ids))
    conn = get_db()
    rows = conn.execute(f"""
        SELECT p.*, u.display_name, u.username, u.avatar_path, u.pronouns
        FROM posts p JOIN users u ON p.user_id=u.id
        WHERE p.user_id NOT IN ({ph})
        ORDER BY p.resonance_count DESC, p.created_at DESC LIMIT ?
    """, ids + [limit]).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_posts(uid, limit=50):
    return _post_query("p.user_id=?", [uid], limit)

def has_resonated(post_id, user_id):
    conn = get_db()
    r = conn.execute("SELECT id FROM resonances WHERE post_id=? AND user_id=?",
                     (post_id, user_id)).fetchone()
    conn.close()
    return r is not None

def toggle_resonance(post_id, user_id):
    conn = get_db()
    if has_resonated(post_id, user_id):
        conn.execute("DELETE FROM resonances WHERE post_id=? AND user_id=?", (post_id, user_id))
        conn.execute("UPDATE posts SET resonance_count=MAX(0,resonance_count-1) WHERE id=?", (post_id,))
    else:
        conn.execute("INSERT OR IGNORE INTO resonances (post_id,user_id) VALUES (?,?)", (post_id, user_id))
        conn.execute("UPDATE posts SET resonance_count=resonance_count+1 WHERE id=?", (post_id,))
    conn.commit()
    conn.close()

# ── Media helpers ───────────────────────────────────────────────────────────────
def save_media(uploaded_file, subdir="media"):
    if uploaded_file is None: return None, None
    ext   = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else "bin"
    fname = f"{uuid.uuid4().hex}.{ext}"
    path  = UPLOAD_DIR / subdir / fname
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    mtype = ("image" if ext in ("jpg","jpeg","png","webp","gif","svg") else
             "video" if ext in ("mp4","mov","webm") else
             "audio" if ext in ("mp3","wav","ogg","m4a") else "file")
    return str(path), mtype

def load_b64(path):
    if not path or not os.path.exists(path): return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def get_mime(path):
    if not path: return "image/jpeg"
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","webp":"image/webp",
            "gif":"image/gif","svg":"image/svg+xml","mp4":"video/mp4","mov":"video/quicktime",
            "webm":"video/webm","mp3":"audio/mpeg","wav":"audio/wav","ogg":"audio/ogg",
            "m4a":"audio/mp4"}.get(ext, "application/octet-stream")

def placeholder_avatar(name, size=80):
    initials = "".join(w[0].upper() for w in (name or "?").split()[:2])
    color    = ["#8C7B6E","#7A8C7A","#8C7B8C","#8C8C7B","#7B8C8C","#A89070"][hash(name or "") % 6]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
           f'<circle cx="{size//2}" cy="{size//2}" r="{size//2}" fill="{color}" opacity=".85"/>'
           f'<text x="50%" y="50%" dominant-baseline="central" text-anchor="middle" '
           f'font-family="Cormorant Garamond,serif" font-size="{size//3}" font-weight="300" '
           f'fill="#F7F4EF" opacity=".95">{initials}</text></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

def fmt_time(dt_str):
    if not dt_str: return ""
    try:
        dt   = datetime.fromisoformat(dt_str)
        diff = datetime.utcnow() - dt
        s    = diff.total_seconds()
        if s < 60:    return "şimdi"
        if s < 3600:  return f"{int(s//60)}d"
        if s < 86400: return f"{int(s//3600)}s"
        return dt.strftime("%d %b")
    except:
        return dt_str[:10]

# ── CSS ─────────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&family=DM+Sans:ital,wght@0,200;0,300;0,400;1,300&display=swap');

:root{
  --bg:#F4F0E8; --surface:#EDE8DF; --surface2:#E6E0D5; --card:#F9F6F1;
  --border:rgba(50,40,30,.10); --border2:rgba(50,40,30,.06);
  --ink:#1C1A17; --ash:#5C564F; --dust:#9C948A; --earth:#7A6B5A;
  --blush:#C4A898; --gold:#B89A6A; --sage:#6A7C6A;
  --serif:'Cormorant Garamond',Georgia,serif; --sans:'DM Sans',sans-serif;
  --r:6px; --r-lg:12px;
  --sh:0 1px 12px rgba(30,25,20,.07);
  --sh-md:0 4px 24px rgba(30,25,20,.10);
  --sh-lg:0 8px 40px rgba(30,25,20,.14);
  --t:all .25s cubic-bezier(.4,0,.2,1);
}
*,*::before,*::after{box-sizing:border-box}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"],.main .block-container{
  background:var(--bg)!important; font-family:var(--sans); font-weight:300; color:var(--ink);
}
[data-testid="stSidebar"]{background:var(--surface)!important; border-right:1px solid var(--border)!important;}
[data-testid="stSidebar"]>div:first-child{padding-top:0!important}
#MainMenu,footer,header,[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"]{display:none!important}
.main .block-container{padding:1.5rem 2rem 5rem!important; max-width:760px!important}
::-webkit-scrollbar{width:5px} ::-webkit-scrollbar-track{background:transparent} ::-webkit-scrollbar-thumb{background:rgba(50,40,30,.12);border-radius:3px}
h1,h2,h3{font-family:var(--serif)!important; font-weight:300!important; letter-spacing:.03em}
*:focus-visible{outline:2px solid var(--earth)!important; outline-offset:2px!important}

/* Wordmark */
.wm{font-family:var(--serif);font-size:1.8rem;font-weight:300;letter-spacing:.32em;color:var(--ink);text-transform:uppercase;line-height:1;padding:1.8rem 1.2rem .35rem;display:block}
.wm-sub{font-family:var(--sans);font-size:.58rem;font-weight:300;letter-spacing:.25em;color:var(--dust);text-transform:uppercase;padding:0 1.2rem 1.6rem;display:block}
.nav-div{border:none;border-top:1px solid var(--border);margin:.7rem 1.2rem}
.nav-sec{font-family:var(--sans);font-size:.58rem;letter-spacing:.22em;text-transform:uppercase;color:var(--dust);padding:.8rem 1.2rem .3rem}
.nav-user{display:flex;align-items:center;gap:.7rem;padding:.8rem 1.2rem 1.2rem}
.nav-uname{font-family:var(--serif);font-size:.98rem;font-weight:400;color:var(--ink);line-height:1.2}
.nav-uhandle{font-family:var(--sans);font-size:.64rem;color:var(--dust);letter-spacing:.05em}

/* Buttons */
.stButton>button{font-family:var(--sans)!important;font-size:.7rem!important;font-weight:300!important;letter-spacing:.13em!important;text-transform:uppercase!important;border-radius:var(--r)!important;transition:var(--t)!important;padding:.52rem 1.4rem!important;border:1px solid var(--border)!important;background:var(--card)!important;color:var(--ash)!important;box-shadow:none!important}
.stButton>button:hover{background:var(--surface2)!important;color:var(--ink)!important}
.stButton>button[kind="primary"]{background:var(--ink)!important;color:var(--bg)!important;border-color:var(--ink)!important}
.stButton>button[kind="primary"]:hover{background:var(--earth)!important;border-color:var(--earth)!important}

/* Form labels */
.stTextInput>label,.stTextArea>label,.stSelectbox>label,.stMultiSelect>label,.stFileUploader>label{font-family:var(--serif)!important;font-style:italic!important;font-size:.95rem!important;color:var(--ash)!important;font-weight:300!important}
.stTextInput input,.stTextArea textarea{background:var(--card)!important;border:1px solid var(--border)!important;border-radius:var(--r)!important;font-family:var(--sans)!important;font-weight:300!important;font-size:.87rem!important;color:var(--ink)!important;box-shadow:none!important;transition:var(--t)!important}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:var(--earth)!important;box-shadow:0 0 0 3px rgba(122,107,90,.1)!important}
[data-testid="stFileUploader"] section{background:var(--card)!important;border:1px dashed rgba(50,40,30,.18)!important;border-radius:var(--r)!important}
[data-testid="stFileUploader"] section:hover{border-color:var(--earth)!important}
[data-baseweb="select"]>div{background:var(--card)!important;border:1px solid var(--border)!important;border-radius:var(--r)!important}
.stMultiSelect [data-baseweb="tag"]{background:var(--surface2)!important;color:var(--earth)!important;border:1px solid rgba(122,107,90,.25)!important;font-family:var(--sans)!important;font-size:.65rem!important}
[data-testid="stAlert"]{background:var(--card)!important;border:1px solid var(--border)!important;border-radius:var(--r)!important;font-family:var(--sans)!important;font-size:.83rem!important;font-weight:300!important}
.stCheckbox label{font-family:var(--sans)!important;font-size:.83rem!important;font-weight:300!important;color:var(--ash)!important}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid var(--border)!important;gap:0!important}
.stTabs [data-baseweb="tab"]{font-family:var(--sans)!important;font-size:.67rem!important;letter-spacing:.14em!important;text-transform:uppercase!important;font-weight:300!important;color:var(--dust)!important;background:transparent!important;border:none!important;border-bottom:2px solid transparent!important;padding:.6rem 1.1rem!important;margin-bottom:-1px!important}
.stTabs [aria-selected="true"]{color:var(--ink)!important;border-bottom-color:var(--ink)!important}

/* Post card */
.pc{background:var(--card);border:1px solid var(--border2);border-radius:var(--r-lg);padding:1.2rem 1.4rem 1rem;margin-bottom:1rem;box-shadow:var(--sh);transition:var(--t);position:relative;overflow:hidden}
.pc::before{content:'';position:absolute;top:0;left:0;width:3px;height:100%;background:linear-gradient(to bottom,var(--blush),transparent);opacity:0;transition:var(--t)}
.pc:hover{box-shadow:var(--sh-md)} .pc:hover::before{opacity:1}
.ph{display:flex;align-items:center;gap:.75rem;margin-bottom:.9rem}
.pav{width:38px;height:38px;border-radius:50%;object-fit:cover;flex-shrink:0;border:1px solid var(--border)}
.pmeta{flex:1;min-width:0}
.pname{font-family:var(--serif);font-size:.98rem;font-weight:400;color:var(--ink);line-height:1.2;cursor:pointer;transition:color .2s}
.pname:hover{color:var(--earth)}
.phandle{font-size:.64rem;font-weight:300;color:var(--dust);letter-spacing:.05em}
.ptime{font-size:.64rem;color:var(--dust);flex-shrink:0}
.psoul{font-family:var(--serif);font-size:1.08rem;font-style:italic;font-weight:300;color:var(--ink);line-height:1.65;margin-bottom:.55rem}
.ptext{font-family:var(--sans);font-size:.87rem;font-weight:300;color:var(--ash);line-height:1.7;margin-bottom:.65rem;white-space:pre-wrap}
.pfeeling{display:inline-flex;align-items:center;gap:.3rem;font-size:.64rem;font-weight:300;letter-spacing:.1em;color:var(--dust);text-transform:uppercase;margin-bottom:.65rem}
.pdot{width:5px;height:5px;border-radius:50%;background:var(--blush);flex-shrink:0}
.ptags{display:flex;flex-wrap:wrap;gap:.3rem;margin-bottom:.8rem}
.ptag{font-size:.6rem;font-weight:300;letter-spacing:.12em;text-transform:uppercase;color:var(--earth);border:1px solid rgba(122,107,90,.22);padding:.11rem .48rem;border-radius:20px;background:rgba(122,107,90,.04)}
.pmedia{border-radius:var(--r);overflow:hidden;margin:.75rem 0;border:1px solid var(--border2)}
.pmedia img,.pmedia video{width:100%;display:block;max-height:420px;object-fit:cover}
.pmedia audio{width:100%;padding:.5rem 0}
.pfoot{display:flex;align-items:center;justify-content:space-between;padding-top:.65rem;border-top:1px solid var(--border2);margin-top:.2rem}

/* Sensitive */
.sens-wrap{position:relative;border-radius:var(--r);overflow:hidden;margin:.75rem 0}
.sens-img{filter:blur(22px);transition:filter .4s;width:100%;display:block;max-height:420px;object-fit:cover}
.sens-overlay{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(28,26,23,.38);backdrop-filter:blur(2px);cursor:pointer}
.sens-label{font-family:var(--sans);font-size:.7rem;font-weight:300;letter-spacing:.15em;text-transform:uppercase;color:#F7F4EF;border:1px solid rgba(247,244,239,.4);padding:.38rem .95rem;border-radius:20px;margin-top:.45rem}

/* Auth */
.auth-title{font-family:var(--serif);font-size:2.5rem;font-weight:300;letter-spacing:.32em;text-transform:uppercase;color:var(--ink);text-align:center;margin-bottom:.3rem}
.auth-sub{font-family:var(--sans);font-size:.62rem;font-weight:300;letter-spacing:.2em;text-transform:uppercase;color:var(--dust);text-align:center;margin-bottom:1.8rem}

/* Profile hero */
.prof-hero{background:var(--card);border:1px solid var(--border2);border-radius:var(--r-lg);padding:1.8rem 2rem;box-shadow:var(--sh);margin-bottom:1.4rem}
.prof-hd{display:flex;align-items:flex-start;gap:1.2rem;margin-bottom:1.1rem}
.prof-av{width:72px;height:72px;border-radius:50%;object-fit:cover;border:2px solid var(--border);flex-shrink:0}
.prof-name{font-family:var(--serif);font-size:1.75rem;font-weight:300;color:var(--ink);line-height:1.1;margin-bottom:.12rem}
.prof-pro{font-family:var(--sans);font-size:.63rem;font-weight:300;letter-spacing:.18em;text-transform:uppercase;color:var(--dust);margin-bottom:.35rem}
.prof-ess{font-family:var(--serif);font-size:.98rem;font-style:italic;color:var(--ash);line-height:1.6;border-left:2px solid var(--blush);padding-left:.85rem;margin:.85rem 0}
.cab-grid{display:grid;grid-template-columns:1fr 1fr;gap:.9rem;margin-top:1rem}
.cab-label{font-family:var(--sans);font-size:.59rem;font-weight:300;letter-spacing:.2em;text-transform:uppercase;color:var(--dust);margin-bottom:.18rem}
.cab-val{font-family:var(--serif);font-size:.93rem;color:var(--ink)}
.stats{display:flex;gap:1.4rem;margin:.4rem 0 .8rem}
.stat-v{font-family:var(--serif);font-size:1.25rem;font-weight:300;color:var(--ink);display:block}
.stat-l{font-family:var(--sans);font-size:.59rem;font-weight:300;letter-spacing:.15em;text-transform:uppercase;color:var(--dust)}

/* Section heads */
.stitle{font-family:var(--serif);font-size:1.45rem;font-weight:300;font-style:italic;color:var(--ink);margin-bottom:.15rem}
.ssub{font-family:var(--sans);font-size:.6rem;font-weight:300;letter-spacing:.2em;text-transform:uppercase;color:var(--dust);margin-bottom:1.3rem}
.intro{font-family:var(--serif);font-size:1rem;font-style:italic;font-weight:300;color:var(--ash);line-height:1.75;margin-bottom:1.6rem;border-left:2px solid var(--blush);padding-left:.95rem}

/* Empty */
.empty{text-align:center;padding:3rem 1rem}
.empty-s{font-size:1.8rem;color:var(--dust);margin-bottom:.7rem}
.empty-t{font-family:var(--serif);font-size:1.02rem;font-style:italic;color:var(--dust);line-height:1.7}

/* Discover user rows */
.urow{display:flex;align-items:center;gap:.8rem;background:var(--card);border:1px solid var(--border2);border-radius:var(--r);padding:.75rem .95rem;box-shadow:var(--sh);margin-bottom:.55rem}
.urow-name{font-family:var(--serif);font-size:.95rem;font-weight:400;color:var(--ink)}
.urow-ess{font-family:var(--sans);font-size:.68rem;font-weight:300;color:var(--dust);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

@media(max-width:640px){
  .main .block-container{padding:1rem 1rem 4rem!important}
  .cab-grid{grid-template-columns:1fr}
}
</style>
"""

# ── Render helpers ──────────────────────────────────────────────────────────────
def av_html(path, name, size=38, cls="pav"):
    if path and os.path.exists(path):
        b64  = load_b64(path)
        mime = get_mime(path)
        src  = f"data:{mime};base64,{b64}"
    else:
        src = placeholder_avatar(name, size)
    return f'<img src="{src}" class="{cls}" alt="{name} profil fotoğrafı" width="{size}" height="{size}"/>'

def render_post(post, cur_uid, kpfx=""):
    pid  = post["id"]
    soul = post.get("soul") or ""
    text = post.get("text_content") or ""
    feel = post.get("feeling") or ""
    tags = json.loads(post.get("atmo_tags") or "[]")
    mp   = post.get("media_path")
    mt   = post.get("media_type")
    sens = bool(post.get("is_sensitive"))
    rc   = post.get("resonance_count", 0)
    uname= post.get("username","")
    dname= post.get("display_name","?")
    ap   = post.get("avatar_path")
    pt   = fmt_time(post.get("created_at",""))
    res  = has_resonated(pid, cur_uid) if cur_uid else False

    ava   = av_html(ap, dname, 38)
    t_html= "".join(f'<span class="ptag">{t}</span>' for t in tags)
    f_html= f'<div class="pfeeling"><span class="pdot"></span>{feel}</div>' if feel else ""

    media_html = ""
    if mp and os.path.exists(mp):
        b64  = load_b64(mp)
        mime = get_mime(mp)
        iid  = f"s{pid}{kpfx}"
        if mt == "image":
            if sens:
                media_html = f"""
                <div class="sens-wrap">
                  <img class="sens-img" id="si{iid}" src="data:{mime};base64,{b64}" alt="hassas görsel"/>
                  <div class="sens-overlay" id="so{iid}"
                    role="button" tabindex="0" aria-label="Hassas içeriği göster"
                    onclick="document.getElementById('si{iid}').style.filter='none';this.style.display='none'"
                    onkeydown="if(event.key==='Enter'||event.key===' '){{document.getElementById('si{iid}').style.filter='none';this.style.display='none'}}">
                    <span style="font-size:1.3rem;color:#F7F4EF">⚠</span>
                    <span class="sens-label">Hassas içerik — görmek için dokun</span>
                  </div>
                </div>"""
            else:
                media_html = f'<div class="pmedia"><img src="data:{mime};base64,{b64}" alt="gönderi görseli" loading="lazy"/></div>'
        elif mt == "video":
            media_html = f'<div class="pmedia"><video controls preload="metadata"><source src="data:{mime};base64,{b64}" type="{mime}"/></video></div>'
        elif mt == "audio":
            media_html = f'<div class="pmedia"><audio controls style="width:100%;padding:.5rem 0"><source src="data:{mime};base64,{b64}" type="{mime}"/></audio></div>'
        else:
            fname = (mp or "").rsplit("/",1)[-1]
            media_html = f'<div style="background:var(--surface2);border-radius:var(--r);padding:.65rem .95rem;font-size:.8rem;color:var(--ash);margin:.75rem 0">📎 {fname}</div>'

    st.markdown(f"""
    <article class="pc" aria-label="{dname} gönderisi">
      <div class="ph">
        {ava}
        <div class="pmeta">
          <div class="pname" role="link" tabindex="0"
            onclick="window.parent.location.search='?vu={uname}'"
            onkeydown="if(event.key==='Enter')window.parent.location.search='?vu={uname}'">{dname}</div>
          <div class="phandle">@{uname}</div>
        </div>
        <span class="ptime">{pt}</span>
      </div>
      {f'<p class="psoul">"{soul}"</p>' if soul else ''}
      {f'<p class="ptext">{text}</p>' if text else ''}
      {f_html}
      {media_html}
      {f'<div class="ptags">{t_html}</div>' if t_html else ''}
    </article>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        rlbl = f"{'◈' if res else '◇'}  {rc}" if rc else ("◈" if res else "◇")
        if st.button(rlbl, key=f"r{pid}{kpfx}", help="Bu çalışmayla yankılandım"):
            if cur_uid:
                toggle_resonance(pid, cur_uid)
                st.rerun()
    with c2:
        if st.button(f"→ @{uname}", key=f"gp{pid}{kpfx}", help="Profili gör"):
            st.session_state.view_user = uname
            st.session_state.page = "profile_view"
            st.rerun()

# ── Pages ───────────────────────────────────────────────────────────────────────
def page_auth():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;padding:2.5rem 0 1rem"><div class="auth-title">Still</div><div class="auth-sub">bir bireyin sığınağı</div></div>', unsafe_allow_html=True)

    t1, t2 = st.tabs(["Giriş Yap", "Katıl"])
    with t1:
        with st.form("lf"):
            ident = st.text_input("Kullanıcı adı veya e-posta")
            pw    = st.text_input("Parola", type="password")
            if st.form_submit_button("İçeri gir", use_container_width=True, type="primary"):
                u = login_user(ident, pw)
                if u:
                    st.session_state.user = u
                    st.session_state.page = "feed"
                    st.rerun()
                else:
                    st.error("Bilgiler eşleşmiyor.")
        st.markdown('<p style="font-family:\'DM Sans\',sans-serif;font-size:.74rem;font-weight:300;color:#9C948A;text-align:center;margin-top:.6rem">Demo: <b>elia</b> / <b>demo</b></p>', unsafe_allow_html=True)

    with t2:
        st.markdown('<p style="font-family:\'Cormorant Garamond\',serif;font-style:italic;font-size:.9rem;color:#9C948A;margin-bottom:1rem;line-height:1.65">Şirketler ve markalar buraya adım atamaz.<br>Yalnızca bireyler — tam olarak kendin.</p>', unsafe_allow_html=True)
        with st.form("rf"):
            c1, c2 = st.columns(2)
            with c1: uname = st.text_input("Kullanıcı adı")
            with c2: pro   = st.text_input("Zamirler (isteğe bağlı)", placeholder="o/ona")
            dname = st.text_input("Görünen isim")
            email = st.text_input("E-posta")
            pw1   = st.text_input("Parola", type="password")
            pw2   = st.text_input("Parola tekrar", type="password")
            if st.form_submit_button("Adım at", use_container_width=True, type="primary"):
                if not all([uname,dname,email,pw1]):
                    st.error("Tüm alanları doldur.")
                elif pw1 != pw2:
                    st.error("Parolalar eşleşmiyor.")
                elif len(pw1) < 6:
                    st.error("Parola en az 6 karakter olmalı.")
                else:
                    u, err = register_user(uname, email, pw1, dname, pro)
                    if u:
                        st.session_state.user = u
                        st.session_state.page = "feed"
                        st.rerun()
                    else:
                        st.error(err)

def render_sidebar():
    u = st.session_state.user
    with st.sidebar:
        st.markdown('<span class="wm">Still</span><span class="wm-sub">var olmak yeterli</span>', unsafe_allow_html=True)
        ava = av_html(u.get("avatar_path"), u.get("display_name","?"), 40)
        st.markdown(f'<div class="nav-user">{ava}<div><div class="nav-uname">{u.get("display_name","")}</div><div class="nav-uhandle">@{u.get("username","")}</div></div></div><hr class="nav-div"/>', unsafe_allow_html=True)
        st.markdown('<div class="nav-sec">Gezin</div>', unsafe_allow_html=True)
        cur = st.session_state.get("page","feed")
        for key, lbl, tip in [
            ("feed",         "○  Akış",    "Takip ettiklerinden"),
            ("discover",     "◎  Keşfet",  "Yeni sesler"),
            ("compose",      "◈  Paylaş",  "Bir şey bırak"),
            ("profile_self", "◇  Profil",  "Kendi alanın"),
        ]:
            if st.button(lbl, key=f"nb_{key}", help=tip,
                         use_container_width=True,
                         type="primary" if cur==key else "secondary"):
                st.session_state.page = key
                st.rerun()
        st.markdown('<hr class="nav-div"/>', unsafe_allow_html=True)
        if st.button("← Çıkış", key="logout", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

def page_feed():
    u     = st.session_state.user
    posts = get_feed_posts(u["id"])
    st.markdown('<p class="stitle">Akış</p><p class="ssub">Takip ettiklerinden gelen sesler</p>', unsafe_allow_html=True)
    if not posts:
        st.markdown('<div class="empty"><div class="empty-s">○</div><p class="empty-t">Henüz kimseyi takip etmiyorsun.<br>Keşfet sayfasından yeni sesler bul.</p></div>', unsafe_allow_html=True)
        return
    for p in posts:
        render_post(p, u["id"], "fd")

def page_discover():
    u = st.session_state.user
    st.markdown('<p class="stitle">Keşfet</p><p class="ssub">Henüz tanışmadıkların</p>', unsafe_allow_html=True)

    fids = get_following_ids(u["id"]) + [u["id"]]
    ph   = ",".join("?"*len(fids))
    conn = get_db()
    sugg = conn.execute(f"SELECT * FROM users WHERE id NOT IN ({ph}) ORDER BY RANDOM() LIMIT 6", fids).fetchall()
    conn.close()

    if sugg:
        for su in sugg:
            su  = dict(su)
            ava = av_html(su.get("avatar_path"), su.get("display_name","?"), 36)
            st.markdown(f'<div class="urow">{ava}<div style="flex:1;min-width:0"><div class="urow-name">{su["display_name"]}</div><div class="urow-ess">{su.get("essence") or su.get("bio") or "@"+su["username"]}</div></div></div>', unsafe_allow_html=True)
            c1, c2 = st.columns([1,1])
            with c1:
                already = is_following(u["id"], su["id"])
                if st.button("Takipten çık" if already else "Takip et", key=f"fl_{su['id']}", use_container_width=True):
                    toggle_follow(u["id"], su["id"]); st.rerun()
            with c2:
                if st.button("Profil →", key=f"vp_{su['id']}", use_container_width=True):
                    st.session_state.view_user = su["username"]
                    st.session_state.page = "profile_view"
                    st.rerun()
        st.markdown('<hr style="border:none;border-top:1px solid var(--border);margin:1.4rem 0"/>', unsafe_allow_html=True)

    posts = get_discover_posts(u["id"])
    if not posts:
        st.markdown('<div class="empty"><div class="empty-s">◎</div><p class="empty-t">Keşfedilecek yeni şey yok şimdilik.</p></div>', unsafe_allow_html=True)
        return
    for p in posts:
        render_post(p, u["id"], "dc")

def page_compose():
    st.markdown('<p class="stitle">Bir şey bırak</p><p class="ssub">Performans değil — varoluş</p>', unsafe_allow_html=True)
    with st.form("cf", clear_on_submit=True):
        soul  = st.text_area("Bu çalışmanın ruhu nedir?",
                              placeholder="Zeminde katlanan ışık, tarif edilemeyen bir şey...", height=90)
        text  = st.text_area("Söylemek istediğin bir şey var mı? (isteğe bağlı)",
                              placeholder="Düşünceler, kelimeler, parçalar...", height=75)
        feel  = st.selectbox("Şu an nasıl hissediyorsun?", ["—"] + FEELINGS)
        tags  = st.multiselect("Atmosfer etiketleri (en fazla 4)", ATMO_TAGS, max_selections=4)
        mfile = st.file_uploader(
            "Bir şey yükle — görsel, ses, video, dosya (isteğe bağlı)",
            type=["jpg","jpeg","png","webp","gif","svg","mp4","mov","webm","mp3","wav","ogg","m4a","pdf","txt","md","zip"]
        )
        sens  = st.checkbox("⚠  Bu içerik hassas olabilir — otomatik bulanık gösterilir, izleyici isterse açar")
        if sens:
            st.markdown('<div style="background:rgba(184,154,106,.08);border:1px solid rgba(184,154,106,.22);border-radius:6px;padding:.65rem .95rem;font-size:.78rem;color:#7A6B5A;font-family:\'DM Sans\',sans-serif;font-weight:300;">Instagram\'daki gibi — içerik bulanık gösterilir, okuyucu görmek isterse açar.</div>', unsafe_allow_html=True)

        if st.form_submit_button("Bırak burada", type="primary", use_container_width=True):
            if not soul.strip() and not text.strip() and not mfile:
                st.error("En azından bir şey bırakmalısın.")
            else:
                mp, mt = save_media(mfile) if mfile else (None, None)
                create_post(
                    user_id=st.session_state.user["id"],
                    text_content=text.strip() or None,
                    soul=soul.strip() or None,
                    feeling=feel if feel != "—" else None,
                    atmo_tags=tags, media_path=mp, media_type=mt,
                    is_sensitive=sens
                )
                st.success("Bırakıldı. ○")
                st.balloons()

def page_profile_self():
    u   = st.session_state.user
    uid = u["id"]
    fresh = get_user_by_id(uid)
    if fresh: st.session_state.user = fresh; u = fresh

    t1, t2 = st.tabs(["Profilim", "Düzenle"])
    with t1:
        _profile_view(u, uid, is_own=True)
    with t2:
        st.markdown('<p class="stitle">Profili düzenle</p><p class="ssub">Kim olduğunu söyle — ne yaptığını değil</p>', unsafe_allow_html=True)
        avf = st.file_uploader("Profil fotoğrafı yükle", type=["jpg","jpeg","png","webp"])
        if avf:
            path, _ = save_media(avf, "avatars")
            update_profile(uid, avatar_path=path)
            st.session_state.user = get_user_by_id(uid)
            st.success("Fotoğraf güncellendi."); st.rerun()
        with st.form("epf"):
            dn = st.text_input("Görünen isim",  value=u.get("display_name",""))
            pr = st.text_input("Zamirler",       value=u.get("pronouns","") or "")
            bi = st.text_area("Biyografi",       value=u.get("bio","") or "", height=80,
                               placeholder="Kendini anlat, kısaca veya uzunca...")
            es = st.text_input("Özün — tek cümle", value=u.get("essence","") or "",
                                placeholder="Işığı takip ederim. Hep ederdim.")
            ob = st.text_area("Merak dolabı",    value=u.get("obsessions","") or "", height=70,
                               placeholder="Şu an takıntılı olduğun şeyler...")
            so = st.text_input("Döngüdeki şarkı",value=u.get("song","") or "")
            qu = st.text_area("Seni dengede tutan söz", value=u.get("quote","") or "", height=70)
            if st.form_submit_button("Kaydet", type="primary", use_container_width=True):
                update_profile(uid, display_name=dn.strip(), pronouns=pr.strip(),
                                bio=bi.strip(), essence=es.strip(), obsessions=ob.strip(),
                                song=so.strip(), quote=qu.strip())
                st.session_state.user = get_user_by_id(uid)
                st.success("Profil güncellendi."); st.rerun()

def page_profile_view():
    cur_uid  = st.session_state.user["id"]
    username = st.session_state.get("view_user")
    if not username:
        st.session_state.page = "discover"; st.rerun(); return
    target = get_user_by_username(username)
    if not target:
        st.error("Kullanıcı bulunamadı."); return
    if st.button("← Geri", key="back_pv"):
        st.session_state.page = "discover"; st.rerun()
    _profile_view(target, cur_uid, is_own=(target["id"]==cur_uid))

def _profile_view(user, viewer_uid, is_own=False):
    uid   = user["id"]
    posts = get_user_posts(uid)
    fc    = get_follower_count(uid)
    fwc   = get_following_count(uid)
    ava   = av_html(user.get("avatar_path"), user.get("display_name","?"), 72, "prof-av")

    if not is_own:
        already = is_following(viewer_uid, uid)
        if st.button("Takipten çık" if already else "Takip et", key=f"fl_pv_{uid}"):
            toggle_follow(viewer_uid, uid); st.rerun()

    bio_html = f'<p style="font-family:\'DM Sans\',sans-serif;font-size:.84rem;font-weight:300;color:#5C564F;line-height:1.7;margin-bottom:.75rem">{user["bio"]}</p>' if user.get("bio") else ""
    ess_html = f'<p class="prof-ess">{user["essence"]}</p>' if user.get("essence") else ""
    ob_html  = f'<div class="cab-label">Merak dolabı</div><div class="cab-val">{user["obsessions"]}</div>' if user.get("obsessions") else ""
    so_html  = f'<div class="cab-label">Döngüdeki şarkı</div><div class="cab-val">{user["song"]}</div>' if user.get("song") else ""
    qu_html  = f'<div style="grid-column:span 2"><div class="cab-label">Dengede tutan söz</div><div class="cab-val" style="font-family:\'Cormorant Garamond\',serif;font-style:italic">{user["quote"]}</div></div>' if user.get("quote") else ""

    st.markdown(f"""
    <div class="prof-hero">
      <div class="prof-hd">
        {ava}
        <div style="flex:1">
          <div class="prof-name">{user.get("display_name","")}</div>
          <div class="prof-pro">{user.get("pronouns") or ""}</div>
          <div class="stats">
            <div><span class="stat-v">{len(posts)}</span><span class="stat-l">Artifact</span></div>
            <div><span class="stat-v">{fc}</span><span class="stat-l">Takipçi</span></div>
            <div><span class="stat-v">{fwc}</span><span class="stat-l">Takip</span></div>
          </div>
        </div>
      </div>
      {bio_html}{ess_html}
      <div class="cab-grid">
        {"<div>"+ob_html+"</div>" if ob_html else ""}
        {"<div>"+so_html+"</div>" if so_html else ""}
        {qu_html}
      </div>
    </div>
    """, unsafe_allow_html=True)

    if not posts:
        st.markdown('<div class="empty"><div class="empty-s">○</div><p class="empty-t">Henüz hiçbir şey bırakılmamış.</p></div>', unsafe_allow_html=True)
        return
    for p in posts:
        render_post(p, viewer_uid, f"pv{uid}")

# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="Still", page_icon="○", layout="wide",
                        initial_sidebar_state="expanded")
    init_db()

    if "page" not in st.session_state: st.session_state.page = "auth"
    if "user" not in st.session_state: st.session_state.user = None

    st.markdown(CSS, unsafe_allow_html=True)

    if not st.session_state.user:
        page_auth(); return

    render_sidebar()

    pg = st.session_state.get("page","feed")
    if   pg == "feed":         page_feed()
    elif pg == "discover":     page_discover()
    elif pg == "compose":      page_compose()
    elif pg == "profile_self": page_profile_self()
    elif pg == "profile_view": page_profile_view()
    else:                      page_feed()

if __name__ == "__main__":
    main()
