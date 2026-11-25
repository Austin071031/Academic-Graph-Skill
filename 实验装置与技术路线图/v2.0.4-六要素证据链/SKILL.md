---
name: sci-apparatus-route-figure
description: 当任务要求依据科研输入材料（装置清单、论文方法段落、工艺描述、实验方案、case.json/task.md 中的绘图工单）生成或编辑实验装置图、工艺流程图、步骤流程图或技术路线图，并同时交付可编辑源文件（SVG）与导出件（PNG/PDF）时使用本 Skill。覆盖实体—连接—步骤—流向的结构化抽取、自动布图、图例与来源标注、导出校验与自检报告。不用于数据分析、数值拟合或论文排版。
---

# sci-apparatus-route-figure：实验装置与技术路线图的来源可溯科研绘图

> 本变体优化焦点：六要素证据链（结果完整性的逐项机检与证据落盘）


## 0. 本版本优化焦点：六要素证据链（实际效果／结果完整性 + 可核验性）

题面「结果完整性」要求覆盖六类要素：科学实体、空间关系、数据编码、图例标注、
可编辑源文件、导出格式。父版 pg_check 的 six_elements 只给粗粒度布尔判断
（「数据编码」近乎虚设，溯源缺失无从定位）。本版只改这一处：

1. **`elements_check.py`（阶段4c）**：逐项深度机检并出证据——
   科学实体（每个含 locator，缺失须 inferred+uncertainty）、空间关系（布局声明、
   无悬空/自环）、数据编码（数值表、kinds→线型映射、chart 真实点数）、
   图例标注（SVG 图例项==实际 kinds）、可编辑源文件（每实体 `<g id>`、文本可选、
   字体回退链）、导出格式（PNG 非空、PDF、CJK 命中）。
2. **证据落盘**：`elements_check.json` + `elements_evidence.md`，任一要素未满足即非零退出，
   缺失定位到具体要素，供 run_report.md/sources.md 直接引用。
3. **不放宽判据**：只把父版隐式假设显式化机检，不降低任何一项要求。

## 1. 用途与适用条件

把输入材料（PDF/文本/表格）中的**装置结构、工艺步骤、材料流向、技术路线阶段**转换为一张科学正确的图稿，并同时交付：

1. 可编辑分层源文件 `diagram.svg`（每个实体一个 `<g id="{IR实体id}">`，可在 Inkscape/Illustrator 中直接修改）；
2. 导出件 `diagram.png`（≈300 dpi）与 `diagram.pdf`；
3. 来源与修改记录 `sources.md`、`changes.md`、`run_report.md`、`selfcheck.json`、`export_report.json`、`result.json`。

适用：装置示意图、工艺流程图（PFD）、步骤流程图、技术路线图、基于来源数据的重绘图表（`diagram_type: chart`）。
不适用：数据分析与数值拟合、实验方案科学合理性判断、期刊排版格式适配——遇到此类要求应明确声明超出范围，不做越权推断。

## 2. 核心原则（正确性 backbone）

- **一切图面内容必须可溯源**：IR 中每个实体、连接、步骤都带 `source.locator`（文件名+页码/段落/图号）。无法定位的要素标 `confidence: "inferred"` 并在图中降低不透明度、在 `sources.md` 说明；**严禁凭常识补齐连接或反向推断流向**。
- **材料是事实依据**：先读 `/input/case.json`、`/input/task.md` 与实际材料文件，禁止依据题面标签假设内容。
- **诚实状态**：材料缺失、参数不明、导出失败分别说明；部分结果必须写明 `limits`，不得伪造软件状态或数据。
- **预算纪律**：64 次模型请求、900 秒。阶段化推进，每阶段落盘保存中间件（`ir.json` → `diagram.svg` → 导出 → 自检 → `result.json`），失败时可从最近中间件继续，不从头重跑。

## 3. 调用方式（五阶段流水线）

工作目录约定：中间件写 `/app/work/`，最终交付物写 `/app/output/`。脚本仅依赖 Python 3 标准库（matplotlib 仅作最后回退，评测环境另备 rsvg-convert/inkscape/cairosvg/chromium 后端）。

```bash
S=/skills/weekly-skill            # 以实际安装路径为准
W=/app/work ; O=/app/output
mkdir -p $W $O

# 阶段1 抽取：通读 /input/case.json、/input/task.md 与全部材料文件，
# 构造中间表示 ir.json（schema 见 docs/IR_SCHEMA.md；抽取规则见 §4）
#    阶段1结束即保存 $W/ir.json（部分结果早落盘）

# 阶段2 渲染：IR -> 分层 SVG + meta.json
python3 $S/scripts/pg_render.py --ir $W/ir.json --out $O/diagram.svg --meta $O/diagram.svg.meta.json

# 阶段3 导出：SVG -> PNG/PDF，自动选择可用后端并校验
python3 $S/scripts/pg_export.py --svg $O/diagram.svg --outdir $O --base diagram \
    --meta $O/diagram.svg.meta.json --ir $W/ir.json

# 阶段4 自检：机器核验 IR/SVG/导出件一致性，写 selfcheck.json
python3 $S/scripts/pg_check.py --ir $W/ir.json --svg $O/diagram.svg \
    --meta $O/diagram.svg.meta.json --export-report $O/export_report.json --out $O/selfcheck.json
# 任一检查失败：修复 ir.json 后重跑阶段2-4；若材料本身缺信息，写入 uncertainty 并继续

# 阶段4c 六要素深度机检（本版新增）：逐项完整性证据，缺项定位到具体要素
python3 $S/scripts/elements_check.py --ir $W/ir.json --out $O --report $O/elements_check.json

# 阶段5 汇总：按 case.json output_contract 逐字段组装 result.json（缺失字段标 unavailable+原因，绝不丢弃字段）
python3 $S/scripts/pg_result.py --case /input/case.json --work $W --out $O --skill-version 1.0
```

随后人工撰写（基于真实运行结果，不虚构）：
- `$O/sources.md`：逐要素来源表（实体 id → 材料 → 版本 → 定位 → 原文摘录）；
- `$O/changes.md`：本 case 的修改/判断记录（含 inferred 要素及理由）；
- `$O/run_report.md`：阶段耗时、后端选择、自检结果、限制。

## 4. IR 抽取规则（实体—连接—步骤—流向）

1. **实体 `entities[]`**：`id`（稳定代号 E1..）、`label`（材料中的原名，不改写）、`type`（material/unit/step/stage/instrument/product/waste）、`glyph`（可选，装置图元名，见 assets/glyphs/）、`values[]`（材料中的关键数值，如 "T=350°C"）、`source`。
2. **连接 `connections[]`**：`from/to` 必须是实体 id；`kind` 按材料语义取 material/energy/info/sequence/waste——**物料流向与信息流必须区分**，能量（加热/冷却/电力）用 energy；`cycle: true` 标记回流；方向**只能取自材料描述**（"A 进入 B" ⇒ A→B），描述含糊时标 `confidence: inferred`。
3. **步骤 `steps[]`**：`no` 从 1 连续编号且与正文顺序一致；`actor` 指向执行该步骤的实体；`stage` 标记技术路线阶段（tech_route 模式自动画阶段带）。
4. **图面约束**：`layout.type`（auto/lr/tb/grid/chart）、画布预设（single_column 85mm / double_column 170mm / slide_16x9）。
5. **图表 `chart`**：`diagram_type: chart` 时提供 `series[]`（真实来源数据点，禁止编造或改动数值）、`x_label/y_label`。

## 5. 异常处理（识别→处置→记录）

| 情况 | 处置 |
|---|---|
| 部件参数缺失 | 图中该实体不标数值；ir.uncertainty 记录；sources.md 说明 |
| 工艺描述歧义/接口冲突 | 不擅自裁决：按最保守语义抽取，标 confidence=inferred，changes.md 记录冲突与取舍 |
| CJK 字体缺失 | pg_export 经 fc-list 探测，自动选择已装中文字体；SVG 内保留字体回退链，导出报告记录所用字体 |
| 导出后端全部失败 | 依次尝试 rsvg-convert/inkscape/cairosvg/chromium/matplotlib 后仍失败 ⇒ result.json 声明 partial，保留 SVG 源文件，绝不伪造 PNG |
| 画布溢出 | pg_check 的 canvas_bounds/text_overflow 检出后增大预设或缩短标签重渲染 |
| 材料文件无法解析 | 如实报告 unreadable 与已尝试手段；不根据文件名猜测内容 |

## 6. 最小调用示例

```bash
python3 /skills/weekly-skill/scripts/pg_render.py \
  --ir /app/work/ir.json --out /app/output/diagram.svg \
  --meta /app/output/diagram.svg.meta.json
```

示例 IR 见 `examples/example_ir.json`（**合成示例，仅示意接口，非任何正式案例的答案**）；示例输出请在真实案例上运行后自行生成。

## 7. 限制

- 不评估方案科学合理性；图中数值一律照录材料，不做单位换算以外的加工。
- 自动布局面向清晰度而非美术效果；装置复杂时可改用 grid 布局手工指定行列。
- 文档、图元库、IR schema 与脚本版本对应关系见 CHANGELOG.md。
