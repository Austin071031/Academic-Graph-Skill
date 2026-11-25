# 变更

相对 v1.3.0（attempt 74019，83/100）：补齐「单位与条件标签」完整性。

- `SKILL.md`：每个数值标记、坐标轴和图例项必须携带实际单位与适用条件（物种、剂量、时间、处理、参照组）；比例尺仅在有效物校准时绘制，否则明确标注"not to scale"；最终交付前确认所有单位/条件/比例尺落在图面本身而非仅 sidecar。
- `scripts/charts.py`：bar/line/scatter/box/heatmap 的 x/y 轴标签为空时输出 `missing_axis_label_or_unit` 提示（needs_review，不阻断渲染）。
