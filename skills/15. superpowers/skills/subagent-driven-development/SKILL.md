---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks in the current session
---

# Subagent-Driven Development

Execute plan by dispatching fresh subagent per task, with two-stage review after each: spec compliance review first, then code quality review.

**Core principle:** Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration

## When to Use

- **Have implementation plan?** → yes
- **Tasks mostly independent?** → yes
- **Stay in this session?** → yes → use `subagent-driven-development`
- **Need parallel session?** → use `executing-plans`

## The Process

```
1. Read plan, extract ALL tasks with full text + context
2. Create TodoWrite with all tasks

Per task:
  a. Dispatch implementer subagent (provide full task text + context)
  b. Answer any questions from subagent before proceeding
  c. Subagent implements, tests, commits, self-reviews
  d. Dispatch SPEC COMPLIANCE reviewer subagent
     → If fails: implementer fixes → re-review until ✅
  e. Dispatch CODE QUALITY reviewer subagent
     → If fails: implementer fixes → re-review until ✅
  f. Mark task complete

3. After all tasks: Dispatch final code reviewer for entire implementation
4. Use superpowers:finishing-a-development-branch
```

## Two-Stage Review Order

**1st: Spec Compliance** — Does code match the spec? Nothing missing? Nothing extra?  
**2nd: Code Quality** — Is the implementation well-built?  
**⚠️ Never start code quality review before spec compliance is ✅**

## Red Flags — Never:
- Start on main/master without explicit user consent
- Skip either review stage
- Proceed with unfixed issues
- Dispatch multiple implementation subagents in parallel (conflicts)
- Make subagent read plan file (provide full text instead)
- Accept "close enough" on spec compliance

## Advantages vs. Manual Execution
- Subagents follow TDD naturally
- Fresh context per task (no confusion)
- Two-stage quality gates
- Questions surfaced before work begins (not after)

## Integration
- **REQUIRED before:** `superpowers:using-git-worktrees`
- **Creates plan:** `superpowers:writing-plans`
- **After all tasks:** `superpowers:finishing-a-development-branch`
