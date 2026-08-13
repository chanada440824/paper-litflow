"""config: 章节配置加载与 API key 读取测试。"""

import json

import pytest

from paper_litflow import config


def test_default_sections_returns_copy():
    s = config.load_sections(None)
    assert s["2.1"] == "示例章节一"
    s["2.1"] = "改动不应污染默认值"
    assert config.load_sections(None)["2.1"] == "示例章节一"


def test_load_sections_from_json(tmp_path):
    p = tmp_path / "sections.json"
    p.write_text('{"1.1": "绪论"}', encoding="utf-8")
    assert config.load_sections(str(p)) == {"1.1": "绪论"}


def test_load_sections_with_bom(tmp_path):
    p = tmp_path / "sections.json"
    p.write_bytes(b"\xef\xbb\xbf" + '{"1.1": "绪论"}'.encode("utf-8"))
    assert config.load_sections(str(p)) == {"1.1": "绪论"}


def test_load_sections_empty_object_raises(tmp_path):
    p = tmp_path / "sections.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        config.load_sections(str(p))


def test_load_sections_invalid_json_raises(tmp_path):
    p = tmp_path / "sections.json"
    p.write_text("这不是 JSON", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        config.load_sections(str(p))


def test_get_api_key_missing_raises(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        config.get_api_key()


def test_get_api_key_from_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-123")
    assert config.get_api_key() == "sk-test-123"


def test_dotenv_parsing(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# 注释行\n\nDEEPSEEK_API_KEY=sk-from-file\nOTHER=value=with=equals\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert config.get_api_key(str(env_file)) == "sk-from-file"


def test_dotenv_missing_file_raises(tmp_path):
    with pytest.raises(SystemExit):
        config._load_dotenv(str(tmp_path / "nope.env"))


def test_dotenv_does_not_override_existing_env(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=sk-from-file", encoding="utf-8")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-env")
    assert config.get_api_key(str(env_file)) == "sk-from-env"