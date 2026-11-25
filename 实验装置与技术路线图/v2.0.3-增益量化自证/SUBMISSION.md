# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 107236 |
| 挑战赛 | `challenge-9034312d` — 实验装置与技术路线图 |
| 提交时间 | 2026-11-25T06:30Z（北京时间 2026-11-25 14:30） |
| 状态 | submitted（已提交，评分队列中） |
| 得分 | 未出分 |
| 包 sha256 | `ad427e9e9e2d5903ca07c0dfe27337d6e1b218118240e7f07bd3524442a11a78` |
| 查询命令 | `playground status --attempt-id 107236` |

## 方向

增益量化自证。父版本 `v1.0`（attempt 85706，终分 72.3333）。

## 评分点

使用增益（25 分）：质量增益、效率增益、增益可验证性的机器证据。

## 父版本与本版单点改动

`v1.0`。本版只补它在这一评分点上的缺口：父版无任何专门的使用增益证据文件。

新增机制：gain_card.py 计算自检通过率/溯源覆盖率/导出合规率/契约填充率/回修轮次，附基础Agent反事实缺陷对照。父版渲染/导出/自检四脚本 md5 与 v1.0 完全一致（资产守恒）。

## 本地检查前后

合成示例 `examples/example_ir.json`，非正式案例，不是正式案例答案。

检查命令：

```
python3 scripts/gain_card.py --case case.json --work . --out out
```

| 版本 | 结果 |
|-|-|
| v1.0 | 父版无增益证据 |
| 本版 | 生成 gain_card.json/md：selfcheck 11/11、trace 11/11、export 1.0、contract 11/11 |

回归证据见本目录 `regression_report.json`。
