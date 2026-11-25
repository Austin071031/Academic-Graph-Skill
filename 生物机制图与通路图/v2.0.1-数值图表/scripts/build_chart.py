#!/usr/bin/env python3
"""build_chart.py — data-native chart renderer: SVG + CSV + actual chart.png.

Input chart.json (same public schema as v1.0.0). Optional records may use
series[].points [{x,y,source}], series[].x_values, or series[].categories.
numpy/matplotlib is optional and recorded in chart_render_report.json. No
mechanism graph.json is read and a missing renderer never creates a fake PNG.
Usage: build_chart.py /app/work/chart.json /app/output/chart.svg
"""
import csv
import json
import math
import os
import re
import sys
from xml.sax.saxutils import escape

PALETTE = ["#2166ac", "#b2182b", "#1a9850", "#762a83", "#e08214", "#4393c3"]


def number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def slug(key, index):
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", str(key)).strip("-").lower()
    return safe or "series-%d" % index


def normalize(chart):
    """Single source of truth for every backend: one record per real point.

    None is missing (not zero). Series-specific x arrays are sorted by real x.
    Numeric x always sorts numerically; strings retain declared first-seen order.
    Per-record source overrides the series default and is never lost.
    """
    cats = chart.get("categories", [])
    series_list = chart.get("series", [])
    if not isinstance(series_list, list) or not series_list:
        raise ValueError("chart.json needs non-empty series[]")
    allx = []
    out = []
    for j, series in enumerate(series_list):
        source = series.get("source") or {}
        if not source.get("loc") and not source.get("quote"):
            raise ValueError("series[%d] '%s' lacks source loc/quote" % (j, series.get("name", "")))
        sid = slug(series.get("id", series.get("name", j)), j)
        vals = series.get("values", [])
        if not isinstance(vals, list):
            raise ValueError("series '%s' values must be an array" % sid)
        records = []
        points = series.get("points")
        if points is not None:
            if not isinstance(points, list):
                raise ValueError("series '%s' points must be an array" % sid)
            for i, point in enumerate(points):
                if not isinstance(point, dict):
                    raise ValueError("series '%s' point %d is not an object" % (sid, i))
                records.append([point.get("x", point.get("category")), point.get("y", point.get("value")),
                                point.get("source") or source])
        else:
            xs = series.get("x_values", series.get("categories"))
            if xs is not None and len(xs) != len(vals):
                raise ValueError("series '%s' x_values/categories length differs from values" % sid)
            indices = series.get("source_indices")
            for i, value in enumerate(vals):
                rec = {"loc": source.get("loc"), "quote": source.get("quote")}
                if isinstance(indices, list) and i < len(indices):
                    rec["index"] = indices[i]
                else:
                    rec["index"] = i
                records.append([(xs[i] if xs is not None else (cats[i] if i < len(cats) else None)),
                                value, rec])
        color = series.get("color", PALETTE[j % len(PALETTE)])
        clean = []
        gap_before = False
        for x, y, src in records:
            if x is None:
                raise ValueError("series '%s' contains an undefined x/category" % sid)
            # Reject a numeric array accidentally secretly mixed with text values.
            if number(y):
                rec = {"x": x, "y": float(y), "x_raw": x, "source": src,
                       "series": sid, "name": str(series.get("name", sid))}
            elif y is None or (isinstance(y, str) and y.lower() in ("", "null", "na", "n/a", "nan", "none")):
                gap_before = True
                continue  # Explicit missing input: no zero and no line across this gap.
            else:
                raise ValueError("series '%s' has non-numeric non-missing y value %r" % (sid, y))
            rec["gap_before"] = gap_before
            gap_before = False
            clean.append(rec)
            allx.append(x)
        if not clean:
            raise ValueError("series '%s' has no numeric data (all missing?)" % sid)
        out.append({"id": sid, "name": str(series.get("name", sid)), "color": color,
                    "dashed": bool(series.get("dashed")), "records": clean,
                    "source": source})
    numeric = all(number(x) for x in allx)
    if numeric:
        for s in out:
            s["records"].sort(key=lambda r: float(r["x"]))
    else:
        if any(number(x) for x in allx):
            raise ValueError("do not mix numeric and textual x labels in one axis")
        for s in out:
            s["records"].sort(key=lambda r: cats.index(r["x"]) if r["x"] in cats else len(cats) + allx.index(r["x"]))
    labels = []
    for s in out:
        for r in s["records"]:
            if r["x"] not in labels:
                labels.append(r["x"])
    labels = sorted(labels) if numeric else labels
    return {"series": out, "labels": labels, "numeric_x": numeric,
            "kind": chart.get("kind", "bar")}


def domain(values, include_zero=False):
    lo, hi = min(values), max(values)
    if include_zero:
        lo, hi = min(0, lo), max(0, hi)
    pad = (hi - lo) * 0.08 or max(1.0, abs(hi) * 0.08)
    return lo - pad, hi + pad


def source_text(chart, normalized):
    chunks = []
    if chart.get("source_caption"):
        chunks.append(str(chart["source_caption"]))
    for s in normalized["series"]:
        loc = s["source"].get("loc")
        text = "%s: %s" % (s["name"], loc) if loc else None
        if text and text not in chunks:
            chunks.append(text)
    return " | ".join(chunks) or "Source: see series provenance"


def svg_backend(chart, normalized):
    W, H, ML, MR, MT, MB = 1040, 660, 110, 250, 86, 125
    pw, ph = W - ML - MR, H - MT - MB
    series = normalized["series"]
    kind = normalized["kind"] if normalized["kind"] in ("bar", "line", "scatter") else "bar"
    all_y = [r["y"] for s in series for r in s["records"]]
    ylo, yhi = domain(all_y, kind == "bar")
    if normalized["numeric_x"]:
        xs = [float(x) for x in normalized["labels"]]
        xlo, xhi = domain(xs)
    else:
        xlo, xhi = 0, max(1, len(normalized["labels"]))
    def X(x):
        if normalized["numeric_x"]:
            return ML + (float(x) - xlo) / (xhi - xlo) * pw
        return ML + (normalized["labels"].index(x) + 0.5) / len(normalized["labels"]) * pw
    def Y(y):
        return MT + ph - (y - ylo) / (yhi - ylo) * ph
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="Helvetica,Arial,sans-serif">' % (W, H, W, H),
             '<metadata>%s</metadata>' % escape(json.dumps({"generator": "bio-pathway-chart/2.0",
                "numeric_x": normalized["numeric_x"], "kind": kind,
                "missing_policy": "omit", "sources": [s["source"] for s in series]}, ensure_ascii=False))]
    parts += ['<text x="%d" y="30" font-size="19" font-weight="bold">%s</text>' % (ML, escape(chart.get("title", "Chart"))),
              '<text id="native-source" x="%d" y="52" font-size="11" fill="#444">%s</text>' % (ML, escape(source_text(chart, normalized)))]
    for k in range(6):
        v = ylo + (yhi - ylo) * k / 5
        parts.append('<line x1="%d" y1="%.3f" x2="%d" y2="%.3f" stroke="#ddd"/>' % (ML, Y(v), ML + pw, Y(v)))
        parts.append('<text x="%d" y="%.3f" text-anchor="end" font-size="11">%s</text>' % (ML - 8, Y(v) + 4, escape("%.5g" % v)))
    parts += ['<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333"/>' % (ML, MT, ML, MT + ph),
              '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333"/>' % (ML, MT + ph, ML + pw, MT + ph)]
    ticks = normalized["labels"]
    if normalized["numeric_x"] and len(ticks) > 10:
        # Keep raw extreme values and sample real data x; never linearly invent data labels.
        ticks = sorted(set([normalized["labels"][i] for i in range(0, len(normalized["labels"]),
                                                                  max(1, len(normalized["labels"]) // 9))]
                           + [normalized["labels"][-1]]))
    for x in ticks:
        parts.append('<text x="%.3f" y="%d" font-size="11" text-anchor="middle">%s</text>' % (X(x), MT + ph + 22, escape(str(x))))
    if chart.get("x_label"):
        parts.append('<text x="%.1f" y="%d" font-size="13" text-anchor="middle">%s</text>' % (ML + pw / 2, H - 53, escape(str(chart["x_label"]))))
    if chart.get("y_label"):
        parts.append('<text x="19" y="%.1f" font-size="13" text-anchor="middle" transform="rotate(-90 19 %.1f)">%s</text>' % (MT + ph / 2, MT + ph / 2, escape(str(chart["y_label"]))))
    # Offset bars by stable series position, measured against the requested group.
    ngroups, m = len(normalized["labels"]), len(series)
    group_width = pw / max(1, ngroups) * 0.72
    bw = group_width / m
    for j, s in enumerate(series):
        parts.append('<g id="series-%s" data-series-key="%s">' % (escape(s["id"]), escape(s["id"])))
        if kind == "bar":
            for r in s["records"]:
                center = X(r["x"]) + (j - (m - 1) / 2) * (bw if not normalized["numeric_x"] else min(bw, bw * 0.85))
                width = max(2.0, min(bw, group_width * 0.85))
                y0, yy = Y(max(0, r["y"])), Y(min(0, r["y"]))
                src = r["source"] or {}
                parts.append('<rect class="data-point" data-series-key="%s" data-x="%s" data-value="%.15g" data-source-loc="%s" x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="%s"><title>%s</title></rect>' % (
                    escape(s["id"]), escape(str(r["x"])), r["y"], escape(str(src.get("loc", ""))),
                    center - width / 2, y0, width, max(0.6, yy - y0), s["color"],
                    escape("%s | %s = %s | %s" % (s["name"], r["x"], r["y"], src.get("loc", "")))))
        else:
            segments, segment = [], []
            for r in s["records"]:
                if r.get("gap_before") and segment:
                    segments.append(segment)
                    segment = []
                segment.append(r)
            if segment:
                segments.append(segment)
            if kind == "line":
                for segment in segments:
                    if len(segment) <= 1:
                        continue
                    points = " ".join("%.3f,%.3f" % (X(r["x"]), Y(r["y"])) for r in segment)
                    parts.append('<polyline class="series-line" data-series-key="%s" points="%s" fill="none" stroke="%s" stroke-width="2"%s/>' % (
                        escape(s["id"]), points, s["color"], ' stroke-dasharray="6 4"' if s["dashed"] else ""))
            for r in s["records"]:
                src = r["source"] or {}
                parts.append('<circle class="data-point" data-series-key="%s" data-x="%s" data-value="%.15g" data-source-loc="%s" cx="%.3f" cy="%.3f" r="4.2" fill="%s"><title>%s</title></circle>' % (
                    escape(s["id"]), escape(str(r["x"])), r["y"], escape(str(src.get("loc", ""))),
                    X(r["x"]), Y(r["y"]), s["color"], escape("%s | %s = %s | %s" % (s["name"], r["x"], r["y"], src.get("loc", "")))))
        parts.append('</g>')
    parts.append('<g id="legend">')
    for j, s in enumerate(series):
        yy = MT + j * 34
        parts.append('<g id="legend-series-%s" data-series-key="%s">' % (escape(s["id"]), escape(s["id"])))
        if kind == "bar":
            parts.append('<rect x="%d" y="%d" width="16" height="14" fill="%s"/>' % (ML + pw + 28, yy - 12, s["color"]))
        else:
            parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2.5"/><circle cx="%d" cy="%d" r="4" fill="%s"/>' % (ML + pw + 26, yy - 4, ML + pw + 48, yy - 4, s["color"], ML + pw + 37, yy - 4, s["color"]))
        parts.append('<text x="%d" y="%d" font-size="12">%s</text>' % (ML + pw + 56, yy, escape(s["name"])))
        parts.append('</g>')
    parts += ['</g>', '<text x="%d" y="%d" font-size="10" fill="#555">Missing values omitted; no zero imputation or line bridging.</text>' % (ML, H - 25),
              '</svg>']
    return "\n".join(parts)


def matplotlib_backend(chart, normalized, png):
    """PNG from the same normalized arrays; independent of SVG or graph.json."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    series = normalized["series"]
    numeric = normalized["numeric_x"]
    labels = normalized["labels"]
    positions = {x: i for i, x in enumerate(labels)}
    fig, ax = plt.subplots(figsize=(10.4, 6.6), dpi=150)
    kind = normalized["kind"] if normalized["kind"] in ("bar", "line", "scatter") else "bar"
    width = 0.72 / len(series)
    for j, s in enumerate(series):
        xs = [float(r["x"]) if numeric else positions[r["x"]] for r in s["records"]]
        ys = [r["y"] for r in s["records"]]
        if kind == "bar":
            if numeric:
                delta = min([b - a for a, b in zip(xs, xs[1:])] or [1.0])
                w = width * delta
                ax.bar([x + (j - (len(series) - 1) / 2) * w for x in xs], ys,
                       width=w * 0.85, color=s["color"], label=s["name"])
            else:
                ax.bar([x + (j - (len(series) - 1) / 2) * width for x in xs], ys,
                       width=width * 0.85, color=s["color"], label=s["name"])
        elif kind == "line":
            segments, segment = [], []
            for x, y, record in zip(xs, ys, s["records"]):
                if record.get("gap_before") and segment:
                    segments.append(segment)
                    segment = []
                segment.append((x, y))
            if segment:
                segments.append(segment)
            for segment in segments:
                ax.plot([p[0] for p in segment], [p[1] for p in segment], marker="o",
                        linewidth=1.8, linestyle="--" if s["dashed"] else "-",
                        color=s["color"], label=s["name"] if segment is segments[0] else "_nolegend_")
        else:
            ax.scatter(xs, ys, s=25, color=s["color"], label=s["name"])
    if not numeric:
        ax.set_xticks(range(len(labels)), [str(x) for x in labels])
    ax.set_title(chart.get("title", "Chart"))
    ax.set_xlabel(str(chart.get("x_label", "")))
    ax.set_ylabel(str(chart.get("y_label", "")))
    ax.grid(axis="y", color="#dddddd", linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(title="Series", frameon=False)
    fig.suptitle(source_text(chart, normalized), x=0.06, y=0.965, fontsize=8, ha="left", color="#444444")
    fig.text(0.06, 0.018, "Missing values omitted; no zero imputation or line bridging.", fontsize=7, color="#555555")
    fig.tight_layout(rect=[0, 0.055, 1, 0.94])
    fig.savefig(png)
    plt.close(fig)
    return os.path.getsize(png)


def write_csv(normalized, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        names = [s["name"] for s in normalized["series"]]
        w.writerow(["category"] + names)
        for x in normalized["labels"]:
            row = [x]
            for s in normalized["series"]:
                lookup = {r["x"]: r["y"] for r in s["records"]}
                row.append(lookup.get(x, ""))
            w.writerow(row)


def main():
    cp = sys.argv[1] if len(sys.argv) > 1 else "/app/work/chart.json"
    op = sys.argv[2] if len(sys.argv) > 2 else "/app/output/chart.svg"
    out = os.path.dirname(op) or "."
    os.makedirs(out, exist_ok=True)
    report = {"svg": op, "png": None, "method": None, "errors": []}
    try:
        with open(cp, encoding="utf-8") as f:
            chart = json.load(f)
        normalized = normalize(chart)
        svg = svg_backend(chart, normalized)
        with open(op, "w", encoding="utf-8") as f:
            f.write(svg)
        write_csv(normalized, os.path.join(out, "chart_data.csv"))
        png = os.path.join(out, "chart.png")
        try:
            count = matplotlib_backend(chart, normalized, png)
            report.update({"png": png, "method": "matplotlib", "bytes": count})
        except ImportError as e:
            report["errors"].append("matplotlib/numpy unavailable: %s; real SVG/CSV preserved" % e)
        except Exception as e:
            if os.path.exists(png):
                os.remove(png)
            report["errors"].append("matplotlib chart renderer failed: %s; real SVG/CSV preserved" % e)
        report["records"] = sum(len(s["records"]) for s in normalized["series"])
        report["numeric_x"] = normalized["numeric_x"]
        ok = True
    except Exception as e:
        report["errors"].append(str(e))
        ok = False
    with open(os.path.join(out, "chart_render_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
