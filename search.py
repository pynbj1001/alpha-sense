# -*- coding: utf-8 -*-
"""
全文搜索工具 - 在知识库中搜索关键词
用法: python search.py <关键词> [--limit N] [--context N]

示例:
  python search.py 护城河
  python search.py "贝叶斯拐点" --limit 5
  python search.py 估值 --context 3
"""

import os
import sys
import io
import re
import argparse
from pathlib import Path
from collections import defaultdict


def search_files(root_dir, keyword, limit=10, context_lines=1):
    """
    在所有txt文件中搜索关键词

    Args:
        root_dir: 搜索根目录
        keyword: 搜索关键词
        limit: 每个文件最多显示的匹配数
        context_lines: 显示匹配行前后的上下文行数

    Returns:
        dict: {文件路径: [(行号, 匹配行, 上下文)]}
    """
    root_path = Path(root_dir)
    results = defaultdict(list)

    # 编译正则表达式（不区分大小写）
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)

    # 遍历所有txt文件
    for file_path in root_path.rglob("*.txt"):
        # 跳过虚拟环境
        if ".venv" in str(file_path):
            continue

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            matches = []
            for i, line in enumerate(lines):
                if pattern.search(line):
                    # 获取上下文
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    context = lines[start:end]

                    matches.append(
                        {
                            "line_num": i + 1,
                            "line": line.strip(),
                            "context": [l.strip() for l in context],
                            "context_start": start + 1,
                        }
                    )

                    if len(matches) >= limit:
                        break

            if matches:
                # 使用相对路径
                rel_path = file_path.relative_to(root_path)
                results[str(rel_path)] = matches

        except Exception as e:
            pass  # 忽略读取错误的文件

    return results


def highlight_keyword(text, keyword):
    """高亮显示关键词"""
    pattern = re.compile(f"({re.escape(keyword)})", re.IGNORECASE)
    return pattern.sub(r"【\1】", text)


def print_results(results, keyword):
    """格式化输出搜索结果"""
    if not results:
        print(f"\n未找到包含 '{keyword}' 的内容\n")
        return

    total_matches = sum(len(matches) for matches in results.values())
    print(f"\n找到 {total_matches} 处匹配，分布在 {len(results)} 个文件中:\n")
    print("=" * 70)

    for file_path, matches in sorted(results.items()):
        print(f"\n📄 {file_path}")
        print("-" * 60)

        for match in matches:
            line_num = match["line_num"]
            highlighted = highlight_keyword(match["line"], keyword)

            # 截断过长的行
            if len(highlighted) > 120:
                highlighted = highlighted[:120] + "..."

            print(f"  第 {line_num} 行: {highlighted}")

        print()

    print("=" * 70)
    print(f"共 {total_matches} 处匹配")


def main():
    # 设置stdout编码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    # 解析参数
    parser = argparse.ArgumentParser(
        description="在投研知识库中搜索关键词",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python search.py 护城河
  python search.py "贝叶斯拐点" --limit 5
  python search.py 估值 --context 3
        """,
    )
    parser.add_argument("keyword", help="搜索关键词")
    parser.add_argument(
        "--limit", "-l", type=int, default=5, help="每个文件最多显示的匹配数 (默认: 5)"
    )
    parser.add_argument(
        "--context",
        "-c",
        type=int,
        default=0,
        help="显示匹配行前后的上下文行数 (默认: 0)",
    )
    parser.add_argument(
        "--dir", "-d", type=str, default=None, help="搜索目录 (默认: 当前目录)"
    )

    args = parser.parse_args()

    # 确定搜索目录
    if args.dir:
        root_dir = args.dir
    else:
        root_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"搜索 '{args.keyword}' 在 {root_dir}")

    # 执行搜索
    results = search_files(root_dir, args.keyword, args.limit, args.context)

    # 输出结果
    print_results(results, args.keyword)


if __name__ == "__main__":
    main()
