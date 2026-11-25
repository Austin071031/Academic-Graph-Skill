# 使用说明（USAGE）

## 快速开始

1. 读 `/input/case.json` 与 `/input/task.md`，确认任务要求、输出契约（`output_contract`）与材料清单。
2. 通读全部材料文件（PDF 用平台 pdf-text-tool 解析；**读原文，不用预提取答案层**）。
3. 按 SKILL.md §4 构造 `/app/work/ir.json`（参照 `docs/IR_SCHEMA.md`；最小示例见 `examples/example_ir.json`）。
4. 依次运行 SKILL.md §3 五阶段命令；每阶段产物落盘。
5. 检查 `selfcheck.json`：全过 ⇒ `result.json` 状态 complete；有未过项 ⇒ 修复或如实记录 limits 后以 partial 交付。

## 输入约定

- case 输入：`/input/case.json`（含 `case_id`、`output_contract`、材料路径）；任务说明：`/input/task.md`；材料：PDF/文本/表格。
- IR 输入：`entities/connections/steps/layout/chart`，schema 见 docs/IR_SCHEMA.md。
- 字体：SVG 使用回退链（Noto Sans CJK SC → Source Han Sans SC → WenQuanYi → SimHei → Microsoft YaHei → sans-serif）；导出时用 fc-list 探测并记录实际命中字体。

## 输出解释

| 文件 | 内容 |
|---|---|
| diagram.svg | 分层可编辑源文件：layer-edges / layer-entities / layer-legend / layer-stages，实体 `<g id>` 与 IR id 一致 |
| diagram.svg.meta.json | 布局元数据（节点盒、边、图例项、画布范围），自检与回退导出使用 |
| diagram.png / diagram.pdf | 导出件；export_report.json 记录后端、字节数、字体命中 |
| selfcheck.json | 10 项机器检查结果（pass/fail + 证据） |
| result.json | 按 output_contract 逐字段填充；status / sources / uncertainty / limits |
| sources.md / changes.md / run_report.md | 来源表、修改记录、运行报告（人工撰写，须与真实运行一致） |

## 失败处理与自查

- 渲染退出码 2：IR 缺失或为空 ⇒ 检查 entities 是否抽出。
- 导出退出码 3：全部后端失败 ⇒ 检查 export_report.json attempts 列表；仍失败则以 partial 交付 SVG。
- 自检退出码 1：查看 issues 数组逐项修复；材料原因无法修复的写入 uncertainty。
- 复跑安全性：脚本幂等，覆盖写产物；改 IR 后从阶段2重跑即可。

## 版本与维护

- 版本号见 assets/config.json 与 CHANGELOG.md；脚本与文档同版本发布。
- 已知限制见 docs/LIMITATIONS.md。
