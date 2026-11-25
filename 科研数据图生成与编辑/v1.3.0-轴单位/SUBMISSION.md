# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 待提交 |
| 挑战赛 | `challenge-1bd90d8a` — 科研数据图表生成与编辑 |
| 提交时间 | 待提交 |
| 状态 | 待提交 |
| 得分 | 待提交 |
| 查询命令 | 待提交 |

## 方向

轴单位。父版本 `v1.2.0-图例系列绑定`（attempt 103638，终分 73.3333）。

## 评分点

实际效果 / 结果正确性（15 分）：纵轴单位与数据表一致。

## 父版本

`v1.2.0-图例系列绑定`。本次只补它尚未通过的这一条本地检查。与另一份在途版本打在不同评分点。

## 本地检查前后

合成示例，非正式案例，不进提交包。数据表两行：`A,4,mg/L`、`B,7,mg/L`。规格纵轴写成 `Concentration (ug/L)`，同时声明 `unit_column=unit`。

检查命令：

```
python3 scripts/charts.py render --spec spec.json --out out
python3 scripts/check_axis_unit.py --spec spec.json --svg out/figure.svg
```

`check_axis_unit.py` 要求 SVG 文本含数据表里的单位。

| 版本 | 结果 | 退出码 |
|-|-|-|
| v1.2.0 | 渲染成功，纵轴仍是 ug/L，检查找不到 mg/L | 1 |
| v1.3.0 | 同一检查通过，纵轴单位为 mg/L | 0 |
