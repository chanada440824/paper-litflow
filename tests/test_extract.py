"""extract: 摘抄 prompt 构造与分析调用测试（mock 掉 API 与 PDF 解析）。"""

from paper_litflow.extract import analyze_pdf, build_prompt


def test_build_prompt_contains_section_and_constraints():
    p = build_prompt("论文主题", 5, "2.1.2", "从实体空间到虚实融合空间")
    assert "2.1.2 从实体空间到虚实融合空间" in p
    assert "最多提取 5 条原文" in p
    assert "硕士论文《论文主题》" in p


def test_build_prompt_without_topic():
    p = build_prompt("", 3, "2.1", "绪论")
    assert "硕士论文" not in p


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Response:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, content):
        self._content = content

    def create(self, **kwargs):
        return _Response(self._content)


class _Chat:
    def __init__(self, content):
        self.completions = _Completions(content)


class _FakeClient:
    def __init__(self, content):
        self.chat = _Chat(content)


def test_analyze_pdf_returns_stripped_content(monkeypatch):
    from paper_litflow import extract

    monkeypatch.setattr(extract, "extract_text_from_pdf", lambda p, max_chars=8000: "正文内容")
    client = _FakeClient("  > 原文句子。\n\n**用途**：用于 2.1 的引用。  ")
    result = extract.analyze_pdf(client, "x.pdf", "deepseek-chat", 0.3, 8000, 5, "2.1", "绪论", "主题")
    assert result == "> 原文句子。\n\n**用途**：用于 2.1 的引用。"


def test_analyze_pdf_empty_text_returns_none(monkeypatch):
    from paper_litflow import extract

    monkeypatch.setattr(extract, "extract_text_from_pdf", lambda p, max_chars=8000: "")
    client = _FakeClient("whatever")
    assert extract.analyze_pdf(client, "x.pdf", "deepseek-chat", 0.3, 8000, 5, "2.1", "绪论", "主题") is None