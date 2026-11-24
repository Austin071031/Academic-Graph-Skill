# IR Schema：实体—连接—步骤—流向的结构化中间表示

IR（`ir.json`）是材料与图面之间的唯一中间表示：渲染、自检、来源核验全部基于 IR，保证"图上的每个元素能追溯回材料"。

## 顶层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| case_id | string | 与 case.json 一致 |
| diagram_type | enum | flowchart / tech_route / apparatus / chart |
| title | string | 图题（照录任务或材料中的正式名称） |
| source.materials[] | object | {path, version, locator} 本次用到的全部材料 |
| entities[] | object | 科学实体 |
| connections[] | object | 连接（物料/能量/信息/顺序/废料） |
| steps[] | object | 编号步骤 |
| layout | object | {type: auto/lr/tb/grid/chart, canvas: preset 名} |
| annotations[] | object | 附加标注 {target, text, source} |
| uncertainty[] | string | 不确定项清单 |
| chart | object | chart 模式的数据序列（真实数据） |

## entities[]

```json
{"id": "E1", "label": "原料气", "type": "material|unit|step|stage|instrument|product|waste",
 "glyph": "heater", "values": ["T=350 °C"], "x": 0, "y": 0,
 "source": {"material": "case.pdf", "locator": "p.3 第2段", "quote": "原料气经预热器升温至350 °C"}}
```

规则：`label` 用材料原名；`glyph` 仅 apparatus 模式且材料中有对应装置形态时给出（可选图元见 assets/glyphs/：pump, valve, vessel, condenser, heater, column, sensor, tank, exchanger, inlet, outlet）；`x/y` 为 grid 布局的列/行号（可选）。

## connections[]

```json
{"id": "C1", "from": "E1", "to": "E2", "kind": "material|energy|info|sequence|waste",
 "label": "预热后", "cycle": false, "confidence": "explicit|inferred",
 "source": {"material": "case.pdf", "locator": "p.3 第2段", "quote": "…"}}
```

规则：`from/to` 必须已在 entities 中定义；`kind` 决定线型与图例（material 实线蓝 / energy 虚线橙 / info 点线绿 / sequence 灰 / waste 点划灰）；方向只能来自材料文本；`confidence: inferred` 的边在图中以 55% 不透明度绘制并在 sources.md 中列出理由。

## steps[]

```json
{"id": "S1", "no": 1, "title": "预处理", "actor": "E2", "stage": "阶段一",
 "detail": "…", "source": {"material": "case.pdf", "locator": "§2.1"}}
```

规则：`no` 从 1 起连续，顺序与正文一致；`actor` 指向实体 id（该实体图上自动获得编号徽标）；tech_route 模式下相同 `stage` 的实体被绿色阶段带圈定。

## chart 模式

```json
{"diagram_type": "chart",
 "chart": {"x_label": "时间 (h)", "y_label": "转化率 (%)",
   "series": [{"id": "SER1", "label": "实验组A", "kind": "line", "data": [[0, 12.1], [1, 25.3]]}]}}
```

规则：`data` 必须是材料中的真实数值，逐点照录；缺测点省略并在 uncertainty 中说明，禁止插值编造。

## 自检对应关系

pg_check.py 的 10 项检查直接作用于本 schema：实体覆盖、悬空连接、方向、编号、图例、字体、溢出、画布、导出、六要素。IR 不合法时渲染脚本以非零退出并给出原因。
