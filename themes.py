"""Color themes: built-in presets plus your own custom themes (stored in the database)."""
import re

# The 7 colors a theme is made of. Everything else (soft accent, chips...) is derived in style.css.
COLOR_KEYS = {
    "bg": "Background",
    "panel": "Cards",
    "text": "Text",
    "muted": "Secondary text",
    "border": "Borders",
    "accent": "Accent (buttons & links)",
    "danger": "Warnings & delete",
}

PRESETS = {
    "light": {"name": "Light", "bg": "#f6f7fb", "panel": "#ffffff", "text": "#1d2130", "muted": "#6b7185",
              "border": "#e2e5ee", "accent": "#4f5bd5", "danger": "#c0392b"},
    "dark": {"name": "Dark", "bg": "#15171e", "panel": "#1f222b", "text": "#e8eaf2", "muted": "#9aa0b4",
             "border": "#333744", "accent": "#8b94ff", "danger": "#ff7b6b"},
    "pastel": {"name": "Pastel", "bg": "#fdf5f9", "panel": "#ffffff", "text": "#3b2f3a", "muted": "#85727f",
               "border": "#f0dbe7", "accent": "#b9508a", "danger": "#c0392b"},
    "forest": {"name": "Forest", "bg": "#f1f5ef", "panel": "#ffffff", "text": "#1f2a1f", "muted": "#5f6d58",
               "border": "#d8e2d2", "accent": "#2f7d4f", "danger": "#b03a2e"},
    "sunset": {"name": "Sunset", "bg": "#fff6ef", "panel": "#ffffff", "text": "#2e211a", "muted": "#85695a",
               "border": "#f1dccb", "accent": "#d0552a", "danger": "#a82a24"},
    "ocean": {"name": "Ocean", "bg": "#0e1c2a", "panel": "#15283a", "text": "#e3eef7", "muted": "#93a9bd",
              "border": "#264058", "accent": "#4fb3d9", "danger": "#ff7b6b"},
    "midnight": {"name": "Midnight", "bg": "#0c0c11", "panel": "#17171f", "text": "#ececf3", "muted": "#9a9aae",
                 "border": "#2a2a38", "accent": "#b48cff", "danger": "#ff6b81"},
    "weed": {"name": "Weed 🌿", "bg": "#dff0d2", "panel": "#f7fcf2", "text": "#1b2e14", "muted": "#52704a",
             "border": "#c2dcb1", "accent": "#2f8f24", "danger": "#b03a2e", "stickers": "leaves"},
}

# Decorative stickers a theme can show around the edges of the window.
STICKERS = {"": "None", "leaves": "Cannabis leaves 🌿"}

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def clean_colors(colors: dict) -> dict:
    """Validate a theme's colors. Raises ValueError with a friendly message."""
    out = {}
    for key, label in COLOR_KEYS.items():
        value = str((colors or {}).get(key, "")).strip()
        if not HEX.match(value):
            raise ValueError(f"“{label}” needs a color like #4f5bd5.")
        out[key] = value.lower()
    return out


def _luminance(hex_color: str) -> float:
    def channel(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _vars(colors: dict) -> str:
    # Text on accent-colored buttons: white or near-black, whichever is easier to read.
    on_accent = "#ffffff" if contrast(colors["accent"], "#ffffff") >= contrast(colors["accent"], "#111111") else "#111111"
    scheme = "dark" if _luminance(colors["bg"]) < 0.2 else "light"
    decls = "".join(f"--{k}:{colors[k]};" for k in COLOR_KEYS)
    return f"{decls}--on-accent:{on_accent};color-scheme:{scheme};"


def stickers_for(selected: str, custom: dict) -> str:
    if selected in PRESETS:
        return PRESETS[selected].get("stickers", "")
    if selected in custom:
        return custom[selected].get("stickers", "")
    return ""


def clean_stickers(value) -> str:
    value = str(value or "")
    if value not in STICKERS:
        raise ValueError("Unknown sticker style.")
    return value


def theme_css(selected: str, custom: dict) -> str:
    """CSS for the chosen theme. 'system' follows your Mac's light/dark mode."""
    if selected in PRESETS:
        return f":root{{{_vars(PRESETS[selected])}}}"
    if selected in custom:
        return f":root{{{_vars(custom[selected]['colors'])}}}"
    return (f":root{{{_vars(PRESETS['light'])}}}"
            f"@media (prefers-color-scheme: dark){{:root{{{_vars(PRESETS['dark'])}}}}}")


def presets_for_api():
    return [{"id": pid, "name": p["name"], "colors": {k: p[k] for k in COLOR_KEYS}, "stickers": p.get("stickers", "")}
            for pid, p in PRESETS.items()]
