"""screen: 全库元数据筛选的 prompt 构建、响应解析与结果规整测试。"""

from paper_litflow.screen import (
    build_prompt,
    build_rows,
    normalize_sections,
    parse_response,
    screen_items,
)

SECTIONS = {"2.1": "发展背景", "2.1.1": "空间转变"}
ITEMS = [
    {"标题": "文献甲", "年份": 2020, "作者": "张三", "摘要": "研究协作学习空间。"},
    {"标题": "文献乙", "年份": 2021, "作者": "李四", "摘要": "与本文无关。"},
]


def test_build_prompt_contains_sections_and_items():
    p = build_prompt(ITEMS, SECTIONS, "论文主题")
    assert "2.1.1 空间转变" in p
    assert "[0] 标题：文献甲" in p
    assert "[1] 标题：文献乙" in p
    assert "论文主题" in p


def test_parse_response_strips_fence():
    assert parse_response('```json\n{"results": []}\n```') == {"results": []}
    assert parse_response('{"results": [{"index": 0}]}') == {"results": [{"index": 0}]}


def test_normalize_sections():
    assert normalize_sections("2.1.1,2.1.2") == ["2.1.1", "2.1.2"]
    assert normalize_sections(["2.1.1", 2.1]) == ["2.1.1", "2.1"]
    assert normalize_sections(None) == []
    assert normalize_sections("") == []


def test_screen_items_uses_fake_llm():
    calls = []

    def fake_llm(prompt):
        calls.append(prompt)
        return {"results": [{"index": 0, "sections": ["2.1.1"], "grade": "A"},
                            {"index": 1, "sections": None}]}

    results = screen_items(ITEMS, SECTIONS, "", 5, fake_llm)
    assert len(results) == 2
    assert results[0]["grade"] == "A"
    assert results[1]["sections"] is None
    assert len(calls) == 1


def test_screen_items_retries_on_bad_response():
    calls = []

    def flaky(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            raise ValueError("bad json")
        return {"results": [{"index": 0, "sections": ["2.1.1"], "grade": "B"}]}

    results = screen_items(ITEMS, SECTIONS, "", 5, flaky, retries=1, sleep_s=0)
    assert results[0]["grade"] == "B"
    assert len(calls) == 2


def test_build_rows_skips_unassigned():
    results = [{"sections": ["2.1.1"], "grade": "A"},
               None,
               {"sections": "2.1", "grade": "b"}]
    rows = build_rows(ITEMS + [{"标题": "文献丙"}], results)
    assert rows[0] == {"标题": "文献甲", "相关小节": "2.1.1", "等级": "A"}
    assert rows[1] == {"标题": "文献丙", "相关小节": "2.1", "等级": "B"}
    assert len(rows) == 2