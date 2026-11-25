# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 未提交 |
| 挑战赛 | `challenge-83d4f050` — 生物机制图与通路图 |
| 提交时间 | 未提交 |
| 状态 | 未提交 |
| 得分 | 未提交 |
| 查询命令 | 未提交 |

在途名额最多 2 个，且必须打在不同评分点。本份与拟提交的版本撞车或超出名额，先归档，不提交。

## 方向

受体跨膜。父版本 `v1.0.0`（attempt 85718，终分 73）。

## 评分点

实际效果 / 结果正确性（15 分）：受体画在膜带上。

## 父版本

`v1.0.0`。本次只补它尚未通过的这一条本地检查。

## 本地检查前后

合成示例，非正式案例，不进提交包。受体 `R` 的区室写成 cytoplasm，图里同时有膜带。

```
python3 scripts/build_svg.py graph.json figure.svg
python3 scripts/check_receptor_membrane.py figure.svg
```

| 版本 | 结果 | 退出码 |
|-|-|-|
| v1.0.0 | 受体画在细胞质带 | 1 |
| v1.5.0 | 受体画在膜带上 | 0 |
