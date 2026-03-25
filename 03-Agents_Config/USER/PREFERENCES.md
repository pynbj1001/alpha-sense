# 用户偏好配置 (PREFERENCES)

> 最后更新：2026-03-11

---

## 数据获取策略

### 金融数据优先级（瀑布规则）

在本项目目录中，获取金融数据时遵循以下优先级顺序：

| 优先级 | 数据源 | 适用场景 | 说明 |
|--------|--------|----------|------|
| 1️⃣ **优先** | `yfinance` | 美股、港股实时行情、基本面 | 免费，无需 token |
| 1️⃣ **优先** | `akshare` | A股行情、宏观数据、基金 | 免费，数据丰富 |
| 2️⃣ **备用** | `Tushare Pro` | 当免费渠道找不到数据时 | 需 token，每分钟50次 |

> **规则**：只有当 yfinance / akshare 均无法获取所需数据时，才调用 Tushare。

### Tushare 配置信息

- **版本**：1.4.25（安装于 `.venv-1`，Python 3.14.2）
- **Token**：已通过 `ts.set_token()` 持久化到本地，代码中直接 `ts.pro_api()` 即可
- **频率限制**：每分钟 50 次
- **文档**：`.agents/skills/tushare/SKILL.md`（含 400+ 接口列表）

### 代码范式

```python
import os
import tushare as ts

# 优先用免费渠道
try:
    import yfinance as yf
    # ... yfinance 逻辑
except Exception:
    pass

# 备用：Tushare（免费渠道找不到时）
try:
    pro = ts.pro_api()  # token 已缓存，无需传参
    df = pro.some_api(...)
except Exception as e:
    print(f"[Tushare] 获取失败: {e}")
```

---

## 报告风格偏好

- 语言：中文
- 结构：结论优先（≤3句执行摘要），再展开数据
- 深度：机构级分析，多框架交叉验证
- 数据：必须标注来源与日期，禁止凭记忆引用

---

## 关注标的 & 目标

> 参见 `GOALS.md`
