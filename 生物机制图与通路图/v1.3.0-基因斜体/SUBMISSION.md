# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 未提交 |
| 挑战赛 | `challenge-83d4f050` — 生物机制图与通路图 |
| 提交时间 | 未提交 |
| 状态 | 未提交 |
| 得分 | 未提交 |
| 查询命令 | 未提交 |

在途两份之一，先推送、提交后回填 attempt id。2026-11-25 查分确认：本版尚未提交到平台，无 attempt、未出分，维持未提交。

## 方向

基因斜体。父版本 `v1.0.0`（attempt 85718，终分 73）。

## 评分点

实际效果 / 结果正确性（15 分）：基因文字用斜体，蛋白文字不用斜体。

## 父版本

`v1.0.0`。本次只补它尚未通过的这一条本地检查。

## 本地检查前后

合成示例，非正式案例，不进提交包。一个 `gene` 节点和一个 `protein` 节点，标签都是 `STAT3`。

```
python3 scripts/build_svg.py graph.json figure.svg
python3 scripts/check_gene_italic.py figure.svg
```

| 版本 | 结果 | 退出码 |
|-|-|-|
| v1.0.0 | 基因和蛋白都是正体 | 1 |
| v1.3.0 | 基因斜体，蛋白正体 | 0 |
