# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | **107308** |
| 版本 | v2.0.0-误差含义源列绑定 |
| 挑战赛 | `challenge-1bd90d8a` — 科研数据图表生成与编辑 |
| 提交时间 | 2026-11-25T06:45:54+00:00 |
| 状态 | submitted（queued，平台已接受，未出分） |
| 得分 | 待出分（不预测分数） |
| 查询命令 | `playground status --attempt-id 107308` |

## 父版与唯一改动

父版为当前最高已出分版本 `v1.2.0-图例系列绑定`（attempt 103638，终分 73.3333）。本版仅增加误差含义源列绑定与独立校验：保留父版的图例文字/颜色绑定，不把误差类型写入图例文字。

对应题面正确性检查中的“误差线含义”，以及来源映射与标注复核。此对应关系是评分细则推导，不是官方分项扣分记录。

## 合成回归（非官方案例）

源表含义列为 `SD`，规格手工含义为 `SEM (wrong)`。父版只采用手工含义、没有独立误差含义原生标注；新版在 `panel-0-series-0-error-kind` 显示 `Error: SD`，保留图例 `Control/#0072B2`。

执行并通过：

```bash
python3 scripts/charts.py render --spec spec.json --out out
python3 scripts/check_error_kind.py --spec spec.json --svg out/figure.svg --map out/source_map.json --out out/error_kind_checks.json
python3 scripts/check_legend_series.py --spec spec.json --svg out/figure.svg
python3 scripts/verify_sources.py --map out/source_map.json --out out/source_checks.json
```

代码对缺列、空值或不一致含义明确报错；此失败语义为代码级检查，未单独冒充官方案例结果。未宣称任何官方成绩提升。2026-11-25 的完整五版测试共执行 22 项命令，全部通过。

## 实际提交证据

2026-11-25T06:45:54+00:00 通过 playground CLI 0.1.58 正式提交，平台返回 Attempt **107308**、状态 `submitted`、评分 `queued`。`bundle_sha256=eadb1bf8d9895e4c99a019eae3c38729e48626bf8c20c4c4b13460f93d01ed46`。通过 dry-run 验证的 `SKILL.md` 与脚本与实际提交包一致；此处仅追加提交追溯记录，待平台出分后再回填，不预设达到 80 分。
