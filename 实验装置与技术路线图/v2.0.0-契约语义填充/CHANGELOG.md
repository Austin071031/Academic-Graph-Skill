# CHANGELOG

## 2.0.0

- 单点迭代（父辈 v1.0 / attempt 85706 / 72.3333）：契约语义填充。
- 新增 `scripts/contract_fill.py`：`pg_result.py` 之后按语义回填 output_contract 失落字段——实体/连接/步骤清单、图例 kinds、数值表、逐要素来源定位，替换父版的 `no automatic mapping`。
- 新增 `scripts/contract_check.py`：逐字段机检实质内容，写 `contract_check.json`，不实质即非零退出。
- 本地回归（regression_report.json）：合成 11 字段契约下父版 9 字段 unavailable，新版全部回填，contract_check 11/11 通过。
- 其余管线（渲染/导出/自检）脚本与父版 md5 一致，零改动。
