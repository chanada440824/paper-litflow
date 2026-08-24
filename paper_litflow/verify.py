"""校验工具: 摘抄逐字比对与置信度标签 (纯函数, 便于单测)。

设计来自 2026-08-24 实战: 大模型倾向"转述"而非逐字引用,
必须本地强制校验原文确实存在, 才能作为论文写作素材。
"""

import difflib
import re


def norm_text(s: str) -> str:
    """归一化文本用于比对: 去所有空白 + 统一弯引号/破折号。"""
    s = re.sub(r"\s+", "", s or "")
    return (
        s.replace("“", '"').replace("”", '"')
        .replace("‘", "'").replace("’", "'")
        .replace("—", "-").replace("–", "-")
    )


def validate_excerpts(excerpts, pages_norm: dict, joined_norm: str, fuzzy_ratio: float = 0.90,
                      min_len: int = 10):
    """对模型返回的摘抄列表做逐字校验。

    excerpts: [{"quote":..., "page":int|None, "use_for":...}, ...]
    pages_norm: {页码: 归一化页面文本}
    joined_norm: 全文拼接的归一化文本 (跨页兜底)

    返回保留列表, 每项追加:
      verify: "exact" 单页精确命中 | "fuzzy" 相似度≥fuzzy_ratio 或全文命中 | 被淘汰的不返回
      page:   校正后的页码 (可能为 None 表示跨页/未知); 精确命中时以实际定位页为准
    """
    kept = []
    for ex in excerpts or []:
        q = str(ex.get("quote", "")).strip()
        if not q or len(q) < min_len:
            continue
        qn = norm_text(q)
        page_no = None
        mode = None
        for pi, pn in pages_norm.items():
            if qn in pn:
                page_no, mode = pi, "exact"
                break
        if page_no is None and qn in joined_norm:
            mode = "fuzzy"
        if mode is None and len(qn) >= 20:
            # 匹配块覆盖率: 兼容单字增删把公共子串切成多段的情形
            best_cover, best_page = 0.0, None
            for pi, pn in pages_norm.items():
                sm = difflib.SequenceMatcher(None, qn, pn, autojunk=False)
                cover = sum(b.size for b in sm.get_matching_blocks()) / max(1, len(qn))
                if cover > best_cover:
                    best_cover, best_page = cover, pi
                if best_cover >= 0.95:
                    break
            if best_cover >= fuzzy_ratio:
                page_no, mode = best_page, "fuzzy"
        if mode is None:
            continue
        try:
            declared = int(ex.get("page"))
        except (TypeError, ValueError):
            declared = None
        if page_no is None:
            page_no = declared
        kept.append({
            "quote": q,
            "page": page_no,
            "use_for": str(ex.get("use_for", "")).strip(),
            "verify": mode,
        })
    return kept


def conf_label(channel_high: bool, mode: str) -> str:
    """置信度标签: 高=核心来源且逐字命中; 中=核心来源但模糊命中,或普通来源逐字命中; 低=其余。"""
    if mode == "exact":
        return "高" if channel_high else "中"
    return "中" if channel_high else "低"
