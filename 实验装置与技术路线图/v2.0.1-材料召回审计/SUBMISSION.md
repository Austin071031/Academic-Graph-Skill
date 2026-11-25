# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 107228 |
| 挑战赛 | `challenge-9034312d` — 实验装置与技术路线图 |
| 提交时间 | 2026-11-25T06:30Z（北京时间 2026-11-25 14:30） |
| 状态 | submitted（已提交，评分队列中） |
| 得分 | 未出分 |
| 包 sha256 | `a81c2c35c0877b7f13c84eb5cdb02b8812292c4a03852fde0647ebfd7948a958` |
| 查询命令 | `playground status --attempt-id 107228` |

## 方向

材料召回审计。父版本 `v1.0`（attempt 85706，终分 72.3333）。

## 评分点

实际效果／结果正确性（15 分）：图中实体/连接/步骤逐项可追溯到材料，漏画被机器检出。

## 父版本与本版单点改动

`v1.0`。本版只补它在这一评分点上的缺口：父版案例运行时材料实体/连接/步骤召回不足，漏图但渲染/导出/自检仍正确。

新增机制：recall_audit.py 以材料原文抽取装置/连接/步骤候选，与 IR 比对，遗漏非零退出。父版渲染/导出/自检四脚本 md5 与 v1.0 完全一致（资产守恒）。

## 本地检查前后

合成示例 `examples/example_ir.json`，非正式案例，不是正式案例答案。

检查命令：

```
python3 scripts/recall_audit.py --ir ir.json --materials 材料目录 --report recall_report.json
```

| 版本 | 结果 |
|-|-|
| v1.0 | 洁净例零误报 exit 0 |
| 本版 | 含未收录装置(冷凝器/储罐) exit 1 列出；IR漏步骤3 exit 1 列出 |

回归证据见本目录 `regression_report.json`。
