<!-- Reused from anthropics/financial-services-plugins. -->
<!-- Keep aligned by rerunning tools/sync_financial_plugins_reuse.py -->

---
description: Reused workflow command from financial-services-plugins
---

---
description: Analyze unit economics (ARR cohorts, LTV/CAC, retention)
argument-hint: "[company name or path to data]"
---

Load the `unit-economics` skill and analyze customer economics, ARR cohorts, net retention, and revenue quality.

If a company or file is provided, use it. Otherwise ask the user for the target and available data.
