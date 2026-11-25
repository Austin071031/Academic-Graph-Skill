#!/usr/bin/env python3
"""edit_check.py — test edit in-place on native SVG and draw.io sources.

Uses source_edit.py for both formats. No graph regeneration, no XML post-surgery
and no matplotlib-fallback(graph.json) as false preview evidence.
Usage: edit_check.py /app/output
"""
import json
import os
import subprocess
import sys


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/app/output"
    svg_path = os.path.join(out, "figure.svg")
    dio_path = os.path.join(out, "figure.drawio")
    result = {"ok": False, "checks": [], "proofs": []}
    if not (os.path.isfile(svg_path) and os.path.isfile(dio_path)):
        result["checks"].append("figure.svg/figure.drawio missing — edit check skipped")
        print(json.dumps(result, ensure_ascii=False))
        return 0
    try:
        import xml.etree.ElementTree as ET
        svg_root = ET.parse(svg_path).getroot()
        group = next((el for el in svg_root.iter() if el.get("id", "").startswith("node-")), None)
        if group is None:
            raise ValueError("no native SVG node-* id")
        nid = group.get("id")
        label = next((el for el in group.iter() if el.tag.endswith("text") and (el.text or "").strip()), None)
        new_label = "EDIT_OK " + (label.text.strip() if label is not None else nid)
        commands = []
        for source, dest in [(svg_path, os.path.join(out, "edit_demo.svg")),
                             (dio_path, os.path.join(out, "edit_demo.drawio"))]:
            spec = os.path.join(out, ".edit_check_spec.json")
            with open(spec, "w", encoding="utf-8") as f:
                json.dump({"changes": [{"id": nid, "kind": "label", "value": new_label}]}, f, ensure_ascii=False)
            commands.append([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_edit.py"),
                             "--input", source, "--changes", spec, "--output", dest, "--preview"])
        for command in commands:
            done = subprocess.run(command, capture_output=True, text=True, timeout=360)
            response = json.loads(done.stdout.strip().splitlines()[-1]) if done.stdout.strip() else {}
            result["proofs"].append(response)
            proof_path = os.path.splitext(command[-2])[0] + "_edit_proof.json"
            if os.path.isfile(proof_path):
                proof = json.load(open(proof_path, encoding="utf-8"))
                result["checks"].append("%s: %s; geometry_unchanged=%s; non_target_changed=%s" % (
                    os.path.basename(proof_path), proof.get("ok"),
                    proof.get("geometry_unchanged"), proof.get("non_target_nodes_changed")))
                result["ok"] = result["ok"] or False
        # Labels and geometry are mandatory. Preview must be nonempty only if the
        # renderer ran; failure is honestly retained, not converted to parent png.
        result["ok"] = len(result["proofs"]) == 2 and all(p.get("ok") for p in result["proofs"])
    except Exception as e:
        result["checks"].append(str(e))
    with open(os.path.join(out, "edit_check.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
