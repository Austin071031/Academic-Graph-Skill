#!/usr/bin/env python3
"""build_svg.py — render work/graph.json into a layered, editable SVG figure.

Deterministic, stdlib-only. The SVG is the editable source of record:
  * every compartment is a named <g id="compartment-..."> layer
  * every node/edge carries id="node-<id>"/"edge-<id>" and data-* provenance attrs
  * the legend is DERIVED from the same glyph/encoding tables that draw the
    figure, so legend and figure cannot disagree
  * a <metadata> block records sources, generator version and timestamp

Usage: build_svg.py work/graph.json /app/output/figure.svg
"""
import json, math, sys, datetime
from xml.sax.saxutils import escape

GEN = "bio-pathway-svg/1.0"
W = 1240
MARGIN = 24
BAND_H = {"extracellular": 150, "membrane": 46, "cytoplasm": 300,
          "nucleus": 250, "_default": 220}
DEFAULT_ORDER = {"extracellular": 0, "membrane": 1, "cytoplasm": 2,
                 "cytosol": 2, "mitochondrion": 2.4, "golgi": 2.2,
                 "er": 2.3, "nucleus": 3, "periplasm": 1.5}
NODE_STYLE = {
    "gene":            {"shape": "ellipse", "rx": 52, "ry": 24, "fill": "#fff3c4", "stroke": "#8a6d00"},
    "mrna":            {"shape": "ellipse", "rx": 52, "ry": 20, "fill": "#ffe9ec", "stroke": "#a3123a", "dash": True},
    "protein":         {"shape": "rrect",   "w": 116, "h": 40, "fill": "#d9e8fb", "stroke": "#1d4e89"},
    "receptor":        {"shape": "rrect",   "w": 116, "h": 40, "fill": "#cfe8d8", "stroke": "#1e6b45"},
    "complex":         {"shape": "complex", "w": 124, "h": 44, "fill": "#e8dcf5", "stroke": "#5b2d8e"},
    "small_molecule":  {"shape": "circle",  "r": 17, "fill": "#f6d9c3", "stroke": "#9a4b12"},
    "ion":             {"shape": "diamond", "r": 12, "fill": "#d3f0f0", "stroke": "#0f6b6b"},
    "cell":            {"shape": "rrect",   "w": 150, "h": 56, "fill": "#eeeeee", "stroke": "#555555"},
    "cell_type":       {"shape": "rrect",   "w": 150, "h": 56, "fill": "#eeeeee", "stroke": "#555555"},
    "phenotype":       {"shape": "hex",     "rx": 58, "ry": 30, "fill": "#fbd9e2", "stroke": "#8e2050"},
    "pathway":         {"shape": "rrect",   "w": 130, "h": 40, "fill": "#e2e2e2", "stroke": "#333333"},
    "compartment":     {"shape": "ellipse", "rx": 60, "ry": 28, "fill": "#f2f2f2", "stroke": "#666666"},
}
EDGE_STYLE = {
    "activation":       {"marker": "arrow",  "dash": None,  "color": "#1a6b1a", "w": 2.4, "tag": None},
    "induction":        {"marker": "arrow",  "dash": None,  "color": "#1a6b1a", "w": 2.4, "tag": None},
    "expression":       {"marker": "arrow",  "dash": None,  "color": "#1a6b1a", "w": 2.4, "tag": None},
    "inhibition":       {"marker": "tbar",   "dash": None,  "color": "#b01818", "w": 2.4, "tag": None},
    "repression":       {"marker": "tbar",   "dash": None,  "color": "#b01818", "w": 2.4, "tag": None},
    "binding":          {"marker": "none",   "dash": None,  "color": "#333366", "w": 2.0, "tag": None},
    "association":      {"marker": "none",   "dash": None,  "color": "#333366", "w": 2.0, "tag": None},
    "dissociation":     {"marker": "none",   "dash": "4 3", "color": "#333366", "w": 1.8, "tag": None},
    "phosphorylation":  {"marker": "arrow",  "dash": None,  "color": "#7a3db0", "w": 2.4, "tag": "P"},
    "dephosphorylation":{"marker": "arrow",  "dash": None,  "color": "#7a3db0", "w": 2.4, "tag": "P (-)"},
    "ubiquitination":   {"marker": "arrow",  "dash": None,  "color": "#b06a1a", "w": 2.4, "tag": "Ub"},
    "methylation":      {"marker": "arrow",  "dash": None,  "color": "#b06a1a", "w": 2.4, "tag": "Me"},
    "cleavage":         {"marker": "arrow",  "dash": "6 3", "color": "#555555", "w": 2.0, "tag": "scissors"},
    "translocation":    {"marker": "arrow",  "dash": "6 4", "color": "#0f6b6b", "w": 2.2, "tag": "transloc."},
    "transport":        {"marker": "arrow",  "dash": "6 4", "color": "#0f6b6b", "w": 2.2, "tag": None},
    "secretion":        {"marker": "arrow",  "dash": "6 4", "color": "#0f6b6b", "w": 2.2, "tag": None},
    "input":            {"marker": "arrow",  "dash": "2 3", "color": "#888888", "w": 1.6, "tag": None},
    "unknown":          {"marker": "arrow",  "dash": "2 3", "color": "#888888", "w": 1.6, "tag": "?"},
}
EVIDENCE_STYLE = {"strong": {}, "moderate": {"w": -0.5},
                  "weak": {"dash": "5 4", "w": -0.6},
                  "inferred": {"dash": "5 4", "color": "#777777", "w": -0.8},
                  "predicted": {"dash": "2 3", "color": "#999999", "w": -0.9}}
FONT = "Helvetica, Arial, 'DejaVu Sans', sans-serif"

def wrap(text, n=18):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        if len(cur) + len(wd) + 1 > n and cur:
            lines.append(cur); cur = wd
        else:
            cur = (cur + " " + wd).strip()
    if cur:
        lines.append(cur)
    return lines[:3] or [""]

def node_dims(n):
    st = NODE_STYLE.get(n.get("type", "protein"), NODE_STYLE["protein"])
    s = float(n.get("size", 1.0))
    if st["shape"] == "ellipse":
        return st["rx"] * 2 * s, st["ry"] * 2 * s
    if st["shape"] in ("circle", "diamond"):
        return st["r"] * 2 * s, st["r"] * 2 * s
    if st["shape"] == "hex":
        return st["rx"] * 2 * s, st["ry"] * 2 * s
    return st["w"] * s, st["h"] * s

def anchor(n, geom, side):
    x, y, w, h = geom[n["id"]]
    if side == "out":  # leaving node: prefer bottom
        return (x, y + h / 2)
    if side == "in":
        return (x, y - h / 2)
    return (x, y)

def build(g):
    comps = g.get("compartments", [])
    nodes = g.get("nodes", [])
    edges = g.get("edges", [])
    for c in comps:
        c.setdefault("order", DEFAULT_ORDER.get(c.get("id", ""), 2.5))
    comps.sort(key=lambda c: c.get("order", 2.5))
    comp_of = {}
    band_top = {}
    y = MARGIN + 46  # title block
    svg_band = []
    # nucleus gets an ellipse region; others rectangles
    for c in comps:
        cid = c.get("id", "comp%d" % len(band_top))
        h = BAND_H.get(cid, BAND_H["_default"])
        if cid == "membrane":
            h = BAND_H["membrane"]
        band_top[cid] = (y, h)
        comp_of[cid] = c
        y += h + 18
    body_bottom = y - 18 + MARGIN
    # legend width reservation
    legend_items = []
    used_edge_types = []
    for e in edges:
        t = e.get("type", "unknown")
        if t not in used_edge_types:
            used_edge_types.append(t)
    fig_w = W

    geom = {}
    # group nodes per compartment (membrane handled specially)
    per_comp = {}
    for n in nodes:
        cid = n.get("compartment") or "cytoplasm"
        if cid not in band_top and cid != "membrane":
            cid = "cytoplasm" if "cytoplasm" in band_top else (comps[0]["id"] if comps else cid)
        per_comp.setdefault(cid, []).append(n)
    for cid, ns in per_comp.items():
        if cid == "membrane":
            top, h = band_top.get("membrane", (y, 46))
            my = top + h / 2
            step = max(140, (fig_w - 2 * MARGIN) / max(1, len(ns)))
            for i, n in enumerate(ns):
                w, hh = node_dims(n)
                geom[n["id"]] = (MARGIN + step * (i + 0.5), my, w, hh)
            continue
        if cid not in band_top:
            continue
        top, h = band_top[cid]
        cols = max(1, math.ceil(math.sqrt(len(ns) * (fig_w / max(h, 1)) / 2.2)))
        rows = math.ceil(len(ns) / cols)
        cw = (fig_w - 2 * MARGIN) / cols
        ch = h / max(rows, 1)
        for i, n in enumerate(ns):
            r, c = divmod(i, cols)
            w, hh = node_dims(n)
            geom[n["id"]] = (MARGIN + cw * (c + 0.5),
                             top + ch * (r + 0.5), w, hh)

    # ---- svg parts ----
    parts = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                 'width="%d" height="%d" viewBox="0 0 %d %d" font-family="%s">' %
                 (fig_w, body_bottom, fig_w, body_bottom, FONT))
    parts.append('<metadata id="provenance">%s</metadata>' % escape(json.dumps({
        "generator": GEN, "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "title": g.get("title", ""), "species": g.get("species", ""),
        "sources": [n.get("source") for n in nodes if n.get("source")] +
                   [e.get("source") for e in edges if e.get("source")][:50],
    }, ensure_ascii=False)))
    parts.append('<defs>')
    parts.append('<marker id="m-arrow" markerWidth="12" markerHeight="10" refX="10" refY="5" orient="auto">'
                 '<path d="M1,1 L11,5 L1,9" fill="none" stroke="context-stroke" stroke-width="1.8"/></marker>')
    parts.append('<marker id="m-tbar" markerWidth="14" markerHeight="12" refX="11" refY="6" orient="auto">'
                 '<line x1="9" y1="1" x2="9" y2="11" stroke="context-stroke" stroke-width="2.4"/></marker>')
    parts.append('</defs>')

    # title block
    title = g.get("title", "Mechanism figure")
    parts.append('<g id="title-block">')
    parts.append('<text x="%d" y="%d" font-size="20" font-weight="bold" fill="#111">%s</text>' %
                 (MARGIN, MARGIN + 18, escape(title)))
    subt = []
    if g.get("species"):
        subt.append(g["species"])
    if g.get("source_caption"):
        subt.append(g["source_caption"])
    if subt:
        parts.append('<text x="%d" y="%d" font-size="12" fill="#444">%s</text>' %
                     (MARGIN, MARGIN + 38, escape(" | ".join(subt)[:180])))
    parts.append('</g>')

    # compartment bands
    for c in comps:
        cid = c.get("id")
        top, h = band_top[cid]
        lab = escape(c.get("label", cid))
        parts.append('<g id="compartment-%s">' % escape(str(cid)))
        if cid == "membrane":
            my = top + h / 2
            parts.append('<rect x="%d" y="%d" width="%d" height="5" fill="#caa64b" opacity="0.85"/>' %
                         (MARGIN, my - 8, fig_w - 2 * MARGIN))
            parts.append('<rect x="%d" y="%d" width="%d" height="5" fill="#caa64b" opacity="0.85"/>' %
                         (MARGIN, my + 3, fig_w - 2 * MARGIN))
            parts.append('<text x="%d" y="%d" font-size="11" font-style="italic" fill="#7a6418">%s (membrane)</text>' %
                         (MARGIN + 4, my - 14, lab))
        elif cid == "nucleus":
            cx, cy = fig_w / 2, top + h / 2
            parts.append('<ellipse cx="%.0f" cy="%.0f" rx="%d" ry="%d" fill="#f4f0fa" stroke="#9a86b8" stroke-width="1.5" stroke-dasharray="7 4"/>' %
                         (cx, cy, (fig_w - 2 * MARGIN) / 2 - 10, h / 2 - 8))
            parts.append('<text x="%d" y="%d" font-size="12" font-style="italic" fill="#6a5588">%s</text>' %
                         (MARGIN + 18, top + 20, lab))
        else:
            fill = "#eef5fb" if cid in ("extracellular", "cytoplasm", "cytosol") else "#f5f5f0"
            parts.append('<rect x="%d" y="%d" width="%d" height="%d" rx="10" fill="%s" stroke="#b9c6d2"/>' %
                         (MARGIN, top, fig_w - 2 * MARGIN, h, fill))
            parts.append('<text x="%d" y="%d" font-size="12" font-style="italic" fill="#5a6b7a">%s</text>' %
                         (MARGIN + 12, top + 20, lab))
        parts.append('</g>')

    # edges (under nodes)
    parts.append('<g id="edges">')
    edge_meta = {}
    for e in edges:
        if e.get("from") not in geom or e.get("to") not in geom:
            continue
        et = e.get("type", "unknown")
        st = dict(EDGE_STYLE.get(et, EDGE_STYLE["unknown"]))
        ev = EVIDENCE_STYLE.get(e.get("evidence", "strong"), {})
        for k, v in ev.items():
            if k == "w":
                st["w"] = max(1.0, st.get("w", 2) + v)
            else:
                st[k] = v
        if e.get("color"):
            st["color"] = e["color"]
        if e.get("dash"):
            st["dash"] = e["dash"]
        x1, y1 = anchor({"id": e["from"]}, geom, "out")
        x2, y2 = anchor({"id": e["to"]}, geom, "in")
        # if target below source (feedback), curve sideways
        sweep = 0
        if y2 >= y1 - 1:
            x1, y1 = anchor({"id": e["from"]}, geom, "out")
            x2, y2 = anchor({"id": e["to"]}, geom, "in")
            cx1, cy1 = x1, (y1 + y2) / 2
            cx2, cy2 = x2, (y1 + y2) / 2
        else:
            dx = -60 if (hash(e.get("id", "")) % 2 == 0) else 60
            cx1, cy1 = x1 + dx, y1 - 40
            cx2, cy2 = x2 + dx, y2 + 40
            sweep = 1
        d = "M %.1f %.1f C %.1f %.1f, %.1f %.1f, %.1f %.1f" % (x1, y1, cx1, cy1, cx2, cy2, x2, y2)
        marker = {"arrow": "url(#m-arrow)", "tbar": "url(#m-tbar)"}.get(st["marker"], "")
        dash = ' stroke-dasharray="%s"' % st["dash"] if st.get("dash") else ""
        mkr = ' marker-end="%s"' % marker if marker else ""
        eid = escape(str(e.get("id", "e%d" % len(edge_meta))))
        src = e.get("source") or {}
        parts.append('<path id="edge-%s" class="edge type-%s evidence-%s" d="%s" fill="none" stroke="%s" stroke-width="%.1f"%s%s>' % (
            eid, escape(et), escape(e.get("evidence", "strong")), d, st["color"], st["w"], dash, mkr))
        parts.append('<title>%s</title></path>' % escape(
            "%s: %s --[%s]--> %s (evidence: %s) source: %s %s" % (
                eid, e.get("from"), et, e.get("to"), e.get("evidence", "strong"),
                src.get("loc", ""), src.get("quote", "")[:160])))
        edge_meta[eid] = (x1, y1, x2, y2, st)
    # edge tags / labels
    for e in edges:
        eid = str(e.get("id", ""))
        if eid not in edge_meta:
            continue
        x1, y1, x2, y2, st = edge_meta[eid]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if st.get("tag") and st["tag"] != "none":
            parts.append('<g><rect x="%.0f" y="%.0f" width="30" height="15" rx="4" fill="white" stroke="%s" stroke-width="0.8"/>' %
                         (mx - 15, my - 8, st["color"]))
            parts.append('<text x="%.0f" y="%.0f" font-size="10" text-anchor="middle" fill="%s">%s</text></g>' %
                         (mx, my + 3, st["color"], escape(st["tag"][:10])))
        if e.get("label"):
            for j, ln in enumerate(wrap(e["label"], 22)):
                parts.append('<text x="%.0f" y="%.0f" font-size="10" text-anchor="middle" fill="#333">%s</text>' %
                             (mx, my - 14 - 12 * j, escape(ln)))
    parts.append('</g>')

    # nodes
    parts.append('<g id="nodes">')
    for n in nodes:
        if n["id"] not in geom:
            continue
        x, yc, w, h = geom[n["id"]]
        t = n.get("type", "protein")
        st = dict(NODE_STYLE.get(t, NODE_STYLE["protein"]))
        if n.get("fill"):
            st["fill"] = n["fill"]
        if n.get("stroke"):
            st["stroke"] = n["stroke"]
        dash = ' stroke-dasharray="5 3"' if st.get("dash") else ""
        nid = escape(str(n["id"]))
        src = n.get("source") or {}
        parts.append('<g id="node-%s" class="node type-%s">' % (nid, escape(t)))
        sh = st["shape"]
        if sh == "ellipse":
            parts.append('<ellipse cx="%.0f" cy="%.0f" rx="%.0f" ry="%.0f" fill="%s" stroke="%s" stroke-width="1.6"%s/>' %
                         (x, yc, w / 2, h / 2, st["fill"], st["stroke"], dash))
        elif sh == "rrect":
            parts.append('<rect x="%.0f" y="%.0f" width="%.0f" height="%.0f" rx="9" fill="%s" stroke="%s" stroke-width="1.6"%s/>' %
                         (x - w / 2, yc - h / 2, w, h, st["fill"], st["stroke"], dash))
        elif sh == "complex":
            parts.append('<rect x="%.0f" y="%.0f" width="%.0f" height="%.0f" rx="8" fill="%s" stroke="%s" stroke-width="1.6" opacity="0.55"/>' %
                         (x - w / 2 + 6, yc - h / 2 + 5, w, h, st["fill"], st["stroke"]))
            parts.append('<rect x="%.0f" y="%.0f" width="%.0f" height="%.0f" rx="8" fill="%s" stroke="%s" stroke-width="1.6"/>' %
                         (x - w / 2 - 2, yc - h / 2 - 3, w, h, st["fill"], st["stroke"]))
        elif sh == "circle":
            r = st["r"] * float(n.get("size", 1.0))
            parts.append('<circle cx="%.0f" cy="%.0f" r="%.0f" fill="%s" stroke="%s" stroke-width="1.5"/>' %
                         (x, yc, r, st["fill"], st["stroke"]))
        elif sh == "diamond":
            r = st["r"] * float(n.get("size", 1.0))
            parts.append('<polygon points="%.0f,%.0f %.0f,%.0f %.0f,%.0f %.0f,%.0f" fill="%s" stroke="%s" stroke-width="1.5"/>' %
                         (x, yc - r, x + r, yc, x, yc + r, x - r, yc, st["fill"], st["stroke"]))
        elif sh == "hex":
            rx, ry = st["rx"] * float(n.get("size", 1.0)), st["ry"] * float(n.get("size", 1.0))
            pts = " ".join("%.0f,%.0f" % (x + rx * math.cos(math.pi / 6 + k * math.pi / 3),
                                          yc + ry * math.sin(math.pi / 6 + k * math.pi / 3))
                           for k in range(6))
            parts.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="1.6"/>' % (pts, st["fill"], st["stroke"]))
        for j, ln in enumerate(wrap(n.get("label", nid), 16)):
            parts.append('<text x="%.0f" y="%.0f" font-size="12" font-weight="600" text-anchor="middle" fill="#111">%s</text>' %
                         (x, yc - 4 + 13 * j + (6 if sh in ("complex",) else 0), escape(ln)))
        if n.get("synonyms"):
            parts.append('<text x="%.0f" y="%.0f" font-size="9" text-anchor="middle" fill="#666">(%s)</text>' %
                         (x, yc + h / 2 - 4 + 12, escape(str(n["synonyms"])[:40])))
        parts.append('<title>%s</title>' % escape(
            "%s [%s] compartment=%s source: %s %s" % (
                n.get("label", nid), t, n.get("compartment", ""),
                src.get("loc", ""), src.get("quote", "")[:160])))
        parts.append('</g>')
    parts.append('</g>')

    # ---- legend (derived from what is actually used) ----
    ly = MARGIN + 60
    legend_rows = []
    for et in used_edge_types:
        st = EDGE_STYLE.get(et, EDGE_STYLE["unknown"])
        legend_rows.append(("line", st, et.replace("_", " ")))
    ev_used = []
    for e in edges:
        ev = e.get("evidence", "strong")
        if ev != "strong" and ev not in ev_used:
            ev_used.append(ev)
    for ev in ev_used:
        st = dict(EDGE_STYLE["activation"]); st.update(EVIDENCE_STYLE.get(ev, {}))
        legend_rows.append(("line", st, "evidence: " + ev))
    nt_used = []
    for n in nodes:
        t = n.get("type", "protein")
        if t not in nt_used:
            nt_used.append(t)
    for t in nt_used:
        legend_rows.append(("node", NODE_STYLE.get(t, NODE_STYLE["protein"]), t.replace("_", " ")))
    for item in (g.get("legend") or {}).get("items", []):
        legend_rows.append(("text", None, "%s: %s" % (item.get("label", ""), item.get("meaning", ""))))

    leg_h = 30 + len(legend_rows) * 22 + 16
    leg_y = MARGIN + 60
    parts.append('<g id="legend" transform="translate(%d,%d)">' % (fig_w - 320, leg_y))
    parts.append('<rect x="0" y="0" width="296" height="%d" rx="8" fill="#ffffff" stroke="#bbb" opacity="0.95"/>' % leg_h)
    parts.append('<text x="14" y="22" font-size="13" font-weight="bold" fill="#111">Legend</text>')
    yy = 46
    for kind, st, label in legend_rows:
        if kind == "line" and st:
            color = st.get("color", "#333")
            wdt = max(1.0, st.get("w", 2) if isinstance(st.get("w"), (int, float)) else 2)
            dash = ' stroke-dasharray="%s"' % st["dash"] if st.get("dash") else ""
            mk = {"arrow": "url(#m-arrow)", "tbar": "url(#m-tbar)"}.get(st.get("marker", ""), "")
            m = ' marker-end="%s"' % mk if mk else ""
            parts.append('<line x1="14" y1="%d" x2="58" y2="%d" stroke="%s" stroke-width="%.1f"%s%s/>' % (yy - 4, yy - 4, color, wdt, dash, m))
        elif kind == "node" and st:
            parts.append('<rect x="22" y="%d" width="28" height="14" rx="4" fill="%s" stroke="%s"/>' % (yy - 12, st.get("fill", "#eee"), st.get("stroke", "#333")))
        parts.append('<text x="70" y="%d" font-size="11" fill="#222">%s</text>' % (yy, escape(label[:44])))
        yy += 22
    parts.append('</g>')

    parts.append('</svg>')
    return "\n".join(parts), {"edge_types": used_edge_types, "node_types": nt_used,
                              "evidence_used": ev_used, "legend_rows": len(legend_rows)}

def main():
    gp, op = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("/app/work/graph.json", "/app/output/figure.svg")
    g = json.load(open(gp, encoding="utf-8"))
    svg, stats = build(g)
    import os
    os.makedirs(os.path.dirname(op), exist_ok=True)
    with open(op, "w", encoding="utf-8") as f:
        f.write(svg)
    print(json.dumps({"ok": True, "svg": op, "bytes": len(svg), "stats": stats}, ensure_ascii=False))

if __name__ == "__main__":
    main()
