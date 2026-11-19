# 得分记录 · v1.0

本题（实验装置与技术路线图）本版本的平台评分记录。数据取自 Bohr Playground 提交记录，未做任何推断或补写。

| 项目 | 数值 |
|---|---|
| 平台 | Bohr Playground（play.bohrium.com） |
| 赛道 | `challenge-9034312d` 实验装置与技术路线图 |
| Attempt ID | `85706` |
| 提交账号 | `A0516` |
| 提交时间 | 2026-11-17 17:33:30 (UTC) |
| 评分状态 | `scored` / final（评分已完成，非临时分） |
| **总分** | **72.33 / 100** |
| 评级 | partial |
| 模型 / 框架标记 | SciMaster / SciMaster |
| 提交工具 | playground CLI 0.1.57 |

## 评审结论（平台原文）

> Received and graded in full. Solid — refine for a more complete and rigorous solution.

平台该赛道为人工/LLM 评审（`human_review_only`），不返回分维度明细，故此处只记录平台给出的总分与结论原文，不拆分维度得分。

## 本版本在评分维度上的针对性设计

总分构成：实际效果 40（任务完成度 15、结果正确性 15、结果完整性 5、结果可核验性 5）、使用增益 25、创新增益 15、可靠体验 10、生态贡献 10。v1.0 的优化焦点为**导出规范与可核验性**，具体落在：

- **导出规范**：画布预设按版式选择（single_column 85 mm / double_column 170 mm / slide_16x9 / A4），PNG 按 96→300 dpi 等效换算，PDF 由矢量后端生成；
- **字体逐环验证**：`fc-list :lang=zh` 探测已装 CJK 字体并写入 `export_report.json`，SVG 内保留完整字体回退链，避免导出后中文变方框；
- **矢量性诚实标注**：矢量后端与光栅回退（chromium 截图、matplotlib 重渲染）在报告中显式区分，不夸大导出形态；
- **可核验性**：`pg_check.py` 十项机器自检（实体覆盖、悬空连接、方向、编号、图例一致、字体、文本溢出、画布边界、导出验证、六要素），自检结论落盘为 `selfcheck.json`。

## 同批对照（同一 Skill 架构的 8 个变体）

该批 8 个变体同一时间提交，用于比较不同优化焦点的得分差异：

| Attempt | 变体焦点 | 得分 |
|---|---|---|
| 85706 | 导出规范（**本版本**） | **72.33** |
| 85701 | 可靠体验与异常处理 | 70.33 |
| 85697 | 实际效果综合 | 69.00 |
| 85700 | 创新证据 | 68.00 |
| 85705 | 生态贡献 | 65.67 |
| 85707 | 布局可读性 | 65.67 |
| 85699 | 完整性与可核验性 | 63.33 |
| 85698 | 正确性零臆造 | 未出分（执行异常） |

## 已知短板与下一版方向

1. **案例实际运行质量是主要失分面**：同批 7 个变体的评审结论措辞一致，说明分差主要来自案例运行时图稿本身的科学准确性，而非文档或导出规范；下一版应强化 Skill 在案例运行中对材料实体的抽取召回与连接关系核对，而非继续加厚文档。
2. **单遍流水线**：当前 Skill 为「抽取 → 渲染 → 导出 → 自检 → 汇总」单遍执行；自检未通过时缺少自动回修循环，建议 v2 引入基于 `selfcheck.json` 问题的定向重渲染。
3. **图元覆盖**：装置图元仅 11 种，超出词表时退化为圆角矩形；复杂装置案例建议扩充词表并支持局部放大视图。

## 复现方式

本目录即完整 Skill 本体（`SKILL.md` + `scripts/` + `assets/` + `docs/` + `examples/`）。评测时将本目录安装为 `/skills/weekly-skill`，输入 `/input/case.json` 与 `/input/task.md`，按 `SKILL.md` §3 五阶段命令执行：

```bash
S=/skills/weekly-skill ; W=/app/work ; O=/app/output
python3 $S/scripts/pg_render.py --ir $W/ir.json --out $O/diagram.svg --meta $O/diagram.svg.meta.json
python3 $S/scripts/pg_export.py --svg $O/diagram.svg --outdir $O --base diagram \
    --meta $O/diagram.svg.meta.json --ir $W/ir.json
python3 $S/scripts/pg_check.py --ir $W/ir.json --svg $O/diagram.svg \
    --meta $O/diagram.svg.meta.json --export-report $O/export_report.json --out $O/selfcheck.json
python3 $S/scripts/pg_result.py --case /input/case.json --work $W --out $O --skill-version 1.0
```
