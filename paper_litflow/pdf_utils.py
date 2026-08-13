"""PDF 文本提取与文件名元数据解析。"""

import re

import fitz


def extract_text_from_pdf(pdf_path: str, max_chars: int = 8000) -> str:
    """用 PyMuPDF 提取 PDF 全文, 截断到 max_chars。"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text[:max_chars].strip()
    except Exception as e:
        print(f"  提取文本失败: {e}")
        return ""


def parse_filename_metadata(filename: str):
    """从文件名解析 (作者, 年份, 标题)。

    支持格式: "作者 - 2020 - 标题_28-77.pdf" / "作者 - 标题.pdf" / "标题.pdf"
    """
    name = re.sub(r"_\d+-\d+\.pdf$", ".pdf", filename)
    name = name.replace(".pdf", "")
    match = re.search(r"^(.+?)\s*-\s*(\d{4})\s*-\s*(.+)$", name)
    if match:
        return match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
    match2 = re.search(r"^(.+?)\s*-\s*(.+)$", name)
    if match2:
        return match2.group(1).strip(), "", match2.group(2).strip()
    return "", "", name