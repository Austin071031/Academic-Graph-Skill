#!/usr/bin/env python3
"""make_result.py — assemble /app/output/result.json with full honesty fields.

Merges: case_id + output_contract fields from work/brief.json,
status/sources/uncertainty/change_log from work/run_state.json (written by the
agent during the run), and a manifest of delivered files. Refuses to claim
"complete" when validate.py has hard failures.
Usage: make_result.py /app/work /app/output
"""
import json, os, sys, datetime

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
    status = state.get("status") or ("complete" if check.get("ok") else "partial")
    if check and not check.get("ok"):
        status = "partial"
    result = {
        "case_id": brief.get("case_id"),
        "status": status,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "main_results": state.get("main_results", {}),
        "sources": state.get("sources", []),
        "uncertainty": state.get("uncertainty", []),
        "change_log": state.get("change_log", []),
        "artifacts": files,
        "validation": {"ok": check.get("ok"), "hard_failures": check.get("hard_failures", -1),
                       "warnings": check.get("warnings", -1),
                       "report": "check_report.json"},
    }
    oc = brief.get("output_contract")
    if isinstance(oc, dict):
        for k, spec in oc.items():
            if k in result:
                continue
            if isinstance(spec, str) and spec.lower() in ("file", "path", "artifact"):
                match = [f["path"] for f in files if k.split("_")[0] in f["path"].lower()]
                result[k] = match[0] if match else None
            else:
                result[k] = state.get("contract_fields", {}).get(k)
    rp = os.path.join(out, "result.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": True, "result": rp, "status": status, "fields": sorted(result.keys())}, ensure_ascii=False))

if __name__ == "__main__":
    main()
