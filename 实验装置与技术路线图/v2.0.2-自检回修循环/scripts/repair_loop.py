#!/usr/bin/env python3
"""repair_loop.py — selfcheck-driven targeted re-render loop.

父版是单遍流水线：pg_check 检出 text_overflow / canvas_bounds / numbering_order /
direction_sanity / connection_dangling 等问题后只能人工改 IR 重跑。本版把这一步自动化：
按 selfcheck.json 的 issues 类型执行**最小定向修复**，重渲染并复检，直到全过或预算耗尽。

修复原则（不改渲染器与检查器，只改它们的输入）：
  numbering_order    -> steps.no 按原顺序重排为 1..N（改 IR）
  direction_sanity   -> 删除 from==to 自环连接，记 uncertainty（改 IR）
  connection_dangling-> 删除端点不存在的连接，记 uncertainty（改 IR）
  legend_consistency -> 非法 kind 归一到 material（改 IR）
  text_overflow      -> assets.repair/templates.json 节点 width 逐轮 +48（覆盖件，不动父版资产）
  canvas_bounds      -> assets.repair/templates.json margin 逐轮 +24（覆盖件）
每轮把修复动作、前后 issue 数写入 repair_report.json；预算默认 3 轮。

Usage:
  python3 repair_loop.py --ir /app/work/ir.json --skill /skills/weekly-skill \
      --work /app/work --out /app/output [--rounds 3]
"""
import argparse, json, os, shutil, subprocess, sys

def load(p, d=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return d if d is not None else {}

def save(p, o):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=1)

def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ir", required=True)
    ap.add_argument("--skill", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rounds", type=int, default=3)
    a = ap.parse_args()
    S, W, O = a.skill, a.work, a.out
    ir_p = os.path.join(W, "ir.json")
    assets_repair = os.path.join(W, "assets.repair")
    history = []

    # start from the caller's current ir.json (copy to a working repair file)
    cur_ir = load(ir_p, {})
    steps = sorted(cur_ir.get("steps", []), key=lambda s: s.get("no", 1 << 30))

    def check(assets):
        sh(["python3", os.path.join(S, "scripts/pg_render.py"), "--ir", ir_p,
            "--out", os.path.join(O, "diagram.svg"), "--meta", os.path.join(O, "diagram.svg.meta.json"),
            "--assets", assets])
        exp = os.path.join(O, "export_report.json")
        r = sh(["python3", os.path.join(S, "scripts/pg_check.py"), "--ir", ir_p,
                "--svg", os.path.join(O, "diagram.svg"), "--meta", os.path.join(O, "diagram.svg.meta.json"),
                "--export-report", exp, "--out", os.path.join(O, "selfcheck.json")])
        sc = load(os.path.join(O, "selfcheck.json"), {})
        return sc

    base_assets = os.path.join(S, "assets")
    sc = check(base_assets)
    history.append({"round": 0, "issues": sc.get("issues", []), "passed": sc.get("passed"), "total": sc.get("total")})

    width_boost = 0
    margin_boost = 0
    for rnd in range(1, a.rounds + 1):
        if sc.get("all_pass"):
            break
        issues = sc.get("issues", [])
        ir = load(ir_p, {})
        actions = []
        # IR-level structural repairs
        if "numbering_order" in issues:
            for i, s in enumerate(sorted(ir.get("steps", []), key=lambda s: s.get("no", 1 << 30)), 1):
                s["no"] = i
            actions.append("renumber steps 1..N")
        if "direction_sanity" in issues:
            before = len(ir.get("connections", []))
            ir["connections"] = [c for c in ir.get("connections", []) if c.get("from") != c.get("to")]
            if len(ir["connections"]) != before:
                actions.append(f"drop {before - len(ir['connections'])} self-loop edges")
                ir.setdefault("uncertainty", []).append("自环连接已按自检移除（材料未给出合法两端）")
        if "connection_dangling" in issues:
            ids = {e.get("id") for e in ir.get("entities", [])}
            before = len(ir.get("connections", []))
            ir["connections"] = [c for c in ir.get("connections", []) if c.get("from") in ids and c.get("to") in ids]
            if len(ir["connections"]) != before:
                actions.append(f"drop {before - len(ir['connections'])} dangling edges")
                ir.setdefault("uncertainty", []).append("悬空连接（端点未定义）已按自检移除")
        if "legend_consistency" in issues:
            legal = {"material", "energy", "info", "sequence", "waste"}
            for c in ir.get("connections", []):
                if c.get("kind", "material") not in legal:
                    c["kind"] = "material"
            actions.append("normalize illegal edge kinds")
        # asset-overlay repairs for sizing issues
        need_assets = False
        if "text_overflow" in issues:
            width_boost += 48
            need_assets = True
            actions.append(f"node width +{width_boost}")
        if "canvas_bounds" in issues:
            margin_boost += 24
            need_assets = True
            actions.append(f"canvas margin +{margin_boost}")
        if need_assets:
            os.makedirs(assets_repair, exist_ok=True)
            for fn in os.listdir(base_assets):
                shutil.copy(os.path.join(base_assets, fn), os.path.join(assets_repair, fn))
            tp = os.path.join(assets_repair, "templates.json")
            tpl = load(tp, {})
            nd = tpl.setdefault("node_defaults", {})
            nd["width"] = nd.get("width", 120) + (48 if "text_overflow" in issues else 0)
            nd["margin"] = nd.get("margin", 40) + (24 if "canvas_bounds" in issues else 0)
            save(tp, tpl)
            # glyphs subdir
            if os.path.isdir(os.path.join(base_assets, "glyphs")):
                shutil.copytree(os.path.join(base_assets, "glyphs"), os.path.join(assets_repair, "glyphs"), dirs_exist_ok=True)
        save(ir_p, ir)
        sc = check(assets_repair if need_assets or os.path.isdir(assets_repair) else base_assets)
        history.append({"round": rnd, "actions": actions, "issues": sc.get("issues", []),
                        "passed": sc.get("passed"), "total": sc.get("total")})
        if not actions:
            break

    rep = {"baseline": history[0], "final": history[-1], "rounds": history[1:],
           "all_pass": bool(history[-1].get("issues") == []),
           "improved": (history[-1].get("passed", 0) > history[0].get("passed", 0)) or
                       (history[-1].get("issues") == [] and history[0].get("issues"))}
    save(os.path.join(O, "repair_report.json"), rep)
    print(f"OK repair_loop baseline={history[0]['passed']}/{history[0]['total']} "
          f"final={history[-1]['passed']}/{history[-1]['total']} issues={history[-1]['issues']}")
    sys.exit(0 if history[-1].get("issues") == [] else 1)

if __name__ == "__main__":
    main()
