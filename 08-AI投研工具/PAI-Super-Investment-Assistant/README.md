# PAI Super Investment Assistant (Windows-first Integration)

This package integrates `Personal_AI_Infrastructure` into this investment framework without overwriting your global AI setup.

## What This Adds

- Local PAI runtime in `.pai_runtime/.claude`
- Windows-safe config generation
- `InvestmentCRO` custom skill for this repository
- Continuous memory update hook after each dialogue turn
- One-command setup, verification, and task runners

## Why Local Runtime

Upstream PAI v2.5 installer is Unix-oriented (`chown`, `find`, `lsof`, `bash`), and `PLATFORM.md` marks Windows as unsupported. This integration keeps upstream files intact and applies a local compatibility layer.

## Quick Start

Run from repository root:

```powershell
.\08-AI投研工具\PAI-Super-Investment-Assistant\setup.ps1
.\08-AI投研工具\PAI-Super-Investment-Assistant\verify.ps1
```

Then run daily workflows:

```powershell
.\08-AI投研工具\PAI-Super-Investment-Assistant\run.ps1 -Workflow tracker -NewsLimit 8
.\08-AI投研工具\PAI-Super-Investment-Assistant\run.ps1 -Workflow bond
```

## Installed Layout

- Upstream source: `08-AI投研工具/Personal_AI_Infrastructure` (preferred) or `08-AI投研工具/Personal_AI_Infrastructure_upstream` (fallback)
- Runtime: `.pai_runtime/.claude`
- Custom skill: `.pai_runtime/.claude/skills/InvestmentCRO/SKILL.md`
- Auto-updated profile memory:
  - `.pai_runtime/.claude/skills/InvestmentCRO/USER/GOALS.md`
  - `.pai_runtime/.claude/skills/InvestmentCRO/USER/THOUGHTS.md`
  - `.pai_runtime/.claude/skills/InvestmentCRO/USER/PREFERENCES.md`
  - `.pai_runtime/.claude/skills/InvestmentCRO/USER/EXPERIENCE.md`
- Runtime pointer: `.pai_runtime/USE_THIS_PAI_DIR.txt`

## Using with AI Agents

1. Keep your current project instructions (`AGENTS.md`, `.github/copilot-instructions.md`) as the primary policy.
2. Use `.pai_runtime/.claude/skills/InvestmentCRO/SKILL.md` for PAI-style workflow routing.
3. Use existing project scripts for hard data:
   - `python stock_tracker.py run-daily --news-limit 8`
   - `python bond_data.py --all`

## Notes

- This setup does not replace your global `~/.claude`.
- Hooks and statusline are disabled in runtime settings for Windows safety.
- You can re-enable advanced hooks later after validating each one in your environment.
