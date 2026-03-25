# -*- coding: utf-8 -*-
"""
一键维护脚本 - 转换文档并更新索引
用法: python maintain.py

执行以下操作:
1. 将新的 docx/pdf/epub/mobi 转换为 txt
2. 更新所有目录的 INDEX.md 索引
3. 显示知识库统计信息
"""

import os
import sys
import io
from pathlib import Path
from datetime import datetime


def count_files(root_dir):
    """统计各类文件数量"""
    root_path = Path(root_dir)
    stats = {
        "txt": 0,
        "docx": 0,
        "pdf": 0,
        "epub": 0,
        "mobi": 0,
        "md": 0,
        "xlsx": 0,
        "other": 0,
        "dirs": 0,
    }

    for item in root_path.rglob("*"):
        # 跳过虚拟环境
        if ".venv" in str(item):
            continue

        if item.is_dir():
            stats["dirs"] += 1
        elif item.is_file():
            suffix = item.suffix.lower()
            if suffix in stats:
                stats[suffix.lstrip(".")] += 1
            elif suffix in [".txt"]:
                stats["txt"] += 1
            elif suffix in [".docx"]:
                stats["docx"] += 1
            elif suffix in [".pdf"]:
                stats["pdf"] += 1
            elif suffix in [".md"]:
                stats["md"] += 1
            else:
                stats["other"] += 1

    return stats


def main():
    # 设置stdout编码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    # 获取项目根目录 (提升两层)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))

    print("=" * 60)
    print("📊 投研知识库维护工具")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📍 根目录: {project_root}")
    print("=" * 60)

    # Step 1: 转换文档
    print("\n🔄 Step 1: 转换文档...")
    print("-" * 40)

    convert_script = os.path.join(script_dir, "convert_to_txt.py")
    if os.path.exists(convert_script):
        # 传递项目根目录作为参数
        os.system(f'python "{convert_script}" "{project_root}"')
    else:
        print("  [跳过] convert_to_txt.py 不存在")

    # Step 2: 更新索引
    print("\n📑 Step 2: 更新索引...")
    print("-" * 40)

    index_script = os.path.join(script_dir, "update_index.py")
    if os.path.exists(index_script):
        # 传递项目根目录作为参数
        os.system(f'python "{index_script}" "{project_root}"')
    else:
        print("  [跳过] update_index.py 不存在")

    # Step 3: 统计信息
    print("\n📈 Step 3: 知识库统计...")
    print("-" * 40)

    stats = count_files(project_root)

    print(f"""
  📂 目录数量:     {stats["dirs"]}
  📄 txt 文件:     {stats["txt"]} (AI 直接读取)
  📝 md 文件:      {stats["md"]}
  📋 docx 文件:    {stats["docx"]} (原始格式)
  📕 pdf 文件:     {stats["pdf"]} (原始格式)
  📊 xlsx 文件:    {stats["xlsx"]}
  📚 epub/mobi:    {stats["epub"] + stats["mobi"]}
  🔧 其他文件:     {stats["other"]}
    """)

    print("=" * 60)
    print("✅ 维护完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
