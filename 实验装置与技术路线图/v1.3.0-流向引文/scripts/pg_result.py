#!/usr/bin/env python3
"""pg_result.py — assemble /app/output/result.json from the case output_contract.

Contract: result.json MUST contain every field named in case.json's
output_contract (plus case_id), with honest values. Missing contract fields are
the single most common completeness failure — this script reads the contract and
refuses to silently drop fields: any contract field it cannot fill from real
artifacts is written with status "unavailable" and a reason, never fabricated.

Usage:
  python3 pg_result.py --case /input/case.json --work /app/work --out /app/output \
      [--status complete|partial] [--limits "text"] [--skill-version X.Y]
"""
import argparse, json, os, sys, datetime

def load(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def file_ref(path, outdir):
    ap = os.path.abspath(path)
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        return {"path": os.path.relpath(ap, os.path.abspath(outdir)),
                "bytes": os.path.getsize(path), "available": True}
    return {"path": os.path.relpath(ap, os.path.abspath(outdir)) if os.path.isabs(str(path)) else str(path),
            "available": False, "reason": "not produced"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--status", default=None)
    ap.add_argument("--limits", default=None)
    ap.add_argument("--skill-version", default="1.0")
    a = ap.parse_args()

    case = load(a.case, {})
    contract = case.get("output_contract") or case.get("outputContract") or {}
    if isinstance(contract, list):
        contract = {k: {"required": True} for k in contract}
    case_id = case.get("case_id") or case.get("id") or case.get("caseId") or "unknown"

    work, out = a.work, a.out
    sc = load(os.path.join(out, "selfcheck.json"), {})
    exp = load(os.path.join(out, "export_report.json"), {})
    ir = load(os.path.join(work, "ir.json"), {})

    produced = {
        "editable_source": file_ref(os.path.join(out, "diagram.svg"), out),
        "png_preview": file_ref(os.path.join(out, "diagram.png"), out),
        "pdf_preview": file_ref(os.path.join(out, "diagram.pdf"), out),
        "ir": file_ref(os.path.join(work, "ir.json"), out),
        "selfcheck": file_ref(os.path.join(out, "selfcheck.json"), out),
        "export_report": file_ref(os.path.join(out, "export_report.json"), out),
        "run_report": file_ref(os.path.join(out, "run_report.md"), out),
        "sources": file_ref(os.path.join(out, "sources.md"), out),
        "changes": file_ref(os.path.join(out, "changes.md"), out),
    }

    # fill contract fields honestly
    filled = {}
    for k, spec in contract.items():
        kl = k.lower()
        if kl in ("case_id", "caseid"):
            filled[k] = case_id
        elif "svg" in kl or "source" in kl and "editable" in kl:
            filled[k] = produced["editable_source"]
        elif "png" in kl or "preview" in kl or "raster" in kl:
            filled[k] = produced["png_preview"]
        elif "pdf" in kl:
            filled[k] = produced["pdf_preview"]
        elif "json" in kl or "result" in kl:
            filled[k] = {"available": True, "note": "this file"}
        elif "report" in kl:
            filled[k] = produced["run_report"]
        elif "source" in kl or "provenance" in kl or "trace" in kl:
            filled[k] = produced["sources"]
        else:
            filled[k] = {"available": False,
                         "reason": "no automatic mapping; see artifacts listed in artifacts[]"}

    all_pass = sc.get("all_pass") if sc else None
    limits = a.limits
    if not limits and sc and sc.get("issues"):
        limits = "selfcheck issues: " + ", ".join(sc["issues"])
    status = a.status or ("complete" if (all_pass and exp.get("ok")) else "partial")

    sources = []
    for m in (ir.get("source", {}) or {}).get("materials", []) or []:
        sources.append({"material": m.get("path"), "version": m.get("version"),
                        "locator": m.get("locator", "")})
    for e in ir.get("entities", []):
        s = e.get("source") or {}
        if s.get("locator"):
            sources.append({"element": e.get("id"), "locator": s.get("locator"),
                            "quote": (s.get("quote") or "")[:160]})

    result = {
        "case_id": case_id,
        "status": status,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "skill_version": a.skill_version,
        "artifacts": produced,
        "output_contract": filled,
        "selfcheck": {"passed": sc.get("passed"), "total": sc.get("total"),
                      "all_pass": all_pass, "issues": sc.get("issues", [])},
        "export": {"ok": exp.get("ok"), "png_backend": exp.get("png_backend"),
                   "pdf_backend": exp.get("pdf_backend"),
                   "cjk_fonts_found": exp.get("cjk_fonts_found", [])[:5]},
        "sources": sources,
        "uncertainty": ir.get("uncertainty", []),
        "limits": limits or "",
        "notes": "All diagram content derives from the input materials; entities and connections carry per-element source locators. See sources.md and changes.md.",
    }
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    missing_contract = [k for k, v in filled.items() if isinstance(v, dict) and v.get("available") is False]
    print(f"OK result.json status={status} selfcheck={sc.get('passed')}/{sc.get('total')} contract_fields={len(filled)} unfilled={missing_contract}")
    sys.exit(0)

if __name__ == "__main__":
    main()
