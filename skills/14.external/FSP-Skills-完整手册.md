# Financial Services Plugins — 全技能手册 v1.0

> **文档用途**：全面梳理 14.external/financial-services-plugins 中的所有专业投资分析技能  
> **创建日期**：2026-02-26  
> **技能总数**：41 个 Skills | 38 个 Commands | 11 个 MCP 集成  
> **适用场景**：投资银行、股票研究、私募股权、财富管理、财务分析

---

## 📋 目录

1. [总览与架构](#总览与架构)
2. [核心插件：Financial Analysis](#核心插件financial-analysis-9-skills)
3. [股票研究：Equity Research](#股票研究equity-research-9-skills)
4. [投资银行：Investment Banking](#投资银行investment-banking-9-skills)
5. [私募股权：Private Equity](#私募股权private-equity-9-skills)
6. [财富管理：Wealth Management](#财富管理wealth-management-6-skills)
7. [合作伙伴插件](#合作伙伴插件partner-built)
8. [如何创建新 Skill](#如何创建新-skill)

---

## 总览与架构

### 插件体系结构

```
financial-services-plugins/
├── financial-analysis/     ← 核心插件（必须先安装）
├── equity-research/        ← 股票研究专业技能
├── investment-banking/     ← 投资银行专业技能
├── private-equity/         ← 私募股权专业技能
├── wealth-management/      ← 财富管理专业技能
└── partner-built/          ← 合作伙伴数据源插件
    ├── lseg/              ← LSEG 金融数据
    └── spglobal/          ← S&P Global Capital IQ
```

### 插件安装优先级

| 优先级 | 插件 | 类型 | 包含内容 | MCP 连接器 |
|:---:|---|---|---|---|
| **必须** | **financial-analysis** | 核心 | 财务建模工具 + 所有 MCP 数据连接器 | Daloopa, Morningstar, S&P Global, FactSet, Moody's, MT Newswires, Aiera, LSEG, PitchBook, Chronograph, Egnyte |
| 可选 | investment-banking | 增强 | M&A 交易文件、买方列表、合并模型 | — |
| 可选 | equity-research | 增强 | 研究报告、盈利分析、覆盖启动 | — |
| 可选 | private-equity | 增强 | 尽职调查、IC 备忘录、交易筛选 | — |
| 可选 | wealth-management | 增强 | 客户审查、财务规划、再平衡 | — |

---

## 核心插件：Financial Analysis (9 Skills)

> **核心地位**：提供所有插件共享的建模工具和 MCP 数据连接器，必须优先安装

### 📊 Skill 1: Comps Analysis（可比公司分析）

**用途**：构建机构级可比公司分析，包含运营指标、估值倍数、统计基准  
**输出格式**：Excel 表格（含公式、格式化、统计分析）  
**完美适用场景**：
- 上市公司估值（M&A、投资分析）
- 行业同业对标
- IPO 或融资定价
- 识别估值异常值
- 支持投资委员会演示

**激活关键词**：
```
✅ "build comps for [公司名]"
✅ "comparable company analysis"
✅ "peer valuation benchmarking"
✅ "create trading comps"
✅ "/comps [公司名]"（命令行指令）
```

**数据源优先级**：
1. **首选**：MCP 数据源（S&P Kensho, FactSet, Daloopa）
2. **备选**：Bloomberg Terminal, SEC EDGAR
3. **禁止**：Web 搜索（不可靠）

**关键输出组件**：
- 运营指标表（Revenue, EBITDA, Margins）
- 估值倍数（EV/Revenue, EV/EBITDA, P/E）
- 统计分位数（25th, Median, 75th, Mean）
- 格式标准：蓝色（硬编码输入）、黑色（公式）、绿色（跨表引用）

---

### 💰 Skill 2: DCF Model（现金流折现模型）

**用途**：创建机构质量的 DCF 估值模型，含敏感性分析和执行摘要  
**输出格式**：Excel 模型（完整公式、情景分析、敏感性表）  
**完美适用场景**：
- 股权估值
- 内在价值分析
- 详细财务建模（增长预测 + 终值计算）

**激活关键词**：
```
✅ "build DCF model for [公司名]"
✅ "discounted cash flow valuation"
✅ "intrinsic value analysis"
✅ "/dcf [公司名]"（命令行指令）
```

**核心约束条件**：
- **敏感性表**：所有 75 个单元格必须用完整 DCF 重算公式（3 表 × 25 单元格）
- **单元格注释**：每个蓝色硬编码值必须注明来源（格式："Source: [System/Document], [Date], [URL]"）
- **模型布局规划**：先定义所有章节行位置，后写公式
- **公式验证**：交付前运行 `python recalc.py model.xlsx 30`，零错误要求

**DCF 工作流**：
1. 数据收集（SEC 文件、分析师报告）
2. 现金流预测（5-10 年）
3. WACC 计算（资本成本）
4. 终值计算（永续增长法或倍数法）
5. 敏感性分析（增长率 × WACC 矩阵）
6. 执行摘要生成

---

### 🏢 Skill 3: LBO Model（杠杆收购模型）

**用途**：为 PE 交易创建 LBO 模型，计算 IRR、MOIC 回报指标  
**输出格式**：Excel 模型（Sources & Uses, 债务表, 回报分析）  
**完美适用场景**：
- 私募股权交易
- 并购材料
- 投资委员会演示

**激活关键词**：
```
✅ "build LBO model for [公司名]"
✅ "leveraged buyout analysis"
✅ "PE returns model"
✅ "/lbo [公司名]"（命令行指令）
```

**核心原则**：
- **所有计算必须是 Excel 公式**（不得用 Python 计算后硬编码）
- **使用模板结构**（`examples/LBO_Model.xlsx`）
- **符号约定一致**（现金流出为负数或正数，全模型统一）
- **颜色约定**：蓝色（输入）、黑色（公式）、紫色（同表引用）、绿色（跨表引用）

**LBO 模型核心模块**：
1. Sources & Uses（资金来源与用途）
2. Operating Model（运营假设）
3. Debt Schedule（债务偿还时间表）
4. Returns Analysis（IRR、MOIC、Equity Multiple）

---

### 📑 Skill 4: 3-Statements Model（三表联动模型）

**用途**：完善和填充三表财务模型模板（利润表、资产负债表、现金流量表）  
**输出格式**：Excel 模型（完整链接的三表模型）  
**完美适用场景**：
- 填写模型模板
- 完成部分填充的 IS/BS/CF 框架
- 链接集成财务报表

**激活关键词**：
```
✅ "complete 3-statement model"
✅ "populate financial model template"
✅ "fill out IS/BS/CF"
✅ "/3-statements [公司名]"（命令行指令）
```

**模板识别清单**：
| 常见标签名 | 内容 |
|---|---|
| IS, P&L, Income Statement | 利润表 |
| BS, Balance Sheet | 资产负债表 |
| CF, CFS, Cash Flow | 现金流量表 |
| WC, Working Capital | 营运资金表 |
| DA, D&A, Depreciation, PP&E | 折旧摊销表 |
| Debt, Debt Schedule | 债务表 |
| NOL, Tax, DTA | 净营业亏损表 |
| Assumptions, Inputs, Drivers | 驱动假设 |
| Checks, Audit, Validation | 错误检查仪表板 |

**三表联动核心验证**：
- 利润表净利润 → 现金流量表起始点
- 现金流量表净变化 → 资产负债表现金行项目
- 资产 = 负债 + 股东权益（必须平衡）

---

### 🎯 Skill 5: Competitive Analysis（竞争格局分析）

**用途**：系统性评估竞争动态、市场定位、战略审查  
**输出格式**：PowerPoint 幻灯片或 Word 文档  
**完美适用场景**：
- 竞争格局 Deck
- 同业对比
- 市场结构分析
- 投资建议

**激活关键词**：
```
✅ "competitive landscape analysis"
✅ "market positioning assessment"
✅ "peer comparison deck"
✅ "strategic review"
```

**核心标准**：
- **数据源优先级**：源文件（Excel/CSV）直接提取值，不自行计算
- **提示忠实度**：幻灯片标题、章节名必须与要求完全一致
- **图表 vs 表格**：明确要求"图表"时创建 PowerPoint 图表对象，不用表格替代
- **完整数据系列**：列出 7 个竞争对手则全部包含，不省略

**参考文件**：
- `references/schemas.md` — M&A 交易、情景分析表格模板
- `references/frameworks.md` — 按行业的 2x2 矩阵轴对

---

### 🔍 Skill 6: Check Deck（演示文稿审核）

**用途**：审核 PowerPoint 或 Keynote 演示文稿的专业性、准确性、一致性  
**输出格式**：审核报告（列出问题、建议、风险评级）  

**激活关键词**：
```
✅ "check this deck"
✅ "review presentation"
✅ "QC this pitch deck"
✅ "/check-deck [文件名]"（命令行指令）
```

**审核检查清单**：
- 格式一致性（字体、颜色、对齐）
- 数据准确性（公式、数字、日期）
- 逻辑流程（故事线、章节顺序）
- 来源标注（图表、数据点）
- 品牌合规（Logo、模板）

---

### 🧮 Skill 7: Check Model（财务模型审核）

**用途**：审核 Excel 财务模型的公式、逻辑、错误  
**输出格式**：审核报告（错误列表、公式验证、改进建议）  

**激活关键词**：
```
✅ "check this model"
✅ "audit Excel model"
✅ "validate formulas"
✅ "/debug-model [文件名]"（命令行指令）
```

**审核标准**：
- 公式错误（#REF!, #DIV/0!, #VALUE!）
- 循环引用检测
- 硬编码数字识别（应为公式的单元格）
- 资产负债表平衡验证
- 一致性检查（同一指标在不同位置的值）

---

### 📊 Skill 8: PPT Template Creator（PowerPoint 模板创建）

**用途**：创建可重复使用的 PowerPoint 模板，含品牌元素、标准布局  
**输出格式**：.pptx 模板文件  

**激活关键词**：
```
✅ "create PPT template"
✅ "make slide master"
✅ "design pitch deck template"
✅ "/ppt-template"（命令行指令）
```

**模板标准组件**：
- 封面页（公司 Logo、标题格式）
- 章节页（分隔幻灯片）
- 内容页布局（标题、正文、图表区域）
- 附录页格式
- 配色方案和字体规范

---

### 🛠️ Skill 9: Skill Creator（技能创建器）

**用途**：创建新的 Claude Skills（元技能）  
**输出格式**：SKILL.md 文件（遵循标准格式）  

**激活关键词**：
```
✅ "create a new skill for [用途]"
✅ "build skill template"
✅ "/create-skill"（命令行指令）
```

**Skill 标准结构**（详见后文"如何创建新 Skill"）

---

## 股票研究：Equity Research (9 Skills)

> **专业定位**：为股票研究分析师提供从覆盖启动到季度更新的完整工作流

### 📝 Skill 10: Initiating Coverage（覆盖启动报告）

**用途**：创建机构级首次覆盖研究报告（完整深度报告）  
**输出格式**：Word 文档（30-50 页，15,000-20,000 字）  
**报告结构标准**：JPMorgan / Goldman Sachs / Morgan Stanley 格式  

**激活关键词**：
```
✅ "write initiation report for [公司名]"
✅ "initiate coverage on [公司名]"
✅ "create equity research report"
✅ "/initiate [公司名]"（命令行指令）
```

**工作流（5 任务）**：
1. **公司研究** — 业务、管理、行业
2. **财务建模** — 构建预测模型
3. **估值分析** — DCF + 可比公司
4. **图表生成** — 创建 25-35 张图表
5. **报告组装** — 编译最终报告

**⚠️ 核心约束**：
- **单任务模式**：必须逐个任务执行（不能一次运行全流程）
- **字体要求**：Times New Roman（除非用户另行指定）
- **数据源强制引用**：所有数据必须标注来源

**报告关键组件**：
- 投资摘要（1 页，核心论点）
- 评级与目标价（买入/持有/卖出 + 12 个月目标价）
- 财务摘要表（历史 + 预测）
- 商业模式深度分析
- 行业趋势与竞争格局
- 估值分析（DCF、可比公司、历史倍数）
- 风险因素（3-5 个核心风险）
- 25-35 图表（运营指标、估值、财务趋势）

---

### 📈 Skill 11: Earnings Analysis（季度盈利分析）

**用途**：创建季度盈利更新报告（快速周转格式）  
**输出格式**：Word 文档（8-12 页，3,000-5,000 字）  
**周转时间**：24-48 小时内（财报后）  

**激活关键词**：
```
✅ "earnings update for [公司名] Q3 2024"
✅ "analyze quarterly results"
✅ "post-earnings report"
✅ "/earnings [公司名] [季度]"（命令行指令）
```

**核心要求**：
1. **速度与及时性**：财报公布后 24-48 小时内发布
2. **Beat/Miss 分析**：收入/EPS 是否超预期，量化偏差
3. **简洁格式**：1-3 个摘要表（非全面 P&L/CF/BS）
4. **新信息聚焦**：假定读者已熟悉公司，只报告新内容

**报告结构**：
- 执行摘要（Beat/Miss、关键指标、评级确认/变更）
- 财报亮点（收入、利润率、指引变化）
- 更新后的估值与目标价
- 修订后的财务模型假设
- 8-12 张图表（关键指标趋势）

---

### 🔮 Skill 12: Earnings Preview（盈利预览）

**用途**：财报前预测分析（提前 3-7 天发布）  
**输出格式**：简报（5-8 页）  

**激活关键词**：
```
✅ "earnings preview for [公司名] Q4 2024"
✅ "pre-earnings analysis"
✅ "/earnings-preview [公司名] [季度]"（命令行指令）
```

**预览核心内容**：
- 华尔街共识（收入/EPS 预期）
- 我们的预测 vs 共识
- 关键关注指标
- 潜在超预期/不及预期因素
- 历史 Beat/Miss 模式

---

### 💡 Skill 13: Idea Generation（投资创意筛选）

**用途**：系统性筛选市场机会、生成投资创意  
**输出格式**：创意列表（含初步筛选逻辑）  

**激活关键词**：
```
✅ "screen for investment ideas in [行业]"
✅ "find undervalued stocks"
✅ "generate trade ideas"
✅ "/screen [筛选条件]"（命令行指令）
```

**筛选维度**：
- 估值筛选（P/E、P/B、EV/EBITDA）
- 成长筛选（收入/EPS 增速）
- 质量筛选（ROE、ROIC、负债率）
- 技术筛选（动量、相对强弱）
- 催化剂筛选（即将财报、并购传闻、行业拐点）

---

### 📅 Skill 14: Catalyst Calendar（催化剂日历）

**用途**：跟踪覆盖股票的关键事件时间表  
**输出格式**：日历表格（含事件、日期、影响预测）  

**激活关键词**：
```
✅ "create catalyst calendar"
✅ "upcoming events for [公司名]"
✅ "/catalysts"（命令行指令）
```

**跟踪事件类型**：
- 财报日期
- 投资者日/分析师日
- 产品发布/监管批准
- 并购里程碑
- 大宗股票解禁/高管交易

---

### 🌅 Skill 15: Morning Note（晨会简报）

**用途**：总结隔夜动态、交易创意、关键事件  
**输出格式**：简报（2 分钟可读完）  
**目标场景**：早上 7 点晨会  

**激活关键词**：
```
✅ "morning note for today"
✅ "what happened overnight"
✅ "trade idea for this morning"
✅ "/morning-note"（命令行指令）
```

**晨会简报结构**：
```
[日期] Morning Note — [分析师名]
[行业覆盖]

核心观点: [标题 — PM 需要听到的一件事]
- 2-3 句话描述关键动态及重要性
- 股票影响：目标价、评级重申/变更

隔夜/盘前动态：
- [公司 A]：财报/新闻一句话摘要 + 我们的看法
- [公司 B]：一句话摘要 + 我们的看法
- [行业/宏观]：相关全行业动态

今日关键事件：
- [时间]: [公司] 财报电话会议
- [时间]: 经济数据发布（预期 vs 我们的看法）
- [时间]: 投资者会议
```

---

### 📊 Skill 16: Sector Overview（行业综述）

**用途**：撰写行业整体分析报告（市场、趋势、关键参与者）  
**输出格式**：研究报告（15-25 页）  

**激活关键词**：
```
✅ "sector overview for [行业]"
✅ "industry analysis report"
✅ "/sector [行业名]"（命令行指令）
```

**行业综述核心章节**：
- 行业规模与增长趋势（TAM/SAM/CAGR）
- 竞争格局与市场份额
- 关键驱动因素与逆风
- 估值对比（行业内相对估值）
- 投资建议（超配/标配/低配 + 首选股）

---

### 🎯 Skill 17: Thesis Tracker（投资论点追踪）

**用途**：维护覆盖股票的核心投资论点，定期验证假设  
**输出格式**：追踪表格（论点 + 验证状态 + 证据）  

**激活关键词**：
```
✅ "track investment thesis for [公司名]"
✅ "thesis validation dashboard"
✅ "/thesis [公司名]"（命令行指令）
```

**论点追踪结构**：
| 投资论点 | 核心假设 | 当前状态 | 支持证据 | 反面证据 | 置信度变化 |
|---|---|---|---|---|---|
| 例：云转型驱动增长 | ARR 增速 >30% | ✅ 验证 | Q3 ARR +35% | 获客成本上升 | ↑ 提升 |

---

### 🔄 Skill 18: Model Update（模型更新）

**用途**：在财报后或重大事件后更新财务预测模型  
**输出格式**：Excel 模型（更新的预测 + 变化说明）  

**激活关键词**：
```
✅ "update model for [公司名] after Q3 earnings"
✅ "revise estimates post-guidance"
✅ "/model-update [公司名]"（命令行指令）
```

**模型更新流程**：
1. 实际结果 vs 之前预测对比
2. 更新财务假设（收入增速、利润率、资本支出）
3. 滚动预测期（删除已过季度，添加新远期季度）
4. 重新计算估值（DCF、目标价）
5. 输出"变化桥接"表（旧目标价 → 新目标价的驱动因素）

---

## 投资银行：Investment Banking (9 Skills)

> **专业定位**：M&A 交易全流程支持（从 Teaser 到 CIM、并购模型到买方列表）

### 📄 Skill 19: Teaser（项目简介）

**用途**：撰写匿名单页公司简介（卖方 M&A 流程）  
**输出格式**：单页 Word/PDF（无公司名称）  
**目的**：在签署保密协议前测试买方兴趣  

**激活关键词**：
```
✅ "draft teaser for sell-side process"
✅ "blind teaser for [行业]"
✅ "anonymous company profile"
✅ "/teaser [项目代号]"（命令行指令）
```

**Teaser 结构**：
```
项目代号：Project [名称]
行业描述：「某领域的领先 XX 服务平台」
机密 — 仅供讨论

公司描述（2-3 句）：
- 业务内容（不透露公司名）
- 市场地位（"行业前三"、"领先供应商"）
- 地理覆盖（区域级别，不具体到城市）

投资亮点（4-6 点）：
- 市场领导地位 / 定位
- 收入质量（经常性 %、留存率、多元化）
- 增长轨迹
- 利润率特征与扩张机会
- 管理团队实力
- 战略价值 / 协同潜力

财务摘要表：
| 指标 | 数值 |
| 收入 | $XXM |
| 收入增长 | XX% CAGR |
| EBITDA | $XXM |
| EBITDA 利润率 | XX% |
| 员工数 | XXX |

交易概述（2-3 句）：
- 出售内容（100% 股权、控股权、成长型股权）
- 时间表
- 联系方式（银行家/顾问无公司直接联系）
```

---

### 📚 Skill 20: CIM Builder（机密信息备忘录）

**用途**：为卖方 M&A 流程构建完整 CIM  
**输出格式**：Word 或 InDesign 文档（40-80 页）  
**目的**：向签署保密协议的买方提供全面公司信息  

**激活关键词**：
```
✅ "build CIM for [公司名]"
✅ "draft confidential information memorandum"
✅ "create offering memorandum"
✅ "/cim [公司名]"（命令行指令）
```

**CIM 标准目录**：

**I. 执行摘要（2-3 页）**
- 公司概览 — 业务、竞争优势
- 投资亮点（5-7 条核心卖点）
- 财务摘要 — 收入、EBITDA、增长、利润率
- 交易概述 — 出售内容、参考时间表

**II. 公司概览（3-5 页）**
- 历史与创始故事
- 使命与价值主张
- 产品与服务描述
- 商业模式与收入流
- 核心差异化优势

**III. 行业概览（3-5 页）**
- 市场规模与增长（TAM/SAM/SOM）
- 行业趋势与顺风
- 竞争格局
- 监管环境
- 进入壁垒

**IV. 增长机会（2-3 页）**
- 有机增长杠杆（新产品、市场、定价）
- M&A / 并购机会
- 运营改进
- 技术投资
- 白空间分析

**V. 客户与销售（3-5 页）**
- 客户构成（按行业、规模、地域）
- Top 客户（匿名或聚合，取决于敏感性）
- 销售渠道与 GTM 策略
- 客户留存率与 NPS
- 合同结构（长度、经常性、续约率）

**VI. 运营（2-4 页）**
- 组织架构
- 关键管理团队（简历）
- 设施与房地产
- 技术栈
- 供应链

**VII. 财务分析（5-8 页）**
- 历史财务（3-5 年完整 P&L）
- EBITDA 调整（正常化）
- 营运资金分析
- 资本支出（维护 vs 增长）
- 预算/预测（如有）

**VIII. 附录**
- 详细财务表格
- 客户列表（如适用）
- 产品目录
- 设施清单
- 重大合同摘要（签署 NDA 后提供）

---

### 🛠️ Skill 21: Datapack Builder（数据包构建）

**用途**：为买方尽职调查组织虚拟数据室  
**输出格式**：文件夹结构 + 索引文件  

**激活关键词**：
```
✅ "build data room for [交易名]"
✅ "organize due diligence datapack"
✅ "/datapack [项目名]"（命令行指令）
```

**数据室标准结构**：
```
01_公司信息/
  - 组织架构图
  - 公司历史文件
  - 产品手册

02_财务/
  - 审计报告（3-5 年）
  - 月度财务包（12-24 个月）
  - 预算与预测
  - 税务申报

03_法律/
  - 公司章程
  - 重大合同
  - 知识产权文件
  - 诉讼记录

04_商业/
  - 客户合同（样本）
  - 供应商协议
  - 销售管道数据
  - 定价表

05_人力资源/
  - 组织架构
  - 关键员工简历
  - 员工福利计划
  - 劳动合同

06_运营/
  - 设施租赁
  - 设备清单
  - IT 系统文档
  - 许可证与认证

07_保险与风险/
  - 保险单
  - 索赔历史
  - 环境报告（如适用）

索引文件.xlsx — 所有文件列表（文件夹、文件名、描述、上传日期）
```

---

### 🎯 Skill 22: Buyer List（买方列表）

**用途**：为 M&A 流程构建潜在买方名单  
**输出格式**：Excel 表格（含买方画像、联系人、外联策略）  

**激活关键词**：
```
✅ "build buyer list for [公司名/行业]"
✅ "potential acquirers for [交易]"
✅ "/buyer-list [项目名]"（命令行指令）
```

**买方类别**：
1. **战略买方**（同行业竞争对手、上下游整合）
2. **财务买方**（PE 基金：平台 vs 并购）
3. **国际买方**（寻求地域扩张）
4. **企业发展部门**（上市公司 M&A 团队）

**买方列表表格结构**：
| 买方名称 | 类型 | 战略契合度 | 近期 M&A 活动 | 关键联系人 | 外联优先级 | 备注 |
|---|---|---|---|---|---|---|
| [公司 A] | 战略 | 高（地域扩张） | 2023 收购 [X] | [姓名], VP Corp Dev | 1 | 已表达兴趣 |

**买方研究清单**：
- 近期交易（过去 2-3 年）
- 估值倍数支付
- 整合策略
- 财务能力（现金、债务容量）
- 决策周期（快速 vs 慎重）

---

### 🔗 Skill 23: Merger Model（并购模型）

**用途**：构建增厚/稀释分析（EPS 影响）  
**输出格式**：Excel 模型（Pro Forma EPS、协同敏感性、购买价格分配）  

**激活关键词**：
```
✅ "build merger model for [收购方] acquiring [目标]"
✅ "accretion dilution analysis"
✅ "/merger-model [交易名]"（命令行指令）
```

**并购模型核心组件**：

**1. 购买价格分析**
| 项目 | 数值 |
| 每股报价 | |
| 对当前股价溢价 | |
| 股权价值 | |
| 加：承担净债务 | |
| 企业价值 | |
| 隐含 EV / EBITDA | |
| 隐含 P/E | |

**2. Sources & Uses**
| 资金来源 | $ | 资金用途 | $ |
| 新增债务 | | 股权购买价 | |
| 账面现金 | | 偿还目标债务 | |
| 新增股权 | | 交易费用 | |
| | | 融资费用 | |
| 总计 | | 总计 | |

**3. Pro Forma EPS 分析**
| | 收购方单独 | 目标单独 | Pro Forma（不含协同） | Pro Forma（含协同） |
|---|---|---|---|---|
| 净利润 | | | | |
| 稀释后股数 | | | | |
| EPS | | | | |
| 增厚/(稀释) | — | — | X% | Y% |

**4. 协同敏感性**（协同规模 × 实现时间）

**5. 交易倍数比较**
- 历史可比交易
- 溢价分析
- 合理性检查

---

### 📑 Skill 24: Process Letter（流程函）

**用途**：撰写 M&A 流程管理函件（时间表、规则、下一步骤）  
**输出格式**：Word 文档（格式信函）  

**激活关键词**：
```
✅ "draft process letter for [交易]"
✅ "write management presentation invitation"
✅ "/process-letter [阶段]"（命令行指令）
```

**流程函类型**：
1. **Teaser 函**（初始外联）
2. **保密协议函**（请求签署 NDA）
3. **CIM 分发函**（交付完整资料）
4. **管理层演示邀请**（第二轮/现场会议）
5. **第二轮竞标邀请**（提交标示性报价）
6. **排他性授予函**（进入独家谈判期）

**示例结构（管理层演示邀请）**：
```
[日期]

[买方联系人]
[公司名]
[地址]

主题：Project [代号] — 管理层演示邀请

尊敬的 [姓名]，

感谢您对 Project [代号] 持续的兴趣，以及您对 [日期] 提交的初步报价。基于您的报价和战略契合度，我们很高兴邀请您进入第二轮流程。

下一步骤：管理层演示
- 日期选项：[日期 1] 或 [日期 2]
- 时间：[开始时间 - 结束时间]
- 地点：[城市/虚拟]
- 议程：公司概览、财务回顾、Q&A

请确认：
1. 您的参会意向及首选日期
2. 参会人员名单（姓名、职位）
3. 任何预先问题或信息请求

时间表：
- [日期]：管理层演示
- [日期]：虚拟数据室开放
- [日期]：标示性报价截止
- [日期]：选择最终候选人

如有任何问题，请随时联系。

此致
敬礼

[您的姓名]
[您的职位]
[银行/顾问公司]
```

---

### 📊 Skill 25: Pitch Deck（推介演示）

**用途**：为潜在客户创建 M&A 或融资推介 Deck  
**输出格式**：PowerPoint（15-25 页）  

**激活关键词**：
```
✅ "build pitch deck for [客户/交易]"
✅ "create sell-side pitch"
✅ "M&A advisory presentation"
```

**推介 Deck 标准结构**（卖方顾问）：
1. 封面页（银行 Logo + 客户名 + 日期 + 机密）
2. 议程
3. 执行摘要（为什么现在、为什么我们）
4. 市场环境（行业趋势、M&A 活跃度）
5. 估值分析（可比公司、可比交易）
6. 买方市场（潜在买方类别、近期交易）
7. 流程建议（时间表、阶段、里程碑）
8. 团队介绍（银行家简历、近期交易经验）
9. 附录（详细财务、交易案例研究）

---

### 🏢 Skill 26: Strip Profile（分拆资料）

**用途**：为卖方资产组合中的单个业务单元创建独立资料  
**输出格式**：Word/PowerPoint（10-20 页）  

**激活关键词**：
```
✅ "create strip profile for [业务单元]"
✅ "carve-out business overview"
```

**分拆资料核心内容**：
- 业务单元独立描述（与母公司分离后）
- 财务"分离"（剥离后独立运营的 P&L）
- 共享服务依赖（IT、HR、财务需剥离的成本）
- 独立运营所需资本支出
- 过渡服务协议（TSA）需求

---

### 📋 Skill 27: Deal Tracker（交易追踪）

**用途**：跟踪实时交易的里程碑、DDL、风险  
**输出格式**：Excel 仪表板（甘特图、状态更新）  

**激活关键词**：
```
✅ "create deal tracker for [交易名]"
✅ "track M&A milestones"
✅ "/deal-tracker [项目名]"（命令行指令）
```

**交易追踪仪表板组件**：
| 里程碑 | 计划日期 | 实际日期 | 负责人 | 状态 | 风险 | 备注 |
|---|---|---|---|---|---|---|
| 签署 NDA | | | | ✅ 完成 | — | |
| 提交 LOI | | | | 🟡 进行中 | 估值差距 | |
| 完成尽职调查 | | | | ⚪ 未开始 | — | |

**关键跟踪指标**：
- 时间表遵守情况（是否按计划）
- 开放行动项（谁负责、截止日）
- 风险日志（问题、影响、缓解措施）
- 买方沟通记录

---

## 私募股权：Private Equity (9 Skills)

> **专业定位**：PE 投资全生命周期（交易寻源、尽职调查、IC 备忘录、投后监控）

### 🔍 Skill 28: Deal Sourcing（交易寻源）

**用途**：发现目标公司、检查 CRM 现有关系、起草创始人外联邮件  
**输出格式**：候选公司列表 + 外联邮件草稿  

**激活关键词**：
```
✅ "source deals in [行业]"
✅ "find companies in [地域/行业]"
✅ "draft founder outreach email"
✅ "/source [筛选条件]"（命令行指令）
```

**寻源工作流程（3 步）**：

**步骤 1：发现公司**
- 行业/赛道焦点（例："东南部的 B2B SaaS 医疗保健"）
- 交易参数（收入范围、EBITDA、增长、地域、所有权类型）
- 数据源（行业报告、会议参会者名单、贸易刊物、竞争格局）
- 输出：候选公司清单（名称、描述、估计收入/规模、地点、创始人/CEO、网站、契合理由）

**步骤 2：CRM 检查**
- 搜索用户邮件（Gmail）查找与公司/创始人的往来记录
- 搜索 Slack 查找内部讨论或提及
- 询问用户："您或团队是否与 [公司] 有过联系？"
- 标记关系状态：
  - "新"（无往来）
  - "现有"（有往来 — 总结）
  - "Previously Passed"（有证据表明曾放弃）

**步骤 3：起草创始人外联**
- 语气：专业但温暖（不过度正式，创始人更喜欢真诚简洁的外联）
- 结构：
  1. 简短自我介绍（您和公司）
  2. 为何这家公司吸引您（引用具体产品、市场地位、增长）
  3. 您的寻求（合作伙伴关系，非仅交易）
  4. 软性邀请（"您是否愿意简短交流？"）
- 个性化：引用公司具体产品、近期新闻或市场地位
- 长度：4-6 句话最多（创始人很忙）
- 语音匹配：如用户有往期外联邮件，研究其语气风格

**外联邮件示例**：
```
主题：[公司名] — 快速介绍

嗨 [创始人名]，

我是 [您的名字]，[PE 公司] 的 [职位]，我们专注于 [行业/赛道]。我一直在关注 [公司名] 在 [具体成就/市场趋势] 方面的进展，印象深刻。

我们正在积极寻找与 [行业] 领域优秀创始人的合作伙伴关系，您的业务非常契合我们的论点。如果您愿意，我很乐意找时间快速交流，了解您的愿景以及我们是否能提供价值。

无压力 — 如果时机不合适，我完全理解。

祝好，
[您的名字]
```

---

### 📋 Skill 29: Deal Screening（交易筛选）

**用途**：快速评估潜在交易是否符合投资标准  
**输出格式**：筛选备忘录（Go/No-Go 建议 + 理由）  

**激活关键词**：
```
✅ "screen this deal"
✅ "initial assessment of [公司名]"
✅ "/screen-deal [公司名]"（命令行指令）
```

**筛选检查清单**：

**✅ 通过门槛（必须满足）**
- 收入范围：[$X - $Y]
- EBITDA 范围：[$X - $Y]
- EBITDA 利润率：>X%
- 地域：[目标区域]
- 行业：在投资论点内

**🎯 优先级评分（1-5 分）**
| 标准 | 权重 | 分数 | 注释 |
|---|---|---|---|
| 市场吸引力（增长、规模） | 20% | | |
| 竞争地位（市场份额、差异化） | 20% | | |
| 财务质量（经常性、利润率、现金流） | 25% | | |
| 管理团队 | 15% | | |
| 增值潜力（有机 + 并购） | 20% | | |
| **总分** | 100% | | |

**🚩 红旗检查**
- 客户集中度 >50%
- 持续亏损或负现金流
- 监管/诉讼风险
- 技术过时或颠覆风险
- 关键人风险（单一创始人，无继任计划）

**建议**：Go（进入下一步）/ Conditional Go（需澄清 X 问题）/ No-Go（理由）

---

### ✅ Skill 30: DD Checklist（尽职调查清单）

**用途**：生成和追踪针对目标公司行业、交易类型、复杂性的综合尽职调查清单  
**输出格式**：Excel 追踪器（请求列表、状态、红旗升级）  

**激活关键词**：
```
✅ "create dd checklist for [公司名]"
✅ "due diligence request list"
✅ "what do we still need for diligence"
✅ "/dd-checklist [项目名]"（命令行指令）
```

**尽职调查工作流**（Skill 详见前文）：
1. 确定范围（目标公司、交易类型、关键顾虑、时间表）
2. 生成工作流清单（财务、商业、法律、运营、人力、IT、环境等）
3. 状态追踪（已请求、已收到、审核中、红旗、已清除）
4. 问题升级（致命、严重、中等、低）

**核心工作流**：
- **财务尽调**：QoE、营运资金、债务、资本支出
- **商业尽调**：市场规模、竞争定位、客户分析、定价权
- **法律尽调**：公司结构、重大合同、诉讼、IP、监管
- **运营尽调**：管理团队、组织架构、IT 系统、供应链
- **人力尽调**：关键员工、薪酬、文化、留存计划
- **IT 尽调**：系统架构、网络安全、数据隐私
- **环境尽调**（如适用）：合规、污染、修复

---

### 📅 Skill 31: DD Meeting Prep（尽调会议准备）

**用途**：为管理层会议或现场访问准备问题清单和议程  
**输出格式**：会议议程 + 问题清单  

**激活关键词**：
```
✅ "prep for management meeting with [公司名]"
✅ "site visit agenda"
✅ "/dd-prep [会议类型]"（命令行指令）
```

**管理层会议议程模板**：
```
Project [代号] — 管理层会议
日期：[日期]
地点：[公司办公室/虚拟]
参会人：[PE 团队] + [管理层团队]

时间表：
09:00 - 09:15    欢迎与介绍
09:15 - 10:30    业务概览（CEO）
10:30 - 11:30    财务回顾（CFO）
11:30 - 12:00    销售与客户动态（CRO）
12:00 - 13:00    午餐
13:00 - 14:00    运营与技术（COO/CTO）
14:00 - 15:00    增长计划与增值机会
15:00 - 15:30    Q&A 与下一步

问题清单：
【业务模式】
- 如何获客？CAC 趋势？
- 客户留存驱动因素？
- 定价权历史？

【财务】
- EBITDA 调整理由？
- 营运资金季节性？
- 资本支出：维护 vs 增长？

【竞争】
- 前3竞争对手及您的差异化？
- 最大威胁？
- 有无失去客户给竞争对手的案例？

【团队】
- 关键人？继任计划？
- 股权激励现状？
- 文化如何？

【增长】
- 未开发的最大机会？
- 需要什么资源/能力来实现？
- 过去错过的机会？教训？
```

---

### 💼 Skill 32: IC Memo（投资委员会备忘录）

**用途**：为 PE 交易审批撰写结构化投资委员会备忘录（Skill 详见前文）  
**输出格式**：Word 文档（10-15 页）  

**激活关键词**：
```
✅ "write IC memo for [交易名]"
✅ "investment committee recommendation"
✅ "/ic-memo [项目名]"（命令行指令）
```

**IC 备忘录标准结构**（Skill 详见前文）：
I. 执行摘要（公司、交易理由、关键条款、建议、回报、Top 3 风险）  
II. 公司概览（业务描述、客户、竞争定位、管理团队）  
III. 行业与市场（市场规模、竞争格局、趋势、监管）  
IV. 财务分析（历史表现、QoE 调整、营运资金、资本支出）  
V. 投资论点（3-5 支柱、增值杠杆、100 天计划）  
VI. 回报分析（Base/Upside/Downside）  
VII. 风险分析（关键风险 + 缓解措施）  
VIII. 交易条款（价格、结构、融资）  
IX. 建议（批准/有条件批准/拒绝）

---

### 📏 Skill 33: Unit Economics（单位经济学分析）

**用途**：分析 PE 目标的单位经济学（Skill 详见前文）  
**输出格式**：Excel 模型 + 分析报告  
**核心适用**：SaaS、订阅、经常性收入业务  

**激活关键词**：
```
✅ "analyze unit economics for [公司名]"
✅ "ARR cohort analysis"
✅ "LTV CAC analysis"
✅ "/unit-economics [公司名]"（命令行指令）
```

**核心指标**（Skill 详见前文）：
- **ARR 桥接**：期初 ARR → 新客 → 扩张 → 收缩 → 流失 → 期末 ARR
- **客户经济学**：CAC、LTV、LTV:CAC 比率（目标 >3x）、CAC 回收期
- **留存与扩张**：总留存、净留存（NDR）、Logo 流失、美元流失、扩张率
- **队列分析**：按年份队列的收入留存与增长
- **利润瀑布**：毛利 → S&M → R&D → G&A → EBITDA

---

### 📈 Skill 34: Returns Analysis（回报分析）

**用途**：计算 PE 投资的预期回报（IRR、MOIC）  
**输出格式**：Excel 模型（Base/Upside/Downside 情景）  

**激活关键词**：
```
✅ "calculate returns for [交易名]"
✅ "PE returns sensitivity"
✅ "/returns [项目名]"（命令行指令）
```

**回报分析结构**：
| 情景 | 退出年份 | 退出 EBITDA | 退出倍数 | 企业价值 | 股权价值 | MOIC | IRR |
|---|---|---|---|---|---|---|---|
| 熊市 | 7 | $XXM | 8x | | | 1.8x | 10% |
| 基准 | 5 | $XXM | 10x | | | 3.0x | 25% |
| 牛市 | 4 | $XXM | 12x | | | 4.5x | 40% |

**敏感性表**：IRR（退出倍数 × 持有期）

**关键驱动因素**：
- EBITDA 增长（有机 + 并购）
- 利润率扩张
- 债务偿还（降低净债务）
- 倍数扩张（或收缩）

---

### 🎯 Skill 35: Value Creation Plan（增值计划）

**用途**：制定 PE 持有期增值蓝图（100 天计划 + 长期战略）  
**输出格式**：PowerPoint 或 Word 文档  

**激活关键词**：
```
✅ "create value creation plan for [公司名]"
✅ "100-day plan"
✅ "portfolio company strategy"
```

**增值计划结构**：

**I. 100 天计划（快赢）**
| 优先级 | 举措 | 负责人 | 完成日期 | 影响（$M EBITDA） | 状态 |
|---|---|---|---|---|---|
| 1 | 实施定价变更 | CRO | Day 60 | +$2M | 计划中 |
| 2 | 优化 SG&A 支出 | CFO | Day 90 | +$1M | 进行中 |

**II. 有机增长杠杆（1-3 年）**
- 地域扩张（进入新市场）
- 产品扩展（交叉销售、新 SKU）
- 客户深化（提升钱包份额、提价）
- 销售效率（缩短销售周期、提升转化率）

**III. 并购战略（1-5 年）**
- 并购论点（地域、产品、客户）
- 目标筛选标准
- 整合能力评估
- 财务影响（EBITDA 增加、倍数套利）

**IV. 运营改进（1-3 年）**
- 利润率扩张计划（采购、自动化、外包）
- 技术投资（CRM、ERP、分析）
- 人才升级（关键招聘、留存计划）
- 流程优化（精益、六西格玛）

**V. 退出定位（3-7 年）**
- 目标退出倍数
- 潜在退出路径（战略出售、二次收购、IPO）
- 退出准备（治理、财务系统、可扩展性）

---

### 📊 Skill 36: Portfolio Monitoring（投资组合监控）

**用途**：追踪投后公司的 KPI、预算合规、价值创造进度  
**输出格式**：Excel 仪表板或 BI 报告  

**激活关键词**：
```
✅ "create portfolio monitoring dashboard"
✅ "track KPIs for [公司名]"
✅ "/portfolio [时间段]"（命令行指令）
```

**仪表板关键组件**：

**财务 KPI**
| 公司 | 收入（实际 vs 预算）| EBITDA（实际 vs 预算）| 现金余额 | 净债务/EBITDA | 备注 |
|---|---|---|---|---|---|
| [公司 A] | $XXM (95%) | $XXM (102%) | $XXM | 3.2x | 超预算 |

**运营 KPI（因行业而异）**
- SaaS：ARR、NDR、CAC、LTV
- 制造：产能利用率、单位成本、库存周转
- 服务：利用率、计费率、员工流动率

**增值进度**
| 举措 | 目标完成日 | 状态 | 延迟原因（如有）| 影响 EBITDA |
|---|---|---|---|---|
| 实施新 CRM | Q2 2024 | ✅ 完成 | — | +$0.5M |
| 完成并购交易 | Q3 2024 | 🟡 延迟 | 尽调延长 | +$3M（推迟）|

**治理检查**
- 董事会会议频次
- 管理层报告及时性
- 审计/合规问题
- 关键人变动

---

## 财富管理：Wealth Management (6 Skills)

> **专业定位**：为财富顾问提供客户服务工具（审查、规划、再平衡、报告）

### 👥 Skill 37: Client Review（客户审查准备）

**用途**：为客户审查会议准备投资组合表现摘要、配置分析、谈话要点（Skill 详见前文）  
**输出格式**：会议包（表现报告 + 配置审查 + 议程）  

**激活关键词**：
```
✅ "prep for client review with [客户名]"
✅ "quarterly review meeting"
✅ "/client-review [客户名]"（命令行指令）
```

**客户审查要点**（Skill 详见前文）：
1. 客户背景（账户类型、总 AUM、IPS、生命阶段）
2. 投资组合表现（QTD/YTD/1Y/3Y/ITD vs 基准）
3. 配置审查（当前 vs 目标、漂移、再平衡需求）
4. 谈话要点（表现归因、市场展望、下一步行动）

---

### 📊 Skill 38: Portfolio Rebalance（投资组合再平衡）

**用途**：分析投资组合配置漂移，生成再平衡交易建议（Skill 详见前文）  
**输出格式**：交易列表（考虑税务影响、交易成本）  

**激活关键词**：
```
✅ "rebalance portfolio for [客户名]"
✅ "allocation drift analysis"
✅ "/rebalance [账户名]"（命令行指令）
```

**再平衡要点**（Skill 详见前文）：
1. 漂移分析（当前 vs 目标 %、超出再平衡带的资产类别）
2. 交易建议（买入/卖出列表）
3. 税务感知规则（优先在 IRA/Roth 再平衡、避免短期收益、收割损失）
4. 资产位置审查（税优账户 vs 应税账户）

---

### 📈 Skill 39: Financial Plan（财务规划）

**用途**：创建综合财务规划（退休、教育、遗产）  
**输出格式**：财务规划文档（目标、假设、预测、建议）  

**激活关键词**：
```
✅ "create financial plan for [客户名]"
✅ "retirement planning analysis"
✅ "/financial-plan [客户名]"（命令行指令）
```

**财务规划核心模块**：

**I. 客户情况**
- 家庭构成、年龄、职业
- 当前资产（投资账户、房产、生意）
- 当前负债（抵押贷款、学生贷款）
- 收入与支出

**II. 目标**
- 退休（目标年龄、期望lifestyle、收入需求）
- 教育（子女数量、学校类型、资助程度）
- 重大购买（房产、旅行）
- 遗产（赠与目标、慈善）

**III. 假设**
- 投资回报率（按资产类别）
- 通胀率
- 税率
- 社会保障/养老金预期

**IV. 预测**
- 退休资产预测（当前储蓄轨迹）
- 缺口分析（需要 vs 预测拥有）
- 蒙特卡洛模拟（成功概率）

**V. 建议**
- 储蓄率调整
- 资产配置优化
- 税务优化策略（Roth 转换、税损收割）
- 保险缺口（寿险、残疾险、长期护理险）
- 遗产规划（遗嘱、委托书、信托）

---

### 💰 Skill 40: Investment Proposal（投资提案）

**用途**：为客户准备特定投资机会的提案  
**输出格式**：提案文档（机会描述、风险、适配性）  

**激活关键词**：
```
✅ "prepare investment proposal for [投资名]"
✅ "pitch [投资] to client"
```

**投资提案结构**：
- 机会描述（资产类别、策略、经理）
- 投资论点（为何现在、为何这个）
- 风险因素（市场、流动性、费用）
- 与客户 IPS 的适配性
- 预期回报与风险（历史、预测）
- 建议配置（% 投资组合、美元金额）

---

### 📄 Skill 41: Client Report（客户报告）

**用途**：生成标准化客户季度报告  
**输出格式**：PDF 报告（表现、持仓、配置、费用）  

**激活关键词**：
```
✅ "generate client report for Q4 2024"
✅ "quarterly report for [客户名]"
✅ "/client-report [客户名] [季度]"（命令行指令）
```

**客户报告标准章节**：
1. 封面页（客户名、报告期、机密）
2. 执行摘要（关键要点、表现概览）
3. 投资组合表现（时间加权回报、基准对比）
4. 资产配置（饼图、当前 vs 目标）
5. 账户持仓明细
6. 交易活动（本季度买入/卖出）
7. 费用摘要（管理费、交易成本）
8. 市场评论（季度回顾、展望）

---

### 🌳 Skill 42: Tax-Loss Harvesting（税损收割）

**用途**：识别税损收割机会（应税账户）  
**输出格式**：交易建议（卖出亏损头寸、替代证券）  

**激活关键词**：
```
✅ "tax-loss harvesting opportunities"
✅ "identify losses for [账户名]"
✅ "/tax-loss-harvesting [账户名]"（命令行指令）
```

**税损收割流程**：
1. 扫描应税账户未实现损失头寸
2. 识别候选（损失 > $X 或 Y%）
3. 检查洗售规则（30 天窗口期内无回购）
4. 建议替代证券（相似但不完全相同）
5. 计算税务节省（损失 × 税率）
6. 生成交易指令

**洗售规则合规**：
- 卖出后 30 天内不得回购同一证券
- 跨账户检查（IRA 购买会触发洗售）
- 替代证券建议（不同发行人的同类 ETF、同行业不同股票）

---

## 合作伙伴插件（Partner-Built）

### LSEG Plugin（伦敦证券交易所集团）

**数据覆盖**：固定收益、外汇、股票、宏观  
**核心命令（8 个）**：
1. 债券定价
2. 收益率曲线分析
3. FX 套息交易评估
4. 期权估值
5. 宏观仪表板构建
6. 主权债务分析
7. 信用利差追踪
8. 商品价格监控

**触发关键词**：
```
✅ "price this bond using LSEG"
✅ "analyze yield curve"
✅ "FX carry trade opportunities"
```

---

### S&P Global Plugin（标准普尔全球）

**数据来源**：S&P Capital IQ  
**核心功能**：
1. 公司简报（Tearsheet）
2. 盈利预览
3. 融资摘要

**多受众支持**：
- 股票研究
- 投资银行 / M&A
- 企业发展
- 销售

**触发关键词**：
```
✅ "generate company tearsheet using S&P"
✅ "earnings preview from Capital IQ"
```

---

## 如何创建新 Skill

### Skill 标准文件结构

每个 Skill 必须包含以下文件：

```
your-skill-name/
├── SKILL.md                # 核心指令文件（必须）
├── examples/               # 示例文件（可选但推荐）
│   ├── example_output.xlsx
│   └── example_report.docx
├── references/             # 参考资料（可选）
│   ├── frameworks.md
│   └── schemas.md
└── templates/              # 模板文件（可选）
    └── template.xlsx
```

---

### SKILL.md 文件标准格式

```markdown
---
name: your-skill-name
description: |
  一句话描述技能用途。说明何时使用、输出内容、适用场景。
  
  **Perfect for:**
  - 使用场景 1
  - 使用场景 2
  - 使用场景 3
  
  **Not ideal for:**
  - 不适用场景 1
  - 不适用场景 2
---

# Skill 标题

## Overview
技能概览（2-3 段）：
- 这个技能做什么
- 为谁设计
- 输出什么格式

## When to Use

明确列出触发关键词：
- "用户请求 X"
- "用户说 Y"
- "/command-name"

**Do NOT use if:**
- 条件 A→使用其他技能
- 条件 B→不适用

## Critical Requirements

⭐⭐⭐ 必须遵守的规则：
1. 数据源优先级（MCP > Bloomberg > Web）
2. 输出格式标准（Excel 公式颜色约定、Word 字体要求）
3. 质量门槛（错误零容忍、来源标注强制）

## Workflow

### Step 1: [步骤名称]
详细说明第一步做什么、需要哪些输入

### Step 2: [步骤名称]
详细说明第二步...

### Step 3: [步骤名称]
详细说明第三步...

## Output Format

输出的详细规范：
- 文件类型（.xlsx, .docx, .pptx）
- 结构要求（章节、表格、图表）
- 格式标准（字体、颜色、对齐）

## Examples

（如有）引用 `examples/` 文件夹中的示例文件

## Quality Checks

交付前必须验证的检查清单：
- [ ] 所有公式无错误
- [ ] 数据来源已标注
- [ ] 格式符合标准
- [ ] 逻辑一致性验证

## Common Pitfalls

常见错误及避免方法：
- ❌ 错误做法 A → ✅ 正确做法是 X
- ❌ 错误做法 B → ✅ 正确做法是 Y

## Related Skills

相关技能链接（如适用）：
- 参见 `dcf-model` 技能进行估值
- 参见 `competitive-analysis` 技能进行市场研究
```

---

### 创建 Skill 的 10 条黄金法则

1. **单一职责原则**：每个 Skill 只做一件事，并做好
2. **明确触发词**：用户应能轻松知道何时使用（通过关键词或 `/command`）
3. **数据源优先级**：始终优先使用 MCP 数据源，明确禁止不可靠来源
4. **输出标准化**：定义清晰的输出格式（Excel 颜色约定、Word 结构）
5. **工作流可复现**：Step-by-step 流程应任何人都能遵循
6. **质量门槛硬性**：定义"合格"输出的最低标准（例：零公式错误）
7. **示例驱动学习**：提供 `examples/` 文件夹中的真实案例
8. **反面案例清晰**：明确"何时不使用"和"常见错误"
9. **关联技能链接**：帮助用户发现相关工作流
10. **版本控制与更新**：在 SKILL.md 顶部记录版本号和更新日志

---

### Skill 创建检查清单

在提交新 Skill 前，确保满足：

**✅ 必须项**
- [ ] `SKILL.md` 文件存在且包含所有必需章节
- [ ] `name` 和 `description` 字段完整
- [ ] 至少 3 个明确的触发关键词
- [ ] 工作流分解为清晰的步骤
- [ ] 输出格式有详细规范
- [ ] 质量检查清单明确

**✅ 推荐项**
- [ ] 至少 1 个 `examples/` 文件夹中的示例
- [ ] "何时不使用"明确声明
- [ ] 常见错误与解决方案
- [ ] 与其他 Skills 的关联

**✅ 高级项**
- [ ] `references/` 文件夹包含框架或模板
- [ ] 多情景示例（简单/中等/复杂）
- [ ] 错误处理与边缘案例
- [ ] 性能优化建议（对于计算密集型技能）

---

## 附录：快速参考

### 全部 41 Skills 按字母顺序

| # | Skill 名称 | 所属插件 | 核心用途 | 触发词示例 |
|:---:|---|---|---|---|
| 1 | 3-Statements Model | Financial Analysis | 三表联动模型 | `/3-statements` |
| 2 | Buyer List | Investment Banking | 构建买方列表 | `/buyer-list` |
| 3 | Catalyst Calendar | Equity Research | 催化剂日历 | `/catalysts` |
| 4 | Check Deck | Financial Analysis | 演示文稿审核 | `/check-deck` |
| 5 | Check Model | Financial Analysis | 财务模型审核 | `/debug-model` |
| 6 | CIM Builder | Investment Banking | 机密信息备忘录 | `/cim` |
| 7 | Client Report | Wealth Management | 客户季度报告 | `/client-report` |
| 8 | Client Review | Wealth Management | 客户审查准备 | `/client-review` |
| 9 | Competitive Analysis | Financial Analysis | 竞争格局分析 | `competitive landscape` |
| 10 | Comps Analysis | Financial Analysis | 可比公司分析 | `/comps` |
| 11 | Datapack Builder | Investment Banking | 数据室构建 | `/datapack` |
| 12 | DCF Model | Financial Analysis | 现金流折现模型 | `/dcf` |
| 13 | DD Checklist | Private Equity | 尽职调查清单 | `/dd-checklist` |
| 14 | DD Meeting Prep | Private Equity | 尽调会议准备 | `/dd-prep` |
| 15 | Deal Screening | Private Equity | 交易筛选 | `/screen-deal` |
| 16 | Deal Sourcing | Private Equity | 交易寻源 | `/source` |
| 17 | Deal Tracker | Investment Banking | 交易追踪 | `/deal-tracker` |
| 18 | Earnings Analysis | Equity Research | 季度盈利分析 | `/earnings` |
| 19 | Earnings Preview | Equity Research | 盈利预览 | `/earnings-preview` |
| 20 | Financial Plan | Wealth Management | 财务规划 | `/financial-plan` |
| 21 | IC Memo | Private Equity | 投资委员会备忘录 | `/ic-memo` |
| 22 | Idea Generation | Equity Research | 投资创意筛选 | `/screen` |
| 23 | Initiating Coverage | Equity Research | 覆盖启动报告 | `/initiate` |
| 24 | Investment Proposal | Wealth Management | 投资提案 | `investment proposal` |
| 25 | LBO Model | Financial Analysis | 杠杆收购模型 | `/lbo` |
| 26 | Merger Model | Investment Banking | 并购模型 | `/merger-model` |
| 27 | Model Update | Equity Research | 模型更新 | `/model-update` |
| 28 | Morning Note | Equity Research | 晨会简报 | `/morning-note` |
| 29 | Pitch Deck | Investment Banking | 推介演示 | `pitch deck` |
| 30 | Portfolio Monitoring | Private Equity | 投资组合监控 | `/portfolio` |
| 31 | Portfolio Rebalance | Wealth Management | 投资组合再平衡 | `/rebalance` |
| 32 | PPT Template Creator | Financial Analysis | PPT 模板创建 | `/ppt-template` |
| 33 | Process Letter | Investment Banking | 流程函 | `/process-letter` |
| 34 | Returns Analysis | Private Equity | 回报分析 | `/returns` |
| 35 | Sector Overview | Equity Research | 行业综述 | `/sector` |
| 36 | Skill Creator | Financial Analysis | 技能创建器 | `/create-skill` |
| 37 | Strip Profile | Investment Banking | 分拆资料 | `strip profile` |
| 38 | Tax-Loss Harvesting | Wealth Management | 税损收割 | `/tax-loss-harvesting` |
| 39 | Teaser | Investment Banking | 项目简介 | `/teaser` |
| 40 | Thesis Tracker | Equity Research | 投资论点追踪 | `/thesis` |
| 41 | Unit Economics | Private Equity | 单位经济学分析 | `/unit-economics` |
| 42 | Value Creation Plan | Private Equity | 增值计划 | `value creation plan` |

---

### 按工作流分类

**估值与建模**：Comps Analysis, DCF Model, LBO Model, 3-Statements, Merger Model, Returns Analysis  
**股票研究**：Initiating Coverage, Earnings Analysis, Morning Note, Sector Overview, Model Update  
**M&A 交易**：Teaser, CIM Builder, Buyer List, Deal Tracker, Pitch Deck  
**PE 投资**：Deal Sourcing, DD Checklist, IC Memo, Unit Economics, Value Creation Plan  
**客户服务**：Client Review, Portfolio Rebalance, Financial Plan, Client Report  
**审核与 QC**：Check Deck, Check Model  

---

## 版本历史

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v1.0 | 2026-02-26 | 初始版本：41 Skills 完整梳理 |

---

**文档状态**：✅ 完成  
**适用于**：Financial Services Plugins（所有版本）  
**维护者**：投研认知框架团队  
**反馈渠道**：提交 Issue 到 GitHub 或联系 [维护者]

---

*「将专业知识封装为可复用的 Skills，让 AI 成为机构级金融分析引擎。」*
