"""organize: 标题模糊匹配与 Excel 读取测试。"""

import pandas as pd
import pytest

from paper_litflow.organize import find_pdf_file_by_title, load_names_from_excel


def test_find_pdf_title_substring(tmp_path):
    f = tmp_path / "王五 - 2023 - 协作学习研究.pdf"
    f.write_bytes(b"%PDF-1.7")
    assert find_pdf_file_by_title("协作学习研究", str(tmp_path)) == str(f)


def test_find_pdf_filename_substring_of_title(tmp_path):
    f = tmp_path / "协作学习.pdf"
    f.write_bytes(b"%PDF-1.7")
    assert find_pdf_file_by_title("协作学习研究综述", str(tmp_path)) == str(f)


def test_find_pdf_no_match(tmp_path):
    (tmp_path / "甲 - 2020 - 无关主题.pdf").write_bytes(b"%PDF-1.7")
    assert find_pdf_file_by_title("不存在的标题", str(tmp_path)) is None


def test_find_pdf_multiple_matches_returns_none(tmp_path, capsys):
    (tmp_path / "甲 - 2020 - 协作学习研究.pdf").write_bytes(b"%PDF-1.7")
    (tmp_path / "乙 - 2021 - 协作学习研究续篇.pdf").write_bytes(b"%PDF-1.7")
    assert find_pdf_file_by_title("协作学习研究", str(tmp_path)) is None
    assert "匹配到多个" in capsys.readouterr().out


def test_find_pdf_ignores_non_pdf_files(tmp_path):
    (tmp_path / "notes.txt").write_text("hi", encoding="utf-8")
    assert find_pdf_file_by_title("某主题", str(tmp_path)) is None


def test_excel_missing_file_raises(tmp_path):
    with pytest.raises(SystemExit):
        load_names_from_excel(str(tmp_path / "nope.xlsx"))


def test_excel_missing_title_column_raises(tmp_path):
    p = tmp_path / "t.xlsx"
    pd.DataFrame({"作者": ["甲"]}).to_excel(p, index=False)
    with pytest.raises(SystemExit):
        load_names_from_excel(str(p))


def test_excel_ok(tmp_path):
    p = tmp_path / "t.xlsx"
    pd.DataFrame({"标题": ["T"], "2.1": ["内容"]}).to_excel(p, index=False)
    out = load_names_from_excel(str(p))
    assert list(out.columns) == ["标题", "2.1"]