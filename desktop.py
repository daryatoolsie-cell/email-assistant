"""Runs Email Assistant in its own window (this is what the downloadable Mac app runs).

    python desktop.py              open the app window
    python desktop.py --selftest   start, load each page, and exit (used when building the app)
"""
import os
import socket
import subprocess
import sys
import threading
import urllib.request

from werkzeug.serving import make_server

if getattr(sys, "frozen", False):
    os.environ["EMAIL_ASSISTANT_APP_MODE"] = "1"
    # A Mac app has no Terminal, so messages and errors go to a log file instead:
    # ~/Library/Application Support/Email Assistant/app.log
    from paths import DATA_DIR
    _log = open(DATA_DIR / "app.log", "w", buffering=1, encoding="utf-8")
    sys.stdout = sys.stderr = _log

from app import APP_TOKEN, app  # noqa: E402


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server():
    port = free_port()
    server = make_server("127.0.0.1", port, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{port}"


class Bridge:
    """Functions the page can call (as window.pywebview.api.*) for things a web page can't do itself."""

    def open_url(self, url):
        if not url.startswith(("https://", "http://", "mailto:")):
            return False
        if sys.platform == "darwin":
            subprocess.run(["open", url], check=False)
        else:
            import webbrowser
            webbrowser.open(url)
        return True

    def copy_text(self, text):
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=False)
            return True
        return False


def selftest():
    # A placeholder key so the real pages render instead of redirecting to the setup screen.
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-selftest")
    server, base = start_server()
    failures = []
    for path in ("/setup", "/", "/settings", "/work", "/static/style.css", "/static/common.js"):
        try:
            with urllib.request.urlopen(base + path, timeout=10) as r:
                print(f"{r.status} {path}")
        except Exception as e:  # noqa: BLE001
            failures.append(f"{path}: {e}")
    req = urllib.request.Request(base + "/api/themes", headers={"X-App-Token": APP_TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            print(f"{r.status} /api/themes")
    except Exception as e:  # noqa: BLE001
        failures.append(f"/api/themes: {e}")
    # Make sure the libraries were bundled and their data files are there.
    import anthropic
    from googleapiclient.discovery import build

    import webview  # noqa: F401
    client = anthropic.Anthropic(api_key="sk-ant-selftest")
    _ = (client.beta.messages, client.models)
    build("gmail", "v1", developerKey="selftest", cache_discovery=False, static_discovery=True)
    print("libraries OK")
    server.shutdown()
    if failures:
        print("SELFTEST FAILED:\n" + "\n".join(failures))
        sys.exit(1)
    print("SELFTEST OK")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    import webview

    server, base = start_server()
    webview.create_window("Email Assistant", base, js_api=Bridge(), width=1100, height=860,
                          min_size=(520, 500), text_select=True)
    webview.start()
    server.shutdown()


if __name__ == "__main__":
    main()
