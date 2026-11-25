# CHANGELOG

## 2.0.3

- 单点迭代（父辈 v1.0 / attempt 85706 / 72.3333）：增益量化自证。
- 新增 `scripts/gain_card.py`：由真实产物计算机检指标（自检通过率、溯源覆盖率、导出合规率、契约填充率、回修轮次、机器代替人工修图条目），输出 `gain_card.json/md`，并附基础 Agent 反事实缺陷对照。
- 针对「使用增益 25 分」缺专门可验证证据的空白。
- 本地回归（regression_report.json、regression_gain_card.json）：合成 example 产物上 5 项指标全部正确计算（selfcheck 11/11、trace 11/11、export 1.0、contract 11/11）。
- 其余管线脚本与父版 md5 一致，零改动。
