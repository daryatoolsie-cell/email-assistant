"""Where the app keeps its files.

- Running from the project folder (python app.py): data stays in this folder, like before.
- Running as the downloaded Mac app: data goes in ~/Library/Application Support/Email Assistant,
  so every person who installs the app has their own private data.
"""
import json
import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)  # True inside the packaged .app

# Templates, static files and the optional bundled Google client file.
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))

if FROZEN or os.getenv("EMAIL_ASSISTANT_APP_MODE") == "1":
    if sys.platform == "darwin":
        DATA_DIR = Path.home() / "Library" / "Application Support" / "Email Assistant"
    else:
        DATA_DIR = Path(os.getenv("APPDATA", Path.home() / ".config")) / "Email Assistant"
else:
    DATA_DIR = Path(__file__).parent

DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_DIR / "config.json"


# ---------- Claude API key ----------
# Order: ANTHROPIC_API_KEY (from .env or the environment), then the key saved from the setup screen.

def get_api_key() -> str:
    env_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        return json.loads(CONFIG_FILE.read_text()).get("anthropic_api_key", "").strip()
    except (FileNotFoundError, ValueError):
        return ""


def save_api_key(key: str):
    try:
        config = json.loads(CONFIG_FILE.read_text())
    except (FileNotFoundError, ValueError):
        config = {}
    config["anthropic_api_key"] = key.strip()
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    CONFIG_FILE.chmod(0o600)  # readable only by you


def key_is_from_env() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
