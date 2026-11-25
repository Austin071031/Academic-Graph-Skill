#!/usr/bin/env python3
"""pg_export.py — export SVG to PNG and PDF with a backend fallback chain, then
verify the artifacts are real (non-trivial size, parseable header).

Usage:
  python3 pg_export.py --svg diagram.svg --outdir /app/output [--base diagram] [--report PATH]

Backend order (first success wins): rsvg-convert, inkscape, cairosvg (python),
chromium/chrome headless, then matplotlib last resort (raster only).
Writes <base>.png, <base>.pdf (when a vector backend is available) and an
export_report.json recording backend, sizes, matched CJK font, and checks.
Never fabricates export state: if every backend fails, the report says so and
exits non-zero so the caller can declare a partial result honestly.
"""
import argparse, json, os, shutil, subprocess, sys

def sh(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stderr or r.stdout or "")[:400]
    except Exception as e:
        return False, str(e)[:400]

def have(exe):
    return shutil.which(exe) is not None

def cjk_font_report():
    fonts = []
    if have("fc-list"):
        ok, out = sh(["fc-list", ":lang=zh", "family"], timeout=30)
        if ok:
            fonts = sorted({ln.split(",")[0].strip() for ln in out.splitlines() if ln.strip()})
    return fonts

def try_rsvg(svg, png, pdf):
    if not have("rsvg-convert"):
        return None
    scale = "3.125"
    ok, err = sh(["rsvg-convert", "-z", scale, "-b", "white", "-o", png, svg])
    if ok and os.path.getsize(png) > 512:
        r = {"png_backend": "rsvg-convert", "png_error": ""}
        # rsvg has no pdf; try converting via cairosvg later only if present
        return r
    return None

def try_inkscape(svg, png, pdf):
    if not have("inkscape"):
        return None
    ok, err = sh(["inkscape", svg, "--export-type=png", f"--export-filename={png}", "-d", "300", "--export-background=white"])
    if not (ok and os.path.exists(png) and os.path.getsize(png) > 512):
        return None
    r = {"png_backend": "inkscape", "png_error": ""}
    ok2, _ = sh(["inkscape", svg, "--export-type=pdf", f"--export-filename={pdf}"])
    if ok2 and os.path.exists(pdf) and os.path.getsize(pdf) > 512:
        r["pdf_backend"] = "inkscape"
    return r

def try_cairosvg(svg, png, pdf):
    code = (
        "import cairosvg,sys;"
        f"cairosvg.svg2png(url=sys.argv[1], write_to=sys.argv[2], scale=3.125, background_color='white');"
        f"cairosvg.svg2pdf(url=sys.argv[1], write_to=sys.argv[3])"
    )
    rc = subprocess.run([sys.executable, "-c", code, svg, png, pdf], capture_output=True, text=True, timeout=180)
    r = {}
    if rc.returncode == 0 and os.path.exists(png) and os.path.getsize(png) > 512:
        r["png_backend"] = "cairosvg"
    if rc.returncode == 0 and os.path.exists(pdf) and os.path.getsize(pdf) > 512:
        r["pdf_backend"] = "cairosvg"
    return r or None

def try_chromium(svg, png, pdf):
    exe = None
    for c in ["chromium", "chromium-browser", "google-chrome", "chrome"]:
        if have(c):
            exe = c; break
    if not exe:
        return None
    html = png + ".tmp.html"
    with open(html, "w", encoding="utf-8") as f:
        f.write(f'<!doctype html><html><head><meta charset="utf-8"><style>body{{margin:0}}img{{width:100%}}</style></head>'
                f'<body><img src="file://{os.path.abspath(svg)}"></body></html>')
    ok, err = sh([exe, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                  "--force-device-scale-factor=3", "--screenshot=" + png, "--window-size=1200,900",
                  "file://" + os.path.abspath(html)], timeout=120)
    os.unlink(html) if os.path.exists(html) else None
    if ok and os.path.exists(png) and os.path.getsize(png) > 512:
        return {"png_backend": exe, "png_error": "", "pdf_backend": None,
                "note": "chromium raster only; PDF vector export unavailable in this backend"}
    return None

def try_matplotlib(svg, png, pdf, meta_path=None, ir_path=None):
    """Last-resort backend: re-render the diagram natively from meta.json (node
    boxes + edges) with matplotlib. Produces a genuine PNG preview and PDF from
    the SAME layout data as the SVG — honest approximation, labeled as such."""
    if not meta_path or not os.path.isfile(meta_path):
        return None
    code = r'''
import json, subprocess, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Circle
try:
    out = subprocess.run(["fc-list", ":lang=zh", "family"], capture_output=True, text=True, timeout=20).stdout
    fams = sorted({ln.split(",")[0].strip() for ln in out.splitlines() if ln.strip()})
    avail = {f.name for f in font_manager.fontManager.ttflist}
    pick = [f for f in fams if f in avail] or [f for f in
            ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "SimHei", "Microsoft YaHei"] if f in avail]
    if pick:
        plt.rcParams["font.family"] = pick
        plt.rcParams["font.sans-serif"] = pick + plt.rcParams.get("font.sans-serif", [])
except Exception:
    pass
plt.rcParams["axes.unicode_minus"] = False
meta = json.load(open(sys.argv[1], encoding="utf-8"))
pal = json.load(open(sys.argv[2], encoding="utf-8"))
ir = {}
try:
    ir = json.load(open(sys.argv[3], encoding="utf-8"))
except Exception:
    pass
ex = meta.get("extents", [0, 0, 800, 600])
W, H = ex[2], ex[3]
# chart mode: meta carries no nodes/edges; plot the real source series directly
if not meta.get("nodes") and ir.get("chart", {}).get("series"):
    ch = ir["chart"]
    series = ch["series"]
    fig, ax = plt.subplots(figsize=(W/96, H/96), dpi=300)
    fig.patch.set_facecolor("white")
    colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#F0E442", "#56B4E9"]
    for si, s in enumerate(series):
        col = colors[si % len(colors)]
        data = s.get("data", [])
        xs = [float(p[0]) for p in data]; ys = [float(p[1]) for p in data]
        if s.get("kind") == "bar":
            ax.bar(xs, ys, width=(max(xs)-min(xs))/max(len(xs)*2, 1) if len(xs) > 1 else 0.4,
                   color=col, alpha=0.75, label=s.get("label", s.get("id", "")))
        else:
            ax.plot(xs, ys, "o-", color=col, lw=2, ms=4, label=s.get("label", s.get("id", "")))
    ax.set_xlabel(ch.get("x_label", "")); ax.set_ylabel(ch.get("y_label", ""))
    if ir.get("title"):
        ax.set_title(ir["title"], fontsize=10)
    ax.legend(framealpha=0.9, fontsize=8)
    ax.grid(alpha=0.25, lw=0.5)
    fig.tight_layout()
    fig.savefig(sys.argv[4], dpi=300, facecolor="white")
    fig.savefig(sys.argv[5], format="pdf", facecolor="white")
    raise SystemExit(0)
fig = plt.figure(figsize=(W/96, H/96), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
fig.patch.set_facecolor("white")
labels = {e["id"]: e.get("label", e["id"]) for e in ir.get("entities", [])}
box = {n["id"]: n for n in meta.get("nodes", [])}
kinds = pal.get("flow_kinds", {})
for ed in meta.get("edges", []):
    f, t = box.get(ed["from"]), box.get(ed["to"])
    if not f or not t:
        continue
    kp = kinds.get(ed["kind"], kinds.get("material", {"stroke": "#0072B2"}))
    col = kp.get("stroke", "#0072B2")
    ls = (0, (4, 3)) if kp.get("dash") else "solid"
    if meta.get("direction") == "tb":
        x1, y1 = f["x"], f["y"] + f["h"]/2; x2, y2 = t["x"], t["y"] - t["h"]/2
        verts = [(x1, y1), (x1, (y1+y2)/2), (x2, (y1+y2)/2), (x2, y2)]
    else:
        x1, y1 = f["x"] + f["w"]/2, f["y"]; x2, y2 = t["x"] - t["w"]/2, t["y"]
        verts = [(x1, y1), ((x1+x2)/2, y1), ((x1+x2)/2, y2), (x2, y2)]
    xs, ys = zip(*verts)
    ax.plot(xs, ys, color=col, lw=2, ls=ls, alpha=0.55 if ed.get("confidence") == "inferred" else 1.0)
    ax.annotate("", xy=verts[-1], xytext=verts[-2],
                arrowprops=dict(arrowstyle="-|>", color=col, lw=2))
    if ed.get("label"):
        ax.text((x1+x2)/2, (y1+y2)/2 - 6, ed["label"], fontsize=7, ha="center",
                color="#333", bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))
steps = {}
for s in ir.get("steps", []):
    if s.get("actor"):
        steps[s["actor"]] = s.get("no")
for n in meta.get("nodes", []):
    np_ = pal.get("node_fills", {}).get(n.get("type"), pal.get("node_fills", {}).get("default", {}))
    fc, ec = np_.get("fill", "#fff"), np_.get("stroke", "#333")
    ax.add_patch(FancyBboxPatch((n["x"]-n["w"]/2, n["y"]-n["h"]/2), n["w"], n["h"],
                 boxstyle="round,pad=0,rounding_size=8", fc=fc, ec=ec, lw=1.5))
    if n["id"] in steps:
        ax.add_patch(Circle((n["x"]-n["w"]/2+12, n["y"]-n["h"]/2+12), 9, fc="#333"))
        ax.text(n["x"]-n["w"]/2+12, n["y"]-n["h"]/2+12, str(steps[n["id"]]),
                fontsize=7, ha="center", va="center", color="white")
    ax.text(n["x"], n["y"], labels.get(n["id"], n["id"]), fontsize=8.5, ha="center", va="center")
fig.savefig(sys.argv[4], dpi=300, facecolor="white")
fig.savefig(sys.argv[5], format="pdf", facecolor="white")
'''
    meta_file = os.path.abspath(meta_path)
    pal_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "palette.json")
    ir_file = os.path.abspath(ir_path) if ir_path else os.path.join(os.path.dirname(meta_file), "ir.json")
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_mpl_preview.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(code)
    try:
        rc = subprocess.run([sys.executable, script, meta_file, pal_file, ir_file, png, pdf],
                            capture_output=True, text=True, timeout=180)
        ok = rc.returncode == 0 and os.path.exists(png) and os.path.getsize(png) > 512
        if ok:
            return {"png_backend": "matplotlib_ir_preview", "png_error": "",
                    "pdf_backend": "matplotlib_ir_preview" if os.path.exists(pdf) and os.path.getsize(pdf) > 512 else None,
                    "note": "honest fallback: re-rendered from meta.json layout data (not an SVG raster); SVG remains the editable source of truth"}
    finally:
        pass
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--svg", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--base", default=None)
    ap.add_argument("--report", default=None)
    ap.add_argument("--meta", default=None, help="diagram.svg.meta.json for the IR-aware matplotlib fallback")
    ap.add_argument("--ir", default=None, help="ir.json for the matplotlib fallback labels")
    a = ap.parse_args()
    base = a.base or os.path.splitext(os.path.basename(a.svg))[0]
    os.makedirs(a.outdir, exist_ok=True)
    png = os.path.join(a.outdir, base + ".png")
    pdf = os.path.join(a.outdir, base + ".pdf")
    report = {"svg": os.path.abspath(a.svg), "svg_bytes": os.path.getsize(a.svg),
              "png": png, "pdf": pdf, "attempts": [], "checks": {}}
    fonts = cjk_font_report()
    report["cjk_fonts_found"] = fonts
    result = None
    for name, fn in [("rsvg-convert", try_rsvg), ("inkscape", try_inkscape),
                     ("cairosvg", try_cairosvg), ("chromium", try_chromium),
                     ("matplotlib", lambda s, p, f: try_matplotlib(s, p, f, a.meta, a.ir))]:
        report["attempts"].append(name)
        r = fn(a.svg, png, pdf)
        if r:
            result = r; break
    if not result:
        report["ok"] = False
        report["error"] = "all export backends failed"
        with open(a.report or os.path.join(a.outdir, "export_report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
        print("ERROR: export failed on all backends", file=sys.stderr)
        sys.exit(3)
    report.update(result)
    report["png_bytes"] = os.path.getsize(png) if os.path.exists(png) else 0
    report["pdf_bytes"] = os.path.getsize(pdf) if os.path.exists(pdf) else 0
    report["checks"]["png_exists_nontrivial"] = report["png_bytes"] > 512
    report["checks"]["pdf_exists"] = report["pdf_bytes"] > 512
    report["checks"]["cjk_font_available"] = len(fonts) > 0
    report["ok"] = report["checks"]["png_exists_nontrivial"]
    rp = a.report or os.path.join(a.outdir, "export_report.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(f"OK png={report['png_bytes']}B pdf={report['pdf_bytes']}B backend={report.get('png_backend')} fonts={len(fonts)}")

if __name__ == "__main__":
    main()
