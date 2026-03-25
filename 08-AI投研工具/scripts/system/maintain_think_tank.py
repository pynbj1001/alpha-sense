"""
智囊团（THINK-TANK）定期维护脚本
===================================
每周运行一次，扫描大师知识源文件夹，检测新增/变更文件，
生成迭代建议报告，帮助持续提升大师洞见能力。

用法：
    python maintain_think_tank.py           # 完整扫描 + 生成报告
    python maintain_think_tank.py --diff    # 仅显示自上次扫描以来的变化
    python maintain_think_tank.py --stats   # 显示各大师知识源统计
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# 配置：五位大师的知识源目录映射
# ============================================================

BASE_DIR = Path(__file__).parent

MASTERS = {
    "巴菲特": {
        "emoji": "🛡️",
        "dimension": "商业质量 & 护城河",
        "sources": [
            BASE_DIR / "01-价值投资体系" / "巴菲特",
        ],
        "extra_files": [],
    },
    "芒格": {
        "emoji": "🔍",
        "dimension": "多元思维 & 逆向检验",
        "sources": [
            BASE_DIR / "01-价值投资体系" / "芒格之道",
        ],
        "extra_files": [],
    },
    "卡拉曼": {
        "emoji": "⚖️",
        "dimension": "风险控制 & 安全边际",
        "sources": [
            BASE_DIR / "01-价值投资体系" / "赛斯 卡拉曼 研究框架",
        ],
        "extra_files": [],
    },
    "费雪": {
        "emoji": "🌱",
        "dimension": "成长质量 & 长期持有",
        "sources": [
            BASE_DIR / "02-成长投资体系",
        ],
        "extra_files": [],
    },
    "周金涛": {
        "emoji": "🌊",
        "dimension": "宏观周期 & 择时",
        "sources": [
            BASE_DIR / "03-宏观与周期",
        ],
        "extra_files": [],
    },
}

# 候补大师
BENCH_MASTERS = {
    "格林沃尔德": {"sources": [BASE_DIR / "00-核心投研指南"]},
    "帕伯莱": {"sources": [BASE_DIR / "04-大师投资框架"]},
    "李国飞": {"sources": [BASE_DIR / "02-成长投资体系" / "李国飞禅道投资"]},
    "毛泽东": {"sources": [BASE_DIR / "04-大师投资框架" / "毛泽东思想，论持久战"]},
}

SCAN_EXTENSIONS = {".txt", ".md", ".docx", ".pdf"}
STATE_FILE = BASE_DIR / ".think_tank_state.json"
REPORT_DIR = BASE_DIR / "10-研究报告输出"


def scan_files(directories: list[Path]) -> dict:
    """扫描目录中的所有知识文件，返回 {相对路径: {size, mtime, hash}} 字典"""
    result = {}
    for directory in directories:
        if not directory.exists():
            continue
        for root, _, files in os.walk(directory):
            for fname in files:
                fpath = Path(root) / fname
                if fpath.suffix.lower() in SCAN_EXTENSIONS:
                    rel = str(fpath.relative_to(BASE_DIR))
                    stat = fpath.stat()
                    result[rel] = {
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                    }
    return result


def load_previous_state() -> dict:
    """加载上一次扫描的状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    """保存本次扫描状态"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def compute_diff(old_state: dict, new_state: dict) -> dict:
    """计算文件变更：新增、修改、删除"""
    old_files = set(old_state.keys())
    new_files = set(new_state.keys())

    added = new_files - old_files
    removed = old_files - new_files
    modified = set()
    for f in old_files & new_files:
        if (old_state[f]["size"] != new_state[f]["size"] or
                old_state[f]["mtime"] != new_state[f]["mtime"]):
            modified.add(f)

    return {
        "added": sorted(added),
        "modified": sorted(modified),
        "removed": sorted(removed),
    }


def classify_changes_by_master(diff: dict) -> dict:
    """将变更按大师分类"""
    result = {name: {"added": [], "modified": [], "removed": []} for name in MASTERS}
    result["其他"] = {"added": [], "modified": [], "removed": []}

    for change_type in ["added", "modified", "removed"]:
        for fpath in diff[change_type]:
            assigned = False
            for master_name, config in MASTERS.items():
                for src_dir in config["sources"]:
                    rel_src = str(src_dir.relative_to(BASE_DIR))
                    if fpath.startswith(rel_src):
                        result[master_name][change_type].append(fpath)
                        assigned = True
                        break
                if assigned:
                    break
            if not assigned:
                result["其他"][change_type].append(fpath)

    return result


def generate_stats():
    """生成各大师知识源统计"""
    print("\n" + "=" * 60)
    print("📊 智囊团知识源统计")
    print("=" * 60)

    total_files = 0
    total_size = 0

    for name, config in MASTERS.items():
        files = scan_files(config["sources"])
        file_count = len(files)
        size_sum = sum(f["size"] for f in files.values())
        total_files += file_count
        total_size += size_sum

        # 按格式统计
        format_counts = {}
        for fpath in files:
            ext = Path(fpath).suffix.lower()
            format_counts[ext] = format_counts.get(ext, 0) + 1

        format_str = " | ".join(f"{ext}: {cnt}" for ext, cnt in sorted(format_counts.items()))

        print(f"\n{config['emoji']} {name}（{config['dimension']}）")
        print(f"   文件数: {file_count}  |  总大小: {size_sum / 1024:.0f} KB")
        print(f"   格式: {format_str}")

        # 列出文件名
        for fpath in sorted(files.keys()):
            fname = Path(fpath).name
            fsize = files[fpath]["size"]
            print(f"   📄 {fname} ({fsize / 1024:.0f} KB)")

    print(f"\n{'─' * 60}")
    print(f"📈 总计: {total_files} 个文件, {total_size / 1024:.0f} KB")


def generate_iteration_report(master_changes: dict) -> str:
    """生成迭代建议报告"""
    today = datetime.now().strftime("%Y-%m-%d")
    has_changes = any(
        any(changes.values())
        for changes in master_changes.values()
    )

    lines = [
        f"# 🔄 智囊团迭代维护报告",
        f"> 扫描日期：{today}",
        f"> 状态：{'检测到变更，建议迭代' if has_changes else '无变更，当前版本最新'}",
        "",
    ]

    if not has_changes:
        lines.append("本周未检测到知识源文件变更。所有大师思维引擎保持最新。")
        lines.append("")
        lines.append("## 📋 建议的主动迭代方向")
        lines.append("")
        lines.append("即便没有文件变更，也建议定期主动深挖以下方向：")
        lines.append("")
        lines.append("1. **巴菲特**：重读巴菲特致股东信，提取新的商业洞察和资本配置案例")
        lines.append("2. **芒格**：从100模型中选取新的跨学科模型，补充投资启示")
        lines.append("3. **卡拉曼**：更新市场狂热探测的当前信号检查")
        lines.append("4. **费雪**：跟踪十倍股统计数据的最新研究")
        lines.append("5. **周金涛**：更新周期仪表盘的当前阶段判断")
        return "\n".join(lines)

    lines.append("## 📝 检测到的变更")
    lines.append("")

    for master_name, changes in master_changes.items():
        if not any(changes.values()):
            continue

        emoji = MASTERS.get(master_name, {}).get("emoji", "📌")
        lines.append(f"### {emoji} {master_name}")
        lines.append("")

        if changes["added"]:
            lines.append("**新增文件**：")
            for f in changes["added"]:
                lines.append(f"- 🆕 `{Path(f).name}`")
            lines.append("")

        if changes["modified"]:
            lines.append("**已修改文件**：")
            for f in changes["modified"]:
                lines.append(f"- ✏️ `{Path(f).name}`")
            lines.append("")

        if changes["removed"]:
            lines.append("**已删除文件**：")
            for f in changes["removed"]:
                lines.append(f"- ❌ `{Path(f).name}`")
            lines.append("")

    lines.append("## 🎯 迭代建议")
    lines.append("")
    lines.append("请使用以下 Copilot 指令来执行迭代：")
    lines.append("")
    lines.append("```")
    lines.append("请根据以下新增/变更的知识文件，迭代升级 THINK-TANK.md 中对应大师的思维引擎：")

    for master_name, changes in master_changes.items():
        if changes["added"] or changes["modified"]:
            new_files = changes["added"] + changes["modified"]
            lines.append(f"- {master_name}：{', '.join(Path(f).name for f in new_files)}")

    lines.append("")
    lines.append("要求：")
    lines.append("1. 读取这些新文件，提取尚未纳入的思维维度、分析工具和金句")
    lines.append("2. 更新 THINK-TANK.md 中对应大师的'操作系统'部分")
    lines.append("3. 在迭代升级日志中记录本次变更")
    lines.append("```")

    return "\n".join(lines)


def main():
    args = sys.argv[1:]

    if "--stats" in args:
        generate_stats()
        return

    # 扫描所有大师目录
    print("🔍 扫描智囊团知识源文件...")
    all_sources = []
    for config in MASTERS.values():
        all_sources.extend(config["sources"])
    for config in BENCH_MASTERS.values():
        all_sources.extend(config["sources"])

    current_state = scan_files(all_sources)
    previous_state = load_previous_state()

    if "--diff" in args or previous_state:
        diff = compute_diff(previous_state, current_state)
        master_changes = classify_changes_by_master(diff)

        total_changes = sum(
            len(d["added"]) + len(d["modified"]) + len(d["removed"])
            for d in master_changes.values()
        )

        if total_changes == 0:
            print("✅ 未检测到变更。所有大师知识源保持不变。")
        else:
            print(f"⚡ 检测到 {total_changes} 个变更：")
            for master, changes in master_changes.items():
                n = len(changes["added"]) + len(changes["modified"]) + len(changes["removed"])
                if n > 0:
                    emoji = MASTERS.get(master, {}).get("emoji", "📌")
                    print(f"   {emoji} {master}: +{len(changes['added'])} 新增, "
                          f"~{len(changes['modified'])} 修改, "
                          f"-{len(changes['removed'])} 删除")

        # 生成报告
        report = generate_iteration_report(master_changes)
        today = datetime.now().strftime("%Y-%m-%d")
        report_path = REPORT_DIR / f"{today}-智囊团迭代维护报告.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n📄 迭代报告已生成：{report_path.name}")
    else:
        print("ℹ️ 首次扫描，记录基线状态...")
        total_files = len(current_state)
        print(f"   已记录 {total_files} 个知识源文件")

    # 保存状态
    save_state(current_state)
    print("💾 扫描状态已保存")

    # 显示统计
    if "--stats" not in args:
        generate_stats()


if __name__ == "__main__":
    main()
