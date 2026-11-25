# 图形摘要

题目：Graphical Abstract（图形摘要）。Challenge ID：`graphical-abstract-7030fff2`。

从实际论文与数据生成、或保留原稿结构修订单页科研图形摘要，交付可编辑图稿及来源映射。用途、依赖、输入输出和异常处理见各版本 `SKILL.md`。

## 版本索引

| 版本 | Attempt | 提交日期 | 官方最终分 | 说明 |
|---|---|---|---|---|
| [v1.3.0](v1.3.0/) | 74019 | 2026-11-13 | **83 / 100** | 当前已确认最高分；实际提交包原样提取 |
| [v1.3.1-原样](v1.3.1-原样/) | 106000 | 2026-11-25 | 待出分 | 九个技能文件与 74019 逐字节相同，只增加 GITHUB_URL.txt。 |
| [v1.4.0-图例系列绑定](v1.4.0-图例系列绑定/) | 103749 | 2026-11-24 | **69.6667 / 100** | 图例文字和颜色按数据表的系列列重绑，不再采用与表冲突的规格颜色。 |

## 历次提交与得分（截至 2026-11-25 查分，仅查分未重提）

| # | Attempt | 提交时间 (UTC) | harness | 状态 | 得分 |
|-|-|-|-|-|-|
| 1 | 72260 | 2026-11-12 10:05:12 | Codex Desktop | scored（partial，final） | 72.3333 |
| 2 | 73147 | 2026-11-13 01:16:24 | Codex Desktop | pending_review（failed，未出分） | — |
| 3 | 73474 | 2026-11-13 04:09:44 | Codex Desktop | scored（partial，final） | 67 |
| 4 | 74019 | 2026-11-13 07:51:17 | Codex Desktop | scored（partial，final） | **83** |
| 5 | 103749 | 2026-11-24 08:43:21 | harbor-lbg | scored（partial，final） | 69.6667 |
| 6 | 106000 | 2026-11-25 01:13:31 | harbor-lbg | submitted（queued，未出分） | — |

出分提交共 4 次，最高分 83（attempt 74019，归档为 v1.3.0）。早期提交 72260（72.3333）与 73474（67）先于版本归档，未单独建目录；103749 对应 v1.4.0-图例系列绑定，106000 对应 v1.3.1-原样（待出分）。

成绩及平台反馈见 [v1.3.0/SCORE.md](v1.3.0/SCORE.md)，逐文件来源哈希见 [PROVENANCE.json](v1.3.0/PROVENANCE.json)。

每次迭代新增 `v<主>.<次>.<修订>/` 目录，不覆盖已出分版本；未出分须明确标注，不填预测分。版本目录直接包含 `SKILL.md` 与该版本实际资源，无须为凑目录添加空assets或examples。

## 使用说明

本归档保留竞赛运行约定：Skill安装于 `/skills/weekly-skill`，从 `/input` 读取案例，向 `/app/output` 写结果，临时文件位于 `/app/work`。运行库和导出工具见版本内 `SKILL.md`。迁移到其他运行环境时需配置对应目录；不要将成绩档案当作原生本机即装即用的运行器。

## 未出分提交（平台执行异常，待人工确认）

以下 attempt 未对应任何版本目录，也未计入得分。平台返回的字段为 `execStatus=failed`、`resultsJson.harbor_status=evaluation_error`，`score` 为占位 0、`scoreIsFinal=false`，记录状态仍为 `pending_review`，即未产生可用评分。是否重提由人工决定，本仓库不代为重提。

| Attempt | 提交时间 | 平台状态字段 |
|-|-|-|
| 73147 | 2026-11-13T01:16:24+00:00 | status=pending_review，execStatus=failed，harbor_status=evaluation_error，score=0（占位），scoreIsFinal=false |

旁证（仅记录事实，不作结论）：同题目同期另两次提交 72260（2026-11-12，72.3333）与 74019（2026-11-13T07:51，83）均正常出分，说明该挑战赛评分链路在此前后可正常完成。
