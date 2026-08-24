"""analyze 增量工具与 extract-v2 辅助函数测试。"""

import json
import os

from paper_litflow.analyze import collect_pdfs, file_key, load_state, save_state
from paper_litflow.extract_v2 import iter_pdf_files, load_keywords


def _touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"x")


def test_collect_pdfs_flat_vs_recursive(tmp_path):
    _touch(str(tmp_path / "a.pdf"))
    _touch(str(tmp_path / "sub" / "b.pdf"))
    _touch(str(tmp_path / "note.txt"))

    flat = collect_pdfs(str(tmp_path), recursive=False)
    assert flat == ["a.pdf"]

    rec = collect_pdfs(str(tmp_path), recursive=True)
    assert len(rec) == 2 and any(p.startswith("sub") for p in rec)


def test_file_key_changes_with_mtime_and_stable_within_call(tmp_path):
    p = str(tmp_path / "x.pdf")
    _touch(p)
    k1 = file_key(p)
    k2 = file_key(p)
    assert k1 == k2 and len(k1) == 32

    old = os.stat(p).st_mtime_ns
    os.utime(p, ns=(old + 10**9, old + 10**9))
    assert file_key(p) != k1


def test_state_roundtrip(tmp_path):
    out = str(tmp_path / "out.xlsx")
    save_state(out, {"k": {"标题": "A"}})
    assert load_state(out)["k"]["标题"] == "A"


def test_iter_pdf_files_matches_chapter_prefix_and_walks_deep(tmp_path):
    d13 = tmp_path / "2.1.2 空间演进"
    _touch(str(d13 / "sub" / "paper.pdf"))
    d22 = tmp_path / "2.2 其他章"
    _touch(str(d22 / "other.pdf"))
    _touch(str(d13 / "ignore.txt"))

    got = list(iter_pdf_files(str(tmp_path), ["2.1.2"]))
    assert len(got) == 1
    code, title, path = got[0]
    assert (code, title) == ("2.1.2", "空间演进")
    assert path.endswith("paper.pdf")


def test_load_keywords_utf8_bom_safe(tmp_path):
    p = tmp_path / "kw.json"
    p.write_text('{"1.3.1": "协作学习"}', encoding="utf-8-sig")
    assert load_keywords(str(p))["1.3.1"] == "协作学习"
    assert load_keywords(None) == {}
