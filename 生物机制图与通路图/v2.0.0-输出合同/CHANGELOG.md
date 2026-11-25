# 变更

相对 v1.0.0：仅强化输出合同与交付闭环。
- 字典/列表合同规范化，优先显式 path，完整扩展名解析，不用前缀猜文件。
- null、缺失、错格式必需文件 HARD；可选缺失不 HARD。
- provisional result → validate → final result，避免 stale check 和错误 partial。
- 文档按同一实际调用顺序更新。
