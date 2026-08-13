"""extract 命令: 按章节目录结构逐篇摘抄, 输出 Markdown。"""

import os
import time

from openai import OpenAI
from tqdm import tqdm

from . import config
from .pdf_utils import extract_text_from_pdf


def build_prompt(topic: str, max_excerpts: int, section_code: str, section_title: str) -> str:
    """构造摘抄 prompt: 只摘取与当前小节相关的原文, 保留格式约束。"""
    topic_line = f"你正在协助撰写硕士论文《{topic}》" if topic else ""
    section_full = f"{section_code} {section_title}"
    return f"""你是一位专业的学术研究助手，{topic_line}，负责整理文献综述。

当前正在分析文献, 请仅摘取与该文献相关的原文段落。

**重要约束**：
- 只为本篇论文提取与 **当前小节** ({section_full}) 相关的原文句子。
- 每条摘抄的用途只能标注为「{section_full}」中的具体用途，禁止使用其他小节编号。
- 如果原文与当前小节无关，不要提取任何摘抄。
- 每篇论文最多提取 {max_excerpts} 条原文，每条原文不超过 200 字。
- 输出格式：每条摘抄之间用 '---' 单独一行分隔，格式如下：
> 原文内容：

**用途**：用于 {section_full} 的具体引用，一句话说明。

直接输出摘抄，不要输出解释和多余内容。
"""


def analyze_pdf(client, pdf_path: str, model: str, temperature: float, max_chars: int, max_excerpts: int, section_code: str, section_title: str, topic: str):
    text = extract_text_from_pdf(pdf_path, max_chars)
    if not text:
        return None

    prompt = build_prompt(topic, max_excerpts, section_code, section_title) + text

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=2000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  API 调用失败: {e}")
        return None


def run(args) -> int:
    if not os.path.exists(args.pdf_root):
        print(f"根目录不存在: {args.pdf_root}")
        return 1

    api_key = config.get_api_key(args.env_file)
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    sections = config.load_sections(args.sections_file)
    chapters = [c.strip() for c in args.chapters.split(",") if c.strip()]

    # 收集匹配章节的目录
    chapter_dirs = []
    for d in os.listdir(args.pdf_root):
        full = os.path.join(args.pdf_root, d)
        if os.path.isdir(full) and any(d.startswith(ch) for ch in chapters):
            chapter_dirs.append(d)
    if not chapter_dirs:
        print(f"未找到以 {chapters} 开头的章节目录")
        return 1

    os.makedirs(args.output_root, exist_ok=True)

    for chapter in chapter_dirs:
        chapter_path = os.path.join(args.pdf_root, chapter)
        sub_dirs = [d for d in os.listdir(chapter_path) if os.path.isdir(os.path.join(chapter_path, d))]
        if not sub_dirs:
            print(f"  警告: {chapter} 下没有子目录, 跳过")
            continue

        print(f"\n处理章节: {chapter}")
        for sub in sub_dirs:
            sub_path = os.path.join(chapter_path, sub)
            pdf_files = []
            for root, _, files in os.walk(sub_path):
                for file in files:
                    if file.lower().endswith(".pdf"):
                        pdf_files.append(os.path.join(root, file))
            if not pdf_files:
                print(f"    警告: {sub} 下没有 PDF 文件, 跳过")
                continue
            print(f"    处理小节: {sub} (共 {len(pdf_files)} 篇 PDF)")

            section_code, section_title = sub.split(maxsplit=1) if " " in sub else (sub, sub)

            for pdf_path in pdf_files:
                base_name = os.path.basename(pdf_path).replace(".pdf", ".md")
                output_file = os.path.join(args.output_root, chapter, sub, base_name)
                os.makedirs(os.path.dirname(output_file), exist_ok=True)

                print(f"      处理: {os.path.basename(pdf_path)}")
                result = analyze_pdf(
                    client, pdf_path, args.model, args.temperature,
                    args.max_chars, args.max_excerpts, section_code, section_title, args.topic,
                )
                if result and result.strip():
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(f"# {os.path.basename(pdf_path)}\n\n{result}")
                else:
                    print(f"        警告: {os.path.basename(pdf_path)} 未提取到有效摘抄")
                time.sleep(1)

    print("\n全部处理完成!")
    return 0