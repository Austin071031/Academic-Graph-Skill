# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 107233 |
| 挑战赛 | `challenge-9034312d` — 实验装置与技术路线图 |
| 提交时间 | 2026-11-25T06:30Z（北京时间 2026-11-25 14:30） |
| 状态 | submitted（已提交，评分队列中） |
| 得分 | 未出分 |
| 包 sha256 | `9971482f4f7f35d0223082b78f228deb2c6e16dfe3511bce20daee51e570fde9` |
| 查询命令 | `playground status --attempt-id 107233` |

## 方向

自检回修循环。父版本 `v1.0`（attempt 85706，终分 72.3333）。

## 评分点

可靠体验／运行稳定性（4 分）+ 结果正确性：selfcheck 不过时自动定向修复，重复运行结果一致。

## 父版本与本版单点改动

`v1.0`。本版只补它在这一评分点上的缺口：父版单遍流水线，自检未过无自动回修。

新增机制：repair_loop.py 按 issue 类型最小定向修复（编号/自环/悬空/kind/加宽/边距），assets.repair 覆盖件不改父版资产。父版渲染/导出/自检四脚本 md5 与 v1.0 完全一致（资产守恒）。

## 本地检查前后

合成示例 `examples/example_ir.json`，非正式案例，不是正式案例答案。

检查命令：

```
python3 scripts/repair_loop.py --ir ir.json --skill . --work . --out out --rounds 3
```

| 版本 | 结果 |
|-|-|
| v1.0 | 注入自环+悬空+编号断档，selfcheck 8/11 |
| 本版 | 自动修复到 11/11（renumber/drop self-loop/drop dangling） |

回归证据见本目录 `regression_report.json`。
