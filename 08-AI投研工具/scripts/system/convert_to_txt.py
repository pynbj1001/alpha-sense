# -*- coding: utf-8 -*-
"""
批量转换 docx/pdf/epub/mobi 为 txt 文件
用法: python convert_to_txt.py [目录路径]
默认处理当前目录及所有子目录
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path


def convert_docx_to_txt(docx_path):
    """将docx转换为txt"""
    try:
        from docx import Document

        doc = Document(docx_path)
        text = []
        for para in doc.paragraphs:
            clean_text = para.text.replace("\xa0", " ")
            text.append(clean_text)
        return "\n".join(text)
    except Exception as e:
        print(f"  [错误] docx转换失败: {e}")
        return None


def convert_pdf_to_txt(pdf_path):
    """将pdf转换为txt"""
    try:
        import fitz  # pymupdf

        doc = fitz.open(pdf_path)
        text = []
        for page in doc:
            text.append(page.get_text())
        doc.close()
        return "\n".join(text)
    except Exception as e:
        print(f"  [错误] pdf转换失败: {e}")
        return None


def convert_epub_to_txt(epub_path):
    """将epub转换为txt"""
    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup

        book = epub.read_epub(epub_path)
        text = []

        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), "lxml")
                chapter_text = soup.get_text(separator="\n", strip=True)
                if chapter_text:
                    text.append(chapter_text)

        return "\n\n".join(text)
    except Exception as e:
        print(f"  [错误] epub转换失败: {e}")
        return None


def convert_mobi_to_txt(mobi_path):
    """将mobi转换为txt"""
    try:
        import mobi
        from bs4 import BeautifulSoup

        # mobi库会解压到临时目录
        tempdir, extracted_path = mobi.extract(mobi_path)

        text = []

        # 遍历解压后的文件，找到HTML内容
        for root, dirs, files in os.walk(tempdir):
            for file in files:
                if file.endswith((".html", ".htm", ".xhtml")):
                    file_path = os.path.join(root, file)
                    try:
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            soup = BeautifulSoup(f.read(), "lxml")
                            chapter_text = soup.get_text(separator="\n", strip=True)
                            if chapter_text:
                                text.append(chapter_text)
                    except:
                        pass

        # 清理临时目录
        try:
            shutil.rmtree(tempdir)
        except:
            pass

        return "\n\n".join(text) if text else None
    except Exception as e:
        print(f"  [错误] mobi转换失败: {e}")
        return None


def process_directory(root_dir):
    """处理目录下所有docx、pdf、epub和mobi文件"""
    root_path = Path(root_dir)

    # 统计
    stats = {
        "docx_converted": 0,
        "pdf_converted": 0,
        "epub_converted": 0,
        "mobi_converted": 0,
        "skipped": 0,
        "failed": 0,
    }

    # 遍历所有文件
    for file_path in root_path.rglob("*"):
        suffix = file_path.suffix.lower()

        if suffix == ".docx":
            txt_path = file_path.with_suffix(".txt")

            if (
                txt_path.exists()
                and txt_path.stat().st_mtime >= file_path.stat().st_mtime
            ):
                stats["skipped"] += 1
                continue

            print(f"转换: {file_path.name}")
            content = convert_docx_to_txt(str(file_path))
            if content:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(content)
                stats["docx_converted"] += 1
            else:
                stats["failed"] += 1

        elif suffix == ".pdf":
            txt_path = file_path.with_suffix(".txt")

            if (
                txt_path.exists()
                and txt_path.stat().st_mtime >= file_path.stat().st_mtime
            ):
                stats["skipped"] += 1
                continue

            print(f"转换: {file_path.name}")
            content = convert_pdf_to_txt(str(file_path))
            if content:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(content)
                stats["pdf_converted"] += 1
            else:
                stats["failed"] += 1

        elif suffix == ".epub":
            txt_path = file_path.with_suffix(".txt")

            if (
                txt_path.exists()
                and txt_path.stat().st_mtime >= file_path.stat().st_mtime
            ):
                stats["skipped"] += 1
                continue

            print(f"转换: {file_path.name}")
            content = convert_epub_to_txt(str(file_path))
            if content:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(content)
                stats["epub_converted"] += 1
            else:
                stats["failed"] += 1

        elif suffix == ".mobi":
            txt_path = file_path.with_suffix(".txt")

            if (
                txt_path.exists()
                and txt_path.stat().st_mtime >= file_path.stat().st_mtime
            ):
                stats["skipped"] += 1
                continue

            print(f"转换: {file_path.name}")
            content = convert_mobi_to_txt(str(file_path))
            if content:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(content)
                stats["mobi_converted"] += 1
            else:
                stats["failed"] += 1

    return stats


if __name__ == "__main__":
    # 设置stdout编码为utf-8
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    # 获取目录路径
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        target_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"开始处理目录: {target_dir}")
    print("-" * 50)

    stats = process_directory(target_dir)

    print("-" * 50)
    print("完成!")
    print(f"  - docx 转换: {stats['docx_converted']} 个")
    print(f"  - pdf 转换: {stats['pdf_converted']} 个")
    print(f"  - epub 转换: {stats['epub_converted']} 个")
    print(f"  - mobi 转换: {stats['mobi_converted']} 个")
    print(f"  - 跳过(已是最新): {stats['skipped']} 个")
    print(f"  - 失败: {stats['failed']} 个")
