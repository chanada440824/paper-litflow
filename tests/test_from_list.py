"""from_list: 清单解析、小节选择与等级过滤测试 (纯函数, 不触磁盘)。"""

import pandas as pd

from paper_litflow.from_list import (
    choose_primary,
    extract_section_codes,
    filter_rows,
    normalize_title,
)


def test_extract_section_codes():
    assert extract_section_codes("1.3.1,1.3.2") == ["1.3.1", "1.3.2"]
    assert extract_section_codes("相关: 1.3.2 / 1.3.3") == ["1.3.2", "1.3.3"]
    assert extract_section_codes("") == []
    assert extract_section_codes("纯文字无编号") == []


def test_choose_primary_takes_first():
    assert choose_primary(["1.3.1", "1.3.2"]) == "1.3.1"
    assert choose_primary([]) is None


def test_normalize_title_ignores_whitespace_and_quotes():
    assert normalize_title("foo  bar“x”") == normalize_title("foobar\"x\"")


def _df():
    return pd.DataFrame({
        "标题": ["A论文", "B论文", "C论文"],
        "相关小节": ["1.3.1,1.3.2", "1.3.2", "无关"],
        "等级": ["A", "b", "D"],
    })


def test_filter_rows_case_insensitive():
    out = filter_rows(_df(), {"A", "B"})
    assert list(out["标题"]) == ["A论文", "B论文"]


def test_filter_rows_empty_grades_keeps_all():
    assert len(filter_rows(_df(), [])) == 3
