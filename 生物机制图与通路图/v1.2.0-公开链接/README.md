# bio-mechanism-pathway-illustrator

把生物机制/通路材料转成可编辑、可核验、可重新导出的科研图稿（SVG + draw.io + PNG/PDF）。

## 安装
整个目录被平台安装为 `/skills/weekly-skill`。零 Python 第三方依赖（标准库即可运行全部脚本）；
渲染预览需要 cairosvg/rsvg-convert/inkscape/resvg 之一（缺失自动降级并记录）。

## 快速开始
见 SKILL.md「六步流水线」与 `examples/minimal_example.md`。

## 依赖与版本
- Python ≥ 3.8，标准库。
- 可选：poppler（pdftotext）、PyMuPDF、cairosvg、rsvg-convert、inkscape、resvg、matplotlib。
- 全部脚本不联网、不 pip install、不读写 Skill 目录之外除 /app/work、/app/output 外的位置。

## 适用范围
- 机制示意图、信号通路图、调控流程图、数据图表（带真实数据来源）。
- 既有图稿的 source-preserving 编辑（改标签/样式，保留结构重导出）。

## 限制
- 不做统计分析、不判定实验结论真伪；图的科学判断以输入材料为依据。
- 自动布局为分层网格，特殊美学需求需在 graph.json 节点级覆盖 x/y。
- draw.io 导出对抑制端点用 open arrow 近似 T-bar（draw.io 标记限制），SVG 为准。

## 维护
CHANGELOG.md 记录版本；validate.py 的 check_report.json 是每次运行的质量基线。
