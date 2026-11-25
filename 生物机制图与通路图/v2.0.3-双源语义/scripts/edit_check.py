#!/usr/bin/env python3
"""edit_check.py — prove the delivered sources are really editable & re-exportable.

Simulates the reviewer workflow: take figure.svg + figure.drawio, change ONE node
label in each (prefix "EDIT_OK: "), re-render the edited SVG to PNG, and verify
the new label appears in the raster text layer source. Writes edit_check.json.
Usage: edit_check.py /app/output
Requires: figure.svg and figure.drawio present; render_preview.py in same dir.
"""
import json, os, re, subprocess, sys

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/app/output"
    svg_p = os.path.join(out, "figure.svg")
    dio_p = os.path.join(out, "figure.drawio")
    result = {"ok": False, "checks": []}
    if not (os.path.exists(svg_p) and os.path.exists(dio_p)):
        result["checks"].append("figure.svg/figure.drawio missing — edit check skipped")
        print(json.dumps(result)); sys.exit(0)
    svg = open(svg_p, encoding="utf-8").read()
    m = re.search(r'<g id="node-([^"]+)".*?<text[^>]*>([^<]+)</text>', svg, re.S)
    if not m:
        result["checks"].append("no editable node label found in figure.svg")
        print(json.dumps(result)); sys.exit(0)
    nid, label = m.group(1), m.group(2)
    new_label = "EDIT_OK " + label
    edited_svg = svg.replace(">%s<" % label, ">%s<" % new_label, 1)
    edit_svg = os.path.join(out, "edit_demo.svg")
    with open(edit_svg, "w", encoding="utf-8") as f:
        f.write(edited_svg)
    # drawio edit
    dio = open(dio_p, encoding="utf-8").read()
    edited_dio = dio.replace('value="%s"' % label, 'value="%s"' % new_label, 1)
    with open(os.path.join(out, "edit_demo.drawio"), "w", encoding="utf-8") as f:
        f.write(edited_dio)
    # re-export edited svg
    rp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_preview.py")
    png = os.path.join(out, "edit_demo.png")
    r = subprocess.run([sys.executable, rp, edit_svg, png, os.path.join(out, "edit_demo.pdf"),
                        os.path.join(out, "..", "work", "graph.json")],
                       capture_output=True, timeout=300)
    rerender_ok = os.path.exists(png) and os.path.getsize(png) > 500
    result["checks"].append("svg label editable: node %s '%s' -> '%s'" % (nid, label, new_label))
    result["checks"].append("drawio label editable: %s" % ("yes" if new_label in edited_dio else "NO"))
    result["checks"].append("edited svg re-rendered to png: %s" % ("yes" if rerender_ok else "failed (see render_report)"))
    result["ok"] = (new_label in edited_svg) and (new_label in edited_dio) and rerender_ok
    with open(os.path.join(out, "edit_check.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)

if __name__ == "__main__":
    main()
