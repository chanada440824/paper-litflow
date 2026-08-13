"""organize 命令: 按 Excel 中的小节归类, 复制 PDF 到章节目录结构。"""

import os
import re
import shutil
from pathlib import Path

import pandas as pd

from . import config


def find_pdf_file_by_title(title: str, source_folder: str):
    """在 source_folder 中按规范化标题 (去符号/空格/小写) 模糊匹配 PDF。"""
    def normalize(s: str) -> str:
        s = re.sub(r"[^\w\u4e00-\u9fff]+", "", s)
        return s.lower().strip()

    norm_title = normalize(title)
    candidates = []
    for f in os.listdir(source_folder):
        if not f.lower().endswith(".pdf"):
            continue
        base = os.path.splitext(f)[0]
        norm_base = normalize(base)
        if norm_title in norm_base or norm_base in norm_title:
            candidates.append(os.path.join(source_folder, f))
    if len(candidates) == 1:
        return candidates[0]
    elif len(candidates) > 1:
        print(f"  警告: 标题 '{title}' 匹配到多个文件: {candidates}")
    else:
        print(f"  警告: 找不到与 '{title}' 匹配的文件")
    return None


def load_names_from_excel(excel_path: str):
    """读取 analyze 输出的 Excel, 返回 (章节编号集合, 行列表)。"""
    if not os.path.exists(excel_path):
        raise SystemExit(f"Excel 文件不存在: {excel_path}")
    df = pd.read_excel(excel_path)
    if "标题" not in df.columns:
        raise SystemExit('Excel 缺少"标题"列')
    return df


def run(args) -> int:
    df = load_names_from_excel(args.excel)
    sections = config.load_sections(args.sections_file)

    # 章节编号 -> 文件夹名 (编号 + 标题)
    section_names = {num: f"{num} {title}" for num, title in sections.items()}
    # 章节编号 -> 一级章节编号
    section_to_chapter = {sec: sec[:3] for sec in section_names}
    chapters = {sec[:3] for sec in section_names}

    Path(args.target_root).mkdir(parents=True, exist_ok=True)
    copied_count = 0

    for idx, row in df.iterrows():
        title = row["标题"]
        if pd.isna(title) or not title:
            continue

        src_path = find_pdf_file_by_title(title, args.source_pdf)
        if src_path is None:
            continue

        for col in df.columns:
            if col not in section_names:
                continue
            if pd.isna(row[col]) or row[col] == "":
                continue
            chapter_num = section_to_chapter[col]
            target_dir = (
                Path(args.target_root)
                / f"{chapter_num} {sections.get(chapter_num, chapter_num)}"
                / section_names[col]
            )
            target_dir.mkdir(parents=True, exist_ok=True)
            dest_path = target_dir / os.path.basename(src_path)
            shutil.copy2(src_path, dest_path)
            print(f"已复制: {os.path.basename(src_path)} -> {target_dir}")
            copied_count += 1

    print(f"\n完成, 共复制 {copied_count} 个文件 (同一论文可能复制到多个小节)")
    return 0