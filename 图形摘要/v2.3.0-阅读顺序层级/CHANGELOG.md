# 变更

相对 v1.3.0（attempt 74019，83/100）：补「版式与视觉层级」的阅读顺序与主结果面积。

- `SKILL.md`：面板按 question → methods → results → conclusion 的阅读顺序（从左到右、从上到下）排布；主结果占最大可用面积，让视觉重心落在发现上。
- `scripts/abstract.py`：新增校验——阅读顺序偏离四要素顺序时告警；主结果不是最大面板时告警（均为 warning，不阻断）。
