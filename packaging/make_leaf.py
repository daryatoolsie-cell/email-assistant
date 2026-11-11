"""Generates the cannabis-leaf sticker shape (an SVG path) used by the Weed theme.
Output is pasted into templates/stickers.html. Run: python packaging/make_leaf.py"""
import math


def leaflet(length, width, angle_deg, teeth=9):
    """One pointed, jagged-edged leaflet starting at (0,0), pointing at angle (0 = straight up)."""
    pts_right, pts_left = [], []
    n = teeth * 2
    for i in range(1, n):
        t = i / n
        w = width * (math.sin(math.pi * t) ** 0.8) * (1 - 0.35 * t)
        if i % 2:  # tooth tip sticks out a bit
            w *= 1.18
        y = -length * t
        pts_right.append((w, y))
        pts_left.append((-w, y))
    outline = [(0, 0)] + pts_right + [(0, -length)] + list(reversed(pts_left))
    a = math.radians(angle_deg)
    rot = [(x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)) for x, y in outline]
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in rot) + "Z"


LEAFLETS = [(100, 13, 0), (88, 12, 26), (88, 12, -26), (68, 10, 54), (68, 10, -54), (40, 7, 86), (40, 7, -86)]
paths = [leaflet(*spec) for spec in LEAFLETS]
paths.append("M-2.5 0 L2.5 0 L1.5 34 L-1.5 34Z")  # stem
print(" ".join(paths))
