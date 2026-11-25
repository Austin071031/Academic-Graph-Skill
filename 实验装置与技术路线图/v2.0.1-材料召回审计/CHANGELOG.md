# CHANGELOG

## 2.0.1

- 单点迭代（父辈 v1.0 / attempt 85706 / 72.3333）：材料召回审计。
- 新增 `scripts/recall_audit.py`：阶段1 抽取后以材料原文为唯一事实源，抽取装置名词（设备词典+工程代号）、连接描述、步骤编号，与 IR 比对，遗漏写 `recall_report.json` 并非零退出；确属不入图的须在 `ir.uncertainty` 说明方可豁免。
- 针对父版主要失分面「案例实际运行质量（漏实体/漏连接/漏步骤）」。
- 本地回归（regression_report.json）：洁净例零误报 exit 0；材料含未收录装置（冷凝器/储罐）exit 1 并列出；IR 漏步骤 3 exit 1 并列出。
- 其余管线脚本与父版 md5 一致，零改动。
