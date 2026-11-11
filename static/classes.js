// Classes page: one tidy card per class with its syllabus info and exams/assignments.

const FACTS = [
  ["🕑", "Office hours", (p) => p.office_hours],
  ["📅", "Class times", (p) => p.course_info.class_times],
  ["📍", "Where", (p) => p.course_info.location],
  ["👥", "TAs", (p) => p.course_info.teaching_assistants],
];

function shortDate(it) {
  if (!it.due_date) return it.date_text ? esc(it.date_text) : "No date";
  const d = new Date(`${it.due_date}T${it.due_time || "00:00"}`);
  return d.toLocaleDateString([], { month: "short", day: "numeric" }) +
    (it.due_time ? ", " + d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "");
}

function countdown(it) {
  if (!it.due_date) return "";
  const n = Math.round((new Date(it.due_date) - new Date(localToday())) / 86400000);
  if (n < 0) return `<span class="chip">past</span>`;
  const label = n === 0 ? "today" : n === 1 ? "tomorrow" : `in ${n} days`;
  return `<span class="chip ${n <= 2 ? "err" : n <= 7 ? "warn" : ""}">${label}</span>`;
}

function itemLine(it) {
  const details = [it.topics && `<div><strong>${it.kind === "exam" || it.kind === "quiz" ? "What's on it" : "Notes"}:</strong> ${esc(it.topics)}</div>`,
                   it.description && `<div class="muted">${esc(it.description)}</div>`,
                   it.weight && `<div class="muted">Worth ${esc(it.weight)}</div>`].filter(Boolean).join("");
  const line = `<span class="il-date">${shortDate(it)}</span>
    <span class="il-title">${(KIND_LABELS[it.kind] || "").split(" ")[0]} ${esc(it.title)}</span> ${countdown(it)}`;
  return details
    ? `<li><details><summary>${line}</summary><div class="il-more small">${details}</div></details></li>`
    : `<li><div class="il-row">${line}</div></li>`;
}

function classCard(p, items) {
  const info = p.course_info || {};
  const today = localToday();
  const open = items.filter((it) => !it.done && (!it.due_date || it.due_date >= today));
  const doneCount = items.length - open.length;
  const facts = FACTS.map(([icon, label, get]) => [icon, label, get(p)]).filter(([, , v]) => v);
  const subtitle = [info.course_title, info.term].filter(Boolean).join(" · ");
  return `
  <section class="panel class-card" id="class-${p.id}">
    <div class="class-head">
      <div>
        <h2>${esc(p.course)}${subtitle ? ` <span class="muted class-sub">${esc(subtitle)}</span>` : ""}</h2>
        <div class="muted small">${esc(p.name)} · ${esc(p.email)}</div>
      </div>
      <div class="row" style="margin:0">
        <a class="btn secondary" href="/?prof=${p.id}">✉️ Email</a>
        <button class="link" data-upload="${p.id}">Update syllabus</button>
      </div>
    </div>

    ${facts.length ? `<div class="facts">${facts.map(([icon, label, v]) =>
      `<div class="fact-tile"><div class="muted small">${icon} ${label}</div><div>${esc(v)}</div></div>`).join("")}</div>` : ""}

    ${info.grading || info.policies ? `<div class="fold-row">
      ${info.grading ? `<details><summary>📊 Grading</summary><div class="small fold-body">${esc(info.grading)}</div></details>` : ""}
      ${info.policies ? `<details><summary>📋 Policies</summary><div class="small fold-body">${esc(info.policies)}</div></details>` : ""}
    </div>` : ""}

    ${items.length ? `
      <h3 class="items-head">Exams &amp; assignments <span class="muted small">${open.length} upcoming${doneCount ? ` · ${doneCount} done or past` : ""}</span></h3>
      ${open.length ? `<ul class="item-lines">${open.map(itemLine).join("")}</ul>` : `<p class="muted small">Nothing upcoming. 🎉</p>`}
      <a class="small" href="/upcoming">Check off items &amp; study checklists on Upcoming →</a>`
    : `<p class="muted small">No syllabus added for this class yet.</p>`}
  </section>`;
}

async function loadClasses() {
  const [profs, items] = await Promise.all([api("GET", "/api/professors"), api("GET", "/api/items")]);
  $("#class-list").innerHTML = profs.map((p) => classCard(p, items.filter((it) => it.professor_id === p.id))).join("");
  $("#classes-empty").classList.toggle("hidden", profs.length > 0);
  if (location.hash) document.querySelector(location.hash)?.scrollIntoView();
}

// "Update syllabus" uses the same upload → review flow (it matches the class automatically).
$("#class-list").addEventListener("click", (e) => {
  if (e.target.dataset.upload) $("#syllabus-file").click();
});

window.afterSyllabusSaved = async (id) => {
  await loadClasses();
  document.querySelector(`#class-${id}`)?.scrollIntoView({ behavior: "smooth" });
};

loadClasses();
