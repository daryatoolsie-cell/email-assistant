# PyInstaller recipe for the Mac app. Built by GitHub Actions (.github/workflows/build-mac.yml).
# To build on your own Mac instead:  pyinstaller --noconfirm packaging/EmailAssistant.spec
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
VERSION = os.getenv("APP_VERSION", "0.0.0").lstrip("v")

datas = [
    (os.path.join(ROOT, "templates"), "templates"),
    (os.path.join(ROOT, "static"), "static"),
]
# Optional: a Google "Desktop app" client so people can click Connect Gmail without their own setup.
client = os.path.join(ROOT, "packaging", "google_client.json")
if os.path.exists(client):
    datas.append((client, "."))
datas += collect_data_files("googleapiclient")  # Gmail API description files

a = Analysis(
    [os.path.join(ROOT, "desktop.py")],
    pathex=[ROOT],
    datas=datas,
    hiddenimports=collect_submodules("webview.platforms") + ["webview.platforms.cocoa"],
    excludes=["tkinter", "PyInstaller"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Email Assistant", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="Email Assistant")

icon = os.path.join(ROOT, "packaging", "icon.icns")
app = BUNDLE(
    coll,
    name="Email Assistant.app",
    icon=icon if os.path.exists(icon) else None,
    bundle_identifier="app.emailassistant.desktop",
    version=VERSION,
    info_plist={
        "CFBundleDisplayName": "Email Assistant",
        "CFBundleShortVersionString": VERSION,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
    },
)
