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

被动方向。父版本 `v1.0.0`（attempt 85718，终分 73）。

## 评分点

实际效果 / 结果正确性（15 分）：“A is activated by B” 的箭头从 B 指向 A。

## 父版本

`v1.0.0`。本次只补它尚未通过的这一条本地检查。

## 本地检查前后

合成示例，非正式案例，不进提交包。边从 `K` 指向 `R`，引文是 `K is activated by R`。

```
python3 scripts/build_svg.py graph.json figure.svg
python3 scripts/check_passive_direction.py figure.svg
```

| 版本 | 结果 | 退出码 |
|-|-|-|
| v1.0.0 | 箭头仍是 K → R | 1 |
| v1.4.0 | 箭头改为 R → K | 0 |
