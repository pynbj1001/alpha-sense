<!-- Reused from anthropics/financial-services-plugins. -->
<!-- Keep aligned by rerunning tools/sync_financial_plugins_reuse.py -->

---
description: Reused workflow command from financial-services-plugins
---

---
description: Screen an inbound deal (CIM or teaser)
argument-hint: "[path to CIM/teaser file]"
---

Load the `deal-screening` skill and quickly evaluate an inbound deal against the fund's investment criteria.

If a file path is provided, use it. Otherwise ask the user for the deal materials or description.
