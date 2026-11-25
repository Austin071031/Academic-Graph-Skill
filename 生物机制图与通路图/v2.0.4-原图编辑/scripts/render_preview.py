#!/usr/bin/env python3
"""render_preview.py — produce PNG and PDF previews from SVG files.

Cascade (first success wins), each recorded in render_report.json:
  1. cairosvg (python)
  2. rsvg-convert
  3. inkscape
  4. resvg
  5. soffice --convert-to (drawio only)
Never fabricates a preview: if every renderer fails, report it honestly and
let the agent fall back to a matplotlib sketch or document the gap.
Usage: render_preview.py /app/output/figure.svg /app/output/figure.png /app/output/figure.pdf [work/graph.json]
"""
import json, os, shutil, subprocess, sys

def try_cairosvg(svg, png, pdf):
    try:
        import cairosvg
    except Exception:
        return None
    try:
        cairosvg.svg2png(url=svg, write_to=png, output_width=1600)
        meth = {"png": "cairosvg"}
        if pdf:
            try:
                cairosvg.svg2pdf(url=svg, write_to=pdf)
                meth["pdf"] = "cairosvg"
            except Exception:
                pass
        return meth
    except Exception:
        return None

def try_cmd(exe, args_png, args_pdf, png, pdf):
    if not shutil.which(exe):
        return None
    meth = {}
    try:
        r = subprocess.run([exe] + args_png, capture_output=True, timeout=180)
        if r.returncode == 0 and os.path.exists(png) and os.path.getsize(png) > 0:
            meth["png"] = exe
        elif os.path.exists(png):
            os.remove(png)
    except Exception:
        if os.path.exists(png):
            try: os.remove(png)
            except OSError: pass
    if pdf:
        try:
            r = subprocess.run([exe] + args_pdf, capture_output=True, timeout=180)
            if r.returncode == 0 and os.path.exists(pdf) and os.path.getsize(pdf) > 0:
                meth["pdf"] = exe
            elif os.path.exists(pdf):
                os.remove(pdf)
        except Exception:
            pass
    return meth or None

def matplotlib_fallback(graph_json, png, pdf):
    """Rough but honest preview straight from graph.json (boxes + labeled edges).
    Used only when no SVG rasterizer exists. Returns True on success."""
    if not graph_json or not os.path.exists(graph_json):
        return False
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    try:
        import json, math
        g = json.load(open(graph_json, encoding="utf-8"))
        comps = sorted(g.get("compartments", []),
                       key=lambda c: c.get("order", {"extracellular": 0, "membrane": 1,
                                                     "cytoplasm": 2, "nucleus": 3}.get(c.get("id", ""), 2.5)))
        nodes, edges = g.get("nodes", []), g.get("edges", [])
        band, y = {}, 0
        for c in comps:
            band[c.get("id")] = y
            y += 1
        if not band:
            band = {"cytoplasm": 0}
        per = {}
        for n in nodes:
            cid = n.get("compartment") or "cytoplasm"
            if cid not in band:
                cid = "cytoplasm" if "cytoplasm" in band else list(band)[0]
            per.setdefault(cid, []).append(n)
        pos = {}
        for cid, ns in per.items():
            for i, n in enumerate(ns):
                pos[n["id"]] = (i + 0.5 - (len(ns) - 1) / 2.0, -band[cid])
        fig, ax = plt.subplots(figsize=(10, 8))
        for cid, yy in band.items():
            ax.axhspan(-yy - 0.45, -yy + 0.45, color="#f2f6fa" if cid != "membrane" else "#e9d9a8", alpha=0.6)
            ax.text(-0.5, -yy + 0.38, cid, fontsize=9, style="italic", color="#666")
        for e in edges:
            if e.get("from") in pos and e.get("to") in pos:
                (x1, y1), (x2, y2) = pos[e["from"]], pos[e["to"]]
                style = "--" if e.get("evidence") in ("weak", "inferred", "predicted") else "-"
                ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                            arrowprops=dict(arrowstyle="-|>" if e.get("type") not in ("binding", "association") else "-",
                                            linestyle=style, color="#333", lw=1.6))
                ax.text((x1 + x2) / 2, (y1 + y2) / 2, e.get("type", ""), fontsize=7, color="#555")
        for n in nodes:
            x, yy = pos[n["id"]]
            ax.text(x, yy, n.get("label", n["id"]), fontsize=9, ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.35", fc="#dce9f7", ec="#335", lw=1.2))
        ax.set_title(g.get("title", "mechanism") + "  (fallback preview from graph.json)")
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(png, dpi=150)
        if pdf:
            fig.savefig(pdf)
        plt.close(fig)
        return True
    except Exception:
        return False

def main():
    svg = sys.argv[1]
    png = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(svg)[0] + ".png"
    pdf = sys.argv[3] if len(sys.argv) > 3 else os.path.splitext(svg)[0] + ".pdf"
    graph_json = sys.argv[4] if len(sys.argv) > 4 else "/app/work/graph.json"
    report = {"svg": svg, "png": None, "pdf": None, "methods": {}, "errors": []}
    meth = try_cairosvg(svg, png, pdf)
    if meth:
        report["methods"].update(meth)
    if not report["methods"].get("png"):
        m = try_cmd("rsvg-convert", ["-w", "1600", "-o", png, svg], [], png, None)
        if m: report["methods"].update(m)
    if not report["methods"].get("png"):
        m = try_cmd("inkscape", [svg, "--export-type=png", "--export-filename=" + png, "-w", "1600"],
                    [svg, "--export-type=pdf", "--export-filename=" + pdf], png, pdf)
        if m: report["methods"].update(m)
    if not report["methods"].get("png"):
        m = try_cmd("resvg", ["-w", "1600", svg, png], [svg, pdf], png, pdf)
        if m: report["methods"].update(m)
    if os.path.exists(png) and os.path.getsize(png) > 0:
        report["png"] = png
    if os.path.exists(pdf) and os.path.getsize(pdf) > 0:
        report["pdf"] = pdf
    if not report["png"]:
        if matplotlib_fallback(graph_json, png, pdf):
            report["methods"]["png"] = "matplotlib-fallback(graph.json)"
            report["png"] = png
            if pdf and os.path.exists(pdf) and os.path.getsize(pdf) > 0:
                report["methods"]["pdf"] = "matplotlib-fallback(graph.json)"
                report["pdf"] = pdf
        else:
            report["errors"].append("no SVG rasterizer available (cairosvg/rsvg-convert/inkscape/resvg all missing or failed) and matplotlib fallback unavailable")
    if not report["pdf"] and not report["errors"] and os.path.exists(pdf) is False:
        report["errors"].append("PDF export failed for all renderers")
    rp = os.path.join(os.path.dirname(svg) or ".", "render_report.json")
    with open(rp, "a", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False)
        f.write("\n")
    print(json.dumps(report, ensure_ascii=False))
    sys.exit(0 if report["png"] or report["pdf"] else 1)

if __name__ == "__main__":
    main()
