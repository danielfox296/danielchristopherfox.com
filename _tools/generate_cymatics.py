#!/usr/bin/env python3
"""
generate_cymatics.py — deterministic Chladni-figure SVG thumbnails.

For each article slug, derives a seed from md5(slug), picks a Chladni
plate mode pair (n, m) with n != m in 2..7 plus a slight rotation, and
renders the zero-level contour of

    f(x, y) = cos(n*pi*x) * cos(m*pi*y) - cos(m*pi*x) * cos(n*pi*y)

on the unit square as hand-rolled minimal SVG line art (no fill, no
axes, transparent background). Output: website/assets/cym/<slug>.svg
plus a manifest.json mapping slug -> {file, category, stroke}.

All 32 figures are guaranteed visually distinct: if two slugs hash to
the same (n, m, rotation-bucket), the collider is bumped to the next
free mode pair.

Usage:
    python3 _tools/generate_cymatics.py            # generate everything
Requires: numpy, matplotlib
    pip install numpy matplotlib --break-system-packages
"""

import hashlib
import json
import math
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")  # headless; we only use contour math, never its renderer
import matplotlib.pyplot as plt

# ----------------------------------------------------------------- config

SIZE = 400          # SVG viewBox is 0 0 SIZE SIZE
MARGIN = 24         # inner margin in px
STROKE_WIDTH = 2.2
GRID = 261          # samples per axis for the contour grid
RDP_EPS = 0.32      # path simplification tolerance, in output px
MAX_BYTES = 60 * 1024

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)                      # .../website
OUT_DIR = os.path.join(SITE, "assets", "cym")

CATEGORIES = {
    "field-guide": {
        "stroke": "#B1832F",  # butter-dark, legible on cream
        "slugs": [
            "store-music-and-customer-behavior",
            "store-music-and-retail-media",
            "make-your-stores-feel-premium",
            "differentiate-physical-retail-from-ecommerce",
            "increase-retail-dwell-time",
            "the-roi-of-in-store-experience",
        ],
    },
    "essay": {
        "stroke": "#C03A78",  # deep pink
        "slugs": [
            "catch-the-good-accident",
            "designing-for-permission",
            "every-room-is-already-scored",
            "music-in-the-public-square",
            "the-fools-errand",
            "the-rooms-that-cant-say-no",
            "two-and-a-half-buttons",
            "what-we-call-soul",
            "your-worth-was-never-the-work",
        ],
    },
    "note": {
        "stroke": "#2E7D46",  # deep green
        "slugs": [
            "best-music-tempo-for-retail",
            "can-music-change-what-people-buy",
            "can-music-make-customers-pay-more",
            "can-music-make-your-store-feel-premium",
            "does-background-music-increase-revenue",
            "does-music-affect-retail-sales",
            "does-music-influence-shoppers-subconsciously",
            "does-music-make-customers-browse-longer",
            "does-slow-music-make-people-shop-longer",
            "first-five-minutes-in-store",
            "how-music-affects-customer-behavior",
            "how-music-sets-the-mood-in-a-store",
            "is-your-music-driving-customers-away",
            "music-that-triggers-impulse-buying",
            "what-is-dwell-time-in-retail",
            "what-music-should-i-play-in-my-store",
            "when-does-fast-music-help-a-store",
        ],
    },
}

# All unordered Chladni pairs (n, m), n < m, in 2..7 — 15 distinct figures.
# (n, m) and (m, n) give mirror images of the same figure, so we treat
# them as one pattern and rely on rotation buckets for extra variety.
ALL_PAIRS = [(n, m) for n in range(2, 8) for m in range(n + 1, 8)]


# ------------------------------------------------------- deterministic pick

def params_for_slug(slug):
    """md5(slug) -> (n, m, rotation_deg). Deterministic, no RNG state."""
    h = hashlib.md5(slug.encode("utf-8")).digest()
    pair = ALL_PAIRS[h[0] % len(ALL_PAIRS)]
    # slight rotation: 13 buckets across roughly -9..+9 degrees
    rot_bucket = h[1] % 13
    rot = (rot_bucket - 6) * 1.5
    return pair[0], pair[1], rot, rot_bucket


def assign_params(slugs):
    """Assign (n, m, rot) per slug; on (pair, rot-bucket) collision, bump
    to the next free pair (then next rot bucket) so all figures differ."""
    used = set()
    out = {}
    for slug in slugs:
        n, m, rot, bucket = params_for_slug(slug)
        pair_idx = ALL_PAIRS.index((n, m))
        b = bucket
        for attempt in range(len(ALL_PAIRS) * 13):
            key = (ALL_PAIRS[pair_idx], b)
            if key not in used:
                break
            pair_idx = (pair_idx + 1) % len(ALL_PAIRS)
            if pair_idx == ALL_PAIRS.index((n, m)):
                b = (b + 1) % 13  # exhausted pairs at this bucket; shift rot
        used.add((ALL_PAIRS[pair_idx], b))
        nn, mm = ALL_PAIRS[pair_idx]
        out[slug] = (nn, mm, (b - 6) * 1.5)
    return out


# ------------------------------------------------------------ contour math

def chladni_contours(n, m):
    """Zero-level contour segments of the Chladni function on [0,1]^2.
    Returns a list of (k, 2) float arrays in unit-square coords."""
    t = np.linspace(0.0, 1.0, GRID)
    x, y = np.meshgrid(t, t)
    f = (np.cos(n * np.pi * x) * np.cos(m * np.pi * y)
         - np.cos(m * np.pi * x) * np.cos(n * np.pi * y))
    fig = plt.figure()
    ax = fig.add_subplot(111)
    cs = ax.contour(x, y, f, levels=[0.0])
    segs = []
    # allsegs is stable across matplotlib versions (vs .collections, removed in 3.10)
    for level_segs in cs.allsegs:
        for seg in level_segs:
            if len(seg) >= 2:
                segs.append(np.asarray(seg, dtype=float))
    plt.close(fig)
    return segs


# ------------------------------------------------------- path simplification

def rdp(points, eps):
    """Iterative Ramer-Douglas-Peucker on an (k, 2) array."""
    if len(points) < 3:
        return points
    keep = np.zeros(len(points), dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        seg = points[a:b + 1]
        d = seg[-1] - seg[0]
        norm = math.hypot(d[0], d[1])
        if norm < 1e-12:
            dist = np.hypot(seg[:, 0] - seg[0, 0], seg[:, 1] - seg[0, 1])
        else:
            rel = seg[0] - seg
            dist = np.abs(d[0] * rel[:, 1] - d[1] * rel[:, 0]) / norm
        i = int(np.argmax(dist))
        if dist[i] > eps:
            keep[a + i] = True
            stack.append((a, a + i))
            stack.append((a + i, b))
    return points[keep]


# ------------------------------------------------------------- SVG building

def to_svg_coords(seg_unit, rot_deg):
    """Unit-square contour -> rotated, scaled px coords inside the margin."""
    theta = math.radians(rot_deg)
    c, s = math.cos(theta), math.sin(theta)
    # shrink so the rotated square still fits in the drawing box
    shrink = 1.0 / (abs(c) + abs(s))
    half = (SIZE - 2 * MARGIN) / 2.0
    cx = cy = SIZE / 2.0
    p = seg_unit - 0.5                      # center
    xr = (p[:, 0] * c - p[:, 1] * s) * shrink
    yr = (p[:, 0] * s + p[:, 1] * c) * shrink
    out = np.empty_like(p)
    out[:, 0] = cx + xr * 2 * half
    out[:, 1] = cy - yr * 2 * half          # flip y for SVG
    return out


def fmt(v):
    s = ("%.1f" % v).rstrip("0").rstrip(".")
    return s if s else "0"


def path_d(points):
    parts = ["M%s %s" % (fmt(points[0][0]), fmt(points[0][1]))]
    px, py = points[0]
    for x, y in points[1:]:
        parts.append("l%s %s" % (fmt(x - px), fmt(y - py)))
        px, py = x, y
    return "".join(parts)


def build_svg(slug, n, m, rot, stroke):
    segs = chladni_contours(n, m)
    eps = RDP_EPS
    for _ in range(6):  # tighten until under the size budget
        paths = []
        for seg in segs:
            pts = to_svg_coords(seg, rot)
            pts = rdp(pts, eps)
            if len(pts) >= 2:
                paths.append(path_d(np.round(pts, 1)))
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
            'role="img" aria-label="Chladni resonance figure (mode %d,%d)">'
            '<g fill="none" stroke="%s" stroke-width="%s" '
            'stroke-linecap="round" stroke-linejoin="round">'
            % (SIZE, SIZE, n, m, stroke, STROKE_WIDTH)
        )
        svg += "".join('<path d="%s"/>' % d for d in paths)
        svg += "</g></svg>"
        data = svg.encode("utf-8")
        if len(data) <= MAX_BYTES:
            return data, len(paths)
        eps *= 1.8
    return data, len(paths)  # best effort (should never reach here)


# --------------------------------------------------------------------- main

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_slugs = []
    slug_cat = {}
    for cat, info in CATEGORIES.items():
        for slug in info["slugs"]:
            all_slugs.append(slug)
            slug_cat[slug] = cat

    params = assign_params(all_slugs)
    manifest = {}
    total = 0
    failed = []
    for slug in all_slugs:
        n, m, rot = params[slug]
        cat = slug_cat[slug]
        stroke = CATEGORIES[cat]["stroke"]
        try:
            data, npaths = build_svg(slug, n, m, rot, stroke)
        except Exception as e:  # pragma: no cover
            failed.append((slug, str(e)))
            continue
        out_path = os.path.join(OUT_DIR, slug + ".svg")
        with open(out_path, "wb") as fh:
            fh.write(data)
        total += len(data)
        manifest[slug] = {
            "file": "assets/cym/%s.svg" % slug,
            "category": cat,
            "stroke": stroke,
        }
        print("  %-50s (n=%d, m=%d, rot=%+.1f)  %2d paths  %5.1f KB"
              % (slug, n, m, rot, npaths, len(data) / 1024.0))

    with open(os.path.join(OUT_DIR, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print("\n%d SVGs, %.1f KB total -> %s" % (len(manifest), total / 1024.0, OUT_DIR))
    if failed:
        print("FAILED: %s" % failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
