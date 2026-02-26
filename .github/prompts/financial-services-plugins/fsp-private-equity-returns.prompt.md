<!-- Reused from anthropics/financial-services-plugins. -->
<!-- Keep aligned by rerunning tools/sync_financial_plugins_reuse.py -->

---
description: Reused workflow command from financial-services-plugins
---

---
description: Build IRR/MOIC sensitivity tables
argument-hint: "[company or deal parameters]"
---

Load the `returns-analysis` skill and model PE returns with sensitivity across entry multiple, leverage, exit multiple, and growth scenarios.

If deal parameters are provided, use them. Otherwise ask the user for entry EBITDA, valuation, and financing assumptions.
