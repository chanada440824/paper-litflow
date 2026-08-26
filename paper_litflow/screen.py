"""screen 命令: 全库元数据筛选 (标题+摘要), 批量分配小节与 A/B/C 等级, 输出 from-list 清单。

与 analyze (PDF 级) 的区别: screen 只读元数据 JSON, 便宜快速, 适合先全库过一遍,
再由 from-list 按等级/小节建目录、extract-v2 精抽。输入格式见 zotero_meta.json:
[{"item_id":..,"标题":..,"作者":..,"年份":..,"摘要":..}, ...]
"""

import json
import os
import re
import time

import pandas as pd

from . import config

MAX_ABSTRACT = 260


def build_prompt(items, sections, topic):
    """构造批量筛选 prompt: 每条 [序号] 标题｜年份｜作者｜摘要, 要求按小节分配 + A/B/C。"""
    if topic:
        topic_line = "你在为硕士论文《%s》筛选写作素材文献。" % topic
    else:
        topic_line = "你在为硕士论文筛选写作素材文献。"
    section_list = "\n".join("- %s %s" % (k, v) for k, v in sections.items())
    lines = []
    for idx, m in enumerate(items):
        ab = (m.get("摘要") or "").replace("\n", " ")[:MAX_ABSTRACT]
        lines.append("[%d] 标题：%s｜年份：%s｜作者：%s｜摘要：%s"
                     % (idx, m["标题"], m.get("年份"), m.get("作者"), ab))
    item_block = "\n".join(lines)
    return (
        topic_line
        + "\n\n小节（三级）：\n" + section_list
        + "\n\n对下面每条文献（[序号] 标题｜年份｜作者｜摘要），判断它是否可作为该章的写作素材：\n"
        + "- 完全不相关 → 该条返回 null\n"
        + "- 相关 → 给出最贴切的 1~3 个小节编号（可跨节），并给相关度等级：A=直接支撑、B=间接支撑、C=边缘相关\n"
        + '\n严格只返回 JSON：{"results":[{"index":0,"sections":["2.1.1"],"grade":"A"} 或 null, ...]}，'
        + "顺序与输入一致，无其他文字。\n\n文献列表：\n" + item_block
    )


def parse_response(text):
    """解析 LLM 返回, 兼容 ```json 围栏; 失败抛异常由调用方重试。"""
    txt = (text or "").strip()
    if txt.startswith("```"):
        txt = txt.strip("`").lstrip("json").strip()
    return json.loads(txt)


def normalize_sections(secs):
    """把 sections 字段规范化为列表 (兼容 字符串/列表/None)。"""
    if not secs:
        return []
    if isinstance(secs, str):
        return [s for s in re.split(r"[,，、\s]+", secs) if s]
    return [str(s) for s in secs if s]


def screen_items(items, sections, topic, batch, llm_func, retries=2, sleep_s=2):
    """批量筛选, llm_func(prompt)->parsed dict; 返回与 items 等长的结果列表 (未命中为 None)。"""
    results = [None] * len(items)
    for start in range(0, len(items), batch):
        chunk = items[start:start + batch]
        prompt = build_prompt(chunk, sections, topic)
        parsed = None
        for attempt in range(retries + 1):
            try:
                parsed = llm_func(prompt)
                break
            except Exception:
                if attempt == retries:
                    break
                time.sleep(sleep_s)
        if parsed and isinstance(parsed, dict):
            rmap = {r["index"]: r for r in parsed.get("results", []) if r}
            for k, r in rmap.items():
                if start + k < len(items):
                    results[start + k] = r
    return results


def build_rows(items, results):
    """结果 -> from-list 清单行 (标题/相关小节/等级), 跳过未命中或无小节条目。"""
    rows = []
    for m, r in zip(items, results):
        if not r:
            continue
        secs = normalize_sections(r.get("sections"))
        if not secs:
            continue
        rows.append({"标题": m["标题"], "相关小节": ",".join(secs),
                     "等级": str(r.get("grade", "C")).upper()})
    return rows


def run(args) -> int:
    if not os.path.exists(args.meta):
        print("元数据文件不存在: %s" % args.meta)
        return 1
    with open(args.meta, encoding="utf-8-sig") as f:
        items = json.load(f)
    sections = config.load_sections(args.sections_file)
    if not items:
        print("元数据为空")
        return 1

    from openai import OpenAI
    client = OpenAI(api_key=config.get_api_key(args.env_file),
                    base_url="https://api.deepseek.com/v1")

    def llm_func(prompt):
        resp = client.chat.completions.create(
            model=args.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        return parse_response(resp.choices[0].message.content)

    results = screen_items(items, sections, args.topic, args.batch, llm_func)
    rows = build_rows(items, results)
    df = pd.DataFrame(rows).drop_duplicates(subset=["标题"])
    df.to_excel(args.output, index=False)

    print("全库筛选完成: 处理 %d 条, 命中 %d 条 (A/B/C 见输出)" % (len(items), len(rows)))
    from collections import Counter
    print("等级分布:", dict(Counter(df["等级"])))
    print("清单已写:", args.output)
    return 0