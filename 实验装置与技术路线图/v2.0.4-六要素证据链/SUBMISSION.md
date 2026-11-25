# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 107237 |
| 挑战赛 | `challenge-9034312d` — 实验装置与技术路线图 |
| 提交时间 | 2026-11-25T06:30Z（北京时间 2026-11-25 14:30） |
| 状态 | submitted（已提交，评分队列中） |
| 得分 | 未出分 |
| 包 sha256 | `edf95ec4473ab02aa551b7cbb74ca07d7ed1a66ec23c17b01a268478fe34873a` |
| 查询命令 | `playground status --attempt-id 107237` |

## 方向

六要素证据链。父版本 `v1.0`（attempt 85706，终分 72.3333）。

## 评分点

实际效果／结果完整性（5 分）+ 可核验性（5 分）：六类要素逐项机检出证据。

## 父版本与本版单点改动

`v1.0`。本版只补它在这一评分点上的缺口：父版 pg_check 的 six_elements 粗粒度，完整性缺口无从定位。

新增机制：elements_check.py 逐项深度机检六要素（实体locator/空间关系/数据编码/图例/可编辑/导出）。父版渲染/导出/自检四脚本 md5 与 v1.0 完全一致（资产守恒）。

## 本地检查前后

合成示例 `examples/example_ir.json`，非正式案例，不是正式案例答案。

检查命令：

```
python3 scripts/elements_check.py --ir ir.json --out out --report elements_check.json
```

| 版本 | 结果 |
|-|-|
| v1.0 | 完整产物六要素全过 exit 0 |
| 本版 | 去除实体locator检出「1_科学实体」exit 1 |

回归证据见本目录 `regression_report.json`。
