"""extract-v2 命令: 带页码、关键词预检、逐字校验与置信度标签的摘抄 (v2)。

与 v1 (extract) 的区别:
- 文本按页注入【P页码】标记, 模型必须回报出处页码
- 送 LLM 前先做本地关键词预检, 未命中小节关键词的 PDF 直接跳过 (省 token)
- 返回严格 JSON 摘抄, 本地逐字校验通过才落盘; 模糊命中降级为低/中置信
- state.json 断点续跑: 中断后重跑只处理未完成条目
"""

import hashlib
import csv
import json
import os
import re
import time

import fitz
from openai import OpenAI
from tqdm import tqdm

from . import config
from .verify import conf_label, norm_text, validate_excerpts

DEFAULT_KEYWORDS = {
    # 未提供 --keywords-json 时不做预检 (空 dict 表示跳过预检逻辑)
}


def load_keywords(path):
    if not path:
        return dict(DEFAULT_KEYWORDS)
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def pdf_pages(path):
    """返回非空页文本列表 (下标0 = 第1页)。"""
    doc = fitz.open(path)
    pages = []
    for p in doc:
        t = p.get_text().strip()
        if t:
            pages.append(t)
    doc.close()
    return pages


def build_marked(pages, max_chars):
    """拼接带【P页码】标记的文本, 截断到 max_chars。"""
    parts, total = [], 0
    for i, t in enumerate(pages, 1):
        piece = f"【P{i}】{t}\n"
        if total + len(piece) > max_chars:
            break
        parts.append(piece)
        total += len(piece)
    return "".join(parts)


def build_prompt(topic, max_excerpts, section_code, section_title, title, text):
    topic_line = f"，{topic_line_inner(topic)}" if topic else ""
    return f"""你是专业的学术研究助手{topic_line}，正在整理硕士论文「文献综述」写作素材。

当前小节：{section_code} {section_title}
文献标题：{title}

任务：从下方文献内容（带【P页码】标记）中，只摘取能支撑**当前小节**论述的**逐字原文**。

严格约束：
1. quote 必须与原文**逐字一致**（包括标点、全角半角、专有名词写法），像复印一样照抄；禁止改写、概括、缩写、拼接不相邻句子、增删任何字符；不要加省略号或引号。每条不超过200字。
2. page 必须是该段原文所在页的整数页码（对应【P数字】标记）；若引用跨页，填起始页码并在 use_for 开头注明“跨页”。
3. 共1~{max_excerpts}条；与当前小节无关则返回空数组。
4. use_for：一句话说明该原文可支撑小节中的哪个具体论点（≤40字）。
5. 只返回严格 JSON：{{"excerpts":[{{"quote":"...","page":1,"use_for":"..."}}]}}，无其他文字。

文献内容：
{text}"""


def topic_line_inner(topic):
    return f"你正在协助撰写硕士论文《{topic}》"


def call_llm(client, prompt, temperature, retries=2):
    for a in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            txt = resp.choices[0].message.content.strip()
            if txt.startswith("```"):
                txt = txt.strip("`").lstrip("json").strip()
            return json.loads(txt).get("excerpts", [])
        except Exception:
            if a == retries:
                return None
            time.sleep(2)
    return None


def iter_pdf_files(pdf_root, chapters):
    """遍历章节目录 (目录名以 chapters 前缀开头), 产出 (section_code, section_title, pdf_path)。"""
    for d in sorted(os.listdir(pdf_root)):
        full = os.path.join(pdf_root, d)
        if not (os.path.isdir(full) and any(d.startswith(c) for c in chapters)):
            continue
        code, _, title = d.partition(" ")
        section_title = title.strip() or d
        for root, _, files in os.walk(full):
            for f in files:
                if f.lower().endswith(".pdf"):
                    yield code, section_title, os.path.join(root, f)


def run(args) -> int:
    if not os.path.exists(args.pdf_root):
        print(f"根目录不存在: {args.pdf_root}")
        return 1

    sections = config.load_sections(args.sections_file)
    keywords = load_keywords(args.keywords_file)
    client = OpenAI(api_key=config.get_api_key(args.env_file),
                    base_url="https://api.deepseek.com/v1")
    os.makedirs(args.output_root, exist_ok=True)
    state_path = args.state_file or os.path.join(args.output_root, ".extract_v2_state.json")
    state = {}
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as f:
            state = json.load(f)

    stats = {"ok": 0, "empty": 0, "precheck_skip": 0, "no_text": 0, "resumed": 0, "api_fail": 0}
    retry_rows = []  # 失败/零摘抄条目 -> 重试清单 CSV
    items = list(iter_pdf_files(args.pdf_root, [c.strip() for c in args.chapters.split(",") if c.strip()]))

    for sec, sec_title, pdf_path in tqdm(items, desc="摘抄v2"):
        out_md = os.path.join(args.output_root, sec,
                              os.path.basename(pdf_path).replace(".pdf", ".md"))
        key = hashlib.md5((pdf_path + str(os.path.getsize(pdf_path))).encode()).hexdigest()[:12]
        if key in state and os.path.exists(out_md):
            stats["resumed"] += 1
            continue

        try:
            pages = pdf_pages(pdf_path)
        except Exception as e:
            print(f"  PDF 打开失败 {os.path.basename(pdf_path)}: {e}")
            stats["no_text"] += 1
            retry_rows.append({"文件": os.path.basename(pdf_path), "小节": sec, "原因": f"打开失败: {e}"})
            continue
        if not pages:
            print(f"  无文本层(扫描件?), 跳过: {os.path.basename(pdf_path)}")
            stats["no_text"] += 1
            retry_rows.append({"文件": os.path.basename(pdf_path), "小节": sec, "原因": "无文本层(扫描件)"})
            continue

        kw = keywords.get(sec) or keywords.get(sec.rstrip(".0123456789")) or ""
        if kw:
            joined_raw = "\n".join(pages)
            if not re.search(kw, joined_raw, re.IGNORECASE):
                print(f"  预检未命中关键词, 跳过: {os.path.basename(pdf_path)}")
                stats["precheck_skip"] += 1
                retry_rows.append({"文件": os.path.basename(pdf_path), "小节": sec, "原因": "关键词预检未命中"})
                continue

        marked = build_marked(pages, args.max_chars)
        pages_norm = {i + 1: norm_text(t) for i, t in enumerate(pages)}
        joined_norm = norm_text("".join(pages))
        title = os.path.basename(pdf_path).replace(".pdf", "")
        prompt = build_prompt(args.topic, args.max_excerpts, sec, sec_title, title, marked)

        raw = call_llm(client, prompt, args.temperature)
        if raw is None:
            print(f"  API 失败放弃: {title[:30]}")
            stats["api_fail"] += 1
            retry_rows.append({"文件": os.path.basename(pdf_path), "小节": sec, "原因": "API 调用失败"})
            continue
        kept = validate_excerpts(raw, pages_norm, joined_norm)
        dropped = len(raw or []) - len(kept)
        if kept:
            stats["ok"] += 1
        else:
            stats["empty"] += 1
            retry_rows.append({"文件": os.path.basename(pdf_path), "小节": sec,
                               "原因": f"零有效摘抄 (LLM原始{len(raw or [])}条全部未过逐字校验)"})

        lines = [f"# {title}", ""]
        lines.append(f"- 支撑小节：{sec} {sec_title}")
        lines.append(f"- 校验说明：逐字比对通过 {len(kept)} 条 / LLM原始 {len(raw or [])} 条 / 本地淘汰 {dropped} 条")
        lines.append("")
        if not kept:
            lines.append("> 本次未提取到通过校验的有效摘抄。")
        channel_high = True  # 章节目录来源默认视为已筛选; 如需区分通道可扩展 --channel-json
        for k in kept:
            c = conf_label(channel_high, k["verify"])
            pg = f"第{k['page']}页" if k["page"] else "跨页/页码未知"
            lines += ["---", "",
                      f"> {k['quote']}", "",
                      f"**出处**：{pg}｜**用途**：用于 {sec} 的具体引用——{k['use_for']}｜**置信度**：[{c}]（{k['verify']}）",
                      ""]
        os.makedirs(os.path.dirname(out_md), exist_ok=True)
        with open(out_md, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        if kept:
            # 仅成功的条目写入断点状态; 零摘抄的不锁定, 重跑即自动重试
            state[key] = {"section": sec, "kept": len(kept)}
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False)
        time.sleep(1)

    if retry_rows:
        retry_csv = os.path.join(args.output_root, "重试清单.csv")
        os.makedirs(args.output_root, exist_ok=True)
        with open(retry_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["文件", "小节", "原因"])
            writer.writeheader()
            writer.writerows(retry_rows)
        print(f"重试清单: {retry_csv} ({len(retry_rows)} 条)")

    print("\n=== extract-v2 完成 ===")
    print(json.dumps(stats, ensure_ascii=False))
    print(f"state: {state_path}")
    return 0
