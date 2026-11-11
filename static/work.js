// Work Inbox page: connect Gmail, check for new emails, review AI-drafted replies.

const STATUS = {
  drafted: { label: "Draft saved in Gmail", cls: "ok" },
  no_reply: { label: "No reply needed", cls: "" },
  skipped: { label: "Skipped", cls: "" },
  error: { label: "Problem", cls: "err" },
  done: { label: "Done", cls: "" },
};

let emails = [];

// ---------- Gmail connection ----------
async function loadStatus() {
  const s = await api("GET", "/api/gmail/status");
  const show = (id, on) => $(id).classList.toggle("hidden", !on);
  show("#btn-connect", !s.connected && s.has_credentials_file);
  show("#btn-check", s.connected);
  show("#btn-disconnect", s.connected);
  show("#creds-upload", !s.has_credentials_file);
  if (s.connected) {
    $("#gmail-status").innerHTML = `Connected as <strong>${esc(s.email)}</strong>`;
  } else if (!s.has_credentials_file) {
    $("#gmail-status").innerHTML =
      "To connect Gmail, you need a Google credentials file. Follow “Gmail setup” in the guide, then choose the file below.";
  } else {
    $("#gmail-status").textContent = "Not connected.";
  }
  return s;
}

$("#creds-file").onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  try {
    await api("POST", "/api/gmail/credentials", form);
    toast("Credentials saved. Now click Connect Gmail.");
  } catch (err) {
    alert(err.message);
  }
  e.target.value = "";
  loadStatus();
};

$("#btn-connect").onclick = async () => {
  const btn = $("#btn-connect");
  btn.disabled = true;
  $("#gmail-status").textContent =
    "A Google sign-in tab just opened. Choose your work Gmail account and click Allow, then come back here.";
  try {
    await api("POST", "/api/gmail/connect");
    toast("Gmail connected");
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
    await loadStatus();
    loadEmails();
  }
};

$("#btn-disconnect").onclick = async () => {
  if (!confirm("Disconnect Gmail? Your drafts in Gmail stay where they are.")) return;
  await api("POST", "/api/gmail/disconnect");
  loadStatus();
};

// ---------- Checking the inbox ----------
$("#btn-check").onclick = async () => {
  const btn = $("#btn-check");
  btn.disabled = true;
  btn.textContent = "⏳ Checking…";
  const summary = $("#check-summary");
  summary.className = "summary muted";
  summary.textContent = "Reading new unread emails and drafting replies. This can take a minute…";
  try {
    const c = await api("POST", "/api/work/check");
    if (c.found === 0) {
      summary.textContent = "No new unread emails. You're all caught up! 🎉";
    } else {
      const parts = [`${c.drafted} draft${c.drafted === 1 ? "" : "s"} created`];
      if (c.no_reply) parts.push(`${c.no_reply} didn't need a reply`);
      if (c.skipped) parts.push(`${c.skipped} skipped (newsletters / automated)`);
      if (c.error) parts.push(`${c.error} had a problem`);
      summary.textContent = `Found ${c.found} new email${c.found === 1 ? "" : "s"}: ${parts.join(", ")}.`;
    }
  } catch (err) {
    summary.className = "summary error";
    summary.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "📥 Check inbox";
    loadEmails();
  }
};

// ---------- Email list ----------
function senderName(from) {
  const m = from.match(/^\s*"?([^"<]+?)"?\s*</);
  return m ? m[1] : from;
}

function card(e) {
  const st = STATUS[e.status] || { label: e.status, cls: "" };
  const date = new Date(e.received_ms).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
  const drafted = e.status === "drafted";
  return `
  <div class="email-card" data-id="${esc(e.gmail_id)}">
    <div class="top">
      <span class="from" title="${esc(e.from_addr)}">${esc(senderName(e.from_addr))}</span>
      <span class="chip ${st.cls}">${st.label}</span>
    </div>
    <div class="subject">${esc(e.subject)} <span class="muted small">· ${esc(date)}</span></div>
    ${e.note ? `<div class="muted small">${drafted ? "✍️" : "ℹ️"} ${esc(e.note)}</div>` : ""}
    <details>
      <summary class="muted small">Show original email</summary>
      <pre>${esc(e.body || e.snippet)}</pre>
    </details>
    ${drafted ? `
      <textarea class="reply" rows="9">${esc(e.reply_body)}</textarea>
      <div class="row">
        <button data-act="save" disabled>💾 Save to Gmail draft</button>
        <button class="secondary" data-act="regenerate">🔄 Regenerate</button>
        <button class="secondary" data-act="rewrite" data-style="shorter">✂️ Shorter</button>
        <button class="secondary" data-act="rewrite" data-style="formal">🎓 More Formal</button>
        <button class="secondary" data-act="rewrite" data-style="casual">😊 More Casual</button>
      </div>
      <div class="row">
        ${e.gmail_link ? `<button class="secondary" data-act="open" data-href="${esc(e.gmail_link)}">Open in Gmail ↗</button>` : ""}
        <button class="link" data-act="done">✓ Mark done</button>
        <button class="link danger" data-act="discard">🗑 Delete draft</button>
      </div>` : `
      <div class="row">
        ${e.status === "error"
          ? `<button class="secondary" data-act="regenerate">🔁 Try again</button>`
          : e.status !== "done" ? `<button class="secondary" data-act="regenerate">✍️ Draft a reply anyway</button>` : ""}
        ${e.status !== "done" ? `<button class="link" data-act="done">✓ Mark done</button>` : ""}
      </div>`}
  </div>`;
}

async function loadEmails() {
  emails = await api("GET", `/api/work/emails?show_done=${$("#show-done").checked ? 1 : 0}`);
  $("#emails").innerHTML = emails.map(card).join("");
  $("#emails-empty").classList.toggle("hidden", emails.length > 0);
}

$("#show-done").onchange = loadEmails;

// Enable "Save" as soon as you edit a reply
$("#emails").addEventListener("input", (ev) => {
  if (ev.target.classList.contains("reply")) {
    ev.target.closest(".email-card").querySelector("[data-act=save]").disabled = false;
  }
});

const BUSY_TEXT = { save: "💾 Saving…", regenerate: "✍️ Writing…", rewrite: "✍️ Rewriting…" };

$("#emails").addEventListener("click", async (ev) => {
  const btn = ev.target.closest("button[data-act]");
  if (!btn) return;
  const cardEl = btn.closest(".email-card");
  const id = encodeURIComponent(cardEl.dataset.id);
  const reply = cardEl.querySelector(".reply");
  const act = btn.dataset.act;
  if (act === "open") return openExternal(btn.dataset.href);

  if (act === "discard" && !confirm("Delete this reply draft from Gmail?")) return;
  if (act === "regenerate" && reply && !cardEl.querySelector("[data-act=save]").disabled &&
      !confirm("Regenerating will replace your unsaved edits. Continue?")) return;

  const buttons = cardEl.querySelectorAll("button");
  const wasDisabled = [...buttons].map((b) => b.disabled);
  buttons.forEach((b) => (b.disabled = true));
  const original = btn.textContent;
  if (BUSY_TEXT[act]) btn.textContent = BUSY_TEXT[act];

  try {
    if (act === "save") {
      await api("PUT", `/api/work/emails/${id}`, { reply_body: reply.value });
      toast("Saved to your Gmail draft");
    } else if (act === "regenerate") {
      await api("POST", `/api/work/emails/${id}/regenerate`);
      toast("New draft saved to Gmail");
    } else if (act === "rewrite") {
      await api("POST", `/api/work/emails/${id}/rewrite`, { style: btn.dataset.style, reply_body: reply.value });
      toast("Updated and saved to Gmail");
    } else if (act === "done") {
      await api("POST", `/api/work/emails/${id}/done`);
    } else if (act === "discard") {
      await api("POST", `/api/work/emails/${id}/discard`);
      toast("Draft deleted");
    }
    await loadEmails();
  } catch (err) {
    alert(err.message);
    btn.textContent = original;
    buttons.forEach((b, i) => (b.disabled = wasDisabled[i]));
  }
});

loadStatus();
loadEmails();
