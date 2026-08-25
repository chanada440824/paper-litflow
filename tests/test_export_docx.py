"""export_docx: Markdown 解析、文件名元数据与 Word 生成测试。"""

from docx import Document

from paper_litflow.export_docx import (
    extract_author_year_title,
    generate_word_from_md,
    parse_list_style,
    parse_md_file,
)

QUOTE_MD = """> 原文句子一。

**用途**：用于 2.1.1 的具体引用。

---

> 原文句子二。

**用途**：用于 2.1.2 的具体引用。
"""

LIST_MD = """- **原文内容**：列表原文 A。

- **用途**：用于 2.1 的引用。

- **原文内容**：列表原文 B。

- **用途**：用于 2.2 的引用。
"""


def test_parse_md_quote_style(tmp_path):
    p = tmp_path / "a.md"
    p.write_text(QUOTE_MD, encoding="utf-8")
    assert parse_md_file(str(p)) == [
        ("原文句子一。", "用于 2.1.1 的具体引用。", ""),
        ("原文句子二。", "用于 2.1.2 的具体引用。", ""),
    ]


def test_parse_md_quote_confidence(tmp_path):
    md = """> 高置信原文。

**出处**：第3页｜**用途**：论证 A。｜**置信度**：[高]（exact）

---
> 中置信原文。

**出处**：第4页｜**用途**：论证 B。｜**置信度**：[中]（fuzzy）
"""
    p = tmp_path / "c.md"
    p.write_text(md, encoding="utf-8")
    assert parse_md_file(str(p)) == [
        ("高置信原文。", "论证 A。｜**置信度**：[高]（exact）", "高"),
        ("中置信原文。", "论证 B。｜**置信度**：[中]（fuzzy）", "中"),
    ]


def test_parse_md_list_style(tmp_path):
    p = tmp_path / "b.md"
    p.write_text(LIST_MD, encoding="utf-8")
    assert parse_md_file(str(p)) == [
        ("列表原文 A。", "用于 2.1 的引用。", ""),
        ("列表原文 B。", "用于 2.2 的引用。", ""),
    ]


def test_confidence_rgb():
    from paper_litflow.export_docx import confidence_rgb
    from docx.shared import RGBColor
    assert confidence_rgb("高") == RGBColor(0x00, 0xB0, 0x50)
    assert confidence_rgb("中") == RGBColor(0xED, 0x7D, 0x31)
    assert confidence_rgb("低") == RGBColor(0x80, 0x80, 0x80)
    assert confidence_rgb("") == RGBColor(0x00, 0x00, 0x00)


def test_parse_list_style_missing_usage_skipped():
    assert parse_list_style("- **原文内容**：只有原文没有用途。") == []


def test_parse_list_style_missing_both_skipped():
    assert parse_list_style("随便一段文字。") == []


def test_parse_md_empty_file(tmp_path):
    p = tmp_path / "empty.md"
    p.write_text("", encoding="utf-8")
    assert parse_md_file(str(p)) == []


def test_extract_author_year_title():
    assert extract_author_year_title("张三 - 2020 - 标题_28-77") == ("张三", "2020", "标题")
    assert extract_author_year_title("张三 - 标题") == ("张三", "", "标题")
    assert extract_author_year_title("标题") == ("", "", "标题")


def test_generate_word_from_md(tmp_path):
    md_root = tmp_path / "md"
    (md_root / "2.1 绪论" / "2.1.1 概念界定").mkdir(parents=True)
    (md_root / "2.1 绪论" / "2.1.1 概念界定" / "张三 - 2020 - 标题(1).md").write_text(
        QUOTE_MD, encoding="utf-8"
    )
    out = tmp_path / "out.docx"

    generate_word_from_md(str(md_root), str(out))

    assert out.exists()
    doc = Document(str(out))
    texts = [p.text for p in doc.paragraphs]
    assert "2.1 绪论" in texts
    assert "2.1.1 概念界定" in texts
    assert any("文献一" in t and "张三" in t and "2020" in t for t in texts)
    assert "原文句子一。" in texts
    assert "用途：用于 2.1.1 的具体引用。" in texts