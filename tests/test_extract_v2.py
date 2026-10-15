"""extract-v2: 页码标记、页级关键词定位、prompt、调用与端到端 (全部 mock, 不联网/不读真 PDF)。"""

import argparse

import pytest

from paper_litflow import extract_v2


# ---- build_marked / 页码 ----

def test_build_marked_uses_real_page_numbers():
    pages = [(1, "内容一"), (3, "内容三")]  # 页码有跳(第2页空)
    m = extract_v2.build_marked(pages, 100000)
    assert "【P1】内容一" in m
    assert "【P3】内容三" in m
    assert "【P2】" not in m


def test_build_marked_truncates_to_max_chars():
    pages = [(i, "x" * 100) for i in range(1, 100)]
    m = extract_v2.build_marked(pages, 250)
    assert len(m) <= 260


# ---- select_pages (页级关键词定位) ----

def test_select_pages_no_kw_returns_all():
    pages = [(1, "a"), (2, "b")]
    assert extract_v2.select_pages(pages, "", 1) == pages


def test_select_pages_kw_hit_no_context():
    pages = [(1, "无关"), (2, "关键词命中"), (3, "无关")]
    assert extract_v2.select_pages(pages, "关键词", context=0) == [(2, "关键词命中")]


def test_select_pages_kw_hit_with_context():
    pages = [(1, "无关"), (2, "关键词命中"), (3, "无关"), (4, "无关")]
    sel = extract_v2.select_pages(pages, "关键词", context=1)
    assert [n for n, _ in sel] == [1, 2, 3]


def test_select_pages_kw_miss_returns_none():
    assert extract_v2.select_pages([(1, "a"), (2, "b")], "找不到", 1) is None


# ---- build_prompt ----

def test_build_prompt_contains_constraints():
    p = extract_v2.build_prompt("主题", 5, "2.1.1", "小节", "标题", "【P1】正文")
    assert "逐字一致" in p
    assert "2.1.1 小节" in p
    assert "【P1】正文" in p
    assert "最多" not in p  # v2 用"共1~N条"表述


# ---- iter_pdf_files ----

def test_iter_pdf_files(tmp_path):
    (tmp_path / "2.1 小节A").mkdir()
    (tmp_path / "2.1 小节A" / "a.pdf").write_bytes(b"x")
    (tmp_path / "2.2 小节B").mkdir()
    (tmp_path / "9.9 其他").mkdir()
    items = list(extract_v2.iter_pdf_files(str(tmp_path), ["2.1", "2.2"]))
    assert len(items) == 1
    code, title, _ = items[0]
    assert code == "2.1" and title == "小节A"


# ---- call_llm ----

class _M:
    def __init__(self, c):
        self.content = c


class _C:
    def __init__(self, m):
        self.message = m


class _U:
    prompt_tokens = 10
    completion_tokens = 5


class _R:
    def __init__(self, c):
        self.choices = [_C(_M(c))]
        self.usage = _U()


class _Comp:
    def __init__(self, c):
        self._c = c

    def create(self, **kw):
        return _R(self._c)


class _Chat:
    def __init__(self, c):
        self.completions = _Comp(c)


class _Client:
    def __init__(self, c):
        self.chat = _Chat(c)


def test_call_llm_parses_json_and_usage():
    raw = '{"excerpts":[{"quote":"q","page":1,"use_for":"u"}]}'
    ex, usage = extract_v2.call_llm(_Client(raw), "m", "p", 0.1, retries=0)
    assert ex[0]["quote"] == "q"
    assert usage == (10, 5)


def test_call_llm_strips_fence():
    raw = '```json\n{"excerpts":[]}\n```'
    ex, _ = extract_v2.call_llm(_Client(raw), "m", "p", 0.1, retries=0)
    assert ex == []


# ---- run 端到端 (全 mock) ----

def test_run_end_to_end(tmp_path, monkeypatch):
    root = tmp_path / "已归类" / "2.1 小节"
    root.mkdir(parents=True)
    (root / "作者 - 2020 - 标题.pdf").write_bytes(b"%PDF-1.4 fake")
    out = tmp_path / "摘抄"

    monkeypatch.setattr(extract_v2.pdf_utils, "page_texts",
                        lambda p, **kw: [(1, "图书馆协作学习空间研究"), (2, "正文二")])

    def fake_call(client, model, prompt, temperature, **kw):
        return ([{"quote": "图书馆协作学习空间研究", "page": 1, "use_for": "说明"}], (3, 4))

    monkeypatch.setattr(extract_v2, "call_llm", fake_call)
    monkeypatch.setattr(extract_v2.config, "make_client", lambda *a, **k: object())

    args = argparse.Namespace(
        pdf_root=str(tmp_path / "已归类"), output_root=str(out), chapters="2.1",
        sections_file=None, keywords_file=None, topic="", temperature=0.1,
        max_chars=9000, max_excerpts=5, state_file=None, env_file=None,
        model=None, base_url=None, ocr=False, context_pages=1,
    )
    assert extract_v2.run(args) == 0
    md = out / "2.1" / "作者 - 2020 - 标题.md"
    assert md.exists()
    text = md.read_text(encoding="utf-8")
    assert "图书馆协作学习空间研究" in text
    assert "第1页" in text


def test_run_skips_when_kw_no_hit(tmp_path, monkeypatch):
    root = tmp_path / "已归类" / "2.1 小节"
    root.mkdir(parents=True)
    (root / "x.pdf").write_bytes(b"x")
    kw = tmp_path / "kw.json"
    kw.write_text('{"2.1": "绝不出现的词"}', encoding="utf-8")

    monkeypatch.setattr(extract_v2.pdf_utils, "page_texts",
                        lambda p, **kw: [(1, "完全无关的内容")])
    monkeypatch.setattr(extract_v2.config, "make_client", lambda *a, **k: object())
    monkeypatch.setattr(extract_v2, "call_llm",
                        lambda *a, **k: pytest.fail("命中失败时不应调用模型"))

    args = argparse.Namespace(
        pdf_root=str(tmp_path / "已归类"), output_root=str(tmp_path / "o"), chapters="2.1",
        sections_file=None, keywords_file=str(kw), topic="", temperature=0.1,
        max_chars=9000, max_excerpts=5, state_file=None, env_file=None,
        model=None, base_url=None, ocr=False, context_pages=1,
    )
    assert extract_v2.run(args) == 0
    assert not (tmp_path / "o" / "2.1" / "x.md").exists()
