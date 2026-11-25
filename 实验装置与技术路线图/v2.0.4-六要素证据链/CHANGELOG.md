# CHANGELOG

## 2.0.4

- 单点迭代（父辈 v1.0 / attempt 85706 / 72.3333）：六要素证据链。
- 新增 `scripts/elements_check.py`：题面六类要素逐项深度机检（科学实体 locator、空间关系、数据编码 kinds→线型映射、图例标注、可编辑 `<g id>`/文本/字体链、导出格式），输出 `elements_check.json` + `elements_evidence.md`，缺项非零退出。
- 针对父版 six_elements 粗粒度、完整性无从定位的短板。
- 本地回归（regression_report.json）：完整产物六要素全过 exit 0；去除实体 locator 检出「1_科学实体」exit 1。
- 其余管线脚本与父版 md5 一致，零改动。
