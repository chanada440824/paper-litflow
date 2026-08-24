"""from-list 命令: 从筛选清单 (Excel/CSV) 直接生成章节目录与带链接的清单 Markdown。

解耦 analyze: 不再依赖 organize 的 Excel, 而是读取「相关文献清单」类表格,
按等级过滤后把 PDF 归入小节目录, 并可选内嵌 Zotero 协议跳转链接。
"""

import json
import os
import re
import shutil

import pandas as pd


def normalize_title(s: str) -> str:
    """标题归一化: 去空白, 统一常见全半角差异。"""
    s = re.sub(r"\s+", "", str(s or ""))
    return s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")


def extract_section_codes(related: str):
    """从相关小节字符串中提取编号列表, 如 "2.1.1,2.2" -> ["1.3.1", "1.3.3"]。"""
    return re.findall(r"\d+(?:\.\d+)+", str(related or ""))


def choose_primary(codes):
    """主小节 = 列表第一个; 无则 None。"""
    return codes[0] if codes else None


def filter_rows(df: pd.DataFrame, grades, grade_col: str = "等级"):
    """按等级过滤行 (大小写不敏感)。"""
    if grades:
        allow = {g.strip().upper() for g in grades}
        return df[df[grade_col].astype(str).str.upper().isin(allow)]
    return df


def load_pdf_index(path):
    """加载 标题->pdf路径 索引 JSON: [{"标题":..., "path":...}, ...]。"""
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    index = {}
    for item in data:
        index.setdefault(normalize_title(item.get("标题", "")), item.get("path", ""))
    return index


def load_links(path):
    """加载 标题->markdown链接串 JSON: {"标题": "[Zotero](...) [PDF](...)"}。"""
    if not path:
        return {}
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    return {normalize_title(k): v for k, v in data.items()}


def run(args) -> int:
    if not os.path.exists(args.list_file):
        print(f"清单文件不存在: {args.list_file}")
        return 1
    if not os.path.exists(args.pdf_index):
        print(f"PDF 索引不存在: {args.pdf_index}")
        return 1
    ext = os.path.splitext(args.list_file)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(args.list_file)
    elif ext == ".csv":
        df = pd.read_csv(args.list_file, encoding="utf-8-sig")
    else:
        print(f"不支持的清单格式: {ext} (仅 xlsx/csv)")
        return 1

    for col in (args.title_col, args.sections_col, args.grade_col):
        if col not in df.columns:
            print(f"清单缺少列: {col} (现有列: {list(df.columns)})")
            return 1

    grades = [g for g in args.grades.split(",") if g.strip()]
    df_sel = filter_rows(df, grades, args.grade_col)
    pdf_index = load_pdf_index(args.pdf_index)
    links = load_links(args.links_json)

    os.makedirs(args.target_root, exist_ok=True)
    manifest, missing = [], []
    for _, row in df_sel.iterrows():
        title = str(row[args.title_col])
        codes = extract_section_codes(row[args.sections_col])
        primary = choose_primary(codes)
        if not primary:
            continue
        src = pdf_index.get(normalize_title(title))
        if not src or not os.path.exists(src):
            missing.append(title)
            continue
        dst_dir = os.path.join(args.target_root, primary)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, os.path.basename(src))
        if not args.skip_copy and not os.path.exists(dst):
            shutil.copy2(src, dst)
        manifest.append({"title": title, "section": primary,
                         "sections": codes, "grade": str(row[args.grade_col]),
                         "pdf": src if args.skip_copy else dst})

    # 生成带链接的清单 Markdown
    list_md = args.list_out or os.path.join(args.target_root, "文献清单.md")
    lines = [f"# 文献分类清单（等级 {'/'.join(grades) if grades else '全部'}）", ""]
    by_sec = {}
    for m in manifest:
        by_sec.setdefault(m["section"], []).append(m)
    for sec in sorted(by_sec):
        lines.append(f"## {sec}（{len(by_sec[sec])} 篇）")
        lines.append("")
        for m in by_sec[sec]:
            link_str = links.get(normalize_title(m["title"]), "")
            pdf_flag = "" if os.path.exists(m["pdf"]) and not args.skip_copy else ""
            lines.append(f"- **{m['grade']}** {m['title']}{pdf_flag} {link_str}".rstrip())
        lines.append("")
    with open(list_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"已归类 {len(manifest)} 篇 | 未匹配 PDF: {len(missing)} | 清单: {list_md}")
    for t in missing[:8]:
        print(f"  MISS: {t[:60]}")
    return 0
