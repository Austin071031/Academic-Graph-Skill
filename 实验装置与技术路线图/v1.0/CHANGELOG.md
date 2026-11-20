# CHANGELOG

## 1.1-v7-export

- 变体优化：导出规范强化（字体嵌入/300dpi/画布尺寸/投稿规格）（见 SKILL.md §0）。

## 1.0

- 初始完整版：五阶段流水线（IR 抽取 → SVG 渲染 → PNG/PDF 导出 → 10 项机器自检 → result.json 契约组装）。
- IR schema：实体—连接—步骤—流向结构化中间表示，逐要素 source.locator 溯源；inferred 要素降透明度显式区分。
- 布局：Sugiyama 最长路径分层 + 重心排序（lr/tb）、grid 装置布局、chart 坐标轴模式。
- 图元库：11 种装置 glyph（pump/valve/vessel/tank/column/exchanger/condenser/heater/sensor/inlet/outlet）。
- 导出：rsvg-convert → inkscape → cairosvg → chromium → matplotlib(meta 重渲染) 五级回退；export_report.json 记录后端与字体命中。
- 自检：实体覆盖、悬空连接、方向、编号、图例一致、字体、溢出、画布、导出、六要素共 10 项。
- 文档：SKILL.md、USAGE、IR_SCHEMA、LIMITATIONS、合成示例 example_ir.json。
  - 提交：playground attempt 85706（challenge-9034312d，实验装置与技术路线图）
