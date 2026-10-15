"""PDF 文本提取、OCR 兜底 与 文件名元数据解析。

- page_texts(): 返回 [(原始页码, 文本)]，页码与 PDF 真实页号一致（空页不错位）。
- ocr=True 时，无文字层的页用 Tesseract 识别补齐（依赖 PyMuPDF 渲染 + Tesseract，无需 Ghostscript）。
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import fitz

_TESS_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
]


def find_tesseract():
    """定位 Tesseract 可执行文件: 环境变量 > PATH > 常见安装路径。"""
    env = os.environ.get("PAPER_LITFLOW_TESSERACT", "").strip()
    if env and Path(env).exists():
        return env
    which = shutil.which("tesseract")
    if which:
        return which
    for c in _TESS_CANDIDATES:
        if Path(c).exists():
            return c
    return None


def find_tessdata():
    """定位语言包目录: 环境变量 > ~/.paper-litflow/tessdata > 安装目录。"""
    env = os.environ.get("PAPER_LITFLOW_TESSDATA", "").strip()
    if env and Path(env).is_dir():
        return env
    cands = [Path.home() / ".paper-litflow" / "tessdata",
             Path(r"C:\Program Files\Tesseract-OCR\tessdata")]
    for c in cands:
        if c.is_dir() and (c / "chi_sim.traineddata").exists():
            return str(c)
    for c in cands:
        if c.is_dir():
            return str(c)
    return None


def ocr_image(png_path: str, lang: str = "chi_sim+eng", tesseract: str | None = None,
              tessdata: str | None = None) -> str:
    """对单张图片做 OCR, 返回文本。"""
    tess = tesseract or find_tesseract()
    if not tess:
        raise RuntimeError("未找到 Tesseract。请安装后设置环境变量 PAPER_LITFLOW_TESSERACT")
    td = tessdata or find_tessdata()
    cmd = [tess, png_path, "stdout", "-l", lang]
    if td:
        cmd += ["--tessdata-dir", td]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        raise RuntimeError(f"Tesseract 失败: {(r.stderr or '')[:300]}")
    return r.stdout or ""


def _ocr_page(page, lang: str, dpi: int) -> str:
    """渲染单页为位图后 OCR。"""
    zoom = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    with tempfile.TemporaryDirectory() as d:
        png = os.path.join(d, "p.png")
        pix.save(png)
        try:
            return ocr_image(png, lang=lang)
        except Exception as e:
            print(f"  OCR 失败: {e}")
            return ""


def page_texts(path: str, ocr: bool = False, lang: str = "chi_sim+eng", dpi: int = 300,
               min_chars: int = 10):
    """返回 [(页码, 文本), ...]，页码为 PDF 原始页号(1-based)。

    有文字层的页直接用; ocr=True 时, 文字层为空(疑似扫描页)的页用 Tesseract 补齐。
    """
    doc = fitz.open(path)
    out = []
    try:
        for i, page in enumerate(doc, 1):
            t = page.get_text()
            if ocr and len(t.strip()) < min_chars:
                t = _ocr_page(page, lang, dpi)
            out.append((i, t))
    finally:
        doc.close()
    return out


def extract_text_from_pdf(pdf_path: str, max_chars: int = 8000, ocr: bool = False,
                          lang: str = "chi_sim+eng", dpi: int = 300) -> str:
    """用 PyMuPDF 提取 PDF 全文(可选 OCR 兜底), 截断到 max_chars。"""
    try:
        pages = page_texts(pdf_path, ocr=ocr, lang=lang, dpi=dpi)
        text = "".join(t for _, t in pages)
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
