# -*- coding: utf-8 -*-
"""
Markdown 转 PDF 工具（使用reportlab直接生成）
用法: python md2pdf.py <input.md> [output.pdf]
"""

import re
import os
import sys
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


def sanitize_pdf_text(text):
    """清洗可能导致缺字方块的字符"""
    if text is None:
        return ""
    text = str(text)
    replace_map = {
        "\u200b": "",  # zero width space
        "\u200c": "",
        "\u200d": "",
        "\ufeff": "",
        "\xa0": " ",
        "\u2014": "-",  # em dash
        "\u2013": "-",  # en dash
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
    }
    for k, v in replace_map.items():
        text = text.replace(k, v)
    return text


def clean_markdown_syntax(text):
    """
    清理Markdown语法标记

    Args:
        text: 原始文本

    Returns:
        str: 清理后的文本
    """
    text = sanitize_pdf_text(text)

    # 清理加粗标记 **text**
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)

    # 清理斜体标记 *text*
    text = re.sub(r"\*(.*?)\*", r"\1", text)

    # 清理行内代码 `text`
    text = re.sub(r"`(.*?)`", r"\1", text)

    # 清理删除线 ~~text~~
    text = re.sub(r"~~(.*?)~~", r"\1", text)

    # 清理链接 [text](url)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

    # 清理图片 ![alt](url)
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"\1", text)

    return sanitize_pdf_text(text)


# 注册中文字体
def register_chinese_fonts():
    """注册系统中文字体"""
    # 优先使用 reportlab 内置 CID 中文字体，稳定性更高，避免部分系统字体子集缺字导致黑块
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light"
    except:
        pass

    font_paths = [
        ("C:\\Windows\\Fonts\\simsun.ttc", "SimSun"),
        ("C:\\Windows\\Fonts\\simhei.ttf", "SimHei"),
        ("C:\\Windows\\Fonts\\msyh.ttc", "Microsoft YaHei"),
    ]

    for path, name in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except:
                continue

    return None


# 全局字体名称
CHINESE_FONT = None


class PDFBuilder:
    """PDF构建器"""

    def __init__(self, output_path):
        self.output_path = output_path
        self.story = []
        self.styles = getSampleStyleSheet()

        # 设置中文字体样式
        self.setup_styles()

    def setup_styles(self):
        """设置文档样式"""
        global CHINESE_FONT
        CHINESE_FONT = register_chinese_fonts()

        # 使用系统支持的中文字体，如果没有则使用Helvetica
        font_name = CHINESE_FONT if CHINESE_FONT else "Helvetica"

        # 标题样式
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontName=font_name,
                fontSize=20,
                textColor=colors.HexColor("#1e40af"),
                spaceAfter=12,
                spaceBefore=6,
                borderWidth=3,
                borderColor=colors.HexColor("#2563eb"),
                borderPadding=6,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="CustomH2",
                parent=self.styles["Heading2"],
                fontName=font_name,
                fontSize=14,
                textColor=colors.HexColor("#1e40af"),
                spaceAfter=10,
                spaceBefore=15,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="CustomH3",
                parent=self.styles["Heading3"],
                fontName=font_name,
                fontSize=12,
                textColor=colors.HexColor("#374151"),
                spaceAfter=8,
                spaceBefore=12,
            )
        )

        # 正文样式
        self.styles.add(
            ParagraphStyle(
                name="CustomBody",
                parent=self.styles["BodyText"],
                fontName=font_name,
                fontSize=10,
                leading=15,
                alignment=TA_JUSTIFY,
                spaceAfter=6,
                spaceBefore=6,
            )
        )

        # 表格样式
        self.styles.add(
            ParagraphStyle(
                name="TableCell",
                fontName=font_name,
                fontSize=9,
                leading=12,
            )
        )

    def add_title(self, text):
        """添加标题"""
        text = clean_markdown_syntax(text)
        self.story.append(Paragraph(text, self.styles["CustomTitle"]))

    def add_heading(self, level, text):
        """添加标题"""
        text = clean_markdown_syntax(text)
        if level == 2:
            self.story.append(Paragraph(text, self.styles["CustomH2"]))
        elif level == 3:
            self.story.append(Paragraph(text, self.styles["CustomH3"]))
        else:
            self.story.append(Paragraph(text, self.styles["Heading" + str(level)]))

    def add_paragraph(self, text):
        """添加段落"""
        # 处理特殊字符
        text = text.replace("|", "").strip()
        text = clean_markdown_syntax(text)
        if text:
            self.story.append(Paragraph(text, self.styles["CustomBody"]))

    def add_table(self, headers, rows):
        """添加表格"""
        # 清理Markdown标记
        headers = [clean_markdown_syntax(h) for h in headers]
        rows = [[clean_markdown_syntax(cell) for cell in row] for row in rows]

        # 合并表头和行
        data = [headers] + rows

        # 创建表格
        table = Table(data, repeatRows=1)

        # 设置样式
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        CHINESE_FONT if CHINESE_FONT else "Helvetica-Bold",
                    ),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f8fafc")],
                    ),
                    (
                        "FONTNAME",
                        (0, 1),
                        (-1, -1),
                        CHINESE_FONT if CHINESE_FONT else "Helvetica",
                    ),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        self.story.append(table)
        self.story.append(Spacer(1, 6))

    def add_line(self):
        """添加分隔线"""
        self.story.append(Spacer(1, 6))

    def add_footer(self, text):
        """添加页脚信息"""
        self.story.append(Spacer(1, 30))
        self.story.append(
            Paragraph(
                f'<font size="8" color="gray">{text}</font>', self.styles["Normal"]
            )
        )

    def build(self):
        """生成PDF文件"""
        # 创建PDF文档
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2.5 * cm,
        )

        # 生成
        doc.build(self.story)


def parse_markdown_to_pdf(md_path, pdf_path):
    """
    解析Markdown并生成PDF

    Args:
        md_path: Markdown文件路径
        pdf_path: PDF输出路径

    Returns:
        bool: 是否成功
    """
    try:
        # 读取Markdown
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 创建PDF构建器
        builder = PDFBuilder(pdf_path)

        # 分割行
        lines = content.split("\n")

        # 状态
        in_table = False
        table_headers = []
        table_rows = []

        for line in lines:
            line_orig = line
            line = line.strip()

            # 空行
            if not line:
                if in_table and table_headers and table_rows:
                    builder.add_table(table_headers, table_rows)
                    table_headers = []
                    table_rows = []
                    in_table = False
                continue

            # 标题
            if line.startswith("#"):
                if in_table and table_headers and table_rows:
                    builder.add_table(table_headers, table_rows)
                    table_headers = []
                    table_rows = []
                    in_table = False

                level = line.count("#")
                text = line.lstrip("#").strip()
                if text:
                    if level == 1:
                        builder.add_title(text)
                    else:
                        builder.add_heading(level, text)
                continue

            # 分隔线
            if line.startswith("---") or line.startswith("***"):
                if in_table and table_headers and table_rows:
                    builder.add_table(table_headers, table_rows)
                    table_headers = []
                    table_rows = []
                    in_table = False
                builder.add_line()
                continue

            # 引用块
            if line.startswith(">"):
                text = line.lstrip(">").strip()
                text = clean_markdown_syntax(text)
                builder.add_paragraph(text)
                continue

            # 列表
            if line.startswith("- ") or line.startswith("* "):
                text = "- " + line[2:].strip()
                text = clean_markdown_syntax(text)
                builder.add_paragraph(text)
                continue
            if re.match(r"^\d+\.", line):
                text = clean_markdown_syntax(line)
                builder.add_paragraph(text)
                continue

            # 表格
            if "|" in line:
                # 检查是否是表格分隔线
                if "---" in line:
                    # 分隔线，标记表头结束
                    in_table = True
                    continue

                # 解析表格行
                cells = [cell.strip() for cell in line.split("|")]
                cells = [c for c in cells if c]  # 移除空单元格

                if cells:
                    if not in_table and not table_headers:
                        table_headers = cells
                        in_table = True
                    else:
                        table_rows.append(cells)
                continue

            # 其他段落
            if in_table and table_headers and table_rows:
                builder.add_table(table_headers, table_rows)
                table_headers = []
                table_rows = []
                in_table = False

            builder.add_paragraph(line)

        # 处理最后一张表格
        if in_table and table_headers and table_rows:
            builder.add_table(table_headers, table_rows)

        # 添加页脚
        gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        builder.add_footer(f"投研知识库 · 生成于 {gen_time}")

        # 生成PDF
        builder.build()

        print(f"✅ PDF 生成成功: {os.path.basename(pdf_path)}")
        return True

    except Exception as e:
        print(f"❌ PDF 生成失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def batch_convert(directory, force=False):
    """批量转换"""
    skip_prefixes = ["模板-", "INDEX", "README"]

    md_files = []
    for f in os.listdir(directory):
        if not f.endswith(".md"):
            continue
        if any(f.startswith(prefix) for prefix in skip_prefixes):
            continue
        md_files.append(f)

    if not md_files:
        print("没有找到需要转换的 .md 文件")
        return

    print(f"找到 {len(md_files)} 个报告文件\n")

    success = 0
    failed = 0
    skipped = 0

    for md_file in md_files:
        md_path = os.path.join(directory, md_file)
        pdf_path = os.path.join(directory, md_file.replace(".md", ".pdf"))

        # 检查是否需要更新
        if not force and os.path.exists(pdf_path):
            try:
                pdf_mtime = os.path.getmtime(pdf_path)
                md_mtime = os.path.getmtime(md_path)
                if pdf_mtime >= md_mtime:
                    print(f"⏭️  跳过 (已是最新): {md_file}")
                    skipped += 1
                    continue
            except (OSError, TypeError):
                pass

        if parse_markdown_to_pdf(md_path, pdf_path):
            success += 1
        else:
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"完成: ✅ {success} 成功, ⏭️ {skipped} 跳过, ❌ {failed} 失败")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print("""
📄 Markdown 转 PDF 工具 (reportlab直接生成，已修复Markdown标记残留问题)

用法:
  python md2pdf.py <input.md> [output.pdf]   转换单个文件
  python md2pdf.py --batch [directory]       批量转换目录
  python md2pdf.py --batch --force           强制重新转换所有
        """)
        sys.exit(0)

    if sys.argv[1] == "--batch":
        force = "--force" in sys.argv

        # 查找目录参数
        directory = None
        for arg in sys.argv[2:]:
            if arg != "--force" and os.path.isdir(arg):
                directory = arg
                break

        if directory is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            directory = os.path.join(script_dir, "10-研究报告输出")

        print(f"📂 批量转换: {directory}")
        if force:
            print("🔄 强制模式: 重新转换所有文件")
        print()
        batch_convert(directory, force)
    else:
        source = sys.argv[1]
        output = sys.argv[2] if len(sys.argv) > 2 else None
        if output is None:
            output = os.path.splitext(source)[0] + ".pdf"
        parse_markdown_to_pdf(source, output)
