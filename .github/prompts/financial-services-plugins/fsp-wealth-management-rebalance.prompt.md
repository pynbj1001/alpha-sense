<!-- Reused from anthropics/financial-services-plugins. -->
<!-- Keep aligned by rerunning tools/sync_financial_plugins_reuse.py -->

---
description: Reused workflow command from financial-services-plugins
---

---
description: Analyze drift and generate rebalancing trades
argument-hint: "[client name or account]"
---

Load the `portfolio-rebalance` skill to analyze allocation drift and recommend tax-aware rebalancing trades.

If a client or account is provided, use it. Otherwise ask for the portfolio to analyze.
