"""export 命令: 将摘抄 Markdown 目录导出为 Word 文档 (宋体、层级标题)。"""

import os
import re

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches


def set_font_to_songti(paragraph):
    """将段落所有 run 的字体设置为宋体。"""
    for run in paragraph.runs:
        run.font.name = "宋体"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


def set_heading_font_to_songti(doc, level):
    """设置指定级别的标题样式为宋体。"""
    style = doc.styles[f"Heading {level}"]
    style.font.name = "宋体"
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


def parse_md_file(md_path: str):
    """解析摘抄 Markdown, 返回 [(原文, 用途), ...]。

    支持两种格式:
    1. 引用块格式: '> 原文' + '**用途**：...', 条目间以 '---' 分隔
    2. 列表格式: '- **原文内容**：...' + '- **用途**：...'
    """
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    if "---" in content:
        blocks = re.split(r"\n---\s*\n", content)
        entries = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            match = re.search(r"^>\s*(.*?)\n\s*\*\*用途\*\*：\s*(.*?)$", block, re.DOTALL | re.MULTILINE)
            if match:
                entries.append((match.group(1).strip(), match.group(2).strip()))
            elif "- **原文内容**：" in block:
                entries.extend(parse_list_style(block))
        return entries
    return parse_list_style(content)


def parse_list_style(text: str):
    entries = []
    for para in re.split(r"\n\s*\n", text):
        if not para.strip():
            continue
        original, usage = None, None
        for line in para.strip().split("\n"):
            line = line.strip()
            if line.startswith("- **原文内容**："):
                original = line.replace("- **原文内容**：", "").strip()
            elif line.startswith("- **用途**："):
                usage = line.replace("- **用途**：", "").strip()
        if original and usage:
            entries.append((original, usage))
    return entries


def extract_author_year_title(filename_base: str):
    """从文件名 (去扩展名) 提取 (作者, 年份, 标题)。格式: '作者 - 2020 - 标题_28-77'"""
    base = re.sub(r"_\d+-\d+$", "", filename_base)
    parts = base.split(" - ")
    if len(parts) >= 3:
        return parts[0].strip(), parts[1].strip(), " - ".join(parts[2:]).strip()
    elif len(parts) == 2:
        return parts[0].strip(), "", parts[1].strip()
    return "", "", base


def generate_word_from_md(md_root: str, output_docx: str):
    doc = Document()

    # 默认字体与标题字体设为宋体
    style = doc.styles["Normal"]
    style.font.name = "宋体"
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    for level in range(1, 4):
        set_heading_font_to_songti(doc, level)

    # 读取一级章节目录 (如 '2. ' 开头)
    chapters = [
        d for d in os.listdir(md_root)
        if os.path.isdir(os.path.join(md_root, d)) and re.match(r"^2\.\d", d)
    ]
    chapters.sort()

    num_cn = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]

    for chapter in chapters:
        chapter_path = os.path.join(md_root, chapter)
        sub_chapters = [
            d for d in os.listdir(chapter_path)
            if os.path.isdir(os.path.join(chapter_path, d)) and re.match(r"^2\.\d+\.\d+", d)
        ]
        sub_chapters.sort()

        doc.add_heading(chapter, level=1)
        for sub in sub_chapters:
            sub_path = os.path.join(chapter_path, sub)
            doc.add_heading(sub, level=2)

            md_files = sorted(f for f in os.listdir(sub_path) if f.endswith(".md"))
            if not md_files:
                print(f"警告: {sub} 下没有 md 文件")
                continue

            for idx, md_file in enumerate(md_files, start=1):
                label = f"文献{num_cn[idx-1]}" if idx <= len(num_cn) else f"文献{idx}"
                base = re.sub(r"\(\d+\)", "", md_file.replace(".md", "")).strip()
                author, year, pure_title = extract_author_year_title(base)

                if author and year:
                    heading_text = f"{label}·{author} ({year})·{pure_title}"
                elif author:
                    heading_text = f"{label}·{author}·{pure_title}"
                else:
                    heading_text = f"{label}·{pure_title}"
                doc.add_heading(heading_text, level=3)

                entries = parse_md_file(os.path.join(sub_path, md_file))
                if not entries:
                    print(f"  警告: {md_file} 未解析到任何摘抄条目")
                for original, usage in entries:
                    p = doc.add_paragraph()
                    p.paragraph_format.left_indent = Inches(0.5)
                    run = p.add_run(original)
                    run.italic = True
                    set_font_to_songti(p)
                    p_usage = doc.add_paragraph()
                    p_usage.add_run("用途：").bold = True
                    p_usage.add_run(usage)
                    set_font_to_songti(p_usage)
                    doc.add_paragraph("_" * 50)
                doc.add_paragraph()

    doc.save(output_docx)
    print(f"Word 文档已生成: {output_docx}")


def run(args) -> int:
    if not os.path.exists(args.md_root):
        print(f"根目录不存在: {args.md_root}")
        return 1
    generate_word_from_md(args.md_root, args.output)
    return 0