# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 107227 |
| 挑战赛 | `challenge-9034312d` — 实验装置与技术路线图 |
| 提交时间 | 2026-11-25T06:30Z（北京时间 2026-11-25 14:30） |
| 状态 | submitted（已提交，评分队列中） |
| 得分 | 未出分 |
| 包 sha256 | `9a199ba2b46d9dc92c754ec818d3175d4a01a8ed9b8cc10a016927278e20faf5` |
| 查询命令 | `playground status --attempt-id 107227` |

## 方向

契约语义填充。父版本 `v1.0`（attempt 85706，终分 72.3333）。

## 评分点

实际效果／任务完成度（15 分）+ 结果可核验性（5 分）：output_contract 每个字段都有实质、来源可追溯的内容。

## 父版本与本版单点改动

`v1.0`。本版只补它在这一评分点上的缺口：父版 pg_result.py 仅靠关键词匹配，11 字段契约 9 个被判 unavailable。

新增机制：contract_fill.py 回填失落字段为结构化清单，contract_check.py 逐字段机检。父版渲染/导出/自检四脚本 md5 与 v1.0 完全一致（资产守恒）。

## 本地检查前后

合成示例 `examples/example_ir.json`，非正式案例，不是正式案例答案。

检查命令：

```
python3 scripts/contract_fill.py --case case.json --work . --out out
python3 scripts/contract_check.py --case case.json --out out
```

| 版本 | 结果 |
|-|-|
| v1.0 | 父版 9 字段 no automatic mapping |
| 本版 | 新版全部回填，contract_check 11/11 |

回归证据见本目录 `regression_report.json`。
