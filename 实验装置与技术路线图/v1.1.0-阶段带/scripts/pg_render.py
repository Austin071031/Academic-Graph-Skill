#!/usr/bin/env python3
"""pg_render.py — render an intermediate representation (IR) JSON into a layered,
editable SVG diagram plus meta.json for downstream checks.

Usage:
  python3 pg_render.py --ir /app/work/ir.json --out /app/output/diagram.svg \
      [--assets DIR] [--meta PATH] [--title TEXT]

Stdlib only. Deterministic: same IR -> same SVG (dict order preserved, stable sorts).
Diagram types: flowchart | tech_route | apparatus | chart
Every IR entity becomes <g id="{entity.id}"> so pg_check.py can verify traceability.
"""
import argparse, json, math, os, re, sys
import xml.sax.saxutils as xu

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ASSETS = os.path.normpath(os.path.join(HERE, "..", "assets"))

# ---------------------------------------------------------------- utilities
def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def text_w(s, fs):
    """Estimate rendered text width (px): CJK ~1.0*fs, latin ~0.55*fs."""
    w = 0.0
    for ch in str(s):
        w += fs * (1.0 if ord(ch) > 0x2E80 else 0.55)
    return w

def wrap_label(s, fs, max_w):
    """Greedy wrap for mixed CJK/latin labels; returns list of lines."""
    s = str(s)
    if text_w(s, fs) <= max_w:
        return [s]
    lines, cur, curw = [], "", 0.0
    for ch in s:
        cw = fs * (1.0 if ord(ch) > 0x2E80 else 0.55)
        if cur and curw + cw > max_w:
            lines.append(cur); cur, curw = "", 0.0
        cur += ch; curw += cw
    if cur:
        lines.append(cur)
    return lines

def esc(s):
    return xu.escape(str(s), {'"': "&quot;"})

# ---------------------------------------------------------------- IR access
class IR:
    def __init__(self, data):
        self.d = data
        self.entities = {e["id"]: e for e in data.get("entities", []) if e.get("id")}
        self.edges = [c for c in data.get("connections", []) if c.get("from") in self.entities
                      and c.get("to") in self.entities]
        self.steps = sorted([s for s in data.get("steps", []) if s.get("id")],
                            key=lambda s: (s.get("no", 1 << 30), s["id"]))
        self.dtype = data.get("diagram_type", "flowchart")

# ---------------------------------------------------------------- sugiyama
def sugiyama(ir, direction):
    """Layered layout. Returns {id: [x, y]} of node centers."""
    nd = TPL["node_defaults"]
    W, H, HG, VG = nd["width"], nd["height"], nd["h_gap"], nd["v_gap"]
    nodes = [eid for eid, e in ir.entities.items()
             if e.get("type") not in ("material", "product", "waste") or _has_edge(ir, eid)]
    if not nodes:
        nodes = list(ir.entities.keys())
    adj = {n: [] for n in nodes}
    radj = {n: [] for n in nodes}
    for c in ir.edges:
        f, t = c["from"], c["to"]
        if f in adj and t in adj:
            adj[f].append(t); radj[t].append(f)
    # longest-path layering on DAG; break cycles by dropping the last back edge
    layer = {n: 0 for n in nodes}
    order = sorted(nodes, key=lambda n: (len(radj[n]), n))
    changed = True
    guard = 0
    while changed and guard < 200:
        changed = False; guard += 1
        for n in order:
            if radj[n]:
                m = max(layer[p] for p in radj[n]) + 1
                if m > layer[n]:
                    layer[n] = m; changed = True
    if guard >= 200:  # cyclic: fall back to BFS depth
        layer = {n: 0 for n in nodes}
        seen = set()
        frontier = [n for n in nodes if not radj[n]] or nodes[:1]
        depth = 0
        while frontier:
            for n in frontier:
                if n not in seen:
                    layer[n] = depth; seen.add(n)
            frontier = [m for n in frontier for m in adj[n] if m not in seen]
            depth += 1
    layers = {}
    for n in nodes:
        layers.setdefault(layer[n], []).append(n)
    # barycenter ordering, 2 passes
    for _ in range(2):
        for L in sorted(layers):
            prev = layers.get(L - 1, []); nxt = layers.get(L + 1, [])
            pos = {n: i for i, n in enumerate(layers[L])}
            def bc(n):
                ps = [pos2 for pos2 in ([prev.index(p) for p in radj[n] if p in prev] +
                                        [nxt.index(q) for q in adj[n] if q in nxt])]
                return sum(ps) / len(ps) if ps else pos[n]
            layers[L].sort(key=lambda n: (bc(n), n))
    posx, posy = {}, {}
    for L in sorted(layers):
        members = layers[L]
        for i, n in enumerate(members):
            if direction == "tb":
                posx[n] = (i + 0.5) * (W + HG)
                posy[n] = L * (H + VG) + H / 2
            else:
                posx[n] = L * (W + HG) + W / 2
                posy[n] = (i + 0.5) * (H + VG)
    return {n: [posx[n], posy[n]] for n in nodes}

def _has_edge(ir, eid):
    return any(c["from"] == eid or c["to"] == eid for c in ir.edges)

# ---------------------------------------------------------------- chart mode
def chart_layout(ir):
    series = ir.d.get("chart", {}).get("series", [])
    W, H, m = 640, 420, 56
    return series, W, H, m

def render_chart(ir, pal, fonts):
    series, W, H, m = chart_layout(ir)
    parts = []
    out = [f'<rect x="0" y="0" width="{W}" height="{H}" fill="{pal["canvas_bg"]}"/>']
    colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#F0E442", "#56B4E9"]
    if not series:
        return None, []
    xs, ys = [], []
    for s in series:
        for pt in s.get("data", []):
            xs.append(float(pt[0])); ys.append(float(pt[1]))
    xmin, xmax = (min(xs), max(xs)) if xs else (0, 1)
    ymin, ymax = (min(ys), max(ys)) if ys else (0, 1)
    if xmax == xmin: xmax = xmin + 1
    if ymax == ymin: ymax = ymin + 1
    pad_y = (ymax - ymin) * 0.08; ymin -= pad_y; ymax += pad_y
    fx = lambda v: m + (v - xmin) / (xmax - xmin) * (W - 2 * m)
    fy = lambda v: H - m - (v - ymin) / (ymax - ymin) * (H - 2 * m)
    out.append(f'<g id="layer-axes" stroke="#333" stroke-width="1.2">')
    out.append(f'<line x1="{m}" y1="{H-m}" x2="{W-m}" y2="{H-m}"/>')
    out.append(f'<line x1="{m}" y1="{m}" x2="{m}" y2="{H-m}"/>')
    for i in range(6):
        tx = xmin + (xmax - xmin) * i / 5
        ty = ymin + (ymax - ymin) * i / 5
        out.append(f'<line x1="{fx(tx):.1f}" y1="{H-m}" x2="{fx(tx):.1f}" y2="{H-m+5}" stroke="#333"/>')
        out.append(f'<text x="{fx(tx):.1f}" y="{H-m+18}" font-size="9" text-anchor="middle" font-family="{esc(fonts["svg_font_family"])}">{tx:.3g}</text>')
        out.append(f'<line x1="{m-5}" y1="{fy(ty):.1f}" x2="{m}" y2="{fy(ty):.1f}" stroke="#333"/>')
        out.append(f'<text x="{m-8}" y="{fy(ty)+3:.1f}" font-size="9" text-anchor="end" font-family="{esc(fonts["svg_font_family"])}">{ty:.3g}</text>')
    out.append('</g>')
    ch = ir.d.get("chart", {})
    if ch.get("x_label"):
        out.append(f'<text x="{W/2}" y="{H-12}" font-size="12" text-anchor="middle" font-family="{esc(fonts["svg_font_family"])}">{esc(ch["x_label"])}</text>')
    if ch.get("y_label"):
        out.append(f'<text x="14" y="{H/2}" font-size="12" text-anchor="middle" transform="rotate(-90 14 {H/2})" font-family="{esc(fonts["svg_font_family"])}">{esc(ch["y_label"])}</text>')
    for si, s in enumerate(series):
        col = colors[si % len(colors)]
        sid = esc(s.get("id", f"series{si}"))
        pts = " ".join(f"{fx(float(p[0])):.1f},{fy(float(p[1])):.1f}" for p in s.get("data", []))
        gid = f'<g id="{sid}">'
        body = [gid]
        if s.get("kind", "line") == "bar":
            for p in s.get("data", []):
                bx, by = fx(float(p[0])), fy(float(p[1]))
                body.append(f'<rect x="{bx-8:.1f}" y="{by:.1f}" width="16" height="{H-m-by:.1f}" fill="{col}" fill-opacity="0.75"/>')
        else:
            body.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.2"/>')
        for p in s.get("data", []):
            body.append(f'<circle cx="{fx(float(p[0])):.1f}" cy="{fy(float(p[1])):.1f}" r="3.2" fill="{col}"/>')
        body.append('</g>')
        out.append("".join(body))
    # legend
    lx, ly = W - m + 8, m
    out.append('<g id="layer-legend">')
    for si, s in enumerate(series):
        col = colors[si % len(colors)]
        out.append(f'<rect x="{lx}" y="{ly + si*20 - 9}" width="12" height="4" fill="{col}"/>')
        out.append(f'<text x="{lx + 18}" y="{ly + si*20 - 4}" font-size="10" font-family="{esc(fonts["svg_font_family"])}">{esc(s.get("label", s.get("id", "")))}</text>')
    out.append('</g>')
    src = ir.d.get("source", {})
    if src.get("materials"):
        loc = "; ".join(f"{m2.get('path','?')} {m2.get('locator','')}".strip() for m2 in src["materials"][:3])
        out.append(f'<text x="{m}" y="{H-2}" font-size="8" fill="#666" font-family="{esc(fonts["svg_font_family"])}">source: {esc(loc)}</text>')
    return W, H, out

# ---------------------------------------------------------------- main render
def render(ir, assets, title=None):
    pal = load_json(os.path.join(assets, "palette.json"))
    fonts = load_json(os.path.join(assets, "fonts.json"))
    nd = TPL["node_defaults"]
    FF = fonts["svg_font_family"]
    fs_lab, fs_small = fonts["label_size_px"], fonts["small_size_px"]

    if ir.dtype == "chart":
        res = render_chart(ir, pal, fonts)
        if res[0] is None:
            print("ERROR: chart diagram_type but no chart.series in IR", file=sys.stderr); sys.exit(2)
        W, H, body = res
        meta = {"nodes": [], "edges": [], "extents": [0, 0, W, H], "legend_entries": [],
                "canvas": {"width": W, "height": H}}
        svg = assemble_svg(W, H, body, title or ir.d.get("title", ""), FF)
        return svg, meta

    direction = "tb" if ir.d.get("layout", {}).get("type") == "tb" else "lr"
    if ir.dtype == "apparatus":
        pos = apparatus_positions(ir, nd)
    else:
        pos = sugiyama(ir, direction)

    W, H, node_boxes = canvas_size(ir, pos, nd)
    ox, oy = nd["margin"], nd["margin"] + (28 if (title or ir.d.get("title")) else 0)
    pos = {k: [v[0] + ox, v[1] + oy] for k, v in pos.items()}  # single offset application

    body = [f'<rect x="0" y="0" width="{W}" height="{H}" fill="{pal["canvas_bg"]}"/>']
    t = title or ir.d.get("title")
    if t:
        body.append(f'<text x="{W/2}" y="{oy - 10}" font-size="{fonts["title_size_px"]}" text-anchor="middle" font-weight="bold" fill="{pal["text"]}" font-family="{esc(FF)}">{esc(t)}</text>')

    # ---- edges layer (below nodes)
    body.append('<g id="layer-edges">')
    edge_meta = []
    for c in ir.edges:
        f, tp = c["from"], c["to"]
        if f not in pos or tp not in pos:
            continue
        kind = c.get("kind", "material")
        kp = pal["flow_kinds"].get(kind, pal["flow_kinds"]["material"])
        dash = f' stroke-dasharray="{kp["dash"]}"' if kp.get("dash") else ""
        x1, y1 = pos[f]; x2, y2 = pos[tp]
        if direction == "tb":
            p1 = (x1, y1 + nd["height"]/2); p2 = (x2, y2 - nd["height"]/2)
            midy = (p1[1] + p2[1]) / 2
            path = f'M {p1[0]:.1f} {p1[1]:.1f} L {p1[0]:.1f} {midy:.1f} L {p2[0]:.1f} {midy:.1f} L {p2[0]:.1f} {p2[1]:.1f}'
        else:
            p1 = (x1 + nd["width"]/2, y1); p2 = (x2 - nd["width"]/2, y2)
            midx = (p1[0] + p2[0]) / 2
            path = f'M {p1[0]:.1f} {p1[1]:.1f} L {midx:.1f} {p1[1]:.1f} L {midx:.1f} {p2[1]:.1f} L {p2[0]:.1f} {p2[1]:.1f}'
        lbl = c.get("label", "")
        conf = c.get("confidence", "explicit")
        dash2 = dash + (' stroke-opacity="0.55"' if conf == "inferred" else "")
        mk = f'marker-end="url(#arr-{kind})"'
        eid_attr = esc(c.get("id", "edge"))
        # backward (回流/cycle) edges: arc above nodes to avoid overlapping forward edges
        if c.get("cycle") or (direction == "lr" and x2 < x1) or (direction == "tb" and y2 < y1):
            if direction == "lr":
                sx = x1; sy = y1 - nd["height"]/2
                tx2 = x2; ty2 = y2 - nd["height"]/2
                arc_y = min(sy, ty2) - 40
                path = f'M {sx:.1f} {sy:.1f} C {sx:.1f} {arc_y:.1f}, {tx2:.1f} {arc_y:.1f}, {tx2:.1f} {ty2:.1f}'
            else:
                sx = x1 - nd["width"]/2; sy = y1
                tx2 = x2 - nd["width"]/2; ty2 = y2
                arc_x = min(sx, tx2) - 40
                path = f'M {sx:.1f} {sy:.1f} C {arc_x:.1f} {sy:.1f}, {arc_x:.1f} {ty2:.1f}, {tx2:.1f} {ty2:.1f}'
            body.append(f'<path id="{eid_attr}" d="{path}" fill="none" stroke="{kp["stroke"]}" stroke-width="2"{dash2} {mk}/>')
            if lbl:
                lxy = ((sx + tx2) / 2, arc_y + (2 if direction == "lr" else -8))
        else:
            body.append(f'<path id="{eid_attr}" d="{path}" fill="none" stroke="{kp["stroke"]}" stroke-width="2"{dash2} {mk}/>')
            lxy = ((p1[0]+p2[0])/2, (p1[1]+p2[1])/2 - 5)
        if lbl:
            lw = text_w(lbl, fs_small) + 6
            body.append(f'<rect x="{lxy[0]-lw/2:.1f}" y="{lxy[1]-fs_small:.1f}" width="{lw:.1f}" height="{fs_small+4}" fill="{pal["canvas_bg"]}" fill-opacity="0.85"/>')
            body.append(f'<text x="{lxy[0]:.1f}" y="{lxy[1]:.1f}" font-size="{fs_small}" text-anchor="middle" fill="{pal["text"]}" font-family="{esc(FF)}">{esc(lbl)}</text>')
        edge_meta.append({"id": c.get("id", ""), "from": f, "to": tp, "kind": kind,
                          "confidence": conf, "label": lbl})
    body.append('</g>')

    # ---- entity layer
    body.append('<g id="layer-entities">')
    node_meta = []
    glyphs_dir = os.path.join(assets, "glyphs")
    for eid, e in ir.entities.items():
        if eid not in pos:
            continue
        x, y = pos[eid]
        etype = e.get("type", "default")
        np_ = pal["node_fills"].get(etype, pal["node_fills"]["default"])
        w, h = nd["width"], nd["height"]
        if etype in ("material", "product", "waste"):
            w, h = nd["width"] * 0.72, nd["height"] * 0.6
        g = [f'<g id="{esc(eid)}">']
        glyph_name = e.get("glyph")
        if glyph_name and os.path.isfile(os.path.join(glyphs_dir, glyph_name + ".svg")):
            with open(os.path.join(glyphs_dir, glyph_name + ".svg"), encoding="utf-8") as gf:
                gl = gf.read()
            gl = re.sub(r'<g id="glyph-[^"]*">', "", gl, count=1).rsplit("</g>", 1)[0]
            s = min(w, h) / 100.0
            g.append(f'<g transform="translate({x - w/2:.1f},{y - h/2:.1f}) scale({s:.3f})" '
                     f'fill="{np_["fill"]}" stroke="{np_["stroke"]}">{gl}</g>')
            g.append(f'<rect x="{x - w/2:.1f}" y="{y - h/2:.1f}" width="{w:.1f}" height="{h:.1f}" '
                     f'fill="none" stroke="none"><title>{esc(e.get("label", eid))}</title></rect>')
        else:
            g.append(f'<rect x="{x - w/2:.1f}" y="{y - h/2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="8" '
                     f'fill="{np_["fill"]}" stroke="{np_["stroke"]}" stroke-width="1.8"><title>{esc(e.get("label", eid))}</title></rect>')
        # step number badge
        step_no = next((s.get("no") for s in ir.steps if s.get("actor") == eid or s.get("id") == eid), None)
        label = e.get("label", eid)
        lines = wrap_label(label, fs_lab, w - 12)
        if step_no is not None:
            g.append(f'<circle cx="{x - w/2 + 12:.1f}" cy="{y - h/2 + 12:.1f}" r="9" fill="#333"/>')
            g.append(f'<text x="{x - w/2 + 12:.1f}" y="{y - h/2 + 16:.1f}" font-size="10" text-anchor="middle" fill="#fff" font-family="{esc(FF)}">{esc(step_no)}</text>')
        ty0 = y - (len(lines) - 1) * fs_lab * 0.62
        for i, ln in enumerate(lines):
            g.append(f'<text x="{x:.1f}" y="{ty0 + i * fs_lab * 1.24:.1f}" font-size="{fs_lab}" text-anchor="middle" dominant-baseline="middle" fill="{pal["text"]}" font-family="{esc(FF)}">{esc(ln)}</text>')
        # annotation values, e.g. measured numbers from the source
        vals = e.get("values") or []
        for vi, v in enumerate(vals[:2]):
            g.append(f'<text x="{x:.1f}" y="{y + h/2 + 12 + vi*11:.1f}" font-size="{fs_small}" text-anchor="middle" fill="#555" font-family="{esc(FF)}">{esc(v)}</text>')
        src = e.get("source", {})
        if src.get("locator"):
            g.append(f'<text x="{x:.1f}" y="{y + h/2 + 12 + min(len(vals),2)*11:.1f}" font-size="{fs_small-1}" text-anchor="middle" fill="#999" font-family="{esc(FF)}">[{esc(src["locator"])}]</text>')
        g.append('</g>')
        node_meta.append({"id": eid, "x": x, "y": y, "w": w, "h": h, "label": label, "type": etype})
        body.append("".join(g))
    body.append('</g>')

    # ---- stage banding for tech_route: one box around that stage's actors
    stages = [s for s in ir.steps if s.get("stage")]
    if stages and ir.dtype == "tech_route":
        body.append('<g id="layer-stages">')
        bands = {}
        for s in stages:
            if s.get("actor"):
                bands.setdefault(s["stage"], []).append(s.get("actor"))
        by_id = {nm["id"]: nm for nm in node_meta}
        pad, label_h = 16, 16
        for name, actors in bands.items():
            boxes = [by_id[a] for a in actors if a in by_id]
            if not boxes:
                continue
            x1 = min(b["x"] - b["w"] / 2 for b in boxes) - pad
            y1 = min(b["y"] - b["h"] / 2 for b in boxes) - pad - label_h
            x2 = max(b["x"] + b["w"] / 2 for b in boxes) + pad
            y2 = max(b["y"] + b["h"] / 2 for b in boxes) + pad
            body.append(
                f'<rect data-stage="{esc(name)}" x="{x1:.1f}" y="{y1:.1f}" width="{x2-x1:.1f}" height="{y2-y1:.1f}" '
                f'fill="none" stroke="#009E73" stroke-width="1" stroke-dasharray="6 4" rx="10"/>'
            )
            body.append(
                f'<text x="{x1+8:.1f}" y="{y1+12:.1f}" font-size="10" fill="#009E73" font-family="{esc(FF)}">{esc(name)}</text>'
            )
        body.append('</g>')

    # ---- legend layer (auto from actually-used kinds and types)
    used_kinds = sorted({em["kind"] for em in edge_meta})
    used_types = sorted({nm["type"] for nm in node_meta})
    legend_entries = [("kind", k) for k in used_kinds] + [("type", t2) for t2 in used_types]
    lx, ly = ox, H - 14 - 18 * max(len(legend_entries), 1) - 4
    body.append('<g id="layer-legend">')
    body.append(f'<rect x="{lx-8}" y="{ly-16}" width="{min(W*0.8, 60 + 120*max(len(legend_entries),1)):.0f}" height="{18*len(legend_entries)+26:.0f}" rx="6" fill="{pal["canvas_bg"]}" stroke="#bbb" stroke-width="0.8"/>')
    body.append(f'<text x="{lx}" y="{ly-2}" font-size="{fs_small+1}" font-weight="bold" fill="{pal["text"]}" font-family="{esc(FF)}">图例 Legend</text>')
    for i, (what, key) in enumerate(legend_entries):
        yy = ly + 16 + i * 18
        if what == "kind":
            kp = pal["flow_kinds"].get(key, pal["flow_kinds"]["material"])
            dash = f' stroke-dasharray="{kp["dash"]}"' if kp.get("dash") else ""
            body.append(f'<line x1="{lx}" y1="{yy}" x2="{lx+34}" y2="{yy}" stroke="{kp["stroke"]}" stroke-width="2.4"{dash}/>')
            body.append(f'<text x="{lx+42}" y="{yy+4}" font-size="{fs_small}" fill="{pal["text"]}" font-family="{esc(FF)}">{esc(kp["label_zh"])}</text>')
        else:
            np_ = pal["node_fills"].get(key, pal["node_fills"]["default"])
            body.append(f'<rect x="{lx}" y="{yy-8}" width="34" height="13" rx="3" fill="{np_["fill"]}" stroke="{np_["stroke"]}" stroke-width="1.2"/>')
            body.append(f'<text x="{lx+42}" y="{yy+4}" font-size="{fs_small}" fill="{pal["text"]}" font-family="{esc(FF)}">{esc(key)}</text>')
    body.append('</g>')

    # ---- title block / provenance
    srcs = ir.d.get("source", {}).get("materials", [])
    if srcs:
        prov = "; ".join(f"{s.get('path','?')}({s.get('version','?')}) {s.get('locator','')}".strip() for s in srcs[:4])
        body.append(f'<text x="{W - ox}" y="{H - 8}" font-size="{fs_small-1}" text-anchor="end" fill="#888" font-family="{esc(FF)}">来源: {esc(prov[:160])}</text>')

    meta = {"nodes": node_meta, "edges": edge_meta, "legend_entries": legend_entries,
            "extents": [0, 0, W, H], "canvas": {"width": W, "height": H},
            "direction": direction, "diagram_type": ir.dtype}
    svg = assemble_svg(W, H, body, t or "", FF, pal, used_kinds)
    return svg, meta

def apparatus_positions(ir, nd):
    """grid layout: explicit entity.x/entity.y (grid col,row) else row-major."""
    pos = {}
    auto = [eid for eid, e in ir.entities.items() if "x" not in e]
    cols = max(2, math.ceil(math.sqrt(len(ir.entities))))
    for i, eid in enumerate(auto):
        e = ir.entities[eid]
        col = e.get("x", i % cols); row = e.get("y", i // cols)
        pos[eid] = (col * (nd["width"] + nd["h_gap"]) + nd["width"] / 2,
                    row * (nd["height"] + nd["v_gap"]) + nd["height"] / 2)
    for eid, e in ir.entities.items():
        if eid not in pos and "x" in e:
            pos[eid] = (e["x"] * (nd["width"] + nd["h_gap"]) + nd["width"] / 2,
                        e.get("y", 0) * (nd["height"] + nd["v_gap"]) + nd["height"] / 2)
    return pos

def canvas_size(ir, pos, nd):
    if not pos:
        return nd["width"] + 2 * nd["margin"], nd["height"] + 2 * nd["margin"] + 30, {}
    xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
    W = max(xs) + nd["width"] + nd["margin"] * 2
    H = max(ys) + nd["height"] + nd["margin"] * 2 + 30
    return W, H, {}

def assemble_svg(W, H, body, title, FF, pal=None, used_kinds=None):
    defs = ['<defs>']
    if pal and used_kinds:
        for k in used_kinds:
            kp = pal["flow_kinds"].get(k, pal["flow_kinds"]["material"])
            defs.append(f'<marker id="arr-{k}" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M 0 0 L 10 4 L 0 8 Z" fill="{kp["stroke"]}"/></marker>')
    defs.append('</defs>')
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{esc(FF)}">')
    head += f'<title>{esc(title)}</title>'
    return head + "".join(defs) + "".join(body) + "</svg>"

TPL = None
def main():
    global TPL
    ap = argparse.ArgumentParser()
    ap.add_argument("--ir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--assets", default=DEFAULT_ASSETS)
    ap.add_argument("--meta", default=None)
    ap.add_argument("--title", default=None)
    a = ap.parse_args()
    TPL = load_json(os.path.join(a.assets, "templates.json"), {})
    TPL.setdefault("node_defaults", {"width": 120, "height": 52, "h_gap": 70, "v_gap": 34, "margin": 24})
    ir_data = load_json(a.ir)
    if not ir_data or not ir_data.get("entities"):
        print("ERROR: IR missing or has no entities", file=sys.stderr); sys.exit(2)
    ir = IR(ir_data)
    svg, meta = render(ir, a.assets, a.title)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(svg)
    meta_path = a.meta or (a.out + ".meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"OK svg={a.out} bytes={len(svg)} nodes={len(meta['nodes'])} edges={len(meta['edges'])}")

if __name__ == "__main__":
    main()
