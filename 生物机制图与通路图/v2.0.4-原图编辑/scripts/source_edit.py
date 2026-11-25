#!/usr/bin/env python3
"""source_edit.py — bounded, source-preserving edits to native SVG/draw.io.

Required dependency: lxml (reported, not silently substituted). Only list fields,
attrs, native text and explicitly allowlisted style attributes are editable.
Geometry, viewBox, ids, topology and every non-target object must remain intact.

Usage:
  source_edit.py --input /input/original.svg \
    --changes /app/work/edit_spec.json --output /app/output/edited_figure.svg
  source_edit.py --check proof.json

  edit_spec = {"changes":[{"id":"node-a", "kind":"label", "value":"new label"},
                         {"id":"node-a", "kind":"attribute",
                          "name":"fill", "value":"#d73027"}]}
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

LABEL_KINDS = {"label", "text", "rename", "change_label", "title"}
STYLE_KINDS = {"attribute", "style", "attr"}
GEOMETRY_ATTRS = {"x", "y", "x1", "x2", "y1", "y2", "cx", "cy", "width", "height",
                  "rx", "ry", "r", "d", "points", "viewBox", "transform"}
ALLOWED_ATTRS = {"fill", "stroke", "stroke-width", "stroke-dasharray", "stroke-opacity",
                 "fill-opacity", "opacity", "color", "font-family", "font-size",
                 "font-style", "font-weight", "text-anchor", "letter-spacing", "class",
                 "visibility", "display", "size", "bold", "italic"}
SVG = "{http://www.w3.org/2000/svg}"


def sha_element(element):
    data = etree.tostring(element, method="c14n")
    return hashlib.sha256(data).hexdigest()


def parse(path):
    parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False,
                              remove_comments=False, huge_tree=False)
    return etree.parse(path, parser)


def document_fingerprint(root):
    """Signature of every id, plus geometry for every element (id-less included)."""
    ids = {}
    geometry = {}
    for i, el in enumerate(root.iter()):
        if el.get("id"):
            ids[el.get("id")] = sha_element(el)
        geometry[str(root.getroottree().getpath(el))] = {
            key: el.get(key) for key in sorted(GEOMETRY_ATTRS) if el.get(key) is not None
        }
        for g in el.iter():
            # Nested mxGeometry/mxPoint are included by path regardless of ids.
            pass
    connections = {}
    for el in root.iter():
        if el.get("source") or el.get("target"):
            connections[str(root.getroottree().getpath(el))] = (el.get("source"), el.get("target"))
    return ids, geometry, connections


def selected_scope(target):
    scope = set()
    el = target
    while el is not None:
        if el.get("id"):
            scope.add(el.get("id"))
        el = el.getparent()
    return scope


def apply_change(root, change):
    if not isinstance(change, dict):
        raise ValueError("each changes[] entry must be an object with an existing id")
    target_id = change.get("id", change.get("target_id", change.get("selector")))
    if not target_id:
        raise ValueError("change is missing target id (no invented placeholder target allowed)")
    targets = root.xpath("//*[@id=$id]", id=str(target_id))
    if len(targets) != 1:
        raise ValueError("target id %r matched %d elements (must be exactly one)" % (target_id, len(targets)))
    target = targets[0]
    kind = str(change.get("kind", "label")).lower()
    value = change.get("value", change.get("text", change.get("label")))
    if value is None:
        raise ValueError("target %s has no new value" % target_id)
    before = None
    if kind in LABEL_KINDS:
        tag = etree.QName(target).localname
        if tag in ("text", "tspan", "title", "desc"):
            before = target.text or ""
            target.text = str(value)
        elif tag == "object" and target.get("label") is not None:
            before = target.get("label")
            target.set("label", str(value))
            # draw.io object has a child mxCell carrying the same native label.
            for cell in target:
                if etree.QName(cell).localname == "mxCell":
                    cell.set("value", str(value))
        elif target.get("value") is not None:
            before = target.get("value")
            target.set("value", str(value))
        else:
            labels = target.xpath(".//*[local-name()='text' or local-name()='tspan' or local-name()='label']")
            if not labels:
                raise ValueError("target %s has no native text/label node" % target_id)
            label = labels[0]
            before = label.text or label.get("value") or ""
            if etree.QName(label).localname == "label" and label.get("value") is not None:
                label.set("value", str(value))
            else:
                label.text = str(value)
        method = "native label/text"
    elif kind in STYLE_KINDS:
        name = change.get("name", change.get("attribute", change.get("property")))
        if not name:
            raise ValueError("attribute edit needs name")
        if name in GEOMETRY_ATTRS or name == "id" or name in ("source", "target"):
            raise ValueError("attribute %s would alter geometry/topology/id; forbidden in this edit contract" % name)
        if name not in ALLOWED_ATTRS:
            raise ValueError("attribute %s is not in the declared style allowlist" % name)
        before = target.get(name)
        if etree.QName(target).localname == "object":
            cells = [x for x in target if etree.QName(x).localname == "mxCell"]
            if not cells:
                raise ValueError("object has no native mxCell style target")
            target = cells[0]
        # For a node group, a fill/stroke is applied to its native shape rather
        # than fabricating CSS on a wrapper. Other allowed attributes are local.
        if etree.QName(target).localname == "g" and name in ("fill", "stroke"):
            glyphs = [x for x in target if etree.QName(x).localname in
                      ("rect", "ellipse", "circle", "polygon", "path", "line", "polyline")]
            if not glyphs:
                raise ValueError("target %s has no native glyph for %s" % (target_id, name))
            target = glyphs[0]
        target.set(name, str(value))
        method = "allowlisted native style"
    else:
        raise ValueError("unsupported edit kind %r" % kind)
    return {"id": str(target_id), "kind": kind, "value": str(value),
            "before": before, "method": method, "scope_ids": sorted(selected_scope(target))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input")
    parser.add_argument("--changes")
    parser.add_argument("--output")
    parser.add_argument("--check", help="re-verify a previously written edit proof")
    parser.add_argument("--preview", action="store_true", help="try faithful SVG rendering, no graph fallback")
    args = parser.parse_args()
    if args.check:
        with open(args.check, encoding="utf-8") as f:
            proof = json.load(f)
        if not proof.get("geometry_unchanged") or proof.get("non_target_nodes_changed"):
            print(json.dumps({"ok": False, "proof": args.check}, ensure_ascii=False))
            return 1
        print(json.dumps({"ok": proof.get("ok", False), "proof": args.check,
                          "geometry_unchanged": proof["geometry_unchanged"]}, ensure_ascii=False))
        return 0 if proof.get("ok") else 1
    if not (args.input and args.changes and args.output):
        parser.error("--input, --changes and --output are required")
    report = {"ok": False, "input": args.input, "output": args.output,
              "changes": [], "errors": [], "non_target_nodes_changed": [],
              "geometry_unchanged": False, "lxml": None}
    try:
        global etree
        import lxml.etree as etree_module
        globals()["etree"] = etree_module
        report["lxml"] = etree_module.__version__
        before_doc = parse(args.input)
        before_root = before_doc.getroot()
        before_ids, before_geometry, before_connections = document_fingerprint(before_root)
        with open(args.changes, encoding="utf-8") as f:
            specification = json.load(f)
        changes = specification if isinstance(specification, list) else specification.get("changes")
        if not isinstance(changes, list) or not changes:
            raise ValueError("changes[] must be a non-empty list")
        doc = parse(args.input)
        root = doc.getroot()
        scope = set()
        for change in changes:
            rec = apply_change(root, change)
            scope.update(rec.pop("scope_ids"))
            report["changes"].append(rec)
        after_ids, after_geometry, after_connections = document_fingerprint(root)
        report["non_target_nodes_changed"] = [ident for ident, digest in before_ids.items()
                                               if ident not in scope and after_ids.get(ident) != digest]
        report["geometry_unchanged"] = before_geometry == after_geometry
        report["connections_unchanged"] = before_connections == after_connections
        report["structure_unchanged"] = before_connections == after_connections
        if report["non_target_nodes_changed"]:
            report["errors"].append("non-target node changed: %s" % report["non_target_nodes_changed"])
        if not report["geometry_unchanged"] or not report["connections_unchanged"]:
            report["errors"].append("geometry/viewBox/topology differs after edit")
        # Only verified (or explicitly requested best-effort) data reaches output.
        if report["errors"]:
            raise ValueError("edit proof failed: " + "; ".join(report["errors"]))
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        # lxml preserves native structure; it is not an HTML save or raster overlay.
        xml = etree.tostring(root, encoding="UTF-8", xml_declaration=False, pretty_print=False)
        with open(args.input, "rb") as f:
            original = f.read()
        declaration = b""
        if original.startswith(b"<?xml"):
            declaration = original.split(b"?>", 1)[0] + b"?>\n"
        with open(args.output, "wb") as f:
            f.write(declaration + xml + b"\n")
        # Immediately reparse the real exported artifact to reject truncated XML.
        parse(args.output)
        report["native_export_parses"] = True
        report["ok"] = True
        if args.preview and parse(args.input).getroot().tag == SVG + "svg":
            preview = os.path.splitext(args.output)[0] + ".png"
            pdf = os.path.splitext(args.output)[0] + ".pdf"
            renderer = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_preview.py")
            done = subprocess.run([sys.executable, renderer, args.output, preview, pdf, ""],
                                  capture_output=True, text=True, timeout=300)
            report["preview"] = {"success": done.returncode == 0, "input": args.output,
                                 "stdout": done.stdout[-1000:], "stderr": done.stderr[-1000:]}
    except ImportError as e:
        report["errors"].append("lxml unavailable: %s; install in the development environment" % e)
    except subprocess.TimeoutExpired:
        report["errors"].append("faithful SVG preview timed out")
    except Exception as e:
        report["errors"].append(str(e))
    proof_path = os.path.splitext(args.output)[0] + "_edit_proof.json"
    os.makedirs(os.path.dirname(proof_path) or ".", exist_ok=True)
    with open(proof_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    report["proof"] = proof_path
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
