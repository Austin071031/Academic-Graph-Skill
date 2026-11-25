# 实验装置与技术路线图

赛道：`challenge-9034312d`（Bohr Playground）。任务目标与评分维度见各版本目录内的 `SKILL.md` 与 `SCORE.md`。

## 版本索引

| 版本 | Attempt | 提交日期 | 得分 | 优化焦点 |
|---|---|---|---|---|
| [v1.0](v1.0/) | 85706 | 2026-11-17 | 72.33 / 100 | 导出规范与可核验性（300 dpi、字体逐环验证、十项机器自检） |
| [v1.1.0-阶段带](v1.1.0-阶段带/) | 103716 | 2026-11-24 | 59 / 100 | 阶段带包住该阶段的执行实体 |

## 版本命名约定

- `v<主>.<次>`：主版本对应架构性改动（如新增回修循环、扩充图元库），次版本对应评分维度上的定向优化。
- 每个版本目录内固定包含：`SKILL.md`（入口）、`scripts/`（执行脚本）、`assets/`（配置与图元）、`docs/`（说明）、`examples/`（合成示例）、`SCORE.md`（该版本平台得分与评审原文）、`CHANGELOG.md`。
- 得分只记录平台返回值与本目录产物，不补写分维度明细。

## 当前状态

账号 A0516 在该赛道的成功出分额度（10 次）已用满，历史最高分 72.33（本仓库 v1.0）。下一轮迭代方向见 `v1.0/SCORE.md` 末节。

## 未出分提交（平台执行异常，待人工确认）

以下 4 个 attempt 未对应任何版本目录，也未计入得分。平台返回字段一致：`execStatus=failed`、`resultsJson.harbor_status=evaluation_error`，`score` 为占位 0、`scoreIsFinal=false`，记录状态仍为 `pending_review`，即未产生可用评分。是否重提由人工决定，本仓库不代为重提（重提会消耗提交额度）。

| Attempt | 提交时间 | 平台状态字段 |
|-|-|-|
| 74053 | 2026-11-13T08:00:47+00:00 | status=pending_review，execStatus=failed，harbor_status=evaluation_error，score=0（占位），scoreIsFinal=false |
| 80504 | 2026-11-16T01:25:17+00:00 | status=pending_review，execStatus=failed，harbor_status=evaluation_error，score=0（占位），scoreIsFinal=false |
| 83952 | 2026-11-17T02:27:36+00:00 | status=pending_review，execStatus=failed，harbor_status=evaluation_error，score=0（占位），scoreIsFinal=false |
| 85698 | 2026-11-17T17:32:44+00:00 | status=pending_review，execStatus=failed，harbor_status=evaluation_error，score=0（占位），scoreIsFinal=false |

旁证（仅记录事实，不作结论）：85698 与同批另外 7 次提交在同一分钟内创建，其中 7 次均正常出分（63.3333–72.3333），仅该次异常；80504、83952 所在时段该账号在其它挑战赛也有正常出分记录。
