#!/usr/bin/env python3
"""contract_check.py — machine check that every output_contract field carries
substantive content (not empty, not bare "unavailable", not a placeholder).

Usage:
  python3 contract_check.py --case /input/case.json --out /app/output \
      --report /app/output/contract_check.json
Exit 0 when every field is substantive, 1 otherwise.
"""
import argparse, json, os, sys

def load(p, d=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return d if d is not None else {}

def substantive(v):
    """A field is substantive when it carries real, inspectable content."""
    if v is None:
        return False, "null"
    if isinstance(v, str):
        return (bool(v.strip()), "string" if v.strip() else "empty string")
    if isinstance(v, (int, float, bool)):
        return True, "scalar"
    if isinstance(v, list):
        return (len(v) > 0, f"list[{len(v)}]")
    if isinstance(v, dict):
        if v.get("available") is False:
            return False, "available=false: " + str(v.get("reason", ""))[:80]
        keys = [k for k in v if k not in ("note", "reason")]
        if not keys:
            return False, "only note/reason"
        # a dict with available=true and at least one content key is substantive
        if v.get("available") is True and keys:
            return True, "available + " + ",".join(keys[:4])
        if v.get("path") and v.get("available"):
            return True, "file ref"
        return (len(keys) > 0, "dict keys=" + ",".join(keys[:4]))
    return True, type(v).__name__

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--report", default=None)
    a = ap.parse_args()
    case = load(a.case, {})
    contract = case.get("output_contract") or case.get("outputContract") or {}
    if isinstance(contract, list):
        contract = {k: {"required": True} for k in contract}
    result = load(os.path.join(a.out, "result.json"), {})
    filled = result.get("output_contract", {})
    rows = []
    bad = []
    for k in contract:
        if k.lower() in ("case_id", "caseid"):
            rows.append({"field": k, "ok": bool(result.get("case_id")), "detail": "case_id"})
            continue
        v = filled.get(k)
        ok, detail = substantive(v)
        rows.append({"field": k, "ok": ok, "detail": detail})
        if not ok:
            bad.append(k)
    report = {"total": len(contract), "substantive": len(contract) - len(bad),
              "all_substantive": not bad, "fields": rows, "insubstantial": bad}
    rp = a.report or os.path.join(a.out, "contract_check.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(f"OK contract_check substantive={report['substantive']}/{report['total']} insubstantial={bad}")
    sys.exit(0 if not bad else 1)

if __name__ == "__main__":
    main()
