# CHANGELOG

## 2.0.2

- 单点迭代（父辈 v1.0 / attempt 85706 / 72.3333）：自检回修循环。
- 新增 `scripts/repair_loop.py`：selfcheck issues 驱动的定向回修（编号重排、自环/悬空删除、kind 归一、节点加宽、边距加大），写 `work/assets.repair/` 覆盖件而非改父版资产，预算 3 轮，证据落 `repair_report.json`。
- 针对父版「单遍流水线、自检未过无自动回修」短板（v1.0/SCORE.md 末节建议的 v2 方向）。
- 本地回归（regression_report.json）：注入自环+悬空+编号断档，selfcheck 由 8/11 自动修复到 11/11（actions：renumber/drop self-loop/drop dangling）。
- 其余管线脚本与父版 md5 一致，零改动。
