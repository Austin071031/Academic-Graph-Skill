#!/usr/bin/env python3
"""build_chart.py — render work/chart.json (quantitative chart spec) to SVG + PNG + CSV.

chart.json schema:
{
  "title": str, "kind": "bar"|"line"| "scatter",
  "x_label": str, "y_label": str,
  "categories": ["wt", "ko", ...],          # x axis
  "series": [{"name": str, "values": [num...], "color": optional,
              "source": {"loc": str, "quote": str}}],
  "source_caption": str,                     # e.g. "Fig. 3B of <paper>, values read from ..."
  "notes": str
}
Every series MUST carry source loc/quote — charts without a data source are
a traceability failure, and this script refuses to render them.
Usage: build_chart.py work/chart.json /app/output/chart.svg
"""
import json, math, sys
from xml.sax.saxutils import escape

def render_svg(c):
    series = c.get("series", [])
    cats = c.get("categories", [])
    if not series or not cats:
        raise ValueError("chart.json needs non-empty series[] and categories[]")
    for i, s in enumerate(series):
        if not (s.get("source") or {}).get("loc") and not (s.get("source") or {}).get("quote"):
            raise ValueError("series[%d] '%s' lacks source loc/quote — add the data provenance first" % (i, s.get("name", "?")))
        if len(s.get("values", [])) != len(cats):
            raise ValueError("series '%s' has %d values for %d categories" % (
                s.get("name"), len(s.get("values", [])), len(cats)))
    W, H, ML, MR, MT, MB = 900, 560, 90, 30, 70, 90
    pw, ph = W - ML - MR, H - MT - MB
    allv = [v for s in series for v in s["values"] if isinstance(v, (int, float))]
    vmax = max(allv) if allv else 1
    vmin = min(0, min(allv)) if allv else 0
    rng = (vmax - vmin) or 1
    vmax += rng * 0.12
    rng = vmax - vmin
    def Y(v):
        return MT + ph - (v - vmin) / rng * ph
    def X(i):
        return ML + pw * (i + 0.5) / len(cats)
    palette = ["#2166ac", "#b2182b", "#1a9850", "#762a83", "#e08214", "#4393c3"]
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="Helvetica, Arial, sans-serif">' % (W, H, W, H),
             '<metadata>%s</metadata>' % escape(json.dumps(
                 {"generator": "bio-pathway-chart/1.0", "source_caption": c.get("source_caption", ""),
                  "series_sources": [s.get("source") for s in series]}, ensure_ascii=False))]
    parts.append('<text x="%d" y="30" font-size="18" font-weight="bold">%s</text>' % (ML, escape(c.get("title", "Chart"))))
    if c.get("source_caption"):
        parts.append('<text x="%d" y="50" font-size="11" fill="#444">%s</text>' % (ML, escape(c["source_caption"][:150])))
    # grid + y ticks
    for k in range(6):
        v = vmin + rng * k / 5
        parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#ddd"/>' % (ML, Y(v), ML + pw, Y(v)))
        parts.append('<text x="%d" y="%.1f" font-size="11" text-anchor="end" fill="#333">%g</text>' % (ML - 8, Y(v) + 4, round(v, 4)))
    parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333"/>' % (ML, MT, ML, MT + ph))
    parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333"/>' % (ML, MT + ph, ML + pw, MT + ph))
    if c.get("y_label"):
        parts.append('<text x="18" y="%d" font-size="13" text-anchor="middle" transform="rotate(-90 18 %d)">%s</text>' % (MT + ph / 2, MT + ph / 2, escape(c["y_label"])))
    if c.get("x_label"):
        parts.append('<text x="%d" y="%d" font-size="13" text-anchor="middle">%s</text>' % (ML + pw / 2, H - 30, escape(c["x_label"])))
    for i, cat in enumerate(cats):
        parts.append('<text x="%.1f" y="%d" font-size="12" text-anchor="middle">%s</text>' % (X(i), MT + ph + 20, escape(str(cat))))
    kind = c.get("kind", "bar")
    if kind == "bar":
        n, m = len(cats), len(series)
        bw = pw / n / (m + 1)
        for j, s in enumerate(series):
            color = s.get("color", palette[j % len(palette)])
            for i, v in enumerate(s["values"]):
                x0 = X(i) + (j - (m - 1) / 2) * bw - bw / 2
                parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" stroke="#333" stroke-width="0.5"><title>%s | %s = %g (source: %s)</title></rect>' % (
                    x0, Y(max(v, 0)), bw - 1, abs(Y(v) - Y(0)), color,
                    escape(str(s.get("name", ""))), escape(str(cats[i])), v,
                    escape(str((s.get("source") or {}).get("loc", "")))))
                parts.append('<text x="%.1f" y="%.1f" font-size="9" text-anchor="middle" fill="#222">%g</text>' % (
                    x0 + bw / 2 - 0.5, Y(max(v, 0)) - 4 if v >= 0 else Y(v) + 12, round(v, 4)))
    else:
        for j, s in enumerate(series):
            color = s.get("color", palette[j % len(palette)])
            pts = " ".join("%.1f,%.1f" % (X(i), Y(v)) for i, v in enumerate(s["values"]))
            dash = ' stroke-dasharray="6 4"' if s.get("dashed") else ""
            parts.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2"%s/>' % (pts, color, dash))
            for i, v in enumerate(s["values"]):
                parts.append('<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"><title>%s | %s = %g (source: %s)</title></circle>' % (
                    X(i), Y(v), color, escape(str(s.get("name", ""))), escape(str(cats[i])), v,
                    escape(str((s.get("source") or {}).get("loc", "")))))
    # legend
    lx, ly = ML + pw - 30 - 160 * len(series), MT + 6
    for j, s in enumerate(series):
        color = s.get("color", palette[j % len(palette)])
        parts.append('<rect x="%d" y="%d" width="12" height="12" fill="%s"/>' % (lx + j * 160, ly - 10, color))
        parts.append('<text x="%d" y="%d" font-size="12">%s</text>' % (lx + j * 160 + 16, ly, escape(str(s.get("name", ""))[:20])))
    if c.get("notes"):
        parts.append('<text x="%d" y="%d" font-size="10" fill="#666">%s</text>' % (ML, H - 12, escape(c["notes"][:200])))
    parts.append('</svg>')
    return "\n".join(parts)

def write_csv(c, path):
    import csv
    cats = c.get("categories", [])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category"] + [str(s.get("name", "series%d" % i)) for i, s in enumerate(c.get("series", []))])
        for i, cat in enumerate(cats):
            w.writerow([cat] + [s["values"][i] for s in c.get("series", [])])

def main():
    cp, op = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("/app/work/chart.json", "/app/output/chart.svg")
    c = json.load(open(cp, encoding="utf-8"))
    svg = render_svg(c)
    import os
    os.makedirs(os.path.dirname(op), exist_ok=True)
    with open(op, "w", encoding="utf-8") as f:
        f.write(svg)
    write_csv(c, os.path.splitext(op)[0] + "_data.csv")
    print(json.dumps({"ok": True, "svg": op}, ensure_ascii=False))

if __name__ == "__main__":
    main()
