# -*- coding: utf-8 -*-
import sys
from docx import Document


def read_docx(filepath):
    doc = Document(filepath)
    text = []
    for para in doc.paragraphs:
        if para.text.strip():
            # Replace non-breaking spaces
            clean_text = para.text.replace("\xa0", " ")
            text.append(clean_text)
    return "\n".join(text)


if __name__ == "__main__":
    filepath = (
        sys.argv[1]
        if len(sys.argv) > 1
        else r"C:\Users\pynbj\OneDrive\1.文档-积累要看的文件\1. 投资框架\03-宏观与周期\周金涛周期框架.docx"
    )
    content = read_docx(filepath)

    # Write to txt file with same name
    output_path = filepath.replace(".docx", ".txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Converted: {filepath} -> {output_path}")
