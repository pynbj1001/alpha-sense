# @信号 — 信号捕获 Skill

> 一句话输入 → 结构化投资信号 → 推入贝叶斯追踪器

---

## 触发指令

- `@信号 [任意描述]`
- `@signal [描述]`

---

## 工作流

1. **用户输入**：一句自然语言描述（产品体验、阅读洞察、数据异常等）
2. **关键词匹配**：自动从 50+ 关键词库匹配关联标的（中英文）
3. **催化剂识别**：匹配技术革命框架 3 大催化剂
4. **阶段推断**：推测佩雷丝技术革命 5 阶段
5. **先验计算**：基于信号类型 × 催化剂 × 标的数量 推算先验概率
6. **论点生成**：生成结构化论点草稿
7. **持久化**：保存到 `data/signals.json`
8. **可选推送**：将信号推入贝叶斯追踪器

---

## 信号类型

| 类型 | 说明 |
|---|---|
| `product_intuition` | 🎮 产品直觉 — 作为用户感受到的产品力 |
| `reading_insight` | 📖 阅读洞察 — 研报/书籍/文章触发 |
| `data_anomaly` | 📊 数据异常 — 财务/行业数据异动 |
| `social_signal` | 👥 社会信号 — 身边人行为变化 |
| `framework_deduction` | 🧠 框架推演 — 投资框架逻辑推导 |

---

## 五类根因（用于遗憾复盘联动）

| 根因 | 含义 | 防错规则 |
|---|---|---|
| `no_capture` | 信号没有被捕获 | 当天 @信号 录入 |
| `no_track` | 捕获了但没追踪 | 立即推入贝叶斯追踪器 |
| `no_research` | 追踪了但没深研 | 概率 ≥ 60% 启动 @分析 |
| `no_position` | 研究了但没建仓 | 概率 ≥ 65% 必须试仓 |
| `too_light` | 买了但仓位太轻 | 概率 ≥ 70% 审视加仓 |

---

## 核心 API

```python
from core.signal_capture import capture_signal, push_to_tracker

signal = capture_signal("4090显卡体验极好，AI推理速度惊人", "product_intuition")
push_to_tracker(signal, "NVDA")
```

---

## 可视化

Streamlit 页面: `pages/1_📡_信号捕获.py`
