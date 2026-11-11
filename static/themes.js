// Appearance: pick a theme, or build your own with a live preview.

let themeData = null;  // { selected, presets, custom, labels }
let editingId = null;  // custom theme being edited (null = new theme)
let builderOpen = false;

const builder = $("#theme-builder");

// --- color math (same rules as themes.py) ---
function luminance(hex) {
  const ch = (i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * ch(1) + 0.7152 * ch(3) + 0.0722 * ch(5);
}
function contrast(a, b) {
  const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

// Apply colors to the page right now (used for live preview and instant switching).
function applyColors(colors) {
  const root = document.documentElement.style;
  for (const [k, v] of Object.entries(colors)) root.setProperty(`--${k}`, v);
  root.setProperty("--on-accent", contrast(colors.accent, "#ffffff") >= contrast(colors.accent, "#111111") ? "#ffffff" : "#111111");
  root.setProperty("color-scheme", luminance(colors.bg) < 0.2 ? "dark" : "light");
}
function clearPreview() {
  document.documentElement.removeAttribute("style");
  setStickers(stickersFor(themeData.selected));
}

function setStickers(style) {
  document.documentElement.dataset.stickers = style || "";
}

function stickersFor(id) {
  return allThemes().find((t) => t.id === id)?.stickers || "";
}

function allThemes() {
  return [...themeData.presets, ...themeData.custom];
}

function colorsFor(id) {
  if (id === "system") {
    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    return themeData.presets.find((p) => p.id === (dark ? "dark" : "light")).colors;
  }
  return allThemes().find((t) => t.id === id)?.colors;
}

// --- theme picker ---
function swatch(c, stickers) {
  const leaf = stickers === "leaves" ? `<svg class="mini-leaf" viewBox="-115 -115 230 165"><use href="#sticker-leaf"/></svg>` : "";
  return `<div class="swatch" style="background:${c.bg}">
    <span style="background:${c.panel};border:1px solid ${c.border};width:44px;height:30px"></span>
    <span style="background:${c.accent};width:22px;height:14px"></span>
    <span style="background:${c.text};width:28px;height:4px"></span>
    ${leaf}
  </div>`;
}

function renderGrid() {
  const sys = { id: "system", name: "Match my Mac", colors: themeData.presets[0].colors };
  const cards = [sys, ...themeData.presets, ...themeData.custom].map((t) => {
    const custom = t.id.startsWith("custom-");
    const sw = t.id === "system"
      ? `<div class="swatch" style="background:linear-gradient(135deg, ${themeData.presets[0].colors.bg} 50%, ${themeData.presets[1].colors.bg} 50%)"></div>`
      : swatch(t.colors, t.stickers);
    return `<div class="theme-card ${themeData.selected === t.id ? "selected" : ""}" data-id="${esc(t.id)}" role="button" tabindex="0">
      ${sw}
      <div class="name">${esc(t.name)}${themeData.selected === t.id ? " ✓" : ""}</div>
      ${custom ? `<div class="actions"><button type="button" class="link" data-edit="${esc(t.id)}">Edit</button><button type="button" class="link danger" data-del="${esc(t.id)}">Delete</button></div>` : ""}
    </div>`;
  });
  cards.push(`<div class="theme-card new" data-new="1" role="button" tabindex="0">+ New theme</div>`);
  $("#theme-grid").innerHTML = cards.join("");
}

async function loadThemes() {
  themeData = await api("GET", "/api/themes");
  renderGrid();
}

$("#theme-grid").addEventListener("click", async (e) => {
  const edit = e.target.dataset.edit;
  const del = e.target.dataset.del;
  if (edit) return openBuilder(themeData.custom.find((t) => t.id === edit));
  if (del) {
    const t = themeData.custom.find((x) => x.id === del);
    if (!confirm(`Delete the theme “${t.name}”?`)) return;
    await api("DELETE", `/api/themes/${del}`);
    await loadThemes();
    clearPreview();
    applyColors(colorsFor(themeData.selected));
    return;
  }
  const card = e.target.closest(".theme-card");
  if (!card) return;
  if (card.dataset.new) return openBuilder(null);
  if (builderOpen) closeBuilder();
  const id = card.dataset.id;
  await api("PUT", "/api/themes/selected", { id });
  themeData.selected = id;
  clearPreview();
  if (id === "system") {
    // Reload so the page follows your Mac's light/dark setting again.
    location.reload();
    return;
  }
  applyColors(colorsFor(id));
  setStickers(stickersFor(id));
  renderGrid();
  toast("Theme applied");
});

$("#theme-grid").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.target.classList.contains("theme-card")) e.target.click();
});

// --- theme builder ---
function builderColors() {
  const out = {};
  for (const k of Object.keys(themeData.labels)) out[k] = builder.elements[`c_${k}`].value;
  return out;
}

function fillColors(colors) {
  for (const [k, v] of Object.entries(colors)) builder.elements[`c_${k}`].value = v;
  preview();
}

function preview() {
  const c = builderColors();
  applyColors(c);
  setStickers($("#sticker-select").value);
  const problems = [];
  if (contrast(c.text, c.panel) < 4.5) problems.push("Text is hard to read on the card color.");
  if (contrast(c.text, c.bg) < 4.5) problems.push("Text is hard to read on the background.");
  if (contrast(c.accent, c.panel) < 3) problems.push("Accent color is hard to see on cards.");
  const warn = $("#contrast-warning");
  warn.textContent = problems.length ? `⚠️ ${problems.join(" ")} You can still save it.` : "";
  warn.classList.toggle("hidden", !problems.length);
}

function openBuilder(theme) {
  editingId = theme ? theme.id : null;
  builderOpen = true;
  $("#builder-title").textContent = theme ? `Edit “${theme.name}”` : "New theme";
  $("#color-inputs").innerHTML = Object.entries(themeData.labels)
    .map(([k, label]) => `<label>${esc(label)}<input type="color" name="c_${k}"></label>`).join("");
  $("#sticker-select").innerHTML = Object.entries(themeData.sticker_options)
    .map(([v, label]) => `<option value="${esc(v)}">${esc(label)}</option>`).join("");
  $("#sticker-select").value = theme ? theme.stickers || "" : stickersFor(themeData.selected);
  $("#start-from").innerHTML = `<option value="">—</option>` +
    allThemes().map((t) => `<option value="${esc(t.id)}">${esc(t.name)}</option>`).join("");
  builder.elements.name.value = theme ? theme.name : "";
  const startColors = theme ? theme.colors : (colorsFor(themeData.selected) || themeData.presets[0].colors);
  fillColors(startColors);
  builder.classList.remove("hidden");
  builder.scrollIntoView({ behavior: "smooth" });
  builder.elements.name.focus();
}

function closeBuilder() {
  builderOpen = false;
  editingId = null;
  builder.classList.add("hidden");
  clearPreview();
  if (themeData.selected !== "system") applyColors(colorsFor(themeData.selected));
}

$("#start-from").onchange = (e) => {
  const t = allThemes().find((x) => x.id === e.target.value);
  if (t) {
    $("#sticker-select").value = t.stickers || "";
    fillColors(t.colors);
  }
};
builder.addEventListener("input", (e) => {
  if (e.target.type === "color") preview();
});
$("#sticker-select").onchange = preview;
$("#builder-cancel").onclick = closeBuilder;

builder.onsubmit = async (e) => {
  e.preventDefault();
  const body = { name: builder.elements.name.value, colors: builderColors(), stickers: $("#sticker-select").value };
  try {
    if (editingId) await api("PUT", `/api/themes/${editingId}`, body);
    else await api("POST", "/api/themes", body);
    const wasEditing = editingId;
    builderOpen = false;
    builder.classList.add("hidden");
    await loadThemes();
    if (wasEditing && themeData.selected !== wasEditing) {
      clearPreview();
      if (themeData.selected !== "system") applyColors(colorsFor(themeData.selected));
    }
    toast("Theme saved");
  } catch (err) {
    alert(err.message);
  }
};

loadThemes();
