#!/usr/bin/env python3
"""make_result.py — assemble result.json using the original output_contract.

Usage: make_result.py /app/work /app/output
Call once before validate.py (provisional result) and once after validate.py
(final result), so no report describes an older file manifest or check status.
"""
import json
import os
import re
import sys
import datetime

FILE_EXTENSIONS = {"svg", "png", "pdf", "csv", "json", "md", "txt", "drawio",
                   "jpg", "jpeg", "xlsx", "pptx", "html", "xml"}
CONTRACT_EXTENSION = {"draw.io": "drawio", "jpeg": "jpg"}


def contract_file_entries(contract):
    """Normalize dict/list contract entries as (name, expected_path, required).

    Expected path is set only for explicit file declarations. Scalar structured
    fields retain their values from run_state.json, not fabricated filenames.
    """
    if isinstance(contract, dict):
        raw = list(contract.items())
    elif isinstance(contract, list):
        raw = []
        for item in contract:
            if isinstance(item, str):
                raw.append((item, "file"))
            elif isinstance(item, dict):
                name = item.get("name") or item.get("field") or item.get("key") or item.get("id")
                if name:
                    raw.append((name, item))
    else:
        raw = []
    entries = []
    for name, spec in raw:
        if isinstance(spec, str):
            explicit = None
            required = spec.lower() not in ("optional", "none")
            is_file = spec.lower() in ("file", "path", "artifact")
        elif isinstance(spec, dict):
            typ = str(spec.get("type", spec.get("kind", ""))).lower()
            location = spec.get("path", spec.get("file", spec.get("filename")))
            explicit = location if isinstance(location, str) else None
            required = spec.get("required") is not False and not spec.get("optional", False)
            is_file = typ in ("file", "path", "artifact") or bool(explicit)
        else:
            continue
        if not is_file:
            continue
        expected = explicit or expected_filename(name)
        entries.append((name, expected, required))
    return entries


def expected_filename(name):
    """Convert common contract keys to a full basename, never a prefix match."""
    text = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
    words = [w for w in text.split("_") if w]
    if words and words[-1] in ("file", "path", "artifact"):
        words.pop()
    if words and words[-1] in FILE_EXTENSIONS:
        ext = CONTRACT_EXTENSION.get(words[-1], words[-1])
        stem = "_".join(words[:-1])
        return (stem + "." + ext) if stem else None
    # Some contracts use editable_svg_map rather than a trailing extension.
    for i, word in enumerate(words):
        ext = CONTRACT_EXTENSION.get(word, word)
        if ext in FILE_EXTENSIONS and i > 0:
            stem = "_".join(words[:i])
            return stem + "." + ext
    return None


def resolve_file_field(name, expected, files):
    """Return an existing output basename or an existing explicit relative path.

    A declared format/path wins. No resolution ever returns another extension.
    """
    basenames = {f["path"] for f in files}
    if expected:
        clean = os.path.normpath(expected).replace("\\", "/").lstrip("/")
        if clean in basenames:
            return clean
        # A few contracts prefix output/ although the argument is output itself.
        if clean.startswith("output/") and clean[len("output/"):] in basenames:
            return clean[len("output/"):]
        return None
    if name in basenames:
        return name
    return None


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else "/app/work"
    out = sys.argv[2] if len(sys.argv) > 2 else "/app/output"
    brief = {}
    bp = os.path.join(work, "brief.json")
    if os.path.exists(bp):
        brief = json.load(open(bp, encoding="utf-8"))
    state = {}
    sp = os.path.join(work, "run_state.json")
    if os.path.exists(sp):
        state = json.load(open(sp, encoding="utf-8"))
    check = {}
    cp = os.path.join(out, "check_report.json")
    if os.path.exists(cp):
        try:
            check = json.load(open(cp, encoding="utf-8"))
        except Exception:
            pass
    files = []
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        if os.path.isfile(p):
            files.append({"path": f, "bytes": os.path.getsize(p),
                          "role": state.get("file_roles", {}).get(f, "artifact")})
    result = {
        "case_id": brief.get("case_id"),
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "main_results": state.get("main_results", {}),
        "sources": state.get("sources", []),
        "uncertainty": state.get("uncertainty", []),
        "change_log": state.get("change_log", []),
        "artifacts": files,
        "validation": {"ok": check.get("ok"), "hard_failures": check.get("hard_failures"),
                       "warnings": check.get("warnings"), "report": "check_report.json"},
    }
    values = state.get("contract_fields", {})
    if isinstance(brief.get("output_contract"), dict):
        raw_items = brief["output_contract"].items()
    elif isinstance(brief.get("output_contract"), list):
        raw_items = [(x.get("name"), x) for x in brief["output_contract"]
                     if isinstance(x, dict) and x.get("name")]
    else:
        raw_items = []
    for key, spec in raw_items:
        if key not in result and not (isinstance(spec, str) and spec.lower() in ("file", "path", "artifact")):
            result[key] = values.get(key)
    for key, expected, _ in contract_file_entries(brief.get("output_contract")):
        resolved = resolve_file_field(key, expected, files)
        if resolved is not None:
            result[key] = resolved
        elif key not in result:
            result[key] = values.get(key)
    status = state.get("status") or ("complete" if check and check.get("ok") else "partial")
    if check and not check.get("ok"):
        status = "partial"
    result["status"] = status
    rp = os.path.join(out, "result.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": True, "result": rp, "status": status,
                      "fields": sorted(result.keys())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
