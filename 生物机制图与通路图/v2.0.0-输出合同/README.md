# bio-mechanism-pathway-illustrator · v2.0.0 输出合同

父版：v1.0.0（attempt 85718，73/100）。本版唯一机制增量：从真实 `/input/case.json` 的
`output_contract` 完整回填结构化字段，修复文件扩展名误配和首轮校验顺序。

## 调用与依赖
Python ≥3.8，标准库。沿用父版六步流水线。渲染预览按 render_preview.py 内置
cairosvg→rsvg-convert→inkscape→resvg 尝试；有可用 matplotlib 时明确降级为 graph 预览。
命令与最小输入见 `examples/minimal_example.md`（示意，非正式案例答案）。

## 关键输出
SVG/draw.io 图稿、真实导出件或明确缺口、`result.json`、`check_report.json`、
来源台账、运行日志。字典/列表合同均可；显式 path 优先，`figure_png` 必须指向真实
`figure.png`。必需字段缺失/错格式为 HARD，可选缺失不得冒充完成。

## 限制
未获得平台隐藏案例分项反馈，不声称本地 PASS 等于官方 80 分。官方成绩见 SCORE.md 与
SUBMISSION.md 回填。其它绘图、图表、布局及编辑代码与父版保持独立不合并。
