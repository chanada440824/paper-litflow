"""parse_filename_metadata: 文件名元数据解析测试。"""

from paper_litflow.pdf_utils import parse_filename_metadata


def test_full_author_year_title():
    assert parse_filename_metadata("张三 - 2020 - 智能建筑研究.pdf") == (
        "张三",
        "2020",
        "智能建筑研究",
    )


def test_full_with_page_suffix():
    assert parse_filename_metadata("张三 - 2020 - 智能建筑研究_28-77.pdf") == (
        "张三",
        "2020",
        "智能建筑研究",
    )


def test_author_title_only():
    assert parse_filename_metadata("张三 - 智能建筑研究.pdf") == ("张三", "", "智能建筑研究")


def test_title_only():
    assert parse_filename_metadata("智能建筑研究.pdf") == ("", "", "智能建筑研究")


def test_extra_spaces_around_separators():
    assert parse_filename_metadata(" 张三  -  2021  -  协作学习研究.pdf") == (
        "张三",
        "2021",
        "协作学习研究",
    )


def test_latin_and_suffix_digits():
    assert parse_filename_metadata("（美）John Smith - 2022 - Learning Spaces_1-10.pdf") == (
        "（美）John Smith",
        "2022",
        "Learning Spaces",
    )


# ---- page_texts / OCR ----

import fitz  # noqa: E402
import pytest  # noqa: E402

from paper_litflow import pdf_utils  # noqa: E402


def _make_pdf(path, texts):
    doc = fitz.open()
    for t in texts:
        p = doc.new_page()
        if t:
            p.insert_text((72, 100), t, fontsize=12)
    doc.save(path)
    doc.close()


def test_page_texts_keeps_original_page_numbers(tmp_path):
    f = str(tmp_path / "a.pdf")
    _make_pdf(f, ["page one", "", "page three"])
    d = {n: t for n, t in pdf_utils.page_texts(f)}
    assert "one" in d[1]
    assert "three" in d[3]  # 中间空页不导致页码错位


def test_extract_text_from_pdf_truncates(tmp_path):
    f = str(tmp_path / "a.pdf")
    _make_pdf(f, ["x" * 2000])
    out = pdf_utils.extract_text_from_pdf(f, max_chars=50)
    assert 0 < len(out) <= 50


def test_find_tesseract_from_env(monkeypatch, tmp_path):
    exe = tmp_path / "tesseract.exe"
    exe.write_text("x", encoding="utf-8")
    monkeypatch.setenv("PAPER_LITFLOW_TESSERACT", str(exe))
    assert pdf_utils.find_tesseract() == str(exe)


def test_ocr_image_missing_binary_raises(monkeypatch):
    monkeypatch.setattr(pdf_utils, "find_tesseract", lambda: None)
    with pytest.raises(RuntimeError):
        pdf_utils.ocr_image("x.png")


def test_ocr_image_calls_tesseract(monkeypatch, tmp_path):
    png = tmp_path / "p.png"
    png.write_bytes(b"x")
    seen = {}

    class R:
        returncode = 0
        stdout = "识别文本"
        stderr = ""

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return R()

    monkeypatch.setattr(pdf_utils.subprocess, "run", fake_run)
    monkeypatch.setattr(pdf_utils, "find_tesseract", lambda: "tesseract")
    monkeypatch.setattr(pdf_utils, "find_tessdata", lambda: None)
    out = pdf_utils.ocr_image(str(png), lang="chi_sim+eng")
    assert out == "识别文本"
    assert "chi_sim+eng" in seen["cmd"]