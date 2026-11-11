// "Add from syllabus": upload → Claude reads it → you review and fix → save.
// Used on the Professors and Classes pages. After saving, it calls window.afterSyllabusSaved(id)
// if the page defines one.


let srItems = []; // items being reviewed (keeps study checklists that aren't shown as inputs)
let srProfs = []; // existing professors, for "Save to"

// ---------- Step 1: upload ----------
$("#syllabus-btn").onclick = () => $("#syllabus-file").click();

setupFilePicker($("#syllabus-file"), readSyllabus);

async function readSyllabus(file) {
  const status = $("#syllabus-status");
  const btn = $("#syllabus-btn");
  status.className = "muted";
  status.textContent = `📖 Reading “${file.name}”… This usually takes 30–90 seconds.`;
  btn.disabled = true;
  try {
    const form = new FormData();
    form.append("file", file);
    const r = await api("POST", "/api/syllabus/read", form);
    status.classList.add("hidden");
    await openReview(r);
  } catch (err) {
    status.className = "error";
    status.textContent = err.message;
  } finally {
    btn.disabled = false;
  }
}

// ---------- Step 2: review ----------
async function openReview({ extracted: x, match_id, filename }) {
  srProfs = await api("GET", "/api/professors");
  $("#sr-filename").textContent = filename || "syllabus";
  $("#sr-target").innerHTML = `<option value="">➕ New professor</option>` +
    srProfs.map((p) => `<option value="${p.id}">Update: ${esc(p.name)} (${esc(p.course)})</option>`).join("");
  $("#sr-target").value = match_id ? String(match_id) : "";

  $("#sr-name").value = x.professor_name;
  $("#sr-email").value = x.professor_email;
  $("#sr-course").value = x.course;
  const existing = srProfs.find((p) => p.id === match_id);
  $("#sr-notes").value = existing ? existing.notes : "";
  for (const k of ["office_hours", "class_times", "course_title", "term", "location", "teaching_assistants", "grading", "policies"]) {
    $(`#sr-${k}`).value = x[k] || "";
  }
  srItems = x.items.map((it) => ({ ...it, include: true }));
  renderItems();
  $("#sr-error").classList.add("hidden");
  $("#syllabus-review").classList.remove("hidden");
  $("#syllabus-review").scrollIntoView({ behavior: "smooth" });
}

function itemRow(it, i) {
  const noDate = !it.date;
  return `
  <div class="sr-item ${it.include ? "" : "excluded"}" data-i="${i}">
    <div class="sr-item-top">
      <label class="toggle"><input type="checkbox" data-f="include" ${it.include ? "checked" : ""}> Keep</label>
      <select data-f="kind">${Object.entries(KIND_LABELS).map(([k, l]) => `<option value="${k}" ${k === it.kind ? "selected" : ""}>${l}</option>`).join("")}</select>
      ${noDate ? `<span class="chip warn">⚠️ needs a date</span>` : ""}
      ${it.weight ? `<span class="chip">${esc(it.weight)}</span>` : ""}
    </div>
    <div class="sr-item-grid">
      <label>Title <input data-f="title" value="${esc(it.title)}"></label>
      <label>Date <input type="date" data-f="date" value="${esc(it.date)}"></label>
      <label>Time <input type="time" data-f="time" value="${esc(it.time)}"></label>
    </div>
    ${it.date_text ? `<div class="muted small">Syllabus says: “${esc(it.date_text)}”</div>` : ""}
    ${it.kind === "exam" || it.topics ? `<label>What's on it <textarea data-f="topics" rows="2">${esc(it.topics)}</textarea></label>` : ""}
    ${it.study_checklist?.length ? `<div class="muted small">✅ Study checklist: ${it.study_checklist.length} step${it.study_checklist.length === 1 ? "" : "s"} (shown later on the Upcoming page)</div>` : ""}
  </div>`;
}

function renderItems() {
  $("#sr-items").innerHTML = srItems.map(itemRow).join("") ||
    `<p class="muted">No exams or assignments found. Add them with “+ Add an item”.</p>`;
  const kept = srItems.filter((it) => it.include).length;
  const undated = srItems.filter((it) => it.include && !it.date).length;
  $("#sr-count").textContent = `· ${kept} kept${undated ? `, ${undated} without a date` : ""}`;
}

// Keep srItems in sync as you edit
$("#sr-items").addEventListener("input", (e) => {
  const row = e.target.closest(".sr-item");
  const f = e.target.dataset.f;
  if (!row || !f) return;
  const it = srItems[Number(row.dataset.i)];
  it[f] = e.target.type === "checkbox" ? e.target.checked : e.target.value;
});
// Re-draw (warnings, counts, topic box) only once a change is finished, so typing isn't interrupted.
$("#sr-items").addEventListener("change", (e) => {
  if (["include", "kind", "date"].includes(e.target.dataset.f)) renderItems();
});

$("#sr-add-item").onclick = () => {
  srItems.push({ kind: "assignment", title: "", date: "", date_text: "", time: "", topics: "",
                 description: "", weight: "", study_checklist: [], include: true });
  renderItems();
  $("#sr-items .sr-item:last-child input[data-f=title]").focus();
};

$("#sr-target").onchange = (e) => {
  const p = srProfs.find((x) => String(x.id) === e.target.value);
  if (p && !$("#sr-notes").value) $("#sr-notes").value = p.notes;
};

$("#sr-cancel").onclick = () => {
  if (!confirm("Discard this syllabus? Nothing has been saved yet.")) return;
  $("#syllabus-review").classList.add("hidden");
};

$("#sr-save").onclick = async () => {
  const body = {
    professor_id: $("#sr-target").value ? Number($("#sr-target").value) : null,
    professor: { name: $("#sr-name").value, email: $("#sr-email").value, course: $("#sr-course").value, notes: $("#sr-notes").value },
    office_hours: $("#sr-office_hours").value,
    info: Object.fromEntries(["course_title", "term", "class_times", "location", "teaching_assistants", "grading", "policies"]
      .map((k) => [k, $(`#sr-${k}`).value])),
    items: srItems.filter((it) => it.include && it.title.trim()),
  };
  if (body.professor_id) {
    const p = srProfs.find((x) => x.id === body.professor_id);
    if (!confirm(`Update ${p.name} (${p.course})? Their syllabus items will be replaced with these.`)) return;
  }
  const btn = $("#sr-save");
  btn.disabled = true;
  try {
    const r = await api("POST", "/api/syllabus/save", body);
    $("#syllabus-review").classList.add("hidden");
    toast(`Saved ${r.items_saved} exams & assignments`);
    if (window.afterSyllabusSaved) await window.afterSyllabusSaved(r.professor_id);
  } catch (err) {
    $("#sr-error").textContent = err.message;
    $("#sr-error").classList.remove("hidden");
  } finally {
    btn.disabled = false;
  }
};
