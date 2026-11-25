# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 103749 |
| 挑战赛 | `graphical-abstract-7030fff2` — Graphical Abstract（图形摘要） |
| 提交时间 | 2026-11-24T08:43:21+00:00（北京时间 2026-11-24 16:43） |
| 状态 | scored（已评分，`state: final`，`scoreIsFinal: true`） |
| 得分 | **69.6667 / 100** |
| 查询命令 | `playground status --attempt-id 103749` |

包 sha256：`eb341b060a5196e228ba6636add351fcf3b30c3da368ecf65712ddd2146ddb25`

终分回填：北京时间 2026-11-25 08:17。`harbor_reward` 0.69666667，`zeroReason` 为空，`outcome` 为 partial。

## 方向

图例系列绑定。父版本 `v1.3.0`（attempt 74019，终分 83）。第四期需要一次新提交；父版本保持不动。

## 评分点

实际效果 / 结果正确性（15 分）：图例文字、颜色与数据表的系列一致。

## 父版本

`v1.3.0`。本次只补它尚未通过的这一条本地检查。本题版本目录里没有其他在途提交。

## 本地检查前后

合成示例，非正式案例，不进提交包。数据表四行：`A,Control,#0072B2,4`、`B,Control,#0072B2,6`、`A,Treatment,#D55E00,7`、`B,Treatment,#D55E00,5`。规格里两个系列的 `label` / `color` 写成 `Wrong-1,#111111` 和 `Wrong-2,#222222`，同时声明 `label_column=series`、`color_column=swatch`。

检查命令：

```
python3 scripts/charts.py render --spec spec.json --out out
python3 scripts/check_legend_series.py --spec spec.json --svg out/figure.svg
```

`check_legend_series.py` 要求图例文字和颜色与所选数据行的系列名、色块逐项相同。

| 版本 | 结果 | 退出码 |
|-|-|-|
| v1.3.0 | 渲染成功，但图例为 Wrong-1/#111111、Wrong-2/#222222，检查失败 | 1 |
| v1.4.0 | 同一检查通过，图例为 Control/#0072b2、Treatment/#d55e00 | 0 |
