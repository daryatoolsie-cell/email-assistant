"""Draws the app icon (packaging/icon.png, 1024x1024). The build turns it into a Mac .icns file."""
from pathlib import Path

from PIL import Image, ImageDraw

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

# Rounded-square background with a vertical gradient (macOS icon shape, with margin).
grad = Image.new("RGBA", (S, S))
top, bottom = (110, 122, 240), (69, 79, 196)
for y in range(S):
    t = y / S
    grad.paste(tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)) + (255,), (0, y, S, y + 1))
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle((100, 100, 924, 924), radius=185, fill=255)
img.paste(grad, (0, 0), mask)

d = ImageDraw.Draw(img)
# Envelope
x0, y0, x1, y1 = 250, 330, 774, 700
d.rounded_rectangle((x0, y0, x1, y1), radius=40, fill=(255, 255, 255, 255))
d.line([(x0 + 30, y0 + 40), ((x0 + x1) // 2, y0 + 230), (x1 - 30, y0 + 40)], fill=(110, 122, 240, 255), width=34, joint="curve")
# Sparkle (the "AI" part)
cx, cy, r = 770, 300, 95
d.polygon([(cx, cy - r), (cx + 22, cy - 22), (cx + r, cy), (cx + 22, cy + 22),
           (cx, cy + r), (cx - 22, cy + 22), (cx - r, cy), (cx - 22, cy - 22)], fill=(255, 214, 102, 255))

out = Path(__file__).parent / "icon.png"
img.save(out)
print(f"Wrote {out}")
