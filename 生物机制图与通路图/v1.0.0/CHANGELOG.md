# CHANGELOG

## 1.0.0
- 首版：六步流水线（预检/抽取/结构化/lint/渲染/导出/核验/result.json）。
- 确定性 SVG 渲染：区室分层、SBGN 风格端点（arrow/T-bar/P/Ub 标记）、证据强度线型、
  图例由同一编码表派生。
- draw.io 同名分层导出；图表 SVG+CSV（series 强制来源）。
- validate.py：XML/出处/图例覆盖/合同字段/预览五类核验。
- failure_playbook：10 类异常处置；预算纪律与最小路径。
\n## 变体说明\n- 本变体在 1.0.0 基座上强化特定评分维度（见 SKILL.md「本变体优化重点」）。
  - 提交：playground attempt 85718（challenge-83d4f050，生物机制图与通路图）
