#!/usr/bin/env python3
"""Render floor-plan JSON files in plans/ to builder drawing sheets (SVG) in out/.

Coordinates are in feet. Origin (0, 0) is the front-left corner of the plot,
x grows to the right, y grows toward the rear. See README.md for the format.

Usage:  python3 render.py
"""
import json
import textwrap
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
PLANS = ROOT / "plans"
OUT = ROOT / "out"
FLOOR_ORDER = ["ground_floor", "first_floor"]

PX = 14          # pixels per foot
MX = 130         # left/right margin (px), holds the dimension chains
MT = 90          # top margin (px)

INK = "#1f2a36"
DIM = "#8a6d3b"
DOOR = "#8a5a2b"
GLASS = "#2a7fd4"
MUTED = "#555"


def ftin(v):
    inches = round(abs(v) * 24) / 2
    ft, inch = divmod(inches, 12)
    whole = int(inch)
    frac = "½" if inch - whole else ""
    return f'{whole}{frac}"' if ft == 0 else f"{int(ft)}'-{whole}{frac}\""


def shape(r):
    if "points" in r:
        return r["points"]
    x, y, w, h = r["x"], r["y"], r["w"], r["h"]
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


def bbox(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def area(pts):
    return abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))) / 2


def render(plan: dict) -> str:
    W, D = plan["plot"]["width"], plan["plot"]["depth"]
    wall_t = plan.get("wall_thickness", 0.75)
    sheet_w = W * PX + 2 * MX

    def X(x):
        return MX + x * PX

    def Y(y):
        return MT + (D - y) * PX

    def line(x1, y1, x2, y2, col=INK, sw=1, extra=""):
        return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="{sw}" {extra}/>'

    def text(x, y, t, size=9, col=INK, anchor="middle", weight="normal", rot=None):
        tr = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot is not None else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{col}" text-anchor="{anchor}" '
                f'font-weight="{weight}"{tr}>{escape(str(t))}</text>')

    def poly(pts, fill, stroke="none", sw=0, extra=""):
        p = " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in pts)
        return f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'

    def rect(x, y, w, h, fill="none", stroke=INK, sw=0.8, extra=""):
        return (f'<rect x="{X(x):.1f}" y="{Y(y + h):.1f}" width="{w * PX:.1f}" height="{h * PX:.1f}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')

    s = [
        '<defs>'
        '<pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<rect width="5" height="5" fill="#d3cabd"/><line x1="0" y1="0" x2="0" y2="5" stroke="#a39787" stroke-width="1"/></pattern>'
        f'<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M0,0 L10,5 L0,10 Z" fill="{INK}"/></marker>'
        f'<marker id="end" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
        f'<path d="M0,5 L10,5 M5,0 L5,10" stroke="{INK}" stroke-width="1.5"/></marker>'
        '</defs>'
    ]

    # --- grid (1 ft minor, 5 ft medium, 10 ft major) ------------------------
    for i in range(0, max(W, D) + 1):
        col, sw = ("#c9d1db", 0.8) if i % 10 == 0 else ("#e1e6ec", 0.6) if i % 5 == 0 else ("#f1f3f6", 0.5)
        if i <= W:
            s.append(line(X(i), Y(0), X(i), Y(D), col, sw))
        if i <= D:
            s.append(line(X(0), Y(i), X(W), Y(i), col, sw))
    for i in [*(i for i in range(0, W, 5) if W - i >= 3), W]:
        s.append(text(X(i), Y(0) + 14, f"{i}'", 9, "#8a95a3"))
    for i in [*(i for i in range(0, D, 5) if D - i >= 3), D]:
        s.append(text(X(0) - 6, Y(i) + 3, f"{i}'", 9, "#8a95a3", "end"))

    # --- building envelope: filled with wall hatch, rooms are cut out of it ---
    outline = plan.get("building", {}).get("outline")
    if outline:
        s.append(poly(outline, "url(#hatch)", INK, 1.6))

    covered = plan.get("building", {}).get("covered", [])
    rooms = plan.get("rooms", [])
    for r in rooms:
        s.append(poly(shape(r), r.get("color", "#f4efe6"), "#333", r.get("stroke_width", 0.8)))
    # open covered areas: dashed line = edge of the slab above
    for c in covered:
        s.append(poly(shape(c), "none", INK, 1, 'stroke-dasharray="7 4"'))
    # zone markings inside a room (e.g. where the kitchen passage begins), drawn as thin dashed lines
    for r in rooms:
        for part in r.get("parts", []):
            for (ax, ay), (bx, by) in part.get("boundary", []):
                s.append(line(X(ax), Y(ay), X(bx), Y(by), "#777", 0.8, 'stroke-dasharray="3 3"'))
    for col in plan.get("columns", []):
        s.append(rect(col["x"], col["y"], col["w"], col["h"], "#3a3a3a", INK, 0.8))

    # --- fixtures -------------------------------------------------------------
    for f in plan.get("fixtures", []):
        kind = f["type"]
        if kind == "trap":
            cx, cy, rr = X(f["x"]), Y(f["y"]), 0.3 * PX
            s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr:.1f}" fill="#fff" stroke="{INK}" stroke-width="0.7"/>')
            s.append(line(cx - rr, cy, cx + rr, cy, INK, 0.5))
            s.append(line(cx, cy - rr, cx, cy + rr, INK, 0.5))
            if f.get("label", True):
                s.append(text(cx + rr + 2, cy + 3, "FT", 6, MUTED, "start"))
            continue
        if "points" in f:
            s.append(poly(f["points"], "#ebe3cf", INK, 0.7))
            if f.get("label"):
                s.append(text(X(f["label_x"]), Y(f["label_y"]) + 2.5, f["label"], 6, MUTED))
            continue
        x, y, w, h = f["x"], f["y"], f["w"], f["h"]
        if kind == "counter":
            s.append(rect(x, y, w, h, "#ebe3cf", INK, 0.7))
        elif kind == "shelf":
            s.append(rect(x, y, w, h, "none", INK, 0.7, 'stroke-dasharray="4 3"'))
        elif kind == "sink":
            s.append(rect(x, y, w, h, "#fff", INK, 0.7))
            s.append(rect(x + 0.15, y + 0.15, w - 0.3, h - 0.3, "#eef4f8", INK, 0.5, 'rx="3"'))
        elif kind == "basin":
            s.append(f'<ellipse cx="{X(x + w / 2):.1f}" cy="{Y(y + h / 2):.1f}" rx="{w * PX / 2:.1f}" ry="{h * PX / 2:.1f}" '
                     f'fill="#fff" stroke="{INK}" stroke-width="0.7"/>')
        elif kind == "wc":
            # western WC: cistern against the wall behind, bowl toward `facing`
            tank, facing = 0.5, f.get("facing", "-y")
            if facing in ("-y", "+y"):
                ty0 = y + h - tank if facing == "-y" else y
                bx, by, bw, bh = x, (y if facing == "-y" else y + tank), w, h - tank
                s.append(rect(x, ty0, w, tank, "#fff", INK, 0.7))
            else:
                tx0 = x + w - tank if facing == "-x" else x
                bx, by, bw, bh = (x if facing == "-x" else x + tank), y, w - tank, h
                s.append(rect(tx0, y, tank, h, "#fff", INK, 0.7))
            s.append(f'<ellipse cx="{X(bx + bw / 2):.1f}" cy="{Y(by + bh / 2):.1f}" rx="{bw * PX * 0.46:.1f}" '
                     f'ry="{bh * PX * 0.42:.1f}" fill="#fff" stroke="{INK}" stroke-width="0.7"/>')
            s.append(text(X(bx + bw / 2), Y(by + bh / 2) + 2, "EWC", 5, MUTED))
        elif kind == "indian_wc":
            # squatting pan on a raised platform; footrests toward the user's side (`facing`)
            s.append(rect(x, y, w, h, "#fff", INK, 0.7))
            s.append(rect(x + w * 0.22, y + h * 0.12, w * 0.56, h * 0.76, "#eef4f8", INK, 0.6, f'rx="{w * PX * 0.28:.1f}"'))
            fy = y + h * 0.18 if f.get("facing", "-y") == "-y" else y + h * 0.62
            s.append(rect(x + w * 0.04, fy, w * 0.14, h * 0.2, "#ddd", INK, 0.5))
            s.append(rect(x + w * 0.82, fy, w * 0.14, h * 0.2, "#ddd", INK, 0.5))
            s.append(text(X(x + w / 2), Y(y + h / 2) + 2, "IWC", 5, MUTED))
        if f.get("label"):
            rot = -90 if h > w else None
            ly = f.get("label_y", y + h / 2)
            s.append(text(X(x + w / 2) + (2 if rot else 0), Y(ly) + (0 if rot else 2.5), f["label"], 6, MUTED, rot=rot))

    # --- stairs ---------------------------------------------------------------
    for st in plan.get("stairs", []):
        for fl in st.get("flights", []):
            x, y, w, h, n = fl["x"], fl["y"], fl["w"], fl["h"], fl["treads"]
            s.append(rect(x, y, w, h, "#faf7f0", INK, 0.8))
            for k in range(1, n):
                if fl["dir"] in ("+x", "-x"):
                    s.append(line(X(x + k * w / n), Y(y), X(x + k * w / n), Y(y + h), INK, 0.6))
                else:
                    s.append(line(X(x), Y(y + k * h / n), X(x + w), Y(y + k * h / n), INK, 0.6))
        for ld in st.get("landings", []):
            s.append(rect(ld["x"], ld["y"], ld["w"], ld["h"], "#faf7f0", INK, 0.8))
        if st.get("arrow"):
            p = " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in st["arrow"])
            s.append(f'<polyline points="{p}" fill="none" stroke="{INK}" stroke-width="0.9" marker-end="url(#arr)"/>')
        if st.get("label"):
            lx, ly = st["label_at"]
            s.append(text(X(lx), Y(ly), st["label"], 8, INK, "end", "700"))

    # --- openings: door / window / ventilator / opening -----------------------
    for op in plan.get("openings", []):
        t = op.get("thickness", wall_t)
        L = op["length"]
        horiz = op.get("orientation", "h") == "h"
        u0, v0 = (op["x"], op["y"]) if horiz else (op["y"], op["x"])

        def pt(u, v):
            return (X(u), Y(v)) if horiz else (X(v), Y(u))

        def seg(u1, v1, u2, v2, col=INK, sw=1, extra=""):
            a, b = pt(u1, v1), pt(u2, v2)
            return line(a[0], a[1], b[0], b[1], col, sw, extra)

        # knock the wall out (slightly wider than the wall so room edge lines vanish)
        a, b = pt(u0, v0 - t / 2 - 0.06), pt(u0 + L, v0 + t / 2 + 0.06)
        s.append(f'<rect x="{min(a[0], b[0]):.1f}" y="{min(a[1], b[1]):.1f}" width="{abs(b[0] - a[0]):.1f}" '
                 f'height="{abs(b[1] - a[1]):.1f}" fill="#fff"/>')
        s.append(seg(u0, v0 - t / 2, u0, v0 + t / 2))
        s.append(seg(u0 + L, v0 - t / 2, u0 + L, v0 + t / 2))

        kind = op["type"]
        if kind == "door":
            sg = op.get("swing", 1)
            face = v0 + sg * t / 2
            hu, ou = (u0, u0 + L) if op.get("hinge", "start") == "start" else (u0 + L, u0)
            h_pt, leaf, jamb = pt(hu, face), pt(hu, face + sg * L), pt(ou, face)
            s.append(line(h_pt[0], h_pt[1], leaf[0], leaf[1], DOOR, 1.6))
            cross = (leaf[0] - h_pt[0]) * (jamb[1] - h_pt[1]) - (leaf[1] - h_pt[1]) * (jamb[0] - h_pt[0])
            r_px = L * PX
            s.append(f'<path d="M{leaf[0]:.1f},{leaf[1]:.1f} A{r_px:.1f},{r_px:.1f} 0 0,{1 if cross > 0 else 0} '
                     f'{jamb[0]:.1f},{jamb[1]:.1f}" fill="none" stroke="{DOOR}" stroke-width="0.7"/>')
            tag_side, tag_col = op.get("tag_side", -sg), DOOR
        elif kind in ("window", "ventilator"):
            s.append(seg(u0, v0 - t / 2, u0 + L, v0 - t / 2, INK, 0.7))
            s.append(seg(u0, v0 + t / 2, u0 + L, v0 + t / 2, INK, 0.7))
            if kind == "window":
                s.append(seg(u0, v0 - t / 6, u0 + L, v0 - t / 6, GLASS, 1))
                s.append(seg(u0, v0 + t / 6, u0 + L, v0 + t / 6, GLASS, 1))
            else:
                s.append(seg(u0, v0, u0 + L, v0, GLASS, 1))
            tag_side, tag_col = op.get("tag_side", 1), GLASS
        else:
            tag_side, tag_col = op.get("tag_side", -1), INK
        if op.get("code"):
            tx, ty = pt(u0 + L / 2, v0 + tag_side * (t / 2 + 0.75))
            s.append(text(tx, ty + 3, op["code"], 7.5, tag_col, weight="700"))

    # --- room labels (drawn last so they sit on top) --------------------------
    for r in rooms:
        pts = shape(r)
        x0, y0, x1, y1 = bbox(pts)
        w, h = x1 - x0, y1 - y0
        m = min(w, h)
        f1, f2 = (13, 9.5) if m >= 9 else (11, 8.5) if m >= 6 else (9, 7) if m >= 4.5 else (7.5, 6)
        f1, f2 = r.get("label_font", [f1, f2])
        cx, cy = X(r.get("label_x", (x0 + x1) / 2)), Y(r.get("label_y", (y0 + y1) / 2))
        size = r.get("dims_text") or f"{ftin(w)} × {ftin(h)}"
        cid = f"clip-{abs(hash(r['name'])) % 10**8}"
        s.append(f'<clipPath id="{cid}"><rect x="{X(x0):.1f}" y="{Y(y1):.1f}" width="{w * PX:.1f}" height="{h * PX:.1f}"/></clipPath>')
        s.append(f'<g clip-path="url(#{cid})">')
        s.append(text(cx, cy - 2, r["name"].upper(), f1, "#222", weight="700"))
        area_txt = r.get("area_text") or f"{area(pts):,.0f} sq ft"
        if r.get("show_dims", True):
            s.append(text(cx, cy + f2 + 1, size, f2, MUTED))
            s.append(text(cx, cy + 2 * f2 + 3, area_txt, f2 - 1, "#777"))
        else:
            s.append(text(cx, cy + f2 + 1, area_txt, f2 - 1, "#777"))
        s.append("</g>")

    # --- dimension chains -----------------------------------------------------
    def chain(d):
        axis, pos, at = d["axis"], d["pos"], d["at"]
        frm = d.get("from")
        frm = frm if isinstance(frm, list) else [frm] * len(pos)
        col = d.get("color", DIM)
        out = []
        if axis == "x":
            y = Y(at)
            out.append(line(X(pos[0]), y, X(pos[-1]), y, col, 0.7))
            for p, f in zip(pos, frm):
                x = X(p)
                if f is not None:
                    sg = 1 if y > Y(f) else -1
                    out.append(line(x, Y(f) + 2 * sg, x, y + 4 * sg, col, 0.4))
                out.append(line(x - 3, y + 3, x + 3, y - 3, col, 1.1))
            for a, b in zip(pos, pos[1:]):
                seg_px = (b - a) * PX
                out.append(text((X(a) + X(b)) / 2, y - 3, ftin(b - a), 7.5 if seg_px >= 26 else 6.5, col))
        else:
            x = X(at)
            out.append(line(x, Y(pos[0]), x, Y(pos[-1]), col, 0.7))
            for p, f in zip(pos, frm):
                y = Y(p)
                if f is not None:
                    sg = 1 if x > X(f) else -1
                    out.append(line(X(f) + 2 * sg, y, x + 4 * sg, y, col, 0.4))
                out.append(line(x - 3, y + 3, x + 3, y - 3, col, 1.1))
            for a, b in zip(pos, pos[1:]):
                seg_px = (b - a) * PX
                ym = (Y(a) + Y(b)) / 2
                out.append(text(x - 3, ym, ftin(b - a), 7.5 if seg_px >= 26 else 6.5, col, rot=-90))
        return out

    gaps = None
    if outline:
        bx0, by0, bx1, by1 = bbox(outline + [p for c in covered for p in shape(c)])
        gaps = (bx0, W - bx1, by0, D - by1)
        # plot-level chains, auto-calculated from the envelope so gaps stay current
        s += chain({"axis": "x", "at": by0 - 2.2, "pos": [0, bx0, bx1, W], "from": [None, by0, by0, None]})
        s += chain({"axis": "y", "at": W + 4, "pos": [0, by0, by1, D], "from": [None, bx1, bx1, None]})
    for d in plan.get("dimensions", []):
        s += chain(d)

    # --- plot boundary + overall plot size -------------------------------------
    s.append(f'<rect x="{X(0)}" y="{Y(D)}" width="{W * PX}" height="{D * PX}" fill="none" stroke="{INK}" stroke-width="2.5"/>')
    s.append(line(X(0), Y(D) - 40, X(W), Y(D) - 40, INK, 1, 'marker-start="url(#end)" marker-end="url(#end)"'))
    s.append(text(X(W / 2), Y(D) - 46, f"PLOT {ftin(W)}", 12))
    px = X(W) + 6.8 * PX
    s.append(line(px, Y(D), px, Y(0), INK, 1, 'marker-start="url(#end)" marker-end="url(#end)"'))
    s.append(text(px + 14, Y(D / 2), f"PLOT {ftin(D)}", 12, rot=90))
    # compass: front_side is the direction the road side (bottom of the sheet) faces
    compass = ["NORTH", "EAST", "SOUTH", "WEST"]
    front = plan.get("front_side", "south").upper()
    up = compass[(compass.index(front) + 2) % 4]
    right_dir = compass[(compass.index(up) + 1) % 4]
    left_dir = compass[(compass.index(up) + 3) % 4]
    side_col = "#6b7785"
    s.append(text(X(W / 2), Y(0) + 32, f"FRONT (ROAD) · {front}", 12, side_col, weight="600"))
    s.append(text(X(W / 2), Y(D) - 12, f"REAR · {up}", 10, side_col, weight="600"))
    s.append(text(X(-3.2), Y(D - 6), f"{left_dir} SIDE", 10, side_col, weight="600", rot=-90))
    s.append(text(X(W + 2.8), Y(D - 6), f"{right_dir} SIDE", 10, side_col, weight="600", rot=90))
    nx, ny = 40, 50
    rot = (-compass.index(up) * 90) % 360
    s.append(f'<g transform="rotate({rot} {nx} {ny})">'
             f'<path d="M{nx},{ny - 18} L{nx + 8},{ny + 8} L{nx},{ny + 3} L{nx - 8},{ny + 8} Z" fill="{INK}"/>'
             f'{text(nx, ny - 22, "N", 11, weight="700", rot=-rot)}</g>')

    # --- title block, area statement, schedules, notes ------------------------
    left, right = 24, sheet_w - 24
    ty = Y(0) + 62
    s.append(line(left, ty, right, ty, INK, 1.5))
    s.append(text(left, ty + 26, plan["name"].upper() + " PLAN", 20, INK, "start", "700"))
    if plan.get("subtitle"):
        s.append(text(left, ty + 44, plan["subtitle"], 9.5, MUTED, "start"))
    ty += 62

    def heading(t):
        nonlocal ty
        s.append(text(left, ty, t, 11, INK, "start", "700"))
        s.append(line(left, ty + 4, right, ty + 4, "#c9d1db", 0.8))
        ty += 18

    def table(cols, rows, bold_last=False):
        nonlocal ty
        xs = [left + c[1] for c in cols]
        for x, c in zip(xs, cols):
            s.append(text(x, ty, c[0], 8.5, MUTED, "start", "700"))
        ty += 5
        s.append(line(left, ty, right, ty, "#c9d1db", 0.6))
        ty += 12
        for i, row in enumerate(rows):
            wgt = "700" if bold_last and i == len(rows) - 1 else "normal"
            col = MUTED if not row[0] else INK
            for x, cell in zip(xs, row):
                s.append(text(x, ty, cell, 8.5, col, "start", wgt))
            ty += 13
        ty += 8

    carpet = sum(area(shape(r)) for r in rooms if not r.get("open"))
    built = area(outline) if outline else 0
    open_area = sum(area(shape(c)) for c in covered)
    heading("AREA STATEMENT")
    stats = [f"Plot  {ftin(W)} × {ftin(D)} = {W * D:,.0f} sq ft"]
    if outline:
        stats.append(f"Built-up, enclosed (outside of walls) = {built:,.1f} sq ft")
    if covered:
        stats.append(f"Open covered area under slab ({', '.join(c.get('name', '') for c in covered)}) = {open_area:,.1f} sq ft"
                     f"   ·   Total covered = {built + open_area:,.1f} sq ft")
    if rooms:
        stats.append(f"Carpet (clear areas of enclosed rooms) = {carpet:,.1f} sq ft")
    if outline and rooms:
        stats.append(f"Walls = {built - carpet:,.1f} sq ft   ·   Ground coverage = {(built + open_area) / (W * D) * 100:.1f}% of plot")
    if gaps:
        stats.append(f"Open gaps (min): Left {ftin(gaps[0])} · Right {ftin(gaps[1])} · Front {ftin(gaps[2])} · Rear {ftin(gaps[3])}")
    for line_txt in stats:
        s.append(text(left, ty, line_txt, 9.5, INK, "start"))
        ty += 14
    ty += 10

    if rooms:
        heading("ROOM SCHEDULE (clear inside sizes)")
        rows = []
        for r in rooms:
            x0, y0, x1, y1 = bbox(shape(r))
            rows.append([r["name"] + (" (open, not in carpet)" if r.get("open") else ""),
                         r.get("dims_text") or f"{ftin(x1 - x0)} × {ftin(y1 - y0)}", f"{area(shape(r)):,.1f} sq ft"])
            for part in r.get("parts", []):
                pa = part["w"] * part["h"]
                rows.append([f"   – {part['name']}", f"{ftin(part['w'])} × {ftin(part['h'])}", f"{pa:,.2f} sq ft (included above)"])
        rows.append(["Total carpet (enclosed rooms)", "", f"{carpet:,.1f} sq ft"])
        table([("ROOM", 0), ("SIZE (W × D)", 150), ("AREA", 380)], rows, bold_last=True)

    sched = plan.get("schedule", [])
    if sched:
        heading("DOOR & WINDOW SCHEDULE")
        ops = plan.get("openings", [])
        rows = []
        for e in sched:
            used = [o for o in ops if o.get("code") == e["code"]]
            sill = ftin(e["sill"]) if e.get("sill") is not None else "-"
            rows.append([e["code"], f"{ftin(e['width'])} × {ftin(e['height'])}", sill, str(len(used)),
                         ", ".join(o.get("note", "") for o in used)])
            rows.append(["", e.get("spec", ""), "", "", ""])
        table([("CODE", 0), ("SIZE (W × H)", 42), ("SILL", 170), ("NOS", 215), ("LOCATION", 250)], rows)

    notes = plan.get("notes", [])
    if notes:
        heading("NOTES")
        for i, n in enumerate(notes, 1):
            for j, part in enumerate(textwrap.wrap(n, 100)):
                s.append(text(left + (0 if j == 0 else 16), ty, (f"{i}. " if j == 0 else "") + part, 8.8, INK, "start"))
                ty += 12.5
            ty += 2
        ty += 6

    heading("LEGEND")
    s.append(f'<rect x="{left}" y="{ty - 9}" width="22" height="10" fill="url(#hatch)" stroke="{INK}" stroke-width="0.8"/>')
    s.append(text(left + 28, ty, f'Wall {ftin(wall_t)} brick', 8.5, INK, "start"))
    s.append(text(left + 120, ty, "D = door  W = window  V = ventilator  O = open entry  FT = floor trap  IWC/EWC = Indian/western WC", 8.5, INK, "start"))
    ty += 18
    s.append(f'<rect x="{left + 6}" y="{ty - 9}" width="10" height="10" fill="#3a3a3a" stroke="{INK}" stroke-width="0.8"/>')
    s.append(text(left + 28, ty, 'RCC pillar', 8.5, INK, "start"))
    s.append(line(left + 120, ty - 4, left + 150, ty - 4, INK, 1, 'stroke-dasharray="7 4"'))
    s.append(text(left + 158, ty, "Edge of RCC slab above (open covered area)", 8.5, INK, "start"))
    ty += 24

    sheet_h = ty + 10
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{sheet_w}" height="{sheet_h:.0f}" '
            f'viewBox="0 0 {sheet_w} {sheet_h:.0f}" font-family="Helvetica, Arial, sans-serif">'
            f'<rect width="{sheet_w}" height="{sheet_h:.0f}" fill="#ffffff"/>')
    return "\n".join([head, *s, "</svg>"])


def main():
    OUT.mkdir(exist_ok=True)
    files = sorted(PLANS.glob("*.json"), key=lambda p: (FLOOR_ORDER.index(p.stem) if p.stem in FLOOR_ORDER else 99, p.stem))
    cards = []
    for path in files:
        plan = json.loads(path.read_text())
        svg = render(plan)
        (OUT / f"{path.stem}.svg").write_text(svg)
        if plan.get("visible", True):
            cards.append(svg)
        print(f"rendered {path.name} -> out/{path.stem}.svg" + ("" if plan.get("visible", True) else " (hidden in viewer)"))

    html = (
        "<!doctype html><meta charset='utf-8'><title>House Floor Plans</title>"
        "<style>html,body{margin:0;background:#fff}"
        "main{display:flex;flex-direction:column;align-items:center;gap:24px;padding:12px 0}"
        "svg{display:block;width:min(100vw,1000px);height:auto}</style>"
        f"<main>{''.join(cards)}</main>"
    )
    (OUT / "index.html").write_text(html)
    print("wrote out/index.html")


if __name__ == "__main__":
    main()
