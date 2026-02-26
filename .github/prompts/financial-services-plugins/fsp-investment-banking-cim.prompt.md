<!-- Reused from anthropics/financial-services-plugins. -->
<!-- Keep aligned by rerunning tools/sync_financial_plugins_reuse.py -->

---
description: Reused workflow command from financial-services-plugins
---

---
description: Draft a Confidential Information Memorandum
argument-hint: "[company name]"
---

Load the `cim-builder` skill and structure a CIM for the specified company.

If a company name is provided, use it. Otherwise ask the user for the target company and available source materials.
