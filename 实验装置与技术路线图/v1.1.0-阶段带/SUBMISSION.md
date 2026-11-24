# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 待提交 |
| 挑战赛 | `challenge-9034312d` — 实验装置与技术路线图 |
| 提交时间 | 待提交 |
| 状态 | 未提交 |
| 得分 | 未出分 |
| 查询命令 | 待提交后填写 |

## 方向

阶段带。父版本 `v1.0`（attempt 85706，终分 72.3333）。

## 评分点

实际效果 / 结果正确性（15 分）：技术路线阶段带包住该阶段的执行实体。

## 父版本

`v1.0`。本次只补它尚未通过的这一条本地检查。本题版本目录里没有其他未终分提交。

## 本地检查前后

合成示例 `examples/example_ir.json`，非正式案例，不是正式案例答案。阶段一的执行实体是 E2，阶段二是 E3 与 E4，三个中心在同一行。

检查命令：

```
python3 scripts/pg_render.py --ir examples/example_ir.json --out diagram.svg --meta diagram.svg.meta.json
python3 scripts/stage_band_audit.py --ir examples/example_ir.json --svg diagram.svg --meta diagram.svg.meta.json
```

`stage_band_audit.py` 要求每个 `steps[].actor` 的中心落在自己的阶段矩形内。父版本没有这个脚本，两次检查都用本目录的 `stage_band_audit.py`。

| 版本 | 结果 | 退出码 |
|-|-|-|
| v1.0 | 用 v1.0 的 `pg_render.py` 渲染。阶段二的 E3、E4 不在阶段二的带内 | 1 |
| v1.1.0 | 用本目录渲染。两个阶段的执行实体中心都在各自带内 | 0 |
