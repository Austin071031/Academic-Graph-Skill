# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | **107313** |
| 版本 | v2.0.3-分组类别键对齐 |
| 挑战赛 | `challenge-1bd90d8a` — 科研数据图表生成与编辑 |
| 提交时间 | 2026-11-25T06:46:35+00:00 |
| 状态 | submitted（queued，平台已接受，未出分） |
| 得分 | 待出分（不预测分数） |
| 查询命令 | `playground status --attempt-id 107313` |

## 父版与唯一改动

父版为当前最高已出分版本 `v1.2.0-图例系列绑定`（attempt 103638，终分 73.3333）。本版只按类别键对齐分组数据，不把偶然行序当作数据键。对应结果正确性、不同输入下的稳定性和人工返工减少；没有官方分项扣分证据。

## 合成回归（非官方案例）

系列 1 行序为 A=4、B=6；系列 2 文件行序为 B=5、A=7。父版抛出 `Grouped bar category ordering differs between series`；新版得到 A:4/7、B:6/5，系列 2 的逻辑源行仍为 B 第 2 行、A 第 3 行，未切断溯源。

执行并通过：

```bash
python3 scripts/charts.py render --spec spec.json --out out
python3 scripts/check_category_alignment.py --map out/source_map.json
python3 scripts/check_legend_series.py --spec spec.json --svg out/figure.svg
python3 scripts/verify_sources.py --map out/source_map.json --out out/source_checks.json
```

缺失、额外或重复键保持明确报错；不自动聚合、不插补。2026-11-25 的完整五版测试共执行 22 项命令，全部通过。

## 实际提交证据

2026-11-25T06:46:35+00:00 通过 playground CLI 0.1.58 正式提交，平台返回 Attempt **107313**、状态 `submitted`、评分 `queued`。`bundle_sha256=8bfbd5824bae735bd482cae2bb1addf1b756f1e8394fd6f2ce07c95e313802f6`。此追溯记录在 dry-run 与正式提交后追加，待平台出分后再回填分数。
