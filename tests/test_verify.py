"""verify: 逐字校验与置信度标签测试。"""

from paper_litflow.verify import conf_label, norm_text, validate_excerpts


PAGES = {
    1: norm_text("协作学习起源于二十世纪七十年代，约翰逊兄弟提出了合作学习理论。"),
    2: norm_text("学习共享空间强调空间重组与资源共享，以支持小组研讨。"),
}
JOINED = PAGES[1] + PAGES[2]


def test_norm_unifies_whitespace_and_quotes():
    assert norm_text("协作  学习\n“理论”") == norm_text("协作学习“理论”")
    assert norm_text("A—B") == norm_text("A-B")


def test_exact_hit_returns_page():
    raw = [{"quote": "约翰逊兄弟提出了合作学习理论", "page": 1, "use_for": "起源"}]
    kept = validate_excerpts(raw, PAGES, JOINED)
    assert len(kept) == 1
    assert kept[0]["verify"] == "exact"
    assert kept[0]["page"] == 1


def test_paraphrased_quote_is_dropped():
    raw = [{"quote": "合作学习理论是由约翰逊兄弟在七十年代提出的观点", "page": 1, "use_for": "x"}]
    assert validate_excerpts(raw, PAGES, JOINED) == []


def test_fuzzy_rescue_for_slightly_altered_quote():
    # 与原文差异约 5% (少一个"了"), 应被模糊兜底
    q = "协作学习起源于二十世纪七十年代，约翰逊兄弟提出合作学习理论。"
    raw = [{"quote": q, "page": 1, "use_for": "x"}]
    kept = validate_excerpts(raw, PAGES, JOINED)
    assert len(kept) == 1 and kept[0]["verify"] == "fuzzy"


def test_short_quote_is_skipped():
    raw = [{"quote": "太短", "page": 1, "use_for": ""}]
    assert validate_excerpts(raw, PAGES, JOINED) == []


def test_wrong_declared_page_corrected_to_actual_page():
    raw = [{"quote": "约翰逊兄弟提出了合作学习理论", "page": 2, "use_for": "x"}]
    kept = validate_excerpts(raw, PAGES, JOINED)
    assert kept[0]["page"] == 1


def test_conf_label_matrix():
    assert conf_label(True, "exact") == "高"
    assert conf_label(False, "exact") == "中"
    assert conf_label(True, "fuzzy") == "中"
    assert conf_label(False, "fuzzy") == "低"
