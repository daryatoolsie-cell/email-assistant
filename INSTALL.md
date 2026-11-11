## ✉️ Email Assistant for Mac

Writes emails to your professors and drafts replies to your Gmail with Claude AI. It **never sends anything on its own**: you always review and send.

**Needs:** a Mac with an Apple chip (M1 or newer) running macOS 12 or later.

### Install

1. Download **Email-Assistant-Mac.zip** below (under **Assets**).
2. Open the zip, then drag **Email Assistant** into your **Applications** folder.
3. Open it. The first time, macOS shows a warning because the app isn't from the App Store:
   - **macOS 15 (Sequoia) or newer:** click **Done** on the warning. Open **System Settings → Privacy & Security**, scroll down and click **Open Anyway** next to "Email Assistant", then confirm.
   - **macOS 14 or older:** in Applications, **right-click** Email Assistant, choose **Open**, then click **Open** again.

   You only have to do this once.

### First launch

The app asks for **your own Claude API key**. Each person pays for their own use, about 1¢ per email:

1. Go to [console.anthropic.com](https://console.anthropic.com) and sign up.
2. Add some credit under **Billing** ($5 lasts a long time).
3. Open **API Keys** and click **Create Key**. If it asks about identity federation, choose **Continue with an API key**.
4. Paste the key into the app.

Then add your name and sign-off in **Settings**, and pick a theme while you're there 🎨.

### Gmail (optional)

The **Work Inbox** drafts replies to your unread Gmail as Gmail drafts. To use it:
- If **Connect Gmail** appears straight away, ask the person who shared this app to **add your Gmail address as a tester**, then click it.
- If the app asks for a **credentials file**, follow the "Gmail setup" steps in the project's README to make your own, then choose the file in the app.

Google will say **"Google hasn't verified this app"**. Click **Continue**. That warning appears because this is a small personal project rather than a company app.

### Your data

Everything stays on your Mac, in `~/Library/Application Support/Email Assistant`. Your emails go only to Claude (to write drafts) and to Gmail (if you connect it).
