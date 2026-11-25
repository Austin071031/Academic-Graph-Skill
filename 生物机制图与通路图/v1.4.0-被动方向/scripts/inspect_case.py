#!/usr/bin/env python3
"""inspect_case.py — preflight: parse /input/case.json + /input/task.md into work/brief.json.

Stdlib only. Never crashes the run: on any failure it writes a brief with
status "degraded" and an explicit reason so the agent can proceed manually.
"""
import json, os, sys, glob

def read_json(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return json.load(f)

def read_text(path, limit=200000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except Exception:
        return ""

def main():
    inp = sys.argv[1] if len(sys.argv) > 1 else "/input"
    work = sys.argv[2] if len(sys.argv) > 2 else "/app/work"
    os.makedirs(work, exist_ok=True)
    brief = {"status": "ok", "input_dir": inp, "notes": []}

    case_path = os.path.join(inp, "case.json")
    task_path = os.path.join(inp, "task.md")
    case = {}
    if os.path.exists(case_path):
        try:
            case = read_json(case_path)
        except Exception as e:
            brief["status"] = "degraded"
            brief["notes"].append("case.json parse failed: %s" % e)
    else:
        brief["status"] = "degraded"
        brief["notes"].append("case.json not found in %s" % inp)

    brief["case_id"] = case.get("case_id") or case.get("id") or os.path.basename(inp)
    oc = case.get("output_contract")
    if isinstance(oc, dict):
        brief["output_contract"] = oc
        brief["required_fields"] = sorted(oc.keys())
    elif isinstance(oc, list):
        brief["output_contract"] = oc
        brief["required_fields"] = [x.get("name", str(x)) if isinstance(x, dict) else str(x) for x in oc]
    else:
        brief["output_contract"] = None
        brief["required_fields"] = []
        brief["notes"].append("no output_contract in case.json; read task.md for deliverables")

    # task.md (required context)
    if os.path.exists(task_path):
        brief["task_md_chars"] = os.path.getsize(task_path)
    else:
        brief["notes"].append("task.md not found")

    # materials: everything else in /input
    mats = []
    for p in sorted(glob.glob(os.path.join(inp, "**", "*"), recursive=True)):
        if os.path.isfile(p) and os.path.basename(p) not in ("case.json", "task.md"):
            mats.append({"path": p, "bytes": os.path.getsize(p)})
    brief["materials"] = mats
    pdfs = [m for m in mats if m["path"].lower().endswith(".pdf")]
    brief["pdf_materials"] = len(pdfs)

    with open(os.path.join(work, "brief.json"), "w", encoding="utf-8") as f:
        json.dump(brief, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": True, "case_id": brief["case_id"],
                      "required_fields": brief["required_fields"],
                      "materials": len(mats), "pdfs": len(pdfs),
                      "status": brief["status"], "notes": brief["notes"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
