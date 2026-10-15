"""配置加载: API key / base_url / model 从参数或环境变量读取, 严禁硬编码。

优先级: 命令行参数 > 环境变量 > 默认值。
环境变量:
  PAPER_LITFLOW_API_KEY   自定义 API key(优先于 DEEPSEEK_API_KEY)
  DEEPSEEK_API_KEY        DeepSeek API key
  PAPER_LITFLOW_BASE_URL  模型接口地址(默认 https://api.deepseek.com/v1)
  PAPER_LITFLOW_MODEL     默认模型名(默认 deepseek-chat)
  PAPER_LITFLOW_TESSERACT Tesseract 可执行文件路径(OCR 用)
  PAPER_LITFLOW_TESSDATA  Tesseract 语言包目录(OCR 用)
"""

import json
import os
from pathlib import Path


DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"

# 仅供"成本估算"展示, 单位 ¥/百万 token; 以 DeepSeek 官网为准, 可自行修改
PRICE_IN_PER_M = 2.0
PRICE_OUT_PER_M = 8.0


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


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


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


def get_api_key(env_file: str | None = None) -> str:
    """从环境变量读取 key（PAPER_LITFLOW_API_KEY 优先，其次 DEEPSEEK_API_KEY），可选 .env 文件。"""
    if env_file is not None:
        _load_dotenv(env_file)
    key = _env("PAPER_LITFLOW_API_KEY") or _env("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit(
            "未找到 API key。请设置环境变量 PAPER_LITFLOW_API_KEY 或 DEEPSEEK_API_KEY, "
            "或在同目录 .env 中写入 DEEPSEEK_API_KEY=sk-xxx (参考 .env.example, 不要把 key 提交到仓库)"
        )
    return key


def get_base_url(cli_base_url: str | None = None, env_file: str | None = None) -> str:
    """接口地址: 参数 > PAPER_LITFLOW_BASE_URL > 默认 DeepSeek。"""
    if env_file is not None:
        _load_dotenv(env_file)
    return (cli_base_url or "").strip() or _env("PAPER_LITFLOW_BASE_URL") or DEFAULT_BASE_URL


def resolve_model(cli_model: str | None = None, env_file: str | None = None) -> str:
    """模型名: 参数 > PAPER_LITFLOW_MODEL > 默认 deepseek-chat。"""
    if env_file is not None:
        _load_dotenv(env_file)
    return (cli_model or "").strip() or _env("PAPER_LITFLOW_MODEL") or DEFAULT_MODEL


def _is_local(base_url: str) -> bool:
    b = (base_url or "").lower()
    return "localhost" in b or "127.0.0.1" in b or "0.0.0.0" in b


def make_client(
    env_file: str | None = None,
    cli_base_url: str | None = None,
    cli_api_key: str | None = None,
):
    """构造 OpenAI 兼容 client。

    本地接口(如 Ollama http://localhost:11434/v1)可不需要真实 key。
    """
    from openai import OpenAI

    if env_file is not None:
        _load_dotenv(env_file)
    base = get_base_url(cli_base_url, env_file)
    key = (cli_api_key or "").strip() or _env("PAPER_LITFLOW_API_KEY") or _env("DEEPSEEK_API_KEY")
    if not key:
        if _is_local(base):
            key = "sk-local"  # 本地服务不校验 key
        else:
            raise SystemExit(
                "未找到 API key: 设置 PAPER_LITFLOW_API_KEY / DEEPSEEK_API_KEY, 或写 .env; "
                "本地模型可加 --base-url http://localhost:11434/v1"
            )
    return OpenAI(api_key=key, base_url=base)


def estimate_cost(in_tokens: int, out_tokens: int, price_in: float = PRICE_IN_PER_M,
                  price_out: float = PRICE_OUT_PER_M) -> float:
    """按参考价估算费用(¥)。"""
    return in_tokens / 1_000_000 * price_in + out_tokens / 1_000_000 * price_out
