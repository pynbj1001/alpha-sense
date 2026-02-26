import markdown
from xhtml2pdf import pisa
import os
import sys

def convert_md_to_pdf(source_md_path, output_pdf_path):
    # 1. Read Markdown file
    with open(source_md_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # 2. Convert Markdown to HTML
    # enabling extensions for tables and extra features
    html_text = markdown.markdown(text, extensions=['tables', 'fenced_code'])

    # 3. Add some basic styling for better PDF look
    # We use a font that supports Chinese if possible, but xhtml2pdf has limited font support by default.
    # We will try to use a generic font-family that might map to something capable, or just standard.
    # Note: Chinese character rendering in xhtml2pdf often requires a specific font file (.ttf).
    # For now, we'll try a basic template. If Chinese fails, we might need a more complex solution with a font path.
    
    # Simple CSS to handle basic layout
    css = """
    <style>
        @page { size: A4; margin: 2cm; }
        body { font-family: "Helvetica", "Arial", sans-serif; line-height: 1.5; font-size: 12px; }
        h1 { font-size: 24px; color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }
        h2 { font-size: 18px; color: #444; margin-top: 20px; border-bottom: 1px solid #ddd; }
        h3 { font-size: 14px; color: #666; margin-top: 15px; }
        p { margin-bottom: 10px; }
        code { background-color: #f4f4f4; padding: 2px 5px; font-family: Consolas, monospace; }
        pre { background-color: #f4f4f4; padding: 10px; border: 1px solid #ddd; white-space: pre-wrap; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 15px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        blockquote { border-left: 4px solid #ccc; padding-left: 10px; color: #666; font-style: italic; }
    </style>
    """
    
    # To support Chinese, we usually need a font.
    # Without a specific font path, xhtml2pdf might show squares for Chinese characters.
    # Let's try to check for a system font like SimHei or Microsoft YaHei if on Windows.
    # Since we are on Windows (user path starts with c:\Users...), we can try to load a font.
    
    font_setup = ""
    font_path = "C:\\Windows\\Fonts\\msyh.ttc" # Microsoft YaHei
    if not os.path.exists(font_path):
        font_path = "C:\\Windows\\Fonts\\simhei.ttf" # SimHei
    
    if os.path.exists(font_path):
        font_setup = f"""
        @font-face {{
            font-family: "ChineseFont";
            src: url("{font_path}");
        }}
        body {{ font-family: "ChineseFont", sans-serif; }}
        """
    
    full_html = f"<html><head><meta charset='utf-8'>{css}<style>{font_setup}</style></head><body>{html_text}</body></html>"

    # 4. Write PDF
    with open(output_pdf_path, "wb") as result_file:
        pisa_status = pisa.CreatePDF(
            full_html,
            dest=result_file,
            encoding='utf-8'
        )

    if pisa_status.err:
        print(f"Error converting to PDF: {pisa_status.err}")
        return False
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python md2pdf.py <input_md> <output_pdf>")
    else:
        success = convert_md_to_pdf(sys.argv[1], sys.argv[2])
        if success:
            print(f"Successfully created {sys.argv[2]}")
        else:
            sys.exit(1)
