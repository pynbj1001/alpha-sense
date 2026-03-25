# @遗憾 — 遗憾复盘 Skill

> 系统化追踪"看对了但没赚到"的案例，把痛苦转化为纪律

---

## 触发指令

- `@遗憾 [标的]`
- `@regret [标的]`

---

## 工作流

1. **录入案例**：标的、最早感知时间、当时价格、根因、故事
2. **自动计算**：获取当前价格，计算错过涨幅
3. **根因归类**：5 类根因自动匹配
4. **教训提取**：生成结构化教训
5. **防错规则**：生成可执行的防错规则
6. **持久化**：保存到 `data/regrets.json`
7. **联动更新**：自动追加到 `tasks/lessons.md`

---

## 五类根因

| 根因 | 说明 | 典型案例 |
|---|---|---|
| `no_capture` | 信号根本没被捕获 | 用了4090但没想到投资NVDA |
| `no_track` | 捕获了但没持续跟踪 | 看到新闻但没加入watchlist |
| `no_research` | 在跟踪但没做深度研究 | 一直在列表里但没分析 |
| `no_position` | 研究充分但没有建仓 | 觉得贵/等回调/犹豫 |
| `too_light` | 建仓了但仓位太轻 | 只买了1%错过大涨 |

---

## 核心 API

```python
from core.regret_engine import add_regret, list_regrets, get_statistics

case = add_regret(
    ticker="NVDA",
    company_name="英伟达",
    first_noticed="2023-01-15",
    price_at_notice=150.0,
    root_cause="no_capture",
    narrative="买了4090，性能震撼，知道AI爆炸但没买股票",
)

stats = get_statistics()
```

---

## 可视化

Streamlit 页面: `pages/4_😤_遗憾复盘.py`
