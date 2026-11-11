"""AI Email Assistant.

Run in your browser:   python app.py      then open http://localhost:8000
Run in its own window: python desktop.py  (this is what the downloadable Mac app does)
"""
from dotenv import load_dotenv

load_dotenv()  # loads ANTHROPIC_API_KEY from .env if you have one

import json  # noqa: E402
import re  # noqa: E402
import secrets  # noqa: E402
from datetime import date  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402

from flask import Flask, jsonify, redirect, render_template, request  # noqa: E402

import ai  # noqa: E402
import db  # noqa: E402
import gmail_client as gmail  # noqa: E402
import paths  # noqa: E402
import themes  # noqa: E402

app = Flask(__name__, template_folder=str(paths.RESOURCE_DIR / "templates"),
            static_folder=str(paths.RESOURCE_DIR / "static"))
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # largest upload: a syllabus PDF
db.init_db()

# A new random password every time the app starts. Pages include it and send it with every
# request, so other websites open in your browser can't secretly use this app.
APP_TOKEN = secrets.token_urlsafe(32)


@app.before_request
def protect():
    # Only answer requests addressed to this computer (blocks "DNS rebinding" tricks).
    if request.host.split(":")[0] not in ("127.0.0.1", "localhost"):
        return "Forbidden", 403
    if request.path.startswith("/api/") and request.headers.get("X-App-Token") != APP_TOKEN:
        return jsonify(error="This page is out of date. Refresh the page and try again."), 403
    # First launch: ask for a Claude API key before anything else.
    if (request.method == "GET" and not paths.get_api_key()
            and not request.path.startswith(("/static/", "/api/", "/setup"))):
        return redirect("/setup")


@app.context_processor
def inject_page_basics():
    """Every page gets the app token and the current theme's colors (so there's no flash of the wrong theme)."""
    selected, custom = db.get_settings()["theme"], db.custom_themes()
    return {"app_token": APP_TOKEN,
            "theme_css": themes.theme_css(selected, custom),
            "theme_stickers": themes.stickers_for(selected, custom)}


# ---------- First-run setup / API key ----------

@app.get("/setup")
def setup_page():
    return render_template("setup.html", page="setup")


@app.get("/api/apikey")
def api_key_status():
    key = paths.get_api_key()
    return jsonify(has_key=bool(key), from_env=paths.key_is_from_env(), hint=f"…{key[-4:]}" if key else "")


@app.put("/api/apikey")
def save_api_key():
    key = (request.get_json(force=True).get("key") or "").strip()
    if not key.startswith("sk-ant-"):
        return jsonify(error="Claude API keys start with sk-ant-. Copy it again from console.anthropic.com."), 400
    try:
        ai.check_api_key(key)
    except ai.DraftError as e:
        return jsonify(error=str(e)), 400
    paths.save_api_key(key)
    return jsonify(ok=True, from_env=paths.key_is_from_env())

BUTTON_LABELS = {
    "sick": "🤒 Sick",
    "missing_class": "📅 Missing Class",
    "extension": "⏰ Extension Request",
    "question": "❓ Question About Assignment",
    "office_hours": "🗓️ Office Hours Meeting",
    "custom": "✏️ Custom",
}


@app.get("/")
def index():
    return render_template("index.html", button_labels=BUTTON_LABELS,
                           needs_setup=not db.get_settings()["name"], page="professors")


# ---------- Settings ----------

@app.get("/settings")
def settings_page():
    return render_template("settings.html", page="settings")


@app.get("/api/settings")
def get_settings():
    return jsonify(db.get_settings())


@app.put("/api/settings")
def save_settings():
    db.save_settings(request.get_json(force=True))
    return jsonify(db.get_settings())


# ---------- Professors ----------

def _professor_json(p):
    p = dict(p)
    p["course_info"] = json.loads(p.get("course_info") or "{}")
    return p


@app.get("/api/professors")
def list_professors():
    profs = db.rows(
        "SELECT p.*, (SELECT COUNT(*) FROM course_items i WHERE i.professor_id = p.id) AS item_count "
        "FROM professors p ORDER BY course")
    return jsonify([_professor_json(p) for p in profs])


@app.get("/api/professors/<int:pid>/items")
def professor_items(pid):
    return jsonify(db.items_for(pid))


def _professor_fields():
    data = request.get_json(force=True)
    fields = {k: (data.get(k) or "").strip() for k in ("name", "email", "course", "notes")}
    missing = [k for k in ("name", "email", "course") if not fields[k]]
    return fields, missing


@app.post("/api/professors")
def add_professor():
    f, missing = _professor_fields()
    if missing:
        return jsonify(error=f"Please fill in: {', '.join(missing)}"), 400
    new_id = db.execute(
        "INSERT INTO professors (name, email, course, notes) VALUES (?, ?, ?, ?)",
        (f["name"], f["email"], f["course"], f["notes"]),
    )
    return jsonify(db.row("SELECT * FROM professors WHERE id = ?", (new_id,))), 201


@app.put("/api/professors/<int:pid>")
def update_professor(pid):
    f, missing = _professor_fields()
    if missing:
        return jsonify(error=f"Please fill in: {', '.join(missing)}"), 400
    db.execute(
        "UPDATE professors SET name = ?, email = ?, course = ?, notes = ? WHERE id = ?",
        (f["name"], f["email"], f["course"], f["notes"], pid),
    )
    return jsonify(db.row("SELECT * FROM professors WHERE id = ?", (pid,)))


@app.delete("/api/professors/<int:pid>")
def delete_professor(pid):
    db.execute("DELETE FROM course_items WHERE professor_id = ?", (pid,))
    db.execute("DELETE FROM professors WHERE id = ?", (pid,))
    return "", 204


# ---------- Syllabus upload ----------

SYLLABUS_TYPES = {b"%PDF": "application/pdf", b"\x89PNG": "image/png", b"\xff\xd8\xff": "image/jpeg"}
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})?$")
TIME_RE = re.compile(r"^(\d{2}:\d{2})?$")
INFO_FIELDS = ("course_title", "term", "class_times", "location", "teaching_assistants", "grading", "policies")


def _docx_text(content: bytes) -> str:
    """Pull the text out of a Word (.docx) file, keeping tables as "cell | cell" rows."""
    import io
    import zipfile
    from xml.etree import ElementTree

    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        root = ElementTree.fromstring(z.read("word/document.xml"))

    def para_text(p):
        return "".join(t.text or "" for t in p.iter(f"{w}t")).strip()

    lines = []
    body = root.find(f"{w}body")
    for block in body:
        if block.tag == f"{w}p":
            lines.append(para_text(block))
        elif block.tag == f"{w}tbl":
            for tr in block.iter(f"{w}tr"):
                cells = [" ".join(filter(None, (para_text(p) for p in tc.iter(f"{w}p")))) for tc in tr.iter(f"{w}tc")]
                lines.append(" | ".join(cells))
    return "\n".join(lines).strip()


@app.post("/api/syllabus/read")
def read_syllabus():
    """Step 1: Claude reads the file. Nothing is saved until you review it."""
    upload = request.files.get("file")
    if not upload:
        return jsonify(error="Choose a syllabus file (PDF, or a photo/screenshot)."), 400
    content = upload.read()
    name = (upload.filename or "").lower()
    media_type = next((t for magic, t in SYLLABUS_TYPES.items() if content.startswith(magic)), None)
    if not media_type and content.startswith(b"PK") and name.endswith(".docx"):
        try:
            content, media_type = _docx_text(content).encode("utf-8"), "text/plain"
        except Exception:  # noqa: BLE001
            return jsonify(error="Couldn't open that Word file. In Word, choose File → Save as PDF and upload the PDF."), 400
    elif not media_type and name.endswith((".txt", ".md")):
        media_type = "text/plain"
    if not media_type:
        hint = ""
        if name.endswith(".doc"):
            hint = " Older .doc files: open it in Word and choose File → Save As → .docx or PDF."
        elif name.endswith(".pages"):
            hint = " Pages files: open it in Pages and choose File → Export To → PDF."
        elif name.endswith((".heic", ".webp")):
            hint = " For photos: open it in Preview and choose File → Export → JPEG."
        return jsonify(error="That file type isn't supported. Use a PDF, Word (.docx), or a JPG/PNG photo of the "
                             "syllabus." + hint), 400
    if media_type == "text/plain" and not content.strip():
        return jsonify(error="That file looks empty."), 400
    try:
        extracted = ai.read_syllabus(content, media_type, date.today().isoformat())
    except ai.DraftError as e:
        return jsonify(error=str(e)), 400

    # Is this a class you already added? Match by email, then by course label.
    match = None
    email = extracted.get("professor_email", "").strip().lower()
    course = extracted.get("course", "").strip().lower()
    for p in db.rows("SELECT * FROM professors"):
        if (email and p["email"].lower() == email) or (course and p["course"].lower() == course):
            match = p["id"]
            break
    return jsonify(extracted=extracted, match_id=match, filename=upload.filename)


def _clean_item(it):
    kind = it.get("kind") if it.get("kind") in db.ITEM_KINDS else "other"
    title = (it.get("title") or "").strip()[:200]
    due_date, due_time = (it.get("date") or "").strip(), (it.get("time") or "").strip()
    if not title:
        raise ValueError("Every item needs a title.")
    if not DATE_RE.match(due_date) or not TIME_RE.match(due_time):
        raise ValueError(f"“{title}” has a date or time in the wrong format.")
    checklist = [{"text": str(t)[:200], "done": False} for t in (it.get("study_checklist") or []) if str(t).strip()]
    return {"kind": kind, "title": title, "due_date": due_date, "due_time": due_time,
            "date_text": (it.get("date_text") or "")[:200], "topics": (it.get("topics") or "")[:2000],
            "description": (it.get("description") or "")[:2000], "weight": (it.get("weight") or "")[:50],
            "checklist": checklist}


@app.post("/api/syllabus/save")
def save_syllabus():
    """Step 2: save what you reviewed: the professor card, class details, and exams/assignments."""
    data = request.get_json(force=True)
    prof = {k: (data.get("professor", {}).get(k) or "").strip() for k in ("name", "email", "course", "notes")}
    missing = [k for k in ("name", "email", "course") if not prof[k]]
    if missing:
        return jsonify(error=f"Please fill in the professor's {', '.join(missing)}."), 400
    try:
        items = [_clean_item(it) for it in data.get("items", []) if it.get("include", True)]
    except ValueError as e:
        return jsonify(error=str(e)), 400
    info = {k: (data.get("info", {}).get(k) or "").strip() for k in INFO_FIELDS}
    office_hours = (data.get("office_hours") or "").strip()

    pid = data.get("professor_id")
    if pid and db.row("SELECT id FROM professors WHERE id = ?", (pid,)):
        db.execute("UPDATE professors SET name = ?, email = ?, course = ?, notes = ?, office_hours = ?, "
                   "course_info = ? WHERE id = ?",
                   (prof["name"], prof["email"], prof["course"], prof["notes"], office_hours, json.dumps(info), pid))
    else:
        pid = db.execute("INSERT INTO professors (name, email, course, notes, office_hours, course_info) "
                         "VALUES (?, ?, ?, ?, ?, ?)",
                         (prof["name"], prof["email"], prof["course"], prof["notes"], office_hours, json.dumps(info)))
    db.replace_syllabus_items(pid, items)
    return jsonify(professor_id=pid, items_saved=len(items))


# ---------- Upcoming: exams & assignments ----------

@app.get("/upcoming")
def upcoming_page():
    return render_template("upcoming.html", page="upcoming")


@app.get("/api/items")
def list_items():
    return jsonify(db.all_items())


def _item_updates(data, partial=True):
    """Validate the fields you can change on an item. Returns a dict of column -> value."""
    out = {}
    if "kind" in data:
        out["kind"] = data["kind"] if data["kind"] in db.ITEM_KINDS else "other"
    if "title" in data:
        out["title"] = (data["title"] or "").strip()[:200]
        if not out["title"]:
            raise ValueError("The title can't be empty.")
    if "due_date" in data:
        out["due_date"] = (data["due_date"] or "").strip()
        if not DATE_RE.match(out["due_date"]):
            raise ValueError("Dates look like 2027-03-14.")
    if "due_time" in data:
        out["due_time"] = (data["due_time"] or "").strip()
        if not TIME_RE.match(out["due_time"]):
            raise ValueError("Times look like 23:59.")
    for f in ("topics", "description", "weight"):
        if f in data:
            out[f] = (data[f] or "")[:2000]
    if "done" in data:
        out["done"] = 1 if data["done"] else 0
    if "checklist" in data:
        out["checklist"] = json.dumps([{"text": str(c.get("text", ""))[:200], "done": bool(c.get("done"))}
                                       for c in (data["checklist"] or []) if str(c.get("text", "")).strip()])
    if not partial and "title" not in out:
        raise ValueError("Give it a title.")
    return out


@app.post("/api/items")
def add_item():
    data = request.get_json(force=True)
    if not db.row("SELECT id FROM professors WHERE id = ?", (data.get("professor_id"),)):
        return jsonify(error="Pick a class."), 400
    try:
        f = _item_updates(data, partial=False)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    f.setdefault("kind", "assignment")
    cols = ["professor_id", "source", *f]
    new_id = db.execute(f"INSERT INTO course_items ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                        (data["professor_id"], "manual", *f.values()))
    return jsonify(db.get_item(new_id)), 201


@app.patch("/api/items/<int:item_id>")
def update_item(item_id):
    if not db.get_item(item_id):
        return jsonify(error="Not found."), 404
    try:
        f = _item_updates(request.get_json(force=True))
    except ValueError as e:
        return jsonify(error=str(e)), 400
    if f:
        db.execute(f"UPDATE course_items SET {', '.join(f'{k} = ?' for k in f)} WHERE id = ?", (*f.values(), item_id))
    return jsonify(db.get_item(item_id))


@app.delete("/api/items/<int:item_id>")
def delete_item(item_id):
    db.execute("DELETE FROM course_items WHERE id = ?", (item_id,))
    return "", 204


@app.post("/api/items/<int:item_id>/checklist")
def make_checklist(item_id):
    """Ask Claude for a study checklist (exams without one, or to redo it)."""
    item = db.get_item(item_id)
    if not item:
        return jsonify(error="Not found."), 404
    prof = db.row("SELECT * FROM professors WHERE id = ?", (item["professor_id"],))
    try:
        steps = ai.study_checklist(item, _professor_json(prof))
    except ai.DraftError as e:
        return jsonify(error=str(e)), 400
    checklist = json.dumps([{"text": t[:200], "done": False} for t in steps if t.strip()])
    db.execute("UPDATE course_items SET checklist = ? WHERE id = ?", (checklist, item_id))
    return jsonify(db.get_item(item_id))


# ---------- Drafting ----------

def _draft_context(professor, item_id=None):
    """Class info from the syllabus that helps write a better email."""
    from datetime import timedelta
    today = date.today()
    info = json.loads(professor.get("course_info") or "{}")
    ctx = {"today": today.isoformat(), "office_hours": professor.get("office_hours") or "",
           "class_times": info.get("class_times", "")}
    items = [i for i in db.items_for(professor["id"]) if not i["done"]]
    if item_id:
        ctx["about_item"] = next((i for i in items if i["id"] == int(item_id)), None)
    window = ((today - timedelta(days=1)).isoformat(), (today + timedelta(days=3)).isoformat())
    ctx["nearby_items"] = [i for i in items if i["due_date"] and window[0] <= i["due_date"] <= window[1]]
    return ctx


@app.post("/api/draft")
def make_draft():
    """Create a new draft, or regenerate an existing one when draft_id is given."""
    data = request.get_json(force=True)
    professor = db.row("SELECT * FROM professors WHERE id = ?", (data.get("professor_id"),))
    if not professor:
        return jsonify(error="Professor not found."), 404
    draft_type = data.get("draft_type", "custom")
    details = data.get("details", "")
    if draft_type == "custom" and not details.strip():
        return jsonify(error="For a Custom email, describe what you want in the details box."), 400

    try:
        draft = ai.draft_professor_email(professor, draft_type, details, db.get_settings(),
                                         _draft_context(professor, data.get("item_id")))
    except ai.DraftError as e:
        return jsonify(error=str(e)), 502

    draft_id = data.get("draft_id")
    if draft_id:  # Regenerate: replace the draft in history instead of adding a new one
        db.execute("UPDATE drafts SET details = ?, subject = ?, body = ? WHERE id = ?",
                   (details, draft["subject"], draft["body"], draft_id))
    else:
        draft_id = db.execute(
            """INSERT INTO drafts (professor_id, professor_name, professor_email, course,
                                   draft_type, details, subject, body)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (professor["id"], professor["name"], professor["email"], professor["course"],
             draft_type, details, draft["subject"], draft["body"]),
        )
    return jsonify(id=draft_id, to=professor["email"], **draft)


@app.post("/api/rewrite")
def rewrite_draft():
    """Make Shorter / More Formal / More Casual, applied to the text currently in the editor."""
    data = request.get_json(force=True)
    style = data.get("style")
    if style not in ai.REWRITE_STYLES:
        return jsonify(error="Unknown rewrite style."), 400
    body = (data.get("body") or "").strip()
    if not body:
        return jsonify(error="There's no email to rewrite yet."), 400
    professor = db.row("SELECT * FROM professors WHERE id = ?", (data.get("professor_id"),))

    try:
        result = ai.rewrite_email(data.get("subject", ""), body, style, professor, db.get_settings())
    except ai.DraftError as e:
        return jsonify(error=str(e)), 502

    if data.get("draft_id"):
        db.execute("UPDATE drafts SET subject = ?, body = ? WHERE id = ?",
                   (result["subject"], result["body"], data["draft_id"]))
    return jsonify(result)


# ---------- History ----------

@app.get("/api/history")
def history():
    return jsonify(db.rows("SELECT * FROM drafts ORDER BY id DESC LIMIT 100"))


@app.put("/api/history/<int:did>")
def save_edited_draft(did):
    """Save your manual edits so history shows the version you actually sent."""
    data = request.get_json(force=True)
    db.execute("UPDATE drafts SET subject = ?, body = ? WHERE id = ?",
               (data.get("subject", ""), data.get("body", ""), did))
    return "", 204


@app.delete("/api/history/<int:did>")
def delete_history(did):
    db.execute("DELETE FROM drafts WHERE id = ?", (did,))
    return "", 204


# ---------- Themes ----------

@app.get("/api/themes")
def list_themes():
    return jsonify(selected=db.get_settings()["theme"], presets=themes.presets_for_api(),
                   custom=list(db.custom_themes().values()), labels=themes.COLOR_KEYS,
                   sticker_options=themes.STICKERS)


def _theme_input():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()[:40]
    if not name:
        raise ValueError("Give your theme a name.")
    return name, themes.clean_colors(data.get("colors")), themes.clean_stickers(data.get("stickers"))


@app.post("/api/themes")
def create_theme():
    try:
        name, colors, stickers = _theme_input()
    except ValueError as e:
        return jsonify(error=str(e)), 400
    new_id = db.execute("INSERT INTO themes (name, colors, stickers) VALUES (?, ?, ?)",
                        (name, json.dumps(colors), stickers))
    db.save_settings({"theme": f"custom-{new_id}"})  # switch to the theme you just made
    return jsonify(id=f"custom-{new_id}"), 201


def _custom_id(theme_id):
    if not theme_id.startswith("custom-") or not theme_id[7:].isdigit():
        raise LookupError
    return int(theme_id[7:])


@app.put("/api/themes/<theme_id>")
def update_theme(theme_id):
    try:
        num = _custom_id(theme_id)
        name, colors, stickers = _theme_input()
    except LookupError:
        return jsonify(error="Built-in themes can't be edited. Make a copy instead."), 400
    except ValueError as e:
        return jsonify(error=str(e)), 400
    db.execute("UPDATE themes SET name = ?, colors = ?, stickers = ? WHERE id = ?",
               (name, json.dumps(colors), stickers, num))
    return jsonify(id=theme_id)


@app.delete("/api/themes/<theme_id>")
def delete_theme(theme_id):
    try:
        num = _custom_id(theme_id)
    except LookupError:
        return jsonify(error="Built-in themes can't be deleted."), 400
    db.execute("DELETE FROM themes WHERE id = ?", (num,))
    if db.get_settings()["theme"] == theme_id:
        db.save_settings({"theme": "system"})
    return "", 204


@app.put("/api/themes/selected")
def select_theme():
    theme_id = request.get_json(force=True).get("id", "system")
    if theme_id != "system" and theme_id not in themes.PRESETS and theme_id not in db.custom_themes():
        return jsonify(error="Theme not found."), 404
    db.save_settings({"theme": theme_id})
    return jsonify(selected=theme_id)


# ---------- Work email auto-drafts (Phase 3) ----------
# Reminder: nothing here sends email. Replies are saved as Gmail DRAFTS for you to review.

@app.get("/work")
def work_page():
    return render_template("work.html", page="work")


@app.get("/api/gmail/status")
def gmail_status():
    return jsonify(gmail.status())


@app.post("/api/gmail/connect")
def gmail_connect():
    try:
        gmail.connect()
    except gmail.GmailError as e:
        return jsonify(error=str(e)), 400
    return jsonify(gmail.status())


@app.post("/api/gmail/credentials")
def gmail_upload_credentials():
    """Lets you pick your credentials.json inside the app instead of copying it into a folder."""
    upload = request.files.get("file")
    if not upload:
        return jsonify(error="Choose your credentials .json file."), 400
    try:
        gmail.save_credentials_file(upload.read())
    except gmail.GmailError as e:
        return jsonify(error=str(e)), 400
    return jsonify(gmail.status())


@app.post("/api/gmail/disconnect")
def gmail_disconnect():
    gmail.disconnect()
    return jsonify(gmail.status())


def _work_email_json(row, my_address=None):
    row = dict(row)
    if my_address:
        row["gmail_link"] = gmail.thread_link(row["thread_id"], my_address)
    return row


@app.get("/api/work/emails")
def list_work_emails():
    show_done = request.args.get("show_done") == "1"
    hidden = ("discarded",) if show_done else ("discarded", "done")
    marks = ",".join("?" for _ in hidden)
    # Things that need you first (drafts, problems), then the rest; newest first within each group.
    emails = db.rows(f"SELECT * FROM work_emails WHERE status NOT IN ({marks}) ORDER BY "
                     "CASE status WHEN 'drafted' THEN 0 WHEN 'error' THEN 1 WHEN 'no_reply' THEN 2 "
                     "WHEN 'skipped' THEN 3 ELSE 4 END, received_ms DESC LIMIT 200", hidden)
    me = gmail.status().get("email")
    return jsonify([_work_email_json(e, me) for e in emails])


@app.post("/api/work/check")
def check_inbox():
    """Fetch new unread emails, have Claude draft replies, and save them as Gmail drafts."""
    settings = db.get_settings()
    try:
        svc, me = gmail.get_service()
        known = {r["gmail_id"] for r in db.rows("SELECT gmail_id FROM work_emails")}
        max_new = max(1, min(int(settings.get("max_emails") or 10), 50))
        emails = gmail.fetch_unread(svc, settings.get("gmail_label"), max_new, known)
    except gmail.GmailError as e:
        return jsonify(error=str(e)), 400
    except ValueError:
        return jsonify(error="“Emails per check” in Settings must be a number."), 400

    counts = {"found": len(emails), "drafted": 0, "no_reply": 0, "skipped": 0, "error": 0}

    # 1) Skip automated mail (newsletters, no-reply senders, your own emails) without asking Claude.
    to_draft = []
    for email in emails:
        reason = gmail.automated_reason(email, me)
        if reason:
            db.save_work_email(email, status="skipped", note=reason)
            counts["skipped"] += 1
        else:
            to_draft.append(email)

    # 2) Ask Claude for replies, a few at a time in parallel so it's faster.
    def draft(email):
        try:
            return ai.draft_work_reply(email, settings)
        except ai.DraftError as e:
            return e

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(draft, to_draft))

    # 3) Save each reply as a Gmail draft (one at a time: the Gmail client isn't thread-safe).
    for email, result in zip(to_draft, results):
        if isinstance(result, Exception):
            db.save_work_email(email, status="error", note=str(result))
            counts["error"] += 1
        elif not result["needs_reply"]:
            db.save_work_email(email, status="no_reply", note=result["reason"])
            counts["no_reply"] += 1
        else:
            try:
                draft_id = gmail.save_draft(svc, email, result["body"])
                db.save_work_email(email, status="drafted", note=result["reason"],
                                   reply_body=result["body"], draft_id=draft_id)
                counts["drafted"] += 1
            except gmail.GmailError as e:
                db.save_work_email(email, status="error", note=str(e), reply_body=result["body"])
                counts["error"] += 1
    return jsonify(counts)


def _load_work_email(gmail_id):
    email = db.get_work_email(gmail_id)
    if not email:
        raise LookupError
    return email


def _save_reply(email, body, note=None):
    """Write the reply to Gmail (create or update the draft) and to the local database."""
    svc, me = gmail.get_service()
    draft_id = gmail.save_draft(svc, email, body, email.get("draft_id"))
    changes = {"reply_body": body, "draft_id": draft_id, "status": "drafted"}
    if note is not None:
        changes["note"] = note
    db.save_work_email(email, **changes)
    return _work_email_json(db.get_work_email(email["gmail_id"]), me)


@app.put("/api/work/emails/<gmail_id>")
def save_work_reply(gmail_id):
    """Save your manual edits to the Gmail draft."""
    body = (request.get_json(force=True).get("reply_body") or "").strip()
    if not body:
        return jsonify(error="The reply is empty."), 400
    try:
        return jsonify(_save_reply(_load_work_email(gmail_id), body))
    except LookupError:
        return jsonify(error="Email not found."), 404
    except gmail.GmailError as e:
        return jsonify(error=str(e)), 400


@app.post("/api/work/emails/<gmail_id>/regenerate")
def regenerate_work_reply(gmail_id):
    """New reply from scratch. Also used for “Draft a reply anyway” and “Try again”."""
    try:
        email = _load_work_email(gmail_id)
        result = ai.draft_work_reply(email, db.get_settings(), force=True)
        return jsonify(_save_reply(email, result["body"], note=result["reason"]))
    except LookupError:
        return jsonify(error="Email not found."), 404
    except (ai.DraftError, gmail.GmailError) as e:
        return jsonify(error=str(e)), 400


@app.post("/api/work/emails/<gmail_id>/rewrite")
def rewrite_work_reply(gmail_id):
    data = request.get_json(force=True)
    if data.get("style") not in ai.REWRITE_STYLES:
        return jsonify(error="Unknown rewrite style."), 400
    try:
        email = _load_work_email(gmail_id)
        body = ai.rewrite_work_reply(email, data.get("reply_body") or email["reply_body"],
                                     data["style"], db.get_settings())
        return jsonify(_save_reply(email, body))
    except LookupError:
        return jsonify(error="Email not found."), 404
    except (ai.DraftError, gmail.GmailError) as e:
        return jsonify(error=str(e)), 400


@app.post("/api/work/emails/<gmail_id>/done")
def mark_work_done(gmail_id):
    """Hide it from the dashboard. The Gmail draft (if any) stays in Gmail."""
    db.execute("UPDATE work_emails SET status = 'done' WHERE gmail_id = ?", (gmail_id,))
    return "", 204


@app.post("/api/work/emails/<gmail_id>/discard")
def discard_work_reply(gmail_id):
    """Delete the Gmail draft and hide the email from the dashboard."""
    try:
        email = _load_work_email(gmail_id)
        if email.get("draft_id"):
            svc, _ = gmail.get_service()
            gmail.delete_draft(svc, email["draft_id"])
        db.execute("UPDATE work_emails SET status = 'discarded', draft_id = NULL WHERE gmail_id = ?",
                   (gmail_id,))
    except LookupError:
        return jsonify(error="Email not found."), 404
    except gmail.GmailError as e:
        return jsonify(error=str(e)), 400
    return "", 204


if __name__ == "__main__":
    # Port 8000 because macOS uses port 5000 for AirPlay. 127.0.0.1 = only reachable from this Mac.
    app.run(host="127.0.0.1", port=8000, debug=True)
