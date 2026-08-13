"""analyze 命令: 批量分析 PDF, 按章节归类输出 Excel。"""

import json
import os
import re
import time

import pandas as pd
from openai import OpenAI
from tqdm import tqdm

from . import config
from .pdf_utils import extract_text_from_pdf, parse_filename_metadata


def build_prompt(sections: dict, topic: str) -> str:
    """构造分析 prompt: 让模型按章节归类输出严格 JSON。"""
    section_list = "\n".join([f"- {num} {title}" for num, title in sections.items()])
    topic_line = f"你正在协助撰写硕士论文《{topic}》。" if topic else ""
    prompt = f"""你是一位专业的学术研究助手。{topic_line}

任务：分析以下文献，为每篇论文提取以下信息，**只返回一个严格的 JSON 对象**，不要包含任何其他文字。

- 请直接使用「已知信息」中提供的标题、作者、年份，不要修改。
- 为每个章节小节提供与该小节相关的文献综述内容，没有相关内容则值为空字符串。

章节小节列表：
{section_list}

JSON 示例：
{{
    "文献摘要": "...",
    "关键词": "关键词1,关键词2",
    "2.1.1": "本节可引用的综述内容...",
    "2.1.2": "",
    "2.1.3": "本节可引用的综述内容..."
}}

直接返回 JSON，不要使用 Markdown 代码块。
"""
    return prompt


def parse_json_response(response_text: str):
    """容错解析模型返回的 JSON (剥离 Markdown 代码块围栏)。"""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        cleaned = re.sub(r"^```json\s*", "", response_text)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except Exception:
            print(f"  JSON 解析失败, 原始响应前 500 字符: {response_text[:500]}")
            return None


def analyze_pdf(client, pdf_path: str, filename: str, prompt: str, sections: dict, temperature: float, model: str):
    author, year, title_from_filename = parse_filename_metadata(filename)
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return None

    full_prompt = (
        prompt
        + f"\n已知信息：\n标题：{title_from_filename}\n作者：{author}\n年份：{year if year else '未知'}\n\n"
        + f"文献内容：\n{text}"
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        data = parse_json_response(response.choices[0].message.content.strip())
        if not data:
            return None
        row = {
            "标题": title_from_filename,
            "作者": author,
            "年份": year if year else data.get("年份", ""),
            "文献摘要": data.get("文献摘要", ""),
            "关键词": data.get("关键词", ""),
        }
        for sec in sections.keys():
            row[sec] = data.get(sec, "")
        return row
    except Exception as e:
        print(f"  API 调用失败: {e}")
        return None


def run(args) -> int:
    if not os.path.exists(args.pdf_dir):
        print(f"文件夹不存在: {args.pdf_dir}")
        return 1

    sections = config.load_sections(args.sections_file)
    pdf_files = [f for f in os.listdir(args.pdf_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print("未找到 PDF 文件")
        return 1

    api_key = config.get_api_key(args.env_file)
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    prompt = build_prompt(sections, args.topic)

    print(f"找到 {len(pdf_files)} 篇 PDF")
    results = []
    for idx, filename in enumerate(tqdm(pdf_files, desc="批量分析"), 1):
        print(f"\n[{idx}/{len(pdf_files)}] {filename}")
        row_data = analyze_pdf(
            client,
            os.path.join(args.pdf_dir, filename),
            filename,
            prompt,
            sections,
            args.temperature,
            args.model,
        )
        if row_data:
            row_data["序号"] = idx
            results.append(row_data)
        else:
            print(f"  跳过 {filename}")
        time.sleep(1)

    if results:
        df = pd.DataFrame(results)
        cols = ["序号", "标题", "作者", "年份", "文献摘要", "关键词"] + list(sections.keys())
        df = df[cols]
        df.to_excel(args.output, index=False)
        print(f"\n完成, 结果已保存: {args.output}")
    else:
        print("没有任何成功处理的结果")
    return 0