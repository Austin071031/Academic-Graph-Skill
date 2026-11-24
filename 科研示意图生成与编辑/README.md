# 科研示意图生成与编辑

Challenge ID：`challenge-98e5a474`。从真实科研材料生成或编辑示意图，交付可编辑源文件、实际导出件、来源定位及修改记录。

## 版本索引

| 版本 | Attempt | 提交日期 | 官方最终分 | 说明 |
|---|---|---|---|---|
| [v1.0.1](v1.0.1/) | 73746 | 2026-11-13 | **72.6667 / 100** | 本题本账号当前已确认最高分；从实际提交包原样提取 |
| [v1.1.0-图例分类映射](v1.1.0-图例分类映射/) | 103608 | 2026-11-24 | 待出分 | 图例项和节点填色按数据表分类重绑 |

成绩及反馈见 [SCORE.md](v1.0.1/SCORE.md)，文件来源与哈希见 [PROVENANCE.json](v1.0.1/PROVENANCE.json)。后续迭代新增版本目录，不覆盖已有版本；未出分版本明确标注待评测。

## 使用

入口为版本目录内 `SKILL.md`。保留竞赛约定：平台安装到 `/skills/weekly-skill`，读取 `/input/case.json` 和真实材料，临时文件位于 `/app/work`，实际图稿及 `result.json` 写入 `/app/output`。依赖、接口及异常处理见 Skill 和 references。其他环境需配置相应路径。

## 未出分提交（平台执行异常，待人工确认）

以下 attempt 未对应任何版本目录，也未计入得分。平台返回字段：`execStatus=failed`、`resultsJson.harbor_status=evaluation_error`，`score` 为占位 0、`scoreIsFinal=false`，记录状态仍为 `pending_review`，即未产生可用评分。是否重提由人工决定。

| Attempt | 提交时间 | 平台状态字段 |
|-|-|-|
| 73203 | 2026-11-13T01:31:23+00:00 | status=pending_review，execStatus=failed，harbor_status=evaluation_error，score=0（占位），scoreIsFinal=false |

旁证（仅记录事实，不作结论）：同题目 72125（2026-11-12，62.3333）与 73746（2026-11-13T06:17，72.6667）均正常出分。
