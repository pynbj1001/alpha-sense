"""
Markdown → PDF converter using Python markdown + Chrome headless --print-to-pdf.
Designed for Chinese-language investment research reports.
"""

import sys
import os
import subprocess
import tempfile
import markdown


def md_to_html(md_path: str) -> str:
    """Convert markdown file to styled HTML string."""
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    extensions = ["tables", "fenced_code", "toc", "nl2br", "sane_lists", "smarty"]
    html_body = markdown.markdown(md_text, extensions=extensions)

    css = """
    @page {
        size: A4;
        margin: 20mm 18mm 20mm 18mm;
    }
    body {
        font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB",
                     "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Micro Hei",
                     "Segoe UI", Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.7;
        color: #222;
        max-width: 100%;
        padding: 0;
    }
    h1 {
        font-size: 20pt;
        border-bottom: 3px solid #1a73e8;
        padding-bottom: 8px;
        margin-top: 28px;
        color: #1a237e;
        page-break-after: avoid;
    }
    h2 {
        font-size: 16pt;
        color: #1565c0;
        border-bottom: 1px solid #90caf9;
        padding-bottom: 4px;
        margin-top: 24px;
        page-break-after: avoid;
    }
    h3 {
        font-size: 13pt;
        color: #1976d2;
        margin-top: 18px;
        page-break-after: avoid;
    }
    h4 {
        font-size: 11.5pt;
        color: #333;
        margin-top: 14px;
        page-break-after: avoid;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 12px 0;
        font-size: 9.5pt;
        page-break-inside: avoid;
    }
    th {
        background-color: #1565c0;
        color: white;
        padding: 6px 8px;
        text-align: left;
        font-weight: 600;
    }
    td {
        padding: 5px 8px;
        border: 1px solid #ddd;
    }
    tr:nth-child(even) {
        background-color: #f5f7fa;
    }
    tr:hover {
        background-color: #e8f0fe;
    }
    blockquote {
        border-left: 4px solid #1a73e8;
        margin: 12px 0;
        padding: 8px 16px;
        background-color: #e8f0fe;
        color: #333;
        font-size: 10.5pt;
        page-break-inside: avoid;
    }
    code {
        background-color: #f0f0f0;
        padding: 1px 4px;
        border-radius: 3px;
        font-size: 9.5pt;
        font-family: Consolas, "Courier New", monospace;
    }
    pre {
        background-color: #263238;
        color: #eeffff;
        padding: 12px;
        border-radius: 4px;
        overflow-x: auto;
        font-size: 9pt;
        page-break-inside: avoid;
    }
    pre code {
        background-color: transparent;
        color: inherit;
    }
    strong {
        color: #c62828;
    }
    hr {
        border: none;
        border-top: 2px solid #bdbdbd;
        margin: 20px 0;
    }
    ul, ol {
        margin: 8px 0;
        padding-left: 24px;
    }
    li {
        margin-bottom: 3px;
    }
    p {
        margin: 8px 0;
    }
    /* Print optimizations */
    h1, h2, h3, h4 {
        page-break-after: avoid;
    }
    table, blockquote, pre {
        page-break-inside: avoid;
    }
    """

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Research Report</title>
    <style>{css}</style>
</head>
<body>
{html_body}
</body>
</html>"""
    return html


def html_to_pdf_chrome(html_path: str, pdf_path: str) -> bool:
    """Use Chrome headless to print HTML to PDF.

    Writes temp files to %TEMP% to avoid Chinese chars in file URIs.
    """
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    chrome = None
    for p in chrome_paths:
        if os.path.exists(p):
            chrome = p
            break
    if not chrome:
        print("ERROR: No Chrome or Edge found.")
        return False

    # Copy HTML to a temp location with ASCII-only path
    tmp_dir = tempfile.mkdtemp(prefix="md2pdf_")
    tmp_html = os.path.join(tmp_dir, "report.html")
    tmp_pdf = os.path.join(tmp_dir, "report.pdf")

    import shutil

    shutil.copy2(html_path, tmp_html)

    file_uri = "file:///" + tmp_html.replace("\\", "/")

    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-extensions",
        "--run-all-compositor-stages-before-draw",
        "--disable-software-rasterizer",
        f"--print-to-pdf={tmp_pdf}",
        "--no-pdf-header-footer",
        file_uri,
    ]
    print(f"Running: {os.path.basename(chrome)} --headless=new --print-to-pdf ...")
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=60, encoding="utf-8", errors="replace"
        )
        if result.stderr:
            # Only show non-DevTools lines
            for line in result.stderr.splitlines():
                if "DevTools" not in line and line.strip():
                    print(f"  Chrome: {line.strip()}")
    except subprocess.TimeoutExpired:
        print("ERROR: Chrome timed out after 60s")
        return False

    if os.path.exists(tmp_pdf):
        shutil.copy2(tmp_pdf, pdf_path)
        # Clean up temp dir
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return True
    else:
        print("ERROR: Chrome did not produce a PDF file.")
        # Show full stderr for debugging
        if result.stderr:
            print(f"Full stderr:\n{result.stderr[:1000]}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python _md_to_pdf.py <input.md> [output.pdf]")
        sys.exit(1)

    md_path = sys.argv[1]
    if not os.path.exists(md_path):
        print(f"ERROR: File not found: {md_path}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        pdf_path = sys.argv[2]
    else:
        pdf_path = os.path.splitext(md_path)[0] + ".pdf"

    print(f"Converting: {os.path.basename(md_path)}")
    print(f"Output:     {os.path.basename(pdf_path)}")

    # Step 1: MD → HTML
    html_content = md_to_html(md_path)

    # Step 2: Write temp HTML
    html_dir = os.path.dirname(os.path.abspath(md_path))
    html_path = os.path.join(html_dir, "_temp_report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML generated: {os.path.basename(html_path)}")

    # Step 3: HTML → PDF via Chrome headless
    success = html_to_pdf_chrome(html_path, pdf_path)

    # Clean up temp HTML
    try:
        os.remove(html_path)
    except OSError:
        pass

    if success:
        size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        print(f"SUCCESS: PDF generated ({size_mb:.1f} MB)")
        print(f"Path: {pdf_path}")
    else:
        print("FAILED: PDF generation failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
