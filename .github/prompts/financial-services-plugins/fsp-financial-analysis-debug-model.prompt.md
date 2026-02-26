<!-- Reused from anthropics/financial-services-plugins. -->
<!-- Keep aligned by rerunning tools/sync_financial_plugins_reuse.py -->

---
description: Reused workflow command from financial-services-plugins
---

---
description: Debug and audit a financial model for errors
argument-hint: "[path to .xlsx model file]"
---

Load the `check-model` skill and audit the specified financial model for broken formulas, balance sheet imbalances, hardcoded overrides, circular references, and logic errors.

If a file path is provided, use it. Otherwise ask the user for the model to review.
