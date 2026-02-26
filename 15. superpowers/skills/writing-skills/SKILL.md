---
name: writing-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---

# Writing Skills

## Overview

**Writing skills IS Test-Driven Development applied to process documentation.**

You write test cases (pressure scenarios), watch them fail (baseline behavior without skill), write the skill (documentation), watch tests pass (agents comply), and refactor (close loopholes).

**Core principle:** If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.

## What is a Skill?

A **skill** is a reference guide for proven techniques, patterns, or tools.

**Skills are:** Reusable techniques, patterns, tools, reference guides  
**Skills are NOT:** Narratives about how you solved a problem once

## TDD Mapping for Skills

| TDD Concept | Skill Creation |
|-------------|----------------|
| **Test case** | Pressure scenario with subagent |
| **Production code** | Skill document (SKILL.md) |
| **Test fails (RED)** | Agent violates rule without skill |
| **Test passes (GREEN)** | Agent complies with skill present |
| **Refactor** | Close loopholes while maintaining compliance |

## SKILL.md Structure

```markdown
---
name: skill-name-with-hyphens
description: Use when [specific triggering conditions and symptoms]
---

# Skill Name

## Overview
Core principle in 1-2 sentences.

## When to Use
Bullet list with SYMPTOMS and use cases / When NOT to use

## Core Pattern
Before/after comparison

## Quick Reference
Table or bullets for scanning

## Common Mistakes
What goes wrong + fixes
```

## Critical Rules for Description Field

**Description = When to Use, NOT What the Skill Does**

```yaml
# ❌ BAD: Summarizes workflow
description: Use when executing plans - dispatches subagent per task with code review

# ✅ GOOD: Just triggering conditions
description: Use when executing implementation plans with independent tasks in the current session
```

**Why:** If description summarizes workflow, Claude will follow the summary instead of reading the full skill content.

## The Iron Law (Same as TDD)

```
NO SKILL WITHOUT A FAILING TEST FIRST
```

Write skill before testing? Delete it. Start over.

## Skill Creation Checklist (TDD Adapted)

**RED Phase:**
- [ ] Create pressure scenarios (3+ combined pressures)
- [ ] Run scenarios WITHOUT skill — document baseline behavior
- [ ] Identify rationalization patterns

**GREEN Phase:**
- [ ] Name uses only letters, numbers, hyphens
- [ ] YAML frontmatter with only name + description (max 1024 chars)
- [ ] Description starts with "Use when..." — triggering conditions only
- [ ] Address specific baseline failures from RED phase
- [ ] One excellent code example (not multi-language)
- [ ] Run scenarios WITH skill — verify agents comply

**REFACTOR Phase:**
- [ ] Add explicit counters for new rationalizations
- [ ] Build rationalization table
- [ ] Create red flags list
- [ ] Re-test until bulletproof

## Anti-Patterns

❌ **Narrative Example** — "In session 2025-10-03, we found..."  
❌ **Multi-Language Dilution** — example-js.js, example-py.py, example-go.go  
❌ **Generic Labels** — helper1, helper2, step3

## The Bottom Line

**Creating skills IS TDD for process documentation.**

Same Iron Law: No skill without failing test first.  
Same cycle: RED (baseline) → GREEN (write skill) → REFACTOR (close loopholes).
