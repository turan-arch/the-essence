"""
Still — A sanctuary for individuals. Production-ready with security hardening.
"""

import streamlit as st
import sqlite3
import os
import re
import base64
import json
import hashlib
import hmac
import secrets
import uuid
import html
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURATION  (edit these before deploying)
# ─────────────────────────────────────────────────────────────────────────────
DB_PATH        = "still.db"
UPLOAD_DIR     = Path("uploads")
MAX_FILE_MB    = 20          # max upload size
ADMIN_USERNAME = "admin"    # change this
ADMIN_PASSWORD = "change_me_please"  # CHANGE BEFORE DEPLOY
# ─────────────────────────────────────────────────────────────────────────────

UPLOAD_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "avatars").mkdir(exist_ok=True)
(UPLOAD_DIR / "media").mkdir(exist_ok=True)

ALLOWED_EXT = {
    "image": {"jpg","jpeg","png","webp","gif"},
    "video": {"mp4","mov","webm"},
    "audio": {"mp3","wav","ogg","m4a"},
    "file":  {"pdf","txt","md"},
}
ALL_ALLOWED = {e for s in ALLOWED_EXT.values() for e in s}

ATMO_TAGS = [
    "Morning light","In the shadows","Seeking","Solitude",
    "Deep water","Unfinished","Stillness","Yielding",
    "Broken open","Before dawn","After the storm","Structure",
    "Dissolving","Tender","Held breath","Wonder",
    "Longing","At peace","Chaos","Beginning again",
]

FEELINGS = [
    "Calm","Melancholy","Hopeful","Anxious","Grateful",
    "Surprised","Tired","Serene","Restless","Curious",
    "Nostalgic","Light","Heavy","Lost","Present",
]

REPORT_REASONS = [
    "Harmful or dangerous content",
    "Hateful or discriminatory content",
    "Harassment or bullying",
    "Spam or misleading content",
    "Graphic violence",
    "Sexual content",
    "Privacy violation",
    "Impersonation",
    "Other",
]

# ─────────────────────────────────────────────────────────────────────────────
#  SECURITY UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 with per-user salt stored together."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), 260_000)
    return f"{salt}:{dk.hex()}"

def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, dk_hex = stored.split(":", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), 260_000)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False

def _sanitize(text: str, max_len: int = 2000) -> str:
    """Escape HTML and truncate."""
    if not text:
        return ""
    return html.escape(str(text).strip())[:max_len]

def _validate_username(username: str) -> tuple[bool, str]:
    u = username.strip().lower()
    if len(u) < 3:
        return False, "Username must be at least 3 characters."
    if len(u) > 30:
        return False, "Username must be 30 characters or fewer."
    if not re.fullmatch(r"[a-z0-9_\.]+", u):
        return False, "Only lowercase letters, numbers, _ and . allowed."
    if u in {"admin","still","support","moderator","mod","root","system"}:
        return False, "That username is reserved."
    return True, u

def _validate_email(email: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip().lower()))

def _validate_file(uploaded_file) -> tuple[bool, str, str]:
    """Returns (ok, media_type, error_message)."""
    if uploaded_file is None:
        return True, None, None
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    if ext not in ALL_ALLOWED:
        return False, None, f"File type '.{ext}' is not allowed."
    size_mb = uploaded_file.size / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        return False, None, f"File exceeds {MAX_FILE_MB} MB limit."
    for mt, exts in ALLOWED_EXT.items():
        if ext in exts:
            return True, mt, None
    return False, None, "Unknown file type."

# ─────────────────────────────────────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────────────────────────────────────

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
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT    UNIQUE NOT NULL COLLATE NOCASE,
        email         TEXT    UNIQUE NOT NULL COLLATE NOCASE,
        password      TEXT    NOT NULL,
        display_name  TEXT    NOT NULL,
        pronouns      TEXT    DEFAULT '',
        bio           TEXT    DEFAULT '',
        essence       TEXT    DEFAULT '',
        obsessions    TEXT    DEFAULT '',
        song          TEXT    DEFAULT '',
        quote         TEXT    DEFAULT '',
        avatar_path   TEXT,
        is_banned     INTEGER DEFAULT 0,
        is_admin      INTEGER DEFAULT 0,
        failed_logins INTEGER DEFAULT 0,
        locked_until  TEXT,
        created_at    TEXT    DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS follows (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        follower_id INTEGER NOT NULL,
        followed_id INTEGER NOT NULL,
        created_at  TEXT DEFAULT (datetime('now')),
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
        is_removed      INTEGER DEFAULT 0,
        created_at      TEXT    DEFAULT (datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS resonances (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id    INTEGER NOT NULL,
        user_id    INTEGER NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(post_id, user_id),
        FOREIGN KEY(post_id) REFERENCES posts(id)  ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id)  ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS reports (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        reporter_id INTEGER NOT NULL,
        post_id     INTEGER NOT NULL,
        reason      TEXT    NOT NULL,
        detail      TEXT,
        status      TEXT    DEFAULT 'pending',
        reviewed_at TEXT,
        created_at  TEXT    DEFAULT (datetime('now')),
        FOREIGN KEY(reporter_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(post_id)     REFERENCES posts(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS sessions (
        token      TEXT PRIMARY KEY,
        user_id    INTEGER NOT NULL,
        created_at TEXT    DEFAULT (datetime('now')),
        expires_at TEXT    NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_posts_user   ON posts(user_id);
    CREATE INDEX IF NOT EXISTS idx_follows_flwr ON follows(follower_id);
    CREATE INDEX IF NOT EXISTS idx_reports_stat ON reports(status);
    """)
    conn.commit()
    _seed_demo(conn)
    conn.close()

def _seed_demo(conn):
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        return
    demo = [
        ("elia",  "elia@still.here",  "Elia Voss",   "they/them",
         "I follow light across floors.",
         "rectangles of light on wood, half-read books, the smell of old paper",
         "Weightless – Marconi Union",
         "To pay attention, this is our endless and proper work. — Mary Oliver"),
        ("seren", "seren@still.here", "Seren Çelik", "she/her",
         "Colour before form. Always.",
         "indigo dye, fermentation, Anatolian kilim geometry",
         "Nuvole Bianche – Einaudi",
         "The eye is the first circle. — Emerson"),
        ("miro",  "miro@still.here",  "Miro Nakai",  "he/him",
         "Silence is also a composition.",
         "field recordings, wabi-sabi ceramics, untranslatable words",
         "Solitude Sometimes Is – Yo La Tengo",
         "Less is more. — Mies van der Rohe"),
    ]
    ids = []
    for d in demo:
        cur = conn.execute(
            "INSERT INTO users (username,email,password,display_name,pronouns,essence,obsessions,song,quote) VALUES (?,?,?,?,?,?,?,?,?)",
            (d[0], d[1], _hash_password("demo123"), d[2], d[3], d[4], d[5], d[6], d[7]))
        ids.append(cur.lastrowid)
    for f, t in [(0,1),(1,0),(1,2),(2,1),(2,0),(0,2)]:
        conn.execute("INSERT OR IGNORE INTO follows (follower_id,followed_id) VALUES (?,?)", (ids[f], ids[t]))
    posts = [
        (ids[0], None, "The moment light folded into itself at 4 PM.", "Quietly grateful",  '["Morning light","Solitude"]',    0),
        (ids[0], None, "An unfinished gesture. Maybe it should stay that way.", "Uncertain, tender", '["In the shadows","Unfinished"]', 0),
        (ids[1], None, "Indigo bleeding into ivory. I held my breath.",         "Reverent",          '["Deep water","Yielding"]',       0),
        (ids[1], None, "The grid beneath the chaos. Always the grid.",           "Focused, almost anxious", '["Structure","Seeking"]',  0),
        (ids[2], None, "After three hours of silence, this emerged.",            "Empty and full at once",  '["Morning light","Stillness"]', 0),
        (ids[2], None, "I cracked this on purpose. Kintsugi logic.",             "Defiant, then at peace",  '["Broken open","Seeking"]',     1),
    ]
    for p in posts:
        conn.execute("INSERT INTO posts (user_id,media_path,soul,feeling,atmo_tags,is_sensitive) VALUES (?,?,?,?,?,?)", p)
    conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
#  AUTH / SESSION
# ─────────────────────────────────────────────────────────────────────────────

def _is_locked(user: dict) -> bool:
    if user.get("locked_until"):
        try:
            return datetime.utcnow() < datetime.fromisoformat(user["locked_until"])
        except Exception:
            pass
    return False

def login_user(identifier: str, password: str):
    conn = get_db()
    u = conn.execute(
        "SELECT * FROM users WHERE (username=? OR email=?) COLLATE NOCASE",
        (identifier.strip(), identifier.strip())
    ).fetchone()
    if not u:
        conn.close()
        return None, "Invalid credentials."
    u = dict(u)
    if u.get("is_banned"):
        conn.close()
        return None, "This account has been suspended."
    if _is_locked(u):
        conn.close()
        return None, "Account temporarily locked due to too many failed attempts. Try again later."
    if not _verify_password(password, u["password"]):
        fails = u.get("failed_logins", 0) + 1
        locked = None
        if fails >= 10:
            locked = (datetime.utcnow() + timedelta(minutes=30)).isoformat()
        conn.execute("UPDATE users SET failed_logins=?, locked_until=? WHERE id=?",
                     (fails, locked, u["id"]))
        conn.commit()
        conn.close()
        return None, "Invalid credentials."
    conn.execute("UPDATE users SET failed_logins=0, locked_until=NULL WHERE id=?", (u["id"],))
    conn.commit()
    conn.close()
    return u, None

def register_user(username, email, password, display_name, pronouns):
    ok, uname_or_err = _validate_username(username)
    if not ok:
        return None, uname_or_err
    if not _validate_email(email):
        return None, "Please enter a valid email address."
    if len(password) < 8:
        return None, "Password must be at least 8 characters."
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username,email,password,display_name,pronouns) VALUES (?,?,?,?,?)",
            (uname_or_err, email.strip().lower(), _hash_password(password),
             _sanitize(display_name, 60), _sanitize(pronouns, 30))
        )
        conn.commit()
        u = conn.execute("SELECT * FROM users WHERE username=?", (uname_or_err,)).fetchone()
        conn.close()
        return dict(u), None
    except sqlite3.IntegrityError as e:
        conn.close()
        if "username" in str(e).lower():
            return None, "That username is already taken."
        if "email" in str(e).lower():
            return None, "That email is already registered."
        return None, "Registration failed. Please try again."

def get_user_by_id(uid):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return dict(u) if u else None

def get_user_by_username(username):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone()
    conn.close()
    return dict(u) if u else None

def update_profile(uid, **kwargs):
    safe = {}
    limits = {"display_name":60,"pronouns":30,"bio":500,"essence":200,
              "obsessions":300,"song":100,"quote":300,"avatar_path":500}
    for k, v in kwargs.items():
        if k in limits:
            safe[k] = _sanitize(str(v), limits[k]) if k != "avatar_path" else str(v)
    if not safe:
        return
    conn = get_db()
    conn.execute(
        f"UPDATE users SET {', '.join(f'{k}=?' for k in safe)} WHERE id=?",
        list(safe.values()) + [uid]
    )
    conn.commit()
    conn.close()

def change_password(uid, old_pw, new_pw):
    u = get_user_by_id(uid)
    if not u or not _verify_password(old_pw, u["password"]):
        return False, "Current password is incorrect."
    if len(new_pw) < 8:
        return False, "New password must be at least 8 characters."
    conn = get_db()
    conn.execute("UPDATE users SET password=? WHERE id=?", (_hash_password(new_pw), uid))
    conn.commit()
    conn.close()
    return True, "Password updated."

# ─────────────────────────────────────────────────────────────────────────────
#  FOLLOWS
# ─────────────────────────────────────────────────────────────────────────────

def is_following(follower_id, followed_id):
    conn = get_db()
    r = conn.execute("SELECT 1 FROM follows WHERE follower_id=? AND followed_id=?",
                     (follower_id, followed_id)).fetchone()
    conn.close()
    return r is not None

def toggle_follow(follower_id, followed_id):
    if follower_id == followed_id:
        return
    conn = get_db()
    if is_following(follower_id, followed_id):
        conn.execute("DELETE FROM follows WHERE follower_id=? AND followed_id=?",
                     (follower_id, followed_id))
    else:
        conn.execute("INSERT OR IGNORE INTO follows (follower_id,followed_id) VALUES (?,?)",
                     (follower_id, followed_id))
    conn.commit()
    conn.close()

def get_following_ids(uid):
    conn = get_db()
    rows = conn.execute("SELECT followed_id FROM follows WHERE follower_id=?", (uid,)).fetchall()
    conn.close()
    return [r[0] for r in rows]

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

# ─────────────────────────────────────────────────────────────────────────────
#  POSTS
# ─────────────────────────────────────────────────────────────────────────────

def create_post(user_id, text_content=None, soul=None, feeling=None,
                atmo_tags=None, media_path=None, media_type=None, is_sensitive=0):
    conn = get_db()
    conn.execute(
        "INSERT INTO posts (user_id,text_content,soul,feeling,atmo_tags,media_path,media_type,is_sensitive) VALUES (?,?,?,?,?,?,?,?)",
        (user_id,
         _sanitize(text_content, 2000) if text_content else None,
         _sanitize(soul, 500) if soul else None,
         _sanitize(feeling, 60) if feeling else None,
         json.dumps([_sanitize(t, 50) for t in (atmo_tags or [])]),
         media_path, media_type, int(bool(is_sensitive)))
    )
    conn.commit()
    conn.close()

def delete_post(post_id, user_id):
    """Soft-delete: only owner or admin can remove."""
    conn = get_db()
    conn.execute(
        "UPDATE posts SET is_removed=1 WHERE id=? AND (user_id=? OR ? IN (SELECT id FROM users WHERE is_admin=1))",
        (post_id, user_id, user_id)
    )
    conn.commit()
    conn.close()

def _post_join_select():
    return """
        SELECT p.*, u.display_name, u.username, u.avatar_path, u.pronouns
        FROM posts p JOIN users u ON p.user_id=u.id
        WHERE p.is_removed=0 AND u.is_banned=0
    """

def get_feed_posts(uid, limit=40):
    ids = get_following_ids(uid) + [uid]
    ph  = ",".join("?" * len(ids))
    conn = get_db()
    rows = conn.execute(
        _post_join_select() + f" AND p.user_id IN ({ph}) ORDER BY p.created_at DESC LIMIT ?",
        ids + [limit]
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_discover_posts(uid, limit=40):
    ids = get_following_ids(uid) + [uid]
    ph  = ",".join("?" * len(ids))
    conn = get_db()
    rows = conn.execute(
        _post_join_select() + f" AND p.user_id NOT IN ({ph}) ORDER BY p.resonance_count DESC, p.created_at DESC LIMIT ?",
        ids + [limit]
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_posts(uid, include_removed=False):
    conn = get_db()
    where = "" if include_removed else " AND p.is_removed=0"
    rows = conn.execute(
        f"SELECT p.*, u.display_name, u.username, u.avatar_path, u.pronouns FROM posts p JOIN users u ON p.user_id=u.id WHERE p.user_id=?{where} ORDER BY p.created_at DESC LIMIT 60",
        (uid,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def has_resonated(post_id, user_id):
    conn = get_db()
    r = conn.execute("SELECT 1 FROM resonances WHERE post_id=? AND user_id=?",
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

# ─────────────────────────────────────────────────────────────────────────────
#  REPORTS
# ─────────────────────────────────────────────────────────────────────────────

def submit_report(reporter_id, post_id, reason, detail=""):
    conn = get_db()
    # Prevent spam: max 3 reports per user per post
    existing = conn.execute(
        "SELECT COUNT(*) FROM reports WHERE reporter_id=? AND post_id=?",
        (reporter_id, post_id)
    ).fetchone()[0]
    if existing >= 3:
        conn.close()
        return False, "You've already reported this post."
    conn.execute(
        "INSERT INTO reports (reporter_id,post_id,reason,detail) VALUES (?,?,?,?)",
        (reporter_id, post_id, reason, _sanitize(detail, 500))
    )
    conn.commit()
    conn.close()
    return True, "Report submitted. Thank you for helping keep Still safe."

def get_pending_reports(limit=100):
    conn = get_db()
    rows = conn.execute("""
        SELECT r.*,
               ru.username  AS reporter_username,
               ru.display_name AS reporter_name,
               pu.username  AS post_author_username,
               pu.display_name AS post_author_name,
               p.soul, p.text_content, p.media_type, p.is_removed
        FROM reports r
        JOIN users ru ON r.reporter_id=ru.id
        JOIN posts p  ON r.post_id=p.id
        JOIN users pu ON p.user_id=pu.id
        WHERE r.status='pending'
        ORDER BY r.created_at ASC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_reports(limit=200):
    conn = get_db()
    rows = conn.execute("""
        SELECT r.*,
               ru.username AS reporter_username,
               pu.username AS post_author_username,
               p.soul, p.text_content, p.is_removed
        FROM reports r
        JOIN users ru ON r.reporter_id=ru.id
        JOIN posts p  ON r.post_id=p.id
        JOIN users pu ON p.user_id=pu.id
        ORDER BY r.created_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def resolve_report(report_id, action, admin_uid):
    """Actions: dismiss | remove_post | ban_user"""
    conn = get_db()
    report = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    if not report:
        conn.close()
        return False, "Report not found."
    report = dict(report)
    if action == "remove_post":
        conn.execute("UPDATE posts SET is_removed=1 WHERE id=?", (report["post_id"],))
    elif action == "ban_user":
        conn.execute("UPDATE posts SET is_removed=1 WHERE id=?", (report["post_id"],))
        # Get post author
        post = conn.execute("SELECT user_id FROM posts WHERE id=?", (report["post_id"],)).fetchone()
        if post:
            conn.execute("UPDATE users SET is_banned=1 WHERE id=?", (post["user_id"],))
    conn.execute(
        "UPDATE reports SET status=?, reviewed_at=? WHERE id=?",
        (action, datetime.utcnow().isoformat(), report_id)
    )
    conn.commit()
    conn.close()
    return True, "Done."

def get_report_stats():
    conn = get_db()
    stats = {}
    stats["pending"] = conn.execute("SELECT COUNT(*) FROM reports WHERE status='pending'").fetchone()[0]
    stats["total"]   = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    stats["users"]   = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned=0").fetchone()[0]
    stats["posts"]   = conn.execute("SELECT COUNT(*) FROM posts WHERE is_removed=0").fetchone()[0]
    conn.close()
    return stats

# ─────────────────────────────────────────────────────────────────────────────
#  MEDIA
# ─────────────────────────────────────────────────────────────────────────────

def save_media(uploaded_file, subdir="media") -> tuple:
    if uploaded_file is None:
        return None, None
    ok, media_type, err = _validate_file(uploaded_file)
    if not ok:
        return None, None
    ext   = uploaded_file.name.rsplit(".", 1)[-1].lower()
    fname = f"{uuid.uuid4().hex}.{ext}"
    path  = UPLOAD_DIR / subdir / fname
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(path), media_type

def load_b64(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def get_mime(path):
    if not path:
        return "image/jpeg"
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return {
        "jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","webp":"image/webp",
        "gif":"image/gif","mp4":"video/mp4","mov":"video/quicktime","webm":"video/webm",
        "mp3":"audio/mpeg","wav":"audio/wav","ogg":"audio/ogg","m4a":"audio/mp4",
        "pdf":"application/pdf",
    }.get(ext, "application/octet-stream")

def placeholder_avatar(name, size=80):
    initials = "".join(w[0].upper() for w in (name or "?").split()[:2])
    color    = ["#8C7B6E","#7A8C7A","#8C7B8C","#8C8C7B","#7B8C8C","#A89070"][abs(hash(name or "")) % 6]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
           f'<circle cx="{size//2}" cy="{size//2}" r="{size//2}" fill="{color}"/>'
           f'<text x="50%" y="50%" dominant-baseline="central" text-anchor="middle" '
           f'font-family="Cormorant Garamond,serif" font-size="{size//3}" fill="#F7F4EF">{initials}</text>'
           f'</svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

def fmt_time(dt_str):
    if not dt_str:
        return ""
    try:
        dt   = datetime.fromisoformat(dt_str)
        diff = datetime.utcnow() - dt
        s    = diff.total_seconds()
        if s < 60:    return "just now"
        if s < 3600:  return f"{int(s//60)}m"
        if s < 86400: return f"{int(s//3600)}h"
        if s < 604800:return f"{int(s//86400)}d"
        return dt.strftime("%b %d")
    except Exception:
        return dt_str[:10]

# ─────────────────────────────────────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────────────────────────────────────

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&family=DM+Sans:ital,wght@0,200;0,300;0,400;1,300&display=swap');

:root{
  --bg:#F4F0E8; --surface:#EDE8DF; --surface2:#E6E0D5; --card:#F9F6F1;
  --border:rgba(50,40,30,.10); --border2:rgba(50,40,30,.06);
  --ink:#1C1A17; --ash:#5C564F; --dust:#9C948A; --earth:#7A6B5A;
  --blush:#C4A898; --gold:#B89A6A; --danger:#B85A5A; --success:#5A8C6A;
  --serif:'Cormorant Garamond',Georgia,serif;
  --sans:'DM Sans',sans-serif;
  --r:6px; --r-lg:12px;
  --sh:0 1px 12px rgba(30,25,20,.07);
  --sh-md:0 4px 24px rgba(30,25,20,.11);
  --sh-lg:0 8px 40px rgba(30,25,20,.15);
  --t:all .22s cubic-bezier(.4,0,.2,1);
}
*,*::before,*::after{box-sizing:border-box}

html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"],.main .block-container{
  background:var(--bg)!important;
  font-family:var(--sans);
  font-weight:300;
  color:var(--ink);
}
[data-testid="stSidebar"]{
  background:var(--surface)!important;
  border-right:1px solid var(--border)!important;
}
[data-testid="stSidebar"]>div:first-child{padding-top:0!important}

#MainMenu,footer,header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"]{display:none!important}

.main .block-container{
  padding:1.5rem 2rem 5rem!important;
  max-width:720px!important;
}
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(50,40,30,.13);border-radius:3px}

h1,h2,h3{font-family:var(--serif)!important;font-weight:300!important;letter-spacing:.03em}
*:focus-visible{outline:2px solid var(--earth)!important;outline-offset:2px!important}

/* ── Wordmark ── */
.wm{font-family:var(--serif);font-size:1.75rem;font-weight:300;letter-spacing:.32em;
    color:var(--ink);text-transform:uppercase;line-height:1;padding:1.8rem 1.2rem .3rem;display:block}
.wm-sub{font-family:var(--sans);font-size:.57rem;font-weight:300;letter-spacing:.25em;
        color:var(--dust);text-transform:uppercase;padding:0 1.2rem 1.5rem;display:block}
.nav-div{border:none;border-top:1px solid var(--border);margin:.7rem 1.2rem}
.nav-sec{font-family:var(--sans);font-size:.57rem;letter-spacing:.22em;text-transform:uppercase;
         color:var(--dust);padding:.8rem 1.2rem .25rem}
.nav-user{display:flex;align-items:center;gap:.65rem;padding:.8rem 1.2rem 1.1rem}
.nav-uname{font-family:var(--serif);font-size:.96rem;font-weight:400;color:var(--ink);line-height:1.2}
.nav-uhandle{font-family:var(--sans);font-size:.63rem;color:var(--dust);letter-spacing:.05em}
.nav-badge{background:var(--danger);color:#fff;font-size:.55rem;font-weight:400;
           letter-spacing:.08em;padding:.1rem .4rem;border-radius:10px;margin-left:.4rem}

/* ── Buttons ── */
.stButton>button{
  font-family:var(--sans)!important;font-size:.7rem!important;font-weight:300!important;
  letter-spacing:.13em!important;text-transform:uppercase!important;
  border-radius:var(--r)!important;transition:var(--t)!important;
  padding:.52rem 1.4rem!important;border:1px solid var(--border)!important;
  background:var(--card)!important;color:var(--ash)!important;box-shadow:none!important;
}
.stButton>button:hover{background:var(--surface2)!important;color:var(--ink)!important}
.stButton>button[kind="primary"]{
  background:var(--ink)!important;color:var(--bg)!important;border-color:var(--ink)!important;
}
.stButton>button[kind="primary"]:hover{background:var(--earth)!important;border-color:var(--earth)!important}

/* ── Forms ── */
.stTextInput>label,.stTextArea>label,.stSelectbox>label,
.stMultiSelect>label,.stFileUploader>label{
  font-family:var(--serif)!important;font-style:italic!important;
  font-size:.93rem!important;color:var(--ash)!important;font-weight:300!important;
}
.stTextInput input,.stTextArea textarea{
  background:var(--card)!important;border:1px solid var(--border)!important;
  border-radius:var(--r)!important;font-family:var(--sans)!important;
  font-weight:300!important;font-size:.87rem!important;color:var(--ink)!important;
  box-shadow:none!important;transition:var(--t)!important;
}
.stTextInput input:focus,.stTextArea textarea:focus{
  border-color:var(--earth)!important;
  box-shadow:0 0 0 3px rgba(122,107,90,.1)!important;
}
[data-testid="stFileUploader"] section{
  background:var(--card)!important;border:1px dashed rgba(50,40,30,.18)!important;
  border-radius:var(--r)!important;
}
[data-testid="stFileUploader"] section:hover{border-color:var(--earth)!important}
[data-baseweb="select"]>div{
  background:var(--card)!important;border:1px solid var(--border)!important;
  border-radius:var(--r)!important;
}
.stMultiSelect [data-baseweb="tag"]{
  background:var(--surface2)!important;color:var(--earth)!important;
  border:1px solid rgba(122,107,90,.25)!important;
  font-family:var(--sans)!important;font-size:.64rem!important;
}
[data-testid="stAlert"]{
  background:var(--card)!important;border:1px solid var(--border)!important;
  border-radius:var(--r)!important;font-family:var(--sans)!important;
  font-size:.82rem!important;font-weight:300!important;
}
.stCheckbox label{
  font-family:var(--sans)!important;font-size:.82rem!important;
  font-weight:300!important;color:var(--ash)!important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"]{
  background:transparent!important;border-bottom:1px solid var(--border)!important;gap:0!important;
}
.stTabs [data-baseweb="tab"]{
  font-family:var(--sans)!important;font-size:.66rem!important;letter-spacing:.14em!important;
  text-transform:uppercase!important;font-weight:300!important;color:var(--dust)!important;
  background:transparent!important;border:none!important;
  border-bottom:2px solid transparent!important;
  padding:.58rem 1rem!important;margin-bottom:-1px!important;
}
.stTabs [aria-selected="true"]{color:var(--ink)!important;border-bottom-color:var(--ink)!important}

/* ── Post card ── */
.pc{
  background:var(--card);border:1px solid var(--border2);
  border-radius:var(--r-lg);padding:1.15rem 1.35rem .95rem;
  margin-bottom:.9rem;box-shadow:var(--sh);
  transition:var(--t);position:relative;overflow:hidden;
}
.pc::before{
  content:'';position:absolute;top:0;left:0;width:3px;height:100%;
  background:linear-gradient(to bottom,var(--blush),transparent);
  opacity:0;transition:var(--t);
}
.pc:hover{box-shadow:var(--sh-md)}
.pc:hover::before{opacity:1}
.ph{display:flex;align-items:center;gap:.7rem;margin-bottom:.85rem}
.pav{width:36px;height:36px;border-radius:50%;object-fit:cover;
     flex-shrink:0;border:1px solid var(--border)}
.pmeta{flex:1;min-width:0}
.pname{font-family:var(--serif);font-size:.96rem;font-weight:400;
       color:var(--ink);line-height:1.2;cursor:pointer;transition:color .2s}
.pname:hover{color:var(--earth)}
.phandle{font-size:.63rem;font-weight:300;color:var(--dust);letter-spacing:.04em}
.ptime{font-size:.62rem;color:var(--dust);flex-shrink:0}
.psoul{font-family:var(--serif);font-size:1.07rem;font-style:italic;
       font-weight:300;color:var(--ink);line-height:1.6;margin-bottom:.5rem}
.ptext{font-family:var(--sans);font-size:.86rem;font-weight:300;
       color:var(--ash);line-height:1.7;margin-bottom:.6rem;white-space:pre-wrap}
.pfeeling{display:inline-flex;align-items:center;gap:.28rem;font-size:.63rem;
          font-weight:300;letter-spacing:.1em;color:var(--dust);
          text-transform:uppercase;margin-bottom:.6rem}
.pdot{width:5px;height:5px;border-radius:50%;background:var(--blush);flex-shrink:0}
.ptags{display:flex;flex-wrap:wrap;gap:.28rem;margin-bottom:.75rem}
.ptag{font-size:.59rem;font-weight:300;letter-spacing:.11em;text-transform:uppercase;
      color:var(--earth);border:1px solid rgba(122,107,90,.22);
      padding:.1rem .45rem;border-radius:20px;background:rgba(122,107,90,.04)}
.pmedia{border-radius:var(--r);overflow:hidden;margin:.7rem 0;border:1px solid var(--border2)}
.pmedia img,.pmedia video{width:100%;display:block;max-height:420px;object-fit:cover}
.pmedia audio{width:100%;padding:.45rem 0}
.pfoot{display:flex;align-items:center;justify-content:space-between;
       padding-top:.6rem;border-top:1px solid var(--border2);margin-top:.15rem;gap:.5rem}

/* Sensitive content */
.sw{position:relative;border-radius:var(--r);overflow:hidden;margin:.7rem 0}
.simg{filter:blur(24px);transition:filter .4s;width:100%;display:block;
      max-height:420px;object-fit:cover}
.sov{position:absolute;inset:0;display:flex;flex-direction:column;
     align-items:center;justify-content:center;
     background:rgba(28,26,23,.38);backdrop-filter:blur(2px);cursor:pointer}
.slbl{font-family:var(--sans);font-size:.68rem;font-weight:300;letter-spacing:.14em;
      text-transform:uppercase;color:#F7F4EF;
      border:1px solid rgba(247,244,239,.4);
      padding:.35rem .9rem;border-radius:20px;margin-top:.4rem}

/* Auth */
.auth-wrap{min-height:75vh;display:flex;align-items:center;justify-content:center;padding:1rem}
.auth-box{background:var(--card);border:1px solid var(--border);
          border-radius:var(--r-lg);padding:2.4rem 2.6rem;
          box-shadow:var(--sh-lg);width:100%;max-width:400px}
.auth-title{font-family:var(--serif);font-size:2.4rem;font-weight:300;
            letter-spacing:.32em;text-transform:uppercase;color:var(--ink);
            text-align:center;margin-bottom:.3rem}
.auth-sub{font-family:var(--sans);font-size:.6rem;font-weight:300;letter-spacing:.2em;
          text-transform:uppercase;color:var(--dust);text-align:center;margin-bottom:1.8rem}
.auth-note{font-family:var(--serif);font-size:.87rem;font-style:italic;
           color:var(--dust);text-align:center;margin-top:1.3rem;line-height:1.65;
           border-top:1px solid var(--border);padding-top:1.1rem}

/* Profile */
.prof-hero{background:var(--card);border:1px solid var(--border2);
           border-radius:var(--r-lg);padding:1.8rem 2rem;
           box-shadow:var(--sh);margin-bottom:1.3rem}
.prof-hd{display:flex;align-items:flex-start;gap:1.1rem;margin-bottom:1rem}
.prof-av{width:68px;height:68px;border-radius:50%;object-fit:cover;
         border:2px solid var(--border);flex-shrink:0}
.prof-name{font-family:var(--serif);font-size:1.7rem;font-weight:300;
           color:var(--ink);line-height:1.1;margin-bottom:.1rem}
.prof-pro{font-family:var(--sans);font-size:.62rem;font-weight:300;
          letter-spacing:.17em;text-transform:uppercase;color:var(--dust);margin-bottom:.3rem}
.prof-ess{font-family:var(--serif);font-size:.97rem;font-style:italic;
          color:var(--ash);line-height:1.6;border-left:2px solid var(--blush);
          padding-left:.85rem;margin:.8rem 0}
.cab-grid{display:grid;grid-template-columns:1fr 1fr;gap:.85rem;margin-top:.9rem}
.cab-lbl{font-family:var(--sans);font-size:.58rem;font-weight:300;
         letter-spacing:.2em;text-transform:uppercase;color:var(--dust);margin-bottom:.16rem}
.cab-val{font-family:var(--serif);font-size:.92rem;color:var(--ink)}
.stats{display:flex;gap:1.3rem;margin:.4rem 0 .75rem}
.sv{font-family:var(--serif);font-size:1.22rem;font-weight:300;color:var(--ink);display:block}
.sl{font-family:var(--sans);font-size:.58rem;font-weight:300;
    letter-spacing:.14em;text-transform:uppercase;color:var(--dust)}

/* Section */
.stitle{font-family:var(--serif);font-size:1.4rem;font-weight:300;
        font-style:italic;color:var(--ink);margin-bottom:.13rem}
.ssub{font-family:var(--sans);font-size:.59rem;font-weight:300;
      letter-spacing:.2em;text-transform:uppercase;color:var(--dust);margin-bottom:1.2rem}

/* Empty */
.empty{text-align:center;padding:2.5rem 1rem}
.empty-s{font-size:1.6rem;color:var(--dust);margin-bottom:.6rem}
.empty-t{font-family:var(--serif);font-size:.98rem;font-style:italic;
         color:var(--dust);line-height:1.7}

/* Discover user row */
.urow{display:flex;align-items:center;gap:.75rem;background:var(--card);
      border:1px solid var(--border2);border-radius:var(--r);
      padding:.7rem .9rem;box-shadow:var(--sh);margin-bottom:.5rem}
.urow-name{font-family:var(--serif);font-size:.93rem;font-weight:400;color:var(--ink)}
.urow-ess{font-family:var(--sans);font-size:.67rem;font-weight:300;color:var(--dust);
          white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

/* Admin */
.admin-card{background:var(--card);border:1px solid var(--border2);
            border-radius:var(--r);padding:1rem 1.2rem;margin-bottom:.75rem;box-shadow:var(--sh)}
.admin-tag{font-size:.58rem;font-weight:300;letter-spacing:.1em;text-transform:uppercase;
           padding:.12rem .45rem;border-radius:4px;display:inline-block;margin-bottom:.35rem}
.admin-tag.pending{background:rgba(184,154,106,.12);color:var(--gold);border:1px solid rgba(184,154,106,.3)}
.admin-tag.resolved{background:rgba(90,140,106,.1);color:var(--success);border:1px solid rgba(90,140,106,.25)}
.admin-tag.removed{background:rgba(184,90,90,.1);color:var(--danger);border:1px solid rgba(184,90,90,.25)}
.stat-card{background:var(--card);border:1px solid var(--border2);
           border-radius:var(--r-lg);padding:1.2rem 1.4rem;text-align:center;box-shadow:var(--sh)}
.stat-big{font-family:var(--serif);font-size:2.2rem;font-weight:300;color:var(--ink)}
.stat-sm{font-family:var(--sans);font-size:.6rem;font-weight:300;
         letter-spacing:.18em;text-transform:uppercase;color:var(--dust)}

@media(max-width:640px){
  .main .block-container{padding:1rem 1rem 4rem!important}
  .cab-grid{grid-template-columns:1fr}
  .auth-box{padding:1.7rem 1.3rem}
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
#  RENDER HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def av_html(path, name, size=36, cls="pav"):
    if path and os.path.exists(path):
        b64  = load_b64(path)
        mime = get_mime(path)
        src  = f"data:{mime};base64,{b64}"
    else:
        src = placeholder_avatar(name, size)
    return f'<img src="{src}" class="{cls}" alt="{html.escape(name or "")} avatar" width="{size}" height="{size}"/>'


def render_post(post, cur_uid, kpfx="", is_admin=False):
    pid   = post["id"]
    soul  = post.get("soul") or ""
    text  = post.get("text_content") or ""
    feel  = post.get("feel") or post.get("feeling") or ""
    tags  = json.loads(post.get("atmo_tags") or "[]")
    mp    = post.get("media_path")
    mt    = post.get("media_type")
    sens  = bool(post.get("is_sensitive"))
    rc    = post.get("resonance_count", 0)
    uname = post.get("username","")
    dname = post.get("display_name","?")
    ap    = post.get("avatar_path")
    pt    = fmt_time(post.get("created_at",""))
    resonated = has_resonated(pid, cur_uid) if cur_uid else False

    ava   = av_html(ap, dname, 36)
    t_html= "".join(f'<span class="ptag">{t}</span>' for t in tags)
    f_html= f'<div class="pfeeling"><span class="pdot"></span>{feel}</div>' if feel else ""

    media_html = ""
    if mp and os.path.exists(mp):
        b64  = load_b64(mp)
        mime = get_mime(mp)
        iid  = f"si{pid}{kpfx}"
        if mt == "image":
            if sens:
                media_html = f"""
                <div class="sw">
                  <img class="simg" id="{iid}" src="data:{mime};base64,{b64}" alt="Sensitive content"/>
                  <div class="sov" role="button" tabindex="0"
                    aria-label="Sensitive content — tap to reveal"
                    onclick="document.getElementById('{iid}').style.filter='none';this.style.display='none'"
                    onkeydown="if(event.key==='Enter'||event.key===' '){{document.getElementById('{iid}').style.filter='none';this.style.display='none'}}">
                    <span style="font-size:1.25rem;color:#F7F4EF">⚠</span>
                    <span class="slbl">Sensitive — tap to reveal</span>
                  </div>
                </div>"""
            else:
                media_html = f'<div class="pmedia"><img src="data:{mime};base64,{b64}" alt="Post image" loading="lazy"/></div>'
        elif mt == "video":
            media_html = f'<div class="pmedia"><video controls preload="metadata" aria-label="Post video"><source src="data:{mime};base64,{b64}" type="{mime}"/></video></div>'
        elif mt == "audio":
            media_html = f'<div class="pmedia"><audio controls aria-label="Post audio" style="width:100%;padding:.4rem 0"><source src="data:{mime};base64,{b64}" type="{mime}"/></audio></div>'
        else:
            fname = (mp or "").rsplit("/",1)[-1]
            media_html = f'<div style="background:var(--surface2);border-radius:var(--r);padding:.6rem .9rem;font-size:.8rem;color:var(--ash);margin:.7rem 0">📎 {html.escape(fname)}</div>'

    st.markdown(f"""
    <article class="pc" aria-label="Post by {html.escape(dname)}">
      <div class="ph">
        {ava}
        <div class="pmeta">
          <div class="pname" role="link" tabindex="0"
            onclick="window.parent.postMessage({{type:'profile',username:'{uname}'}}, '*')">{html.escape(dname)}</div>
          <div class="phandle">@{html.escape(uname)}</div>
        </div>
        <span class="ptime" aria-label="Posted {pt}">{pt}</span>
      </div>
      {f'<p class="psoul">"{html.escape(soul)}"</p>' if soul else ''}
      {f'<p class="ptext">{html.escape(text)}</p>' if text else ''}
      {f_html}
      {media_html}
      {f'<div class="ptags" aria-label="Tags">{t_html}</div>' if t_html else ''}
    </article>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
    with c1:
        rlbl = f"{'◈' if resonated else '◇'}  {rc}" if rc else ("◈" if resonated else "◇")
        if st.button(rlbl, key=f"r{pid}{kpfx}", help="Resonate with this"):
            if cur_uid:
                toggle_resonance(pid, cur_uid)
                st.rerun()
    with c2:
        if st.button(f"→ @{uname}", key=f"gp{pid}{kpfx}", help="View profile"):
            st.session_state.view_user = uname
            st.session_state.page = "profile_view"
            st.rerun()
    with c3:
        if cur_uid and st.button("⚑ Report", key=f"rp{pid}{kpfx}", help="Report this post"):
            st.session_state[f"report_open_{pid}"] = True
            st.rerun()
    with c4:
        # Own post delete
        u = st.session_state.get("user", {})
        if u and (u.get("id") == post.get("user_id") or u.get("is_admin")):
            if st.button("✕ Delete", key=f"del{pid}{kpfx}", help="Delete this post"):
                delete_post(pid, u["id"])
                st.rerun()

    # Inline report form
    if st.session_state.get(f"report_open_{pid}"):
        with st.form(key=f"rf{pid}{kpfx}"):
            st.markdown('<p style="font-family:\'Cormorant Garamond\',serif;font-style:italic;font-size:.93rem;color:#5C564F;margin-bottom:.5rem">What concerns you about this post?</p>', unsafe_allow_html=True)
            reason = st.selectbox("Reason", REPORT_REASONS, key=f"rr{pid}{kpfx}", label_visibility="collapsed")
            detail = st.text_area("Additional detail (optional)", height=60, key=f"rd{pid}{kpfx}", label_visibility="collapsed",
                                   placeholder="Tell us more if you'd like...")
            col_a, col_b = st.columns([1,1])
            with col_a:
                if st.form_submit_button("Submit report", type="primary", use_container_width=True):
                    ok, msg = submit_report(cur_uid, pid, reason, detail)
                    st.session_state.pop(f"report_open_{pid}", None)
                    if ok:
                        st.success(msg)
                    else:
                        st.warning(msg)
                    st.rerun()
            with col_b:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state.pop(f"report_open_{pid}", None)
                    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
#  PAGES — AUTH
# ─────────────────────────────────────────────────────────────────────────────

def page_auth():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;padding-bottom:1.5rem"><div class="auth-title">Still</div><div class="auth-sub">a sanctuary for individuals</div></div>', unsafe_allow_html=True)

    t1, t2 = st.tabs(["Sign in", "Join"])

    with t1:
        with st.form("lf", clear_on_submit=False):
            ident = st.text_input("Username or email", placeholder="your@email.com or username",
                                   autocomplete="username")
            pw    = st.text_input("Password", type="password", autocomplete="current-password")
            if st.form_submit_button("Enter", use_container_width=True, type="primary"):
                if not ident.strip() or not pw:
                    st.error("Please fill in both fields.")
                else:
                    u, err = login_user(ident, pw)
                    if u:
                        st.session_state.user = u
                        st.session_state.page = "feed"
                        st.rerun()
                    else:
                        st.error(err)
        st.markdown('<p style="font-family:\'DM Sans\',sans-serif;font-size:.73rem;font-weight:300;color:#9C948A;text-align:center;margin-top:.5rem">Demo accounts: <b>elia</b> / <b>demo123</b></p>', unsafe_allow_html=True)

    with t2:
        st.markdown('<p style="font-family:\'Cormorant Garamond\',serif;font-style:italic;font-size:.9rem;color:#9C948A;margin-bottom:1rem;line-height:1.65">No companies. No brands. No metrics.<br>Just you — exactly as you are.</p>', unsafe_allow_html=True)
        with st.form("rf", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                uname = st.text_input("Username *", placeholder="yourname",
                                       autocomplete="username", max_chars=30)
            with c2:
                pro   = st.text_input("Pronouns", placeholder="they/them", max_chars=30)
            dname = st.text_input("Display name *", max_chars=60, autocomplete="name")
            email = st.text_input("Email *", placeholder="you@example.com",
                                   autocomplete="email")
            pw1   = st.text_input("Password * (min 8 chars)", type="password",
                                   autocomplete="new-password")
            pw2   = st.text_input("Confirm password *", type="password",
                                   autocomplete="new-password")
            agree = st.checkbox("I am an individual, not a company or brand.")
            if st.form_submit_button("Join Still", use_container_width=True, type="primary"):
                if not agree:
                    st.error("Still is for individuals only.")
                elif not all([uname, dname, email, pw1, pw2]):
                    st.error("Please fill in all required fields.")
                elif pw1 != pw2:
                    st.error("Passwords don't match.")
                else:
                    u, err = register_user(uname, email, pw1, dname, pro)
                    if u:
                        st.session_state.user = u
                        st.session_state.page = "feed"
                        st.rerun()
                    else:
                        st.error(err)

    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar():
    u   = st.session_state.user
    uid = u["id"]
    with st.sidebar:
        st.markdown('<span class="wm">Still</span><span class="wm-sub">be here, fully</span>', unsafe_allow_html=True)
        ava = av_html(u.get("avatar_path"), u.get("display_name","?"), 38)
        st.markdown(
            f'<div class="nav-user">{ava}<div>'
            f'<div class="nav-uname">{html.escape(u.get("display_name",""))}</div>'
            f'<div class="nav-uhandle">@{html.escape(u.get("username",""))}</div>'
            f'</div></div><hr class="nav-div"/>',
            unsafe_allow_html=True
        )

        st.markdown('<div class="nav-sec">Navigate</div>', unsafe_allow_html=True)
        cur = st.session_state.get("page","feed")
        for key, lbl, tip in [
            ("feed",         "○  Feed",       "Your followed voices"),
            ("discover",     "◎  Discover",   "Find new presences"),
            ("compose",      "◈  Share",      "Leave something behind"),
            ("profile_self", "◇  Profile",    "Your space"),
        ]:
            if st.button(lbl, key=f"nb_{key}", help=tip, use_container_width=True,
                         type="primary" if cur==key else "secondary"):
                st.session_state.page = key; st.rerun()

        # Admin panel link
        if u.get("is_admin") or u.get("username") == ADMIN_USERNAME:
            pending = get_report_stats().get("pending", 0)
            badge   = f' <span class="nav-badge">{pending}</span>' if pending else ""
            st.markdown(f'<div class="nav-sec">Moderation{badge}</div>', unsafe_allow_html=True)
            if st.button("⚑  Admin Panel", key="nb_admin", use_container_width=True,
                         type="primary" if cur=="admin" else "secondary"):
                st.session_state.page = "admin"; st.rerun()

        st.markdown('<hr class="nav-div"/>', unsafe_allow_html=True)
        if st.button("Sign out", key="logout", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
#  FEED
# ─────────────────────────────────────────────────────────────────────────────

def page_feed():
    u     = st.session_state.user
    posts = get_feed_posts(u["id"])
    st.markdown('<p class="stitle">Feed</p><p class="ssub">voices you follow</p>', unsafe_allow_html=True)
    if not posts:
        st.markdown("""
        <div class="empty">
          <div class="empty-s">○</div>
          <p class="empty-t">You're not following anyone yet.<br>Head to Discover to find new presences.</p>
        </div>""", unsafe_allow_html=True)
        return
    for p in posts:
        render_post(p, u["id"], "fd")

# ─────────────────────────────────────────────────────────────────────────────
#  DISCOVER
# ─────────────────────────────────────────────────────────────────────────────

def page_discover():
    u    = st.session_state.user
    fids = get_following_ids(u["id"]) + [u["id"]]
    st.markdown('<p class="stitle">Discover</p><p class="ssub">people you haven\'t met yet</p>', unsafe_allow_html=True)

    ph   = ",".join("?"*len(fids))
    conn = get_db()
    sugg = conn.execute(
        f"SELECT * FROM users WHERE id NOT IN ({ph}) AND is_banned=0 ORDER BY RANDOM() LIMIT 6",
        fids
    ).fetchall()
    conn.close()

    if sugg:
        for su in [dict(s) for s in sugg]:
            ava = av_html(su.get("avatar_path"), su.get("display_name","?"), 34)
            st.markdown(
                f'<div class="urow">{ava}'
                f'<div style="flex:1;min-width:0">'
                f'<div class="urow-name">{html.escape(su["display_name"])}</div>'
                f'<div class="urow-ess">{html.escape(su.get("essence") or su.get("bio") or "@"+su["username"])}</div>'
                f'</div></div>', unsafe_allow_html=True
            )
            c1, c2 = st.columns([1,1])
            with c1:
                already = is_following(u["id"], su["id"])
                if st.button("Unfollow" if already else "Follow",
                             key=f"fl_{su['id']}", use_container_width=True):
                    toggle_follow(u["id"], su["id"]); st.rerun()
            with c2:
                if st.button("View profile", key=f"vp_{su['id']}", use_container_width=True):
                    st.session_state.view_user = su["username"]
                    st.session_state.page = "profile_view"; st.rerun()
        st.markdown('<hr style="border:none;border-top:1px solid var(--border);margin:1.3rem 0"/>', unsafe_allow_html=True)

    posts = get_discover_posts(u["id"])
    if not posts:
        st.markdown('<div class="empty"><div class="empty-s">◎</div><p class="empty-t">Nothing new to discover right now.</p></div>', unsafe_allow_html=True)
        return
    for p in posts:
        render_post(p, u["id"], "dc")

# ─────────────────────────────────────────────────────────────────────────────
#  COMPOSE
# ─────────────────────────────────────────────────────────────────────────────

def page_compose():
    st.markdown('<p class="stitle">Share something</p><p class="ssub">not a performance — a presence</p>', unsafe_allow_html=True)
    with st.form("cf", clear_on_submit=True):
        soul  = st.text_area("What is the soul of this? *",
                              placeholder="Light folding into itself at 4 PM...",
                              height=85, max_chars=500)
        text  = st.text_area("Words (optional)",
                              placeholder="Thoughts, fragments, what you want to say...",
                              height=75, max_chars=2000)
        feel  = st.selectbox("How are you feeling?", ["—"] + FEELINGS)
        tags  = st.multiselect("Atmospheric tags (up to 4)", ATMO_TAGS, max_selections=4)
        mfile = st.file_uploader(
            f"Upload something — image, audio, video, or document (max {MAX_FILE_MB}MB)",
            type=list(ALL_ALLOWED)
        )
        sens = st.checkbox("⚠  Mark as sensitive content — blurred until viewer chooses to reveal")
        if sens:
            st.markdown('<div style="background:rgba(184,154,106,.08);border:1px solid rgba(184,154,106,.22);border-radius:6px;padding:.6rem .9rem;font-size:.78rem;color:#7A6B5A">Like Instagram\'s sensitive content filter — blurred by default, viewer can choose to see it.</div>', unsafe_allow_html=True)

        submitted = st.form_submit_button("Leave it here", type="primary", use_container_width=True)
        if submitted:
            if not soul.strip() and not text.strip() and not mfile:
                st.error("Leave at least something — a word, an image, anything.")
            else:
                if mfile:
                    ok, mt, err = _validate_file(mfile)
                    if not ok:
                        st.error(err)
                        st.stop()
                mp, mt2 = save_media(mfile) if mfile else (None, None)
                create_post(
                    user_id      = st.session_state.user["id"],
                    text_content = text.strip() or None,
                    soul         = soul.strip() or None,
                    feeling      = feel if feel != "—" else None,
                    atmo_tags    = tags,
                    media_path   = mp,
                    media_type   = mt2,
                    is_sensitive = sens,
                )
                st.success("It has found its place. ○")
                st.balloons()

# ─────────────────────────────────────────────────────────────────────────────
#  PROFILE SELF
# ─────────────────────────────────────────────────────────────────────────────

def page_profile_self():
    uid   = st.session_state.user["id"]
    fresh = get_user_by_id(uid)
    if fresh:
        st.session_state.user = fresh
    u = st.session_state.user

    t1, t2, t3 = st.tabs(["My Profile", "Edit", "Settings"])

    with t1:
        _profile_view(u, uid, is_own=True)

    with t2:
        st.markdown('<p class="stitle">Edit profile</p><p class="ssub">who you are, not what you do</p>', unsafe_allow_html=True)
        avf = st.file_uploader("Profile photo", type=["jpg","jpeg","png","webp"],
                                help=f"Max {MAX_FILE_MB}MB")
        if avf:
            ok, _, err = _validate_file(avf)
            if not ok:
                st.error(err)
            else:
                path, _ = save_media(avf, "avatars")
                if path:
                    update_profile(uid, avatar_path=path)
                    st.session_state.user = get_user_by_id(uid)
                    st.success("Photo updated."); st.rerun()
        with st.form("epf"):
            dn = st.text_input("Display name *", value=u.get("display_name",""), max_chars=60)
            pr = st.text_input("Pronouns",       value=u.get("pronouns","") or "", max_chars=30)
            bi = st.text_area("Bio",             value=u.get("bio","") or "", height=80,
                               max_chars=500,    placeholder="Tell us about yourself, briefly or at length...")
            es = st.text_input("Your essence — one sentence",
                                value=u.get("essence","") or "", max_chars=200,
                                placeholder="I follow light across floors.")
            ob = st.text_area("Cabinet of curiosities",
                               value=u.get("obsessions","") or "", height=70, max_chars=300,
                               placeholder="What you're currently obsessed with...")
            so = st.text_input("Song on loop",   value=u.get("song","") or "", max_chars=100)
            qu = st.text_area("What keeps you grounded",
                               value=u.get("quote","") or "", height=70, max_chars=300)
            if st.form_submit_button("Save", type="primary", use_container_width=True):
                if not dn.strip():
                    st.error("Display name cannot be empty.")
                else:
                    update_profile(uid, display_name=dn, pronouns=pr, bio=bi,
                                   essence=es, obsessions=ob, song=so, quote=qu)
                    st.session_state.user = get_user_by_id(uid)
                    st.success("Profile updated."); st.rerun()

    with t3:
        st.markdown('<p class="stitle">Settings</p><p class="ssub">account security</p>', unsafe_allow_html=True)
        with st.form("cpf"):
            st.markdown('<p style="font-family:\'Cormorant Garamond\',serif;font-style:italic;font-size:.93rem;color:#5C564F;margin-bottom:.5rem">Change password</p>', unsafe_allow_html=True)
            old_pw  = st.text_input("Current password", type="password", autocomplete="current-password")
            new_pw1 = st.text_input("New password (min 8 chars)", type="password", autocomplete="new-password")
            new_pw2 = st.text_input("Confirm new password", type="password", autocomplete="new-password")
            if st.form_submit_button("Update password", type="primary", use_container_width=True):
                if new_pw1 != new_pw2:
                    st.error("Passwords don't match.")
                else:
                    ok, msg = change_password(uid, old_pw, new_pw1)
                    if ok: st.success(msg)
                    else:  st.error(msg)

        st.markdown('<hr style="border:none;border-top:1px solid var(--border);margin:1.5rem 0"/>', unsafe_allow_html=True)
        st.markdown('<p style="font-family:\'DM Sans\',sans-serif;font-size:.78rem;font-weight:300;color:#9C948A;line-height:1.7">Your email address: <strong>{}</strong><br>To change your email, please contact the moderator through the report system.</p>'.format(html.escape(u.get("email",""))), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  PROFILE VIEW
# ─────────────────────────────────────────────────────────────────────────────

def page_profile_view():
    cur_uid  = st.session_state.user["id"]
    username = st.session_state.get("view_user")
    if not username:
        st.session_state.page = "discover"; st.rerun(); return
    target = get_user_by_username(username)
    if not target:
        st.error("User not found."); return
    if target.get("is_banned"):
        st.error("This account has been suspended."); return
    if st.button("← Back", key="back_pv"):
        st.session_state.page = st.session_state.get("prev_page","discover")
        st.rerun()
    _profile_view(target, cur_uid, is_own=(target["id"]==cur_uid))

def _profile_view(user, viewer_uid, is_own=False):
    uid   = user["id"]
    posts = get_user_posts(uid)
    fc    = get_follower_count(uid)
    fwc   = get_following_count(uid)
    ava   = av_html(user.get("avatar_path"), user.get("display_name","?"), 68, "prof-av")

    if not is_own:
        already = is_following(viewer_uid, uid)
        c1, _ = st.columns([1,3])
        with c1:
            if st.button("Unfollow" if already else "Follow", key=f"fl_pv_{uid}", type="primary"):
                toggle_follow(viewer_uid, uid); st.rerun()

    bio_h = f'<p style="font-family:\'DM Sans\',sans-serif;font-size:.84rem;font-weight:300;color:#5C564F;line-height:1.7;margin-bottom:.7rem">{html.escape(user["bio"])}</p>' if user.get("bio") else ""
    ess_h = f'<p class="prof-ess">{html.escape(user["essence"])}</p>' if user.get("essence") else ""
    ob_h  = (f'<div><div class="cab-lbl">Cabinet of curiosities</div>'
             f'<div class="cab-val">{html.escape(user["obsessions"])}</div></div>') if user.get("obsessions") else ""
    so_h  = (f'<div><div class="cab-lbl">Song on loop</div>'
             f'<div class="cab-val">{html.escape(user["song"])}</div></div>') if user.get("song") else ""
    qu_h  = (f'<div style="grid-column:span 2"><div class="cab-lbl">What keeps them grounded</div>'
             f'<div class="cab-val" style="font-family:\'Cormorant Garamond\',serif;font-style:italic">'
             f'{html.escape(user["quote"])}</div></div>') if user.get("quote") else ""

    st.markdown(f"""
    <div class="prof-hero">
      <div class="prof-hd">
        {ava}
        <div style="flex:1">
          <div class="prof-name">{html.escape(user.get("display_name",""))}</div>
          <div class="prof-pro">{html.escape(user.get("pronouns") or "")}</div>
          <div class="stats">
            <div><span class="sv">{len(posts)}</span><span class="sl">Artifacts</span></div>
            <div><span class="sv">{fc}</span><span class="sl">Followers</span></div>
            <div><span class="sv">{fwc}</span><span class="sl">Following</span></div>
          </div>
        </div>
      </div>
      {bio_h}{ess_h}
      <div class="cab-grid">{ob_h}{so_h}{qu_h}</div>
    </div>
    """, unsafe_allow_html=True)

    if not posts:
        st.markdown('<div class="empty"><div class="empty-s">○</div><p class="empty-t">Nothing left here yet.</p></div>', unsafe_allow_html=True)
        return
    for p in posts:
        render_post(p, viewer_uid, f"pv{uid}")

# ─────────────────────────────────────────────────────────────────────────────
#  ADMIN PANEL
# ─────────────────────────────────────────────────────────────────────────────

def page_admin():
    u = st.session_state.user
    # Double-check admin
    if not u.get("is_admin") and u.get("username") != ADMIN_USERNAME:
        st.error("Access denied.")
        return

    # Ensure admin flag is set in DB
    if not u.get("is_admin"):
        conn = get_db()
        conn.execute("UPDATE users SET is_admin=1 WHERE username=?", (ADMIN_USERNAME,))
        conn.commit()
        conn.close()

    stats = get_report_stats()
    st.markdown('<p class="stitle">Admin Panel</p><p class="ssub">moderation & oversight</p>', unsafe_allow_html=True)

    # Stats row
    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl in [
        (c1, stats["pending"], "Pending Reports"),
        (c2, stats["total"],   "Total Reports"),
        (c3, stats["users"],   "Active Users"),
        (c4, stats["posts"],   "Live Posts"),
    ]:
        with col:
            st.markdown(f'<div class="stat-card"><div class="stat-big">{val}</div><div class="stat-sm">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Pending Reports", "All Reports", "Users"])

    # ── Pending Reports ──
    with tab1:
        reports = get_pending_reports()
        if not reports:
            st.markdown('<div class="empty"><div class="empty-s">○</div><p class="empty-t">No pending reports. All clear.</p></div>', unsafe_allow_html=True)
        for r in reports:
            post_preview = (r.get("soul") or r.get("text_content") or "")[:120]
            st.markdown(f"""
            <div class="admin-card">
              <span class="admin-tag pending">Pending</span>
              <div style="font-family:\'DM Sans\',sans-serif;font-size:.8rem;color:#5C564F;line-height:1.6">
                <strong>Reported by:</strong> @{html.escape(r.get("reporter_username",""))} &nbsp;·&nbsp;
                <strong>Post by:</strong> @{html.escape(r.get("post_author_username",""))}<br>
                <strong>Reason:</strong> {html.escape(r.get("reason",""))}<br>
                {f'<strong>Detail:</strong> {html.escape(r.get("detail",""))}<br>' if r.get("detail") else ''}
                <strong>Post preview:</strong> <em>"{html.escape(post_preview)}"</em><br>
                <strong>Reported:</strong> {fmt_time(r.get("created_at",""))}
                {' &nbsp;·&nbsp; <span style="color:var(--danger)">Post already removed</span>' if r.get("is_removed") else ''}
              </div>
            </div>
            """, unsafe_allow_html=True)
            ca, cb, cc = st.columns([1,1,1])
            rid = r["id"]
            with ca:
                if st.button("✓ Dismiss", key=f"dis_{rid}",
                             help="Report is unfounded", use_container_width=True):
                    resolve_report(rid, "dismiss", u["id"]); st.rerun()
            with cb:
                if st.button("✕ Remove post", key=f"rmp_{rid}",
                             help="Remove the reported post", use_container_width=True):
                    resolve_report(rid, "remove_post", u["id"]); st.rerun()
            with cc:
                if st.button("⊘ Ban user", key=f"ban_{rid}",
                             help="Remove post and ban the user", use_container_width=True):
                    resolve_report(rid, "ban_user", u["id"]); st.rerun()
            st.markdown('<hr style="border:none;border-top:1px solid var(--border);margin:.5rem 0"/>', unsafe_allow_html=True)

    # ── All Reports ──
    with tab2:
        reports_all = get_all_reports()
        if not reports_all:
            st.markdown('<p style="color:var(--dust);font-family:var(--sans);font-size:.83rem">No reports yet.</p>', unsafe_allow_html=True)
        for r in reports_all:
            tag_cls = "pending" if r["status"]=="pending" else "resolved"
            st.markdown(f"""
            <div class="admin-card">
              <span class="admin-tag {tag_cls}">{r['status'].upper()}</span>
              <div style="font-family:\'DM Sans\',sans-serif;font-size:.78rem;color:#5C564F;line-height:1.6">
                @{html.escape(r.get("reporter_username",""))} reported @{html.escape(r.get("post_author_username",""))} ·
                <em>{html.escape(r.get("reason",""))}</em> · {fmt_time(r.get("created_at",""))}
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Users ──
    with tab3:
        search = st.text_input("Search users", placeholder="username or display name",
                                label_visibility="collapsed")
        conn = get_db()
        if search.strip():
            users = conn.execute(
                "SELECT * FROM users WHERE username LIKE ? OR display_name LIKE ? ORDER BY created_at DESC LIMIT 50",
                (f"%{search}%", f"%{search}%")
            ).fetchall()
        else:
            users = conn.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 50").fetchall()
        conn.close()
        for usr in [dict(x) for x in users]:
            flags = []
            if usr.get("is_banned"): flags.append("BANNED")
            if usr.get("is_admin"):  flags.append("ADMIN")
            flag_str = " · ".join(flags)
            st.markdown(f"""
            <div class="admin-card" style="display:flex;justify-content:space-between;align-items:center">
              <div>
                <div style="font-family:\'Cormorant Garamond\',serif;font-size:.98rem;font-weight:400;color:var(--ink)">
                  {html.escape(usr["display_name"])} <span style="color:var(--dust);font-size:.8rem">@{html.escape(usr["username"])}</span>
                  {f' · <span style="color:var(--danger);font-size:.72rem">{flag_str}</span>' if flag_str else ''}
                </div>
                <div style="font-size:.7rem;color:var(--dust)">Joined {fmt_time(usr.get("created_at",""))}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            if not usr.get("is_admin"):
                cb_col, _ = st.columns([1,3])
                with cb_col:
                    ban_lbl = "Unban" if usr.get("is_banned") else "Ban"
                    if st.button(ban_lbl, key=f"ubancol_{usr['id']}", use_container_width=True):
                        conn = get_db()
                        conn.execute("UPDATE users SET is_banned=? WHERE id=?",
                                     (0 if usr.get("is_banned") else 1, usr["id"]))
                        conn.commit()
                        conn.close()
                        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title  = "Still",
        page_icon   = "○",
        layout      = "wide",
        initial_sidebar_state = "expanded",
    )
    init_db()

    if "page" not in st.session_state: st.session_state.page = "auth"
    if "user" not in st.session_state: st.session_state.user = None

    st.markdown(CSS, unsafe_allow_html=True)

    # ── Admin login shortcut ──
    if (not st.session_state.user and
            st.query_params.get("admin") == "1"):
        st.session_state.page = "admin_login"

    # ── Not logged in ──
    if not st.session_state.user:
        page_auth()
        return

    # ── Refresh user from DB every request ──
    fresh = get_user_by_id(st.session_state.user["id"])
    if not fresh or fresh.get("is_banned"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.error("Your account has been suspended.")
        st.stop()
    st.session_state.user = fresh

    render_sidebar()

    pg = st.session_state.get("page", "feed")
    if   pg == "feed":         page_feed()
    elif pg == "discover":     page_discover()
    elif pg == "compose":      page_compose()
    elif pg == "profile_self": page_profile_self()
    elif pg == "profile_view": page_profile_view()
    elif pg == "admin":        page_admin()
    else:                      page_feed()


if __name__ == "__main__":
    main()
