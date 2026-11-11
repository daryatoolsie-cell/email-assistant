"""Everything that talks to Gmail lives here.

Safety: this app only READS mail and creates/updates/deletes DRAFTS.
There is no code anywhere in this project that sends an email.
"""
import base64
import html
import json
import re
from email.mime.text import MIMEText

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from paths import DATA_DIR, RESOURCE_DIR

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",  # read your mail
    "https://www.googleapis.com/auth/gmail.compose",   # create drafts
]

# Your own Google client file (see README), if you added one...
USER_CREDENTIALS_FILE = DATA_DIR / "credentials.json"
# ...otherwise the one built into the downloadable app (if the app was built with one).
BUNDLED_CREDENTIALS_FILE = RESOURCE_DIR / "google_client.json"
TOKEN_FILE = DATA_DIR / "token.json"  # created when you click "Connect Gmail"


def credentials_file():
    for f in (USER_CREDENTIALS_FILE, BUNDLED_CREDENTIALS_FILE):
        if f.exists():
            return f
    return None


def save_credentials_file(content: bytes):
    """Save a credentials.json chosen in the app, after checking it's the right kind of file."""
    try:
        data = json.loads(content)
    except ValueError:
        raise GmailError("That isn't a valid credentials file (it should be a .json file from Google Cloud).")
    if "installed" not in data:
        if "web" in data:
            raise GmailError("That's a “Web application” client. In Google Cloud, create a “Desktop app” client instead.")
        raise GmailError("That doesn't look like a Google OAuth client file. See the Gmail setup steps.")
    USER_CREDENTIALS_FILE.write_text(json.dumps(data))
    USER_CREDENTIALS_FILE.chmod(0o600)

# Emails in these Gmail tabs are never answered (newsletters, social, notifications).
SKIP_CATEGORIES = "-category:promotions -category:social -category:updates -category:forums"
AUTOMATED_SENDER = re.compile(r"no-?reply|do-?not-?reply|mailer-daemon|postmaster|notifications?@|bounce", re.I)
MAX_BODY_CHARS = 15000


class GmailError(Exception):
    """A problem we can show to the user in plain English."""


# ---------- Connecting ----------

def _load_credentials():
    if not TOKEN_FILE.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            # Usually the 7-day expiry for apps in "Testing" mode. Make the user reconnect.
            TOKEN_FILE.unlink(missing_ok=True)
            return None
        TOKEN_FILE.write_text(creds.to_json())
        return creds
    return None


def status():
    f = credentials_file()
    info = {"has_credentials_file": f is not None, "using_bundled": f == BUNDLED_CREDENTIALS_FILE,
            "connected": False, "email": None}
    creds = _load_credentials()
    if creds:
        try:
            info["email"] = _service(creds).users().getProfile(userId="me").execute()["emailAddress"]
            info["connected"] = True
        except HttpError:
            pass
    return info


def connect():
    """Opens Google's sign-in page in your browser and waits (up to 5 min) for you to approve."""
    f = credentials_file()
    if not f:
        raise GmailError("No Google credentials file yet. Follow the Gmail setup steps in the README.")
    flow = InstalledAppFlow.from_client_secrets_file(str(f), SCOPES)
    try:
        creds = flow.run_local_server(
            port=0,
            timeout_seconds=300,
            authorization_prompt_message=(
                "\nIf a Google sign-in tab didn't open, copy this link into your browser:\n{url}\n"
            ),
            success_message="Gmail connected! You can close this tab and go back to the Email Assistant.",
        )
    except Exception as e:  # closed tab, timed out, clicked Cancel...
        raise GmailError(f"Gmail sign-in didn't finish. Please try again. ({type(e).__name__})")
    TOKEN_FILE.write_text(creds.to_json())


def disconnect():
    TOKEN_FILE.unlink(missing_ok=True)


def _service(creds=None):
    creds = creds or _load_credentials()
    if not creds:
        raise GmailError("Gmail isn't connected (or the connection expired). Click “Connect Gmail”.")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_service():
    """Returns (gmail service, your email address)."""
    svc = _service()
    try:
        me = svc.users().getProfile(userId="me").execute()["emailAddress"]
    except HttpError as e:
        raise GmailError(f"Couldn't reach Gmail ({e.status_code}). Try reconnecting.")
    return svc, me


# ---------- Reading ----------

def _label_id(svc, label_name):
    if not label_name or label_name.strip().upper() == "INBOX":
        return "INBOX"
    labels = svc.users().labels().list(userId="me").execute().get("labels", [])
    for lab in labels:
        if lab["name"].lower() == label_name.strip().lower():
            return lab["id"]
    raise GmailError(f"No Gmail label called “{label_name}”. Check the label name in Settings.")


def _decode(data):
    return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")


def _html_to_text(raw_html):
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", raw_html)
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</li>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\n\s*\n\s*\n+", "\n\n", text).strip()


def _extract_body(payload):
    """Find the plain-text body, falling back to HTML converted to text."""
    plain, rich = [], []

    def walk(part):
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if data and mime == "text/plain":
            plain.append(_decode(data))
        elif data and mime == "text/html":
            rich.append(_decode(data))
        for sub in part.get("parts", []) or []:
            walk(sub)

    walk(payload)
    if plain:
        body = "\n".join(plain).strip()
    elif rich:
        body = _html_to_text("\n".join(rich))
    else:
        body = ""
    if len(body) > MAX_BODY_CHARS:
        body = body[:MAX_BODY_CHARS] + "\n\n[... rest of the email was too long and was cut off ...]"
    return body


def parse_message(msg):
    headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
    return {
        "gmail_id": msg["id"],
        "thread_id": msg["threadId"],
        "from_addr": headers.get("from", ""),
        "reply_to": headers.get("reply-to") or headers.get("from", ""),
        "subject": headers.get("subject", "(no subject)"),
        "received_ms": int(msg.get("internalDate", 0)),
        "snippet": html.unescape(msg.get("snippet", "")),
        "body": _extract_body(msg["payload"]),
        "message_id_header": headers.get("message-id", ""),
        "references_header": headers.get("references", ""),
        "_headers": headers,
    }


def automated_reason(email, my_address):
    """Returns why an email should be skipped (newsletter, no-reply, from you...), or None."""
    h = email["_headers"]
    sender = email["from_addr"]
    if my_address and my_address.lower() in sender.lower():
        return "Sent by you"
    if AUTOMATED_SENDER.search(sender):
        return "Automated sender (no-reply address)"
    if "list-unsubscribe" in h or h.get("precedence", "").lower() in ("bulk", "list", "junk"):
        return "Looks like a newsletter or mailing list"
    if h.get("auto-submitted", "no").lower() != "no":
        return "Automatic message"
    return None


def fetch_unread(svc, label_name, max_new, known_ids):
    """Unread emails in the label that the app hasn't seen before (newest first)."""
    label = _label_id(svc, label_name)
    resp = svc.users().messages().list(
        userId="me", labelIds=[label], q=f"is:unread {SKIP_CATEGORIES}", maxResults=100
    ).execute()
    emails = []
    for ref in resp.get("messages", []):
        if ref["id"] in known_ids:
            continue
        # format="full" reads the message WITHOUT marking it as read.
        full = svc.users().messages().get(userId="me", id=ref["id"], format="full").execute()
        emails.append(parse_message(full))
        if len(emails) >= max_new:
            break
    return emails


# ---------- Drafts ----------

def _reply_subject(subject):
    return subject if subject.lower().startswith("re:") else f"Re: {subject}"


def _build_reply(email, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = email["reply_to"]
    msg["Subject"] = _reply_subject(email["subject"])
    if email.get("message_id_header"):
        # These two headers make Gmail show the draft inside the original conversation.
        msg["In-Reply-To"] = email["message_id_header"]
        msg["References"] = f"{email.get('references_header', '')} {email['message_id_header']}".strip()
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw, "threadId": email["thread_id"]}


def save_draft(svc, email, body, draft_id=None):
    """Create the reply draft, or update it if it already exists. Returns the draft id."""
    message = _build_reply(email, body)
    if draft_id:
        try:
            svc.users().drafts().update(
                userId="me", id=draft_id, body={"id": draft_id, "message": message}
            ).execute()
            return draft_id
        except HttpError as e:
            if e.status_code != 404:  # 404 = you deleted or sent it in Gmail; make a new one
                raise GmailError(f"Couldn't update the Gmail draft ({e.status_code}).")
    try:
        draft = svc.users().drafts().create(userId="me", body={"message": message}).execute()
    except HttpError as e:
        raise GmailError(f"Couldn't create the Gmail draft ({e.status_code}).")
    return draft["id"]


def delete_draft(svc, draft_id):
    try:
        svc.users().drafts().delete(userId="me", id=draft_id).execute()
    except HttpError as e:
        if e.status_code != 404:
            raise GmailError(f"Couldn't delete the Gmail draft ({e.status_code}).")


def thread_link(thread_id, my_address):
    return f"https://mail.google.com/mail/?authuser={my_address}#all/{thread_id}"
