"""配置加载: API key 从环境变量 / .env 读取, 严禁硬编码。"""

import json
import os
from pathlib import Path


# 内置示例章节配置 (一篇论文的章节目录示例)
DEFAULT_SECTIONS = {
    "2.1": "示例章节一",
    "2.1.1": "示例小节 A",
    "2.1.2": "示例小节 B",
    "2.2": "示例章节二",
    "2.2.1": "示例小节 C",
    "2.2.2": "示例小节 D",
}


def load_sections(path: str | None) -> dict:
    """加载章节配置 JSON; path 为 None 时返回内置示例。

    用 utf-8-sig 读取, 兼容 Windows 记事本/PowerShell 写入的 BOM 头。
    """
    if path is None:
        return dict(DEFAULT_SECTIONS)
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not data:
        raise ValueError("章节配置 JSON 必须是非空对象, 键为章节编号, 值为章节标题")
    return data


def get_api_key(env_file: str | None = None) -> str:
    """从环境变量 DEEPSEEK_API_KEY 读取 key, 可选 .env 文件。"""
    if env_file is not None:
        _load_dotenv(env_file)
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "未找到 DEEPSEEK_API_KEY。请设置环境变量, 或在同目录 .env 中写入 "
            "DEEPSEEK_API_KEY=sk-xxx (参考 .env.example, 不要把 key 提交到仓库)"
        )
    return key


def _load_dotenv(env_file: str) -> None:
    path = Path(env_file)
    if not path.exists():
        raise SystemExit(f".env 文件不存在: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def find_env_file() -> str | None:
    """在项目根目录查找 .env。"""
    candidate = Path(__file__).resolve().parent.parent / ".env"
    return str(candidate) if candidate.exists() else None