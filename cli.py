"""paper-litflow: 文献综述自动化流水线 (CLI entry point)

Usage:
    python cli.py analyze  --pdf-dir <dir> --output <xlsx> [--sections-file sections.json] [--topic "论文主题"] [--model deepseek-chat]
    python cli.py organize --excel <xlsx> --source-pdf <dir> --target-root <dir> [--sections-file sections.json]
    python cli.py extract  --pdf-root <dir> --output-root <dir> [--chapters "2.1,2.2,2.3"] [--sections-file sections.json] [--topic "论文主题"]
    python cli.py export   --md-root <dir> --output <docx>
"""

import argparse
import sys

from paper_litflow import analyze as analyze_cmd
from paper_litflow import organize as organize_cmd
from paper_litflow import extract as extract_cmd
from paper_litflow import export_docx as export_cmd


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="paper-litflow",
        description="文献综述自动化流水线: 分析 → 归类 → 摘抄 → 导出 Word",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- analyze ----
    p_analyze = sub.add_parser("analyze", help="批量分析 PDF, 按章节归类生成 Excel")
    p_analyze.add_argument("--pdf-dir", required=True, help="PDF 文件夹")
    p_analyze.add_argument("--output", required=True, help="输出 Excel 路径")
    p_analyze.add_argument("--sections-file", default=None, help="章节配置 JSON (默认内置示例)")
    p_analyze.add_argument("--topic", default="", help="论文主题 (注入 prompt, 可为空)")
    p_analyze.add_argument("--model", default="deepseek-chat", help="模型名 (默认 deepseek-chat)")
    p_analyze.add_argument("--temperature", type=float, default=0.3)
    p_analyze.add_argument("--max-chars", type=int, default=8000, help="每篇 PDF 提取的最大字符数")
    p_analyze.add_argument("--env-file", default=None, help=".env 文件路径 (默认自动查找)")
    p_analyze.set_defaults(func=analyze_cmd.run)

    # ---- organize ----
    p_organize = sub.add_parser("organize", help="按 Excel 中的小节归类复制 PDF 到章节目录")
    p_organize.add_argument("--excel", required=True, help="analyze 输出的 Excel")
    p_organize.add_argument("--source-pdf", required=True, help="原始 PDF 文件夹")
    p_organize.add_argument("--target-root", required=True, help="目标根目录 (章节/小节 结构)")
    p_organize.add_argument("--sections-file", default=None, help="章节配置 JSON (默认内置示例)")
    p_organize.set_defaults(func=organize_cmd.run)

    # ---- extract ----
    p_extract = sub.add_parser("extract", help="按章节目录逐篇摘抄为 Markdown")
    p_extract.add_argument("--pdf-root", required=True, help="已归类的 PDF 根目录 (organize 的输出)")
    p_extract.add_argument("--output-root", required=True, help="Markdown 输出根目录")
    p_extract.add_argument("--chapters", default="2.1,2.2,2.3", help="处理的章节前缀, 逗号分隔")
    p_extract.add_argument("--sections-file", default=None, help="章节配置 JSON (默认内置示例)")
    p_extract.add_argument("--topic", default="", help="论文主题 (注入 prompt, 可为空)")
    p_extract.add_argument("--model", default="deepseek-chat", help="模型名 (默认 deepseek-chat)")
    p_extract.add_argument("--temperature", type=float, default=0.3)
    p_extract.add_argument("--max-chars", type=int, default=8000, help="每篇 PDF 提取的最大字符数")
    p_extract.add_argument("--max-excerpts", type=int, default=5, help="每篇论文最多摘抄条数")
    p_extract.add_argument("--env-file", default=None, help=".env 文件路径 (默认自动查找)")
    p_extract.set_defaults(func=extract_cmd.run)

    # ---- export ----
    p_export = sub.add_parser("export", help="将摘抄 Markdown 目录导出为 Word 文档")
    p_export.add_argument("--md-root", required=True, help="Markdown 根目录 (extract 的输出)")
    p_export.add_argument("--output", required=True, help="输出 Word 文档路径")
    p_export.set_defaults(func=export_cmd.run)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
