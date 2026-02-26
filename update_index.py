# -*- coding: utf-8 -*-
"""
更新各目录的 INDEX.md 索引文件
优先引用 txt 文件（方便AI读取）
"""

import os
import sys
import io
import urllib.parse
from pathlib import Path


def generate_index_files(root_dir):
    """为每个子目录生成INDEX.md"""
    root_path = Path(root_dir)

    # 获取所有以数字开头的目录
    top_level_dirs = [
        d
        for d in os.listdir(root_path)
        if os.path.isdir(root_path / d) and d[0:2].isdigit()
    ]
    top_level_dirs.sort()

    for d in top_level_dirs:
        dir_path = root_path / d
        generate_index_for_dir(dir_path)

        # 递归处理子目录
        for subdir in dir_path.rglob("*"):
            if subdir.is_dir():
                generate_index_for_dir(subdir)


def generate_index_for_dir(dir_path):
    """为单个目录生成INDEX.md"""
    index_path = dir_path / "INDEX.md"

    try:
        items = os.listdir(dir_path)
    except Exception as e:
        print(f"错误: 无法访问 {dir_path}: {e}")
        return

    items.sort()

    # 分类文件
    txt_files = []
    other_files = []
    subdirs = []

    # 记录已有txt版本的原文件
    txt_basenames = set()

    for item in items:
        if item == "INDEX.md":
            continue

        full_path = dir_path / item
        if full_path.is_dir():
            subdirs.append(item)
        elif item.endswith(".txt"):
            txt_files.append(item)
            txt_basenames.add(item[:-4])  # 去掉.txt后缀
        else:
            other_files.append(item)

    # 过滤掉已有txt版本的原文件
    other_files_filtered = []
    for f in other_files:
        basename = f.rsplit(".", 1)[0] if "." in f else f
        if basename not in txt_basenames:
            other_files_filtered.append(f)

    # 生成内容
    dir_name = dir_path.name
    content = f"# {dir_name}\n\n"
    content += "> 本索引优先引用 `.txt` 文件，方便 AI 直接读取\n\n"

    if subdirs:
        content += "## 📂 子文件夹\n\n"
        for subdir in subdirs:
            link = urllib.parse.quote(subdir)
            content += f"- [{subdir}/]({link}/INDEX.md)\n"
        content += "\n"

    if txt_files:
        content += "## 📄 知识文件 (txt)\n\n"
        for f in txt_files:
            link = urllib.parse.quote(f)
            # 显示更友好的名称（去掉.txt后缀）
            display_name = f[:-4]
            content += f"- [{display_name}]({link})\n"
        content += "\n"

    if other_files_filtered:
        content += "## 📎 其他文件\n\n"
        for f in other_files_filtered:
            link = urllib.parse.quote(f)
            content += f"- [{f}]({link})\n"
        content += "\n"

    if not subdirs and not txt_files and not other_files_filtered:
        content += "(暂无内容)\n"

    # 写入文件
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"更新: {index_path}")
    except Exception as e:
        print(f"错误: 写入 {index_path} 失败: {e}")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        target_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"更新索引: {target_dir}")
    print("-" * 50)
    generate_index_files(target_dir)
    print("-" * 50)
    print("完成!")
