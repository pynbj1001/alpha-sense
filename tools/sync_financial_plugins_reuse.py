#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "14.external" / "financial-services-plugins"
VSCODE_MCP = ROOT / ".vscode" / "mcp.json"
SKILLS_ROOT = ROOT / ".github" / "skills"
PROMPTS_ROOT = ROOT / ".github" / "prompts"
REPORT_DOC = ROOT / "07-实操工具与模板" / "FSP-复用清单.md"


@dataclass
class SyncStats:
    mcp_servers: int = 0
    skills: int = 0
    prompts: int = 0


def slug(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff._-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "unnamed"


def parse_plugin_and_item(path: Path, anchor: str) -> tuple[str, str]:
    # e.g. financial-analysis/skills/dcf-model/SKILL.md
    rel = path.relative_to(SRC)
    parts = rel.parts
    plugin = parts[0]

    try:
        idx = parts.index(anchor)
        item = parts[idx + 1]
    except ValueError:
        item = path.stem
    return slug(plugin), slug(item)


def collect_mcp_servers() -> dict[str, dict]:
    servers: dict[str, dict] = {}
    seen_conf: dict[str, str] = {}
    for p in SRC.glob("**/.mcp.json"):
        raw = json.loads(p.read_text(encoding="utf-8"))
        plugin, _ = parse_plugin_and_item(p, anchor=".")
        mcp_servers = raw.get("mcpServers", {})
        for name, conf in mcp_servers.items():
            n = slug(name)
            conf_key = json.dumps(conf, ensure_ascii=False, sort_keys=True)

            if conf_key in seen_conf:
                continue

            if n in servers and servers[n] != conf:
                n = f"{n}-{plugin}"
            servers[n] = conf
            seen_conf[conf_key] = n
    return dict(sorted(servers.items(), key=lambda x: x[0]))


def write_vscode_mcp(servers: dict[str, dict]) -> None:
    VSCODE_MCP.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "$schema": "https://raw.githubusercontent.com/microsoft/vscode/main/extensions/mcp/schemas/mcp.schema.json",
        "servers": servers,
    }
    VSCODE_MCP.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def sync_skills() -> int:
    for old in SKILLS_ROOT.glob("fsp-*"):
        if old.is_dir():
            shutil.rmtree(old)

    count = 0
    for skill_file in SRC.glob("**/SKILL.md"):
        plugin, skill = parse_plugin_and_item(skill_file, anchor="skills")
        target_dir = SKILLS_ROOT / f"fsp-{plugin}-{skill}"
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(skill_file, target_dir / "SKILL.md")

        source_note = (
            "# Source\n\n"
            f"- Origin: financial-services-plugins\n"
            f"- Path: {skill_file.relative_to(ROOT)}\n"
        )
        (target_dir / "SOURCE.md").write_text(source_note, encoding="utf-8")
        count += 1
    return count


def sync_prompts() -> int:
    count = 0
    target_root = PROMPTS_ROOT / "financial-services-plugins"
    target_root.mkdir(parents=True, exist_ok=True)

    for old in target_root.glob("fsp-*.prompt.md"):
        old.unlink(missing_ok=True)

    for cmd_file in SRC.glob("**/commands/*.md"):
        plugin, _ = parse_plugin_and_item(cmd_file, anchor="commands")
        cmd = slug(cmd_file.stem)
        target = target_root / f"fsp-{plugin}-{cmd}.prompt.md"
        body = cmd_file.read_text(encoding="utf-8")

        if "description:" not in body.splitlines()[0:10]:
            header = "---\ndescription: Reused workflow command from financial-services-plugins\n---\n\n"
            body = header + body

        body = (
            "<!-- Reused from anthropics/financial-services-plugins. -->\n"
            "<!-- Keep aligned by rerunning tools/sync_financial_plugins_reuse.py -->\n\n"
            + body
        )
        target.write_text(body, encoding="utf-8")
        count += 1

    return count


def write_report(stats: SyncStats, servers: dict[str, dict]) -> None:
    REPORT_DOC.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Financial Services Plugins 复用清单",
        "",
        "- 来源仓库：anthropics/financial-services-plugins",
        f"- 同步时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- MCP Servers：{stats.mcp_servers}",
        f"- Skills：{stats.skills}",
        f"- Prompt 模板：{stats.prompts}",
        "",
        "## 产物路径",
        "",
        "- VS Code MCP 配置：.vscode/mcp.json",
        "- 复用技能目录：.github/skills/fsp-*",
        "- 复用提示模板：.github/prompts/financial-services-plugins/*.prompt.md",
        "",
        "## MCP Server 列表",
        "",
        "| Name | Type | URL |",
        "| --- | --- | --- |",
    ]
    for name, conf in servers.items():
        lines.append(f"| {name} | {conf.get('type','')} | {conf.get('url','')} |")

    lines.extend(
        [
            "",
            "## 注意",
            "",
            "- 多数金融数据端点需要各自供应商订阅与凭证。",
            "- 请勿在 mcp.json 中硬编码密钥，优先使用 VS Code 输入变量或环境变量。",
            "- 若上游插件更新，重新执行：python tools/sync_financial_plugins_reuse.py",
            "",
        ]
    )
    REPORT_DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if not SRC.exists():
        print(f"未找到源目录: {SRC}")
        return 2

    servers = collect_mcp_servers()
    write_vscode_mcp(servers)
    skills_count = sync_skills()
    prompts_count = sync_prompts()

    stats = SyncStats(mcp_servers=len(servers), skills=skills_count, prompts=prompts_count)
    write_report(stats, servers)

    print(json.dumps(stats.__dict__, ensure_ascii=False, indent=2))
    print("mcp.json ->", VSCODE_MCP)
    print("skills ->", SKILLS_ROOT)
    print("prompts ->", PROMPTS_ROOT / "financial-services-plugins")
    print("report ->", REPORT_DOC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
