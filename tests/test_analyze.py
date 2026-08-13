"""analyze: prompt 构造与模型 JSON 容错解析测试。"""

from paper_litflow.analyze import build_prompt, parse_json_response

SECTIONS = {"2.1": "绪论与理论基础", "2.2": "协作学习理论"}


def test_build_prompt_lists_all_sections():
    prompt = build_prompt(SECTIONS, "测试论文主题")
    assert "2.1 绪论与理论基础" in prompt
    assert "2.2 协作学习理论" in prompt
    assert "硕士论文《测试论文主题》" in prompt


def test_build_prompt_without_topic():
    prompt = build_prompt(SECTIONS, "")
    assert "硕士论文" not in prompt


def test_parse_pure_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_parse_json_with_fences():
    raw = '```json\n{"a": 1}\n```'
    assert parse_json_response(raw) == {"a": 1}


def test_parse_json_with_loose_fences_and_spaces():
    raw = '```json   \n{"a": 1}   \n```   '
    assert parse_json_response(raw) == {"a": 1}


def test_parse_json_with_trailing_comma_falls_back_clean():
    raw = '{"a": 1,}'
    assert parse_json_response(raw) is None


def test_parse_invalid_returns_none(capsys):
    assert parse_json_response("这不是 JSON") is None
    assert "JSON 解析失败" in capsys.readouterr().out