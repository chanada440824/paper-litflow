"""paper-litflow: 文献综述自动化流水线 (CLI entry point)

Usage:
    python cli.py analyze    --pdf-dir <dir> --output <xlsx> [--sections-file sections.json] [--topic "论文主题"]
    python cli.py organize   --excel <xlsx> --source-pdf <dir> --target-root <dir>
    python cli.py extract    --pdf-root <dir> --output-root <dir> [--chapters "2.1,2.2"] [--sections-file sections.json]
    python cli.py extract-v2 --pdf-root <dir> --output-root <dir> [--chapters "1.3.1,1.3.2"] [--keywords-file kw.json]
                             (页码出处 + 关键词预检 + 逐字校验 + 置信度标签 + 断点续跑)
    python cli.py from-list  --list-file <xlsx|csv> --pdf-index <json> --target-root <dir>
                             [--grades "A,B"] [--links-json links.json] [--list-out 清单.md]
                             (从筛选清单直接建章节目录, 免去 analyze/organize; 可内嵌 Zotero 链接)
    python cli.py export     --md-root <dir> --output <docx>
"""

import argparse
import sys

from paper_litflow import analyze as analyze_cmd
from paper_litflow import organize as organize_cmd
from paper_litflow import extract as extract_cmd
from paper_litflow import extract_v2 as extract_v2_cmd
from paper_litflow import from_list as from_list_cmd
from paper_litflow import export_docx as export_cmd
from paper_litflow import screen as screen_cmd


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
    p_analyze.add_argument("--recursive", action="store_true", help="递归遍历子目录收集 PDF")
    p_analyze.add_argument("--incremental", action="store_true", help="增量模式: 复用 <output>.state.json 中已分析结果, 只处理新增/变化文件")
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

    # ---- extract-v2 ----
    p_ev2 = sub.add_parser("extract-v2", help="摘抄 v2: 页码出处 + 关键词预检 + 逐字校验 + 置信度标签")
    p_ev2.add_argument("--pdf-root", required=True, help="已归类的 PDF 根目录 (章节/小节结构)")
    p_ev2.add_argument("--output-root", required=True, help="Markdown 输出根目录")
    p_ev2.add_argument("--chapters", default="2.1,2.2", help="处理的章节前缀, 逗号分隔")
    p_ev2.add_argument("--sections-file", default=None, help="章节配置 JSON (默认内置示例)")
    p_ev2.add_argument("--keywords-file", default=None, help="小节关键词 JSON {编号: 正则}, 提供则启用预检")
    p_ev2.add_argument("--topic", default="", help="论文主题 (注入 prompt)")
    p_ev2.add_argument("--temperature", type=float, default=0.1)
    p_ev2.add_argument("--max-chars", type=int, default=9000, help="每篇 PDF 注入的最大字符数(含页码标记)")
    p_ev2.add_argument("--max-excerpts", type=int, default=5)
    p_ev2.add_argument("--state-file", default=None, help="断点续跑状态文件 (默认 <output-root>/.extract_v2_state.json)")
    p_ev2.add_argument("--env-file", default=None)
    p_ev2.set_defaults(func=extract_v2_cmd.run)

    # ---- from-list ----
    p_fl = sub.add_parser("from-list", help="从筛选清单 (xlsx/csv) 直接建章节目录 + 生成带链接清单")
    p_fl.add_argument("--list-file", required=True, help="筛选清单 xlsx/csv (需含标题/相关小节/等级列)")
    p_fl.add_argument("--pdf-index", required=True, help="标题->PDF路径 索引 JSON: [{\"标题\":..., \"path\":...}]")
    p_fl.add_argument("--target-root", required=True, help="章节目录输出根路径")
    p_fl.add_argument("--grades", default="A,B", help="保留的等级, 逗号分隔 (默认 A,B; 传空字符串=全部)")
    p_fl.add_argument("--title-col", default="标题")
    p_fl.add_argument("--sections-col", default="相关小节")
    p_fl.add_argument("--grade-col", default="等级")
    p_fl.add_argument("--links-json", default=None, help="可选: 标题->markdown链接串 JSON, 内嵌进清单")
    p_fl.add_argument("--list-out", default=None, help="清单 Markdown 输出路径 (默认 target-root/文献清单.md)")
    p_fl.add_argument("--skip-copy", action="store_true", help="不复制 PDF, 只生成清单 (链接制交付)")
    p_fl.set_defaults(func=from_list_cmd.run)

    # ---- screen ----
    p_screen = sub.add_parser("screen", help="全库元数据筛选: 标题+摘要批量分配小节与 A/B/C 等级, 输出 from-list 清单")
    p_screen.add_argument("--meta", required=True, help="Zotero 元数据 JSON (含 标题/年份/作者/摘要)")
    p_screen.add_argument("--sections-file", required=True, help="小节配置 JSON {编号: 标题}")
    p_screen.add_argument("--topic", default="", help="论文主题 (注入 prompt)")
    p_screen.add_argument("--output", required=True, help="输出 xlsx (标题/相关小节/等级)")
    p_screen.add_argument("--batch", type=int, default=5, help="每批文献条数 (默认 5)")
    p_screen.add_argument("--model", default="deepseek-chat")
    p_screen.add_argument("--env-file", default=None)
    p_screen.set_defaults(func=screen_cmd.run)

    # ---- export ----
    p_export = sub.add_parser("export", help="将摘抄 Markdown 目录导出为 Word 文档")
    p_export.add_argument("--md-root", required=True, help="Markdown 根目录 (extract 的输出)")
    p_export.add_argument("--output", required=True, help="输出 Word 文档路径")
    p_export.add_argument("--sections-file", default=None, help="可选: 章节编号->标题 JSON {编号: 标题}, 美化 Word 层级标题")
    p_export.set_defaults(func=export_cmd.run)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
