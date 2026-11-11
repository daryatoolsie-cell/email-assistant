"""Tiny SQLite helper. All data lives in data.db (see paths.py for where)."""
import sqlite3

from paths import DATA_DIR

DB_PATH = DATA_DIR / "data.db"


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS professors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                course TEXT NOT NULL,
                notes TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                professor_id INTEGER,
                professor_name TEXT,
                professor_email TEXT,
                course TEXT,
                draft_type TEXT,
                details TEXT,
                subject TEXT,
                body TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            -- Phase 3: one row per work email the app has looked at.
            CREATE TABLE IF NOT EXISTS work_emails (
                gmail_id TEXT PRIMARY KEY,
                thread_id TEXT,
                from_addr TEXT,
                reply_to TEXT,
                subject TEXT,
                received_ms INTEGER,
                snippet TEXT,
                body TEXT,
                message_id_header TEXT,
                references_header TEXT,
                reply_body TEXT DEFAULT '',
                draft_id TEXT,
                -- drafted | no_reply | skipped | error | done | discarded
                status TEXT,
                note TEXT DEFAULT '',
                checked_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
            -- Your own color themes. colors = JSON like {"bg": "#ffffff", ...}
            CREATE TABLE IF NOT EXISTS themes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                colors TEXT NOT NULL
            );
            """
        )
        # Added later: themes can show stickers. Add the column to older databases.
        columns = [r[1] for r in conn.execute("PRAGMA table_info(themes)")]
        if "stickers" not in columns:
            conn.execute("ALTER TABLE themes ADD COLUMN stickers TEXT DEFAULT ''")


# ---------- Settings ----------

SETTINGS_DEFAULTS = {
    "name": "",          # e.g. "Alex Rivera"
    "school": "",        # e.g. "Boston University"
    "sign_off": "Thanks,",
    "signature": "",     # optional lines under your name, e.g. "Marketing '28"
    "work_context": "",    # who you are at work + how you like to reply
    "work_signature": "",  # optional full sign-off for work replies (blank = sign-off + name)
    "gmail_label": "",     # blank = Inbox
    "max_emails": "10",    # how many new emails to handle per "Check inbox" click
    "theme": "system",     # "system", a preset id like "forest", or a custom id like "custom-3"
}


def get_settings():
    saved = {r["key"]: r["value"] for r in rows("SELECT key, value FROM settings")}
    return {k: saved.get(k, default) for k, default in SETTINGS_DEFAULTS.items()}


def save_settings(values):
    with connect() as conn:
        for key in SETTINGS_DEFAULTS:
            if key in values:
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, (values[key] or "").strip()),
                )


def rows(sql, params=()):
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def row(sql, params=()):
    result = rows(sql, params)
    return result[0] if result else None


def execute(sql, params=()):
    with connect() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


# ---------- Work emails (Phase 3) ----------

WORK_COLUMNS = ("gmail_id", "thread_id", "from_addr", "reply_to", "subject", "received_ms", "snippet",
                "body", "message_id_header", "references_header", "reply_body", "draft_id", "status", "note")


def save_work_email(email, **changes):
    """Insert a new work email, or update the given fields of an existing one."""
    record = {k: email.get(k) for k in WORK_COLUMNS if k in email}
    record.update(changes)
    cols = ", ".join(record)
    marks = ", ".join("?" for _ in record)
    updates = ", ".join(f"{k} = excluded.{k}" for k in record if k != "gmail_id")
    execute(f"INSERT INTO work_emails ({cols}) VALUES ({marks}) "
            f"ON CONFLICT(gmail_id) DO UPDATE SET {updates}", tuple(record.values()))


def get_work_email(gmail_id):
    return row("SELECT * FROM work_emails WHERE gmail_id = ?", (gmail_id,))


# ---------- Custom themes ----------

def custom_themes():
    """{"custom-3": {"id": "custom-3", "name": "...", "colors": {...}}, ...}"""
    import json
    return {f"custom-{r['id']}": {"id": f"custom-{r['id']}", "name": r["name"], "colors": json.loads(r["colors"]),
                                  "stickers": r.get("stickers") or ""}
            for r in rows("SELECT * FROM themes ORDER BY id")}
