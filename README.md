# ✉️ AI Email Assistant

A personal web app that drafts emails for you with Claude. It runs on your own Mac at `http://localhost:8000`.

**Current status: all 3 phases done**
- ✅ Phase 1: professors, quick-draft buttons, copy / open in Outlook / open in Mail, draft history
- ✅ Phase 2: Settings page (name, school, sign-off, signature) and Regenerate / Make Shorter / Make More Formal / Make More Casual
- ✅ Phase 3: Work Inbox: reads unread Gmail and saves AI-written replies as **Gmail drafts** (never sends)
- ✅ Syllabus upload: auto-fills professors, office hours, exams (with topics) and assignments
- ✅ Themes: 8 built-in themes (including Weed 🌿 with stickers) plus your own (Settings → Appearance)
- ✅ Downloadable Mac app that friends can install from a GitHub release page (see "Mac app & sharing")

## Updating from an earlier phase

Your professors, history and settings are in `data.db`, and your key is in `.env`. Neither file is in the download, so updating won't touch them.

1. Stop the app (`Control + C` in Terminal).
2. Unzip the new download. Open the new `email-assistant` folder, select **everything inside it**, and drag it into your existing `email-assistant` folder. Choose **Replace** when asked.
3. Start the app again with `python app.py`.

**Updating to Phase 3?** Also run `pip install -r requirements.txt` (with the venv active) before starting.

---

## Setup (Mac, one time)

### 1. Check that Python is installed

Open the **Terminal** app and run:

```bash
python3 --version
```

You need **3.10 or newer**. If you get an error or an older version, install the latest Python from <https://www.python.org/downloads/macos/> and open a new Terminal window.

### 2. Go to the project folder

```bash
cd ~/path/to/email-assistant
```

(Tip: type `cd ` with a space, then drag the folder from Finder into the Terminal window and press Enter.)

### 3. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

You'll see `(.venv)` at the start of your Terminal prompt. Run `source .venv/bin/activate` again each time you open a new Terminal window to use the app.

### 4. Get a Claude API key

1. Go to <https://console.anthropic.com> and sign up or log in.
2. Add a little credit under **Billing**. Each email costs about 1 cent with the default model, so $5 lasts a long time.
3. Open **API Keys**, click **Create Key**, and copy it (it starts with `sk-ant-`).

### 5. Put the key in a `.env` file

```bash
cp .env.example .env
```

```bash
open -e .env
```

Replace `sk-ant-your-key-here` with your real key, then save. **Never share this file or upload it anywhere.** It's already listed in `.gitignore`.

> Want it cheaper? Change `CLAUDE_MODEL=claude-opus-5-5` to `CLAUDE_MODEL=claude-haiku-5-5`.

---

## Running the app

```bash
source .venv/bin/activate
```

```bash
python app.py
```

Then open <http://localhost:8000> in your browser. To stop the app, press `Control + C` in Terminal.

## Using it

**First:** open **Settings** (top right) and enter your name, school and sign-off. Your signature is added to the end of every email automatically, exactly as shown in the preview.

1. Click **+ Add professor** and enter their name, email, course (e.g. `Marketing 201`) and any notes (e.g. `Goes by Dr. Smith`, `Very casual`).
2. Click the professor's card ("Email Marketing 201 Professor").
3. If you like, type extra details (e.g. `I have a doctor's note`), then click a button such as **🤒 Sick**.
4. Edit the draft if you want, or use the tweak buttons:
   - **🔄 Regenerate**: writes a fresh version using the same button and details. It replaces the current draft.
   - **✂️ Make Shorter**, **🎓 Make More Formal** and **😊 Make More Casual** rewrite the text that's *currently in the box*, including your own edits. Your signature is kept as is.
5. When it's ready:
   - **📋 Copy**: copies the subject and body to paste anywhere.
   - **Open in Outlook**: opens a new email in Outlook on the web (your school account) with everything filled in.
   - **Open in Mail app**: opens your Mac's default mail app.
6. Every draft is saved under **History**. Edits you make are saved there too when you click out of the text box.

Your professors and history are stored in `data.db` in the project folder. Delete that file to start fresh.

---

## Gmail setup (Phase 3, one time, about 15 minutes)

The Work Inbox reads your unread Gmail and saves suggested replies as **drafts**. It can't send anything: there's no sending code in this app. You always review the draft and click Send yourself in Gmail.

To let the app read your Gmail, Google needs you to create your own small "app" in Google Cloud. It's free.

### 1. Install the new dependencies

In Terminal, in the project folder, with `(.venv)` showing:

```bash
pip install -r requirements.txt
```

### 2. Create a Google Cloud project

1. Go to <https://console.cloud.google.com> and sign in with **the Gmail account you use for work**.
2. If asked, accept the terms. At the top left, click the project picker (it may say "Select a project"), then **New project**.
3. Name it `Email Assistant`, click **Create**, and make sure it's selected at the top.

### 3. Turn on the Gmail API

1. In the search bar at the top, type **Gmail API** and open it.
2. Click **Enable**.

### 4. Set up the sign-in screen

1. Open <https://console.cloud.google.com/auth/overview> (or use the **☰ menu**: **APIs & Services**, then **OAuth consent screen**). Check that **Email Assistant** is the project selected at the top, then click **Get started**.
2. **App name:** `Email Assistant`. **User support email:** your Gmail. Click **Next**.
3. **Audience:** choose **External**. Click **Next**.
4. **Contact information:** your Gmail. Click **Next**, tick the agreement box, then click **Continue** and **Create**.
5. In the left menu, open **Audience**. Under **Test users**, click **Add users**, enter your work Gmail address and click **Save**.
   *(Leave the app in "Testing". You don't need to publish it.)*

### 5. Create the credentials file

1. In the left menu, open **Clients** and click **Create client**.
2. **Application type:** choose **Desktop app**. Name it `Email Assistant Mac` and click **Create**.
3. In the window that appears, click **Download JSON**. (If you closed it, click the client's name, then the download icon.)
4. In Finder, go to **Downloads** and find the file. It's named something like `client_secret_1234...json`.
5. Rename it to exactly `credentials.json` and move it into your `email-assistant` folder, next to `app.py`.

> ⚠️ Macs often hide file extensions, so the file can end up named `credentials.json.json` without you noticing. To check, run `ls` in Terminal inside the project folder. You should see `credentials.json` in the list.

**Keep `credentials.json` and `token.json` private.** Don't share or upload them. They're already in `.gitignore`.

### 6. Connect

1. Restart the app (`Control + C`, then `python app.py`) and open **Work Inbox**.
2. Click **Connect Gmail**. A Google tab opens. Choose your work Gmail account.
3. You'll see **"Google hasn't verified this app"**. That's expected, because it's your own private app. Click **Continue**.
4. Tick the boxes to allow reading email and managing drafts, then click **Continue**.
5. When you see "Gmail connected!", close that tab and go back to the app.

The app saves a `token.json` file so you stay connected.

> **Reconnecting every 7 days is normal.** Google signs "Testing" apps out after 7 days. When it happens, the Work Inbox asks you to connect again. Just click **Connect Gmail** again.

### Using the Work Inbox

1. In **Settings**, fill in **Work context** (your job and how you like to reply). This makes replies much better. Optionally add a **work signature**, a **label** to check (blank = Inbox) and **emails per check** (default 10).
2. On **Work Inbox**, click **📥 Check inbox**. For each new unread email the app:
   - **skips** newsletters, no-reply/automated senders and your own emails (Gmail's Promotions, Social, Updates and Forums tabs are ignored too),
   - asks Claude whether it needs a reply. FYIs and notifications are marked **No reply needed**,
   - otherwise writes a reply and saves it as a **draft in the same Gmail conversation**.
3. Review each reply. Edit it and click **💾 Save to Gmail draft**, or use **Regenerate / Shorter / More Formal / More Casual**. These update the Gmail draft automatically.
4. Click **Open in Gmail ↗**, check the draft, and click **Send** in Gmail yourself.
5. Click **✓ Mark done** to hide an email (the draft stays in Gmail), or **🗑 Delete draft** to remove the draft from Gmail.

Good to know:
- Emails **stay unread** in Gmail. The app doesn't change them.
- Each email is processed **once**. Clicking Check inbox again only picks up emails that are new since last time.
- For a skipped or "no reply needed" email, **✍️ Draft a reply anyway** writes one.
- Cost: about 1¢ per email that gets a reply (with the default model). Skipped emails cost nothing.

## Add a class from its syllabus

On **Professors**, click **📄 Add from syllabus** and choose the syllabus PDF (download it from Brightspace first), or a photo/screenshot of it. Word files: open them and use **File → Save as PDF**.

Claude reads it (30–90 seconds, about 10–20¢) and fills in a **review screen**:
- the professor's name, email and course, plus office hours, class times, TAs, grading and key policies,
- every **exam, quiz, assignment and project** with its date, and for exams **what's on it** (from the syllabus, or worked out from the schedule) plus a study checklist.

Check everything, then click **Save**. Items marked **⚠️ needs a date** had no exact date in the syllabus (e.g. "Week 12"). Add the date if you know it. Untick **Keep** to skip an item, or use **+ Add an item**.

Nothing is saved until you click Save. Uploading a newer syllabus for the same class (same professor email or course) updates it and replaces its syllabus items. When you pick a professor, **📚 Class info & upcoming** shows everything from their syllabus.

---

## Themes

Go to **Settings → Appearance** and click a theme to switch instantly. **Match my Mac** follows your Mac's light/dark mode. **Weed 🌿** adds cannabis-leaf, peace-sign and sparkle stickers around the edges.

To make your own, click **+ New theme**, give it a name, pick a starting theme, change any of the 7 colors, and optionally turn on **Stickers**. The whole app previews your colors as you edit. If text becomes hard to read, a warning appears (you can still save). Custom themes have **Edit** and **Delete** buttons.

---

## Mac app & sharing

The app can also run as a normal Mac app in its own window, with no Terminal, and your friends can download it.

### Try the app window on your Mac

```bash
pip install -r requirements-app.txt
```

```bash
python desktop.py
```

This uses your project folder's data, the same as `python app.py`.

### Publish a download for friends (GitHub)

GitHub builds the Mac app for you on its own Macs, for free:

1. Put this project in a GitHub repository (Claude can set this up for you).
2. Every push to `main` builds and tests the app. Go to the repo's **Actions** tab, open the latest run, and download **Email-Assistant-Mac** under *Artifacts* to try it.
3. To publish a new version for friends, change the number in the `VERSION` file (e.g. `1.0.0` to `1.0.1`) and push. You can also do this on github.com: open `VERSION`, click the ✏️ pencil, change the number, and click **Commit changes**.
   A few minutes later the **Releases** page has a new **Email-Assistant-Mac.zip** with install instructions (from `INSTALL.md`). Share that page's link: `https://github.com/<your-username>/email-assistant/releases/latest`

Good to know:
- **The download is for Macs with Apple chips (M1 and newer).** Intel Macs aren't supported.
- **The "unverified developer" warning:** the app isn't signed with a paid Apple Developer account ($99/year), so macOS warns the first time it opens. `INSTALL.md` explains the one-time fix to your friends.
- **Each friend uses their own Claude API key.** The app asks for it on first launch and stores it only on their Mac.
- **Each install has its own private data**, in `~/Library/Application Support/Email Assistant`.

### Gmail for friends (optional)

Without anything extra, each friend needs their own Google `credentials.json` (the Gmail setup steps above) and chooses it in the Work Inbox. That's a lot to ask of friends. The easier option:

1. In your Google Cloud project, open **Google Auth Platform → Audience** and add each friend's Gmail under **Test users** (up to 100).
2. In GitHub, go to the repo's **Settings → Secrets and variables → Actions → New repository secret**. Name it `GOOGLE_CLIENT_JSON` and paste in the **entire contents** of your `credentials.json`.
3. Publish a new version tag. Now **Connect Gmail** works for your testers with no setup.

Limits from Google: at most 100 test users, and testers are signed out every 7 days while the app is in "Testing". To let anyone use Gmail without being added, Google requires a verification and security review (it costs money and takes weeks). Only people who connect their *own* Gmail can ever see their mail. You can't see your friends' email.

### Moving your current data into the Mac app

The downloaded app keeps its data in a different place from your project folder. To bring your professors, history, settings and Gmail connection with you:

1. Quit both the app and `python app.py`.
2. In Finder, press **Command + Shift + G** and go to `~/Library/Application Support/Email Assistant` (open the Mac app once first, so the folder exists).
3. Copy `data.db`, and also `credentials.json` and `token.json` if you have them, from your project folder into that folder. Replace when asked.

The app will ask for your API key once. Paste the same key that's in your `.env`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `command not found: python` | Use `python3` instead, or activate the venv first (`source .venv/bin/activate`). |
| "Your Claude API key isn't valid" | Check `.env`: the line must be exactly `ANTHROPIC_API_KEY=sk-ant-...` with no quotes or spaces. Restart the app after editing it. |
| "Address already in use" | Another copy is running. Close the other Terminal window, or press `Control + C` there. |
| Open in Outlook shows a login page | Log in with your school account once, then click the button again. |
| Emails sign off as `[Your Name]` | Enter your name on the **Settings** page and click **Save settings**. |
| A page looks broken after updating | Hard-refresh the browser with `Command + Shift + R`. |
| `ModuleNotFoundError: No module named 'google...'` | Run `pip install -r requirements.txt` with the venv active. |
| "credentials.json is missing" | See Gmail setup step 5. Check that the name is exactly `credentials.json` (not `.json.json`) and that it's next to `app.py`. |
| "Access blocked: … has not completed the Google verification process" | You didn't add yourself as a **Test user** (Gmail setup step 4.5), or you signed in with a different Google account. |
| No Google tab opens after Connect Gmail | Look in Terminal: the app prints a sign-in link there. Copy it into your browser. |
| "Gmail isn't connected (or the connection expired)" | The weekly sign-out. Click **Connect Gmail** again. |
| "No Gmail label called …" | The label in Settings must match Gmail exactly. Leave it blank to use your Inbox. |
| "This page is out of date" | The app was restarted while the page was open. Refresh the page (`Command + R`). |
| The Mac app won't open or acts strangely | Look at `~/Library/Application Support/Email Assistant/app.log` for error messages. |

## Project layout

```
app.py              web server and routes (python app.py = browser mode)
desktop.py          runs the app in its own window (what the Mac app runs)
paths.py            where data and the API key are stored
themes.py           built-in themes and theme colors
ai.py               all Claude prompts and API calls
db.py               SQLite storage (data.db)
gmail_client.py     Gmail: sign-in, reading unread mail, creating drafts (never sends)
templates/base.html         shared page layout (header, nav)
templates/index.html        professors, drafting, history
templates/settings.html     settings page
templates/work.html         Work Inbox page
static/common.js            shared JavaScript helpers
static/work.js              Work Inbox page logic
static/themes.js            theme picker and builder
templates/setup.html        first-launch API key screen
packaging/                  Mac app build recipe and icon
.github/workflows/          GitHub's automatic Mac app build
INSTALL.md                  install guide shown on the download page
static/app.js, static/style.css
```
