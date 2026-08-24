# paper-litflow — 文献综述自动化流水线

![tests](https://github.com/chanada440824/paper-litflow/actions/workflows/test.yml/badge.svg)

把「读 PDF → 按论文章节归类 → 摘抄原文 → 排版成 Word」这条文献综述流水线做成一个命令行工具。

> 作者用它把每篇文献的处理时间从约 20 分钟缩短到 2 分钟以内（配合 DeepSeek API）。

## 流水线

```
┌──────────┐   analyze   ┌──────────┐  organize  ┌─────────────┐  extract  ┌─────────┐  export  ┌────────┐
│ PDF 文件夹 │ ──────────▶ │ Excel 归类 │ ─────────▶ │ 章节目录 PDF  │ ─────────▶ │ 摘抄 Markdown │ ────────▶ │ Word 文档 │
└──────────┘             └──────────┘            └─────────────┘           └─────────┘          └────────┘
```

## 模块结构

```
paper-litflow
├── cli.py                    # 入口: analyze / organize / extract / export 子命令
├── paper_litflow/
│   ├── config.py             # 章节配置 JSON 加载（含 BOM 兼容）+ API key 读取（.env）
│   ├── pdf_utils.py          # PDF 文本提取 + 文件名元数据解析（作者-年份-标题）
│   ├── analyze.py            # analyze: 批量分析 → Excel（含模型 JSON 容错解析）
│   ├── organize.py           # organize: 按章节归类复制 PDF
│   ├── extract.py            # extract: 章节化摘抄 → Markdown（含格式约束 prompt）
│   └── export_docx.py        # export: Markdown → 宋体排版 Word
├── tests/                    # pytest 单元测试（42 个用例, CI 自动运行）
└── examples/
    └── sections.example.json # 章节配置示例
```

## 测试

```bash
pip install pytest
pytest
```

每次推送到 GitHub 都会由 CI（GitHub Actions, Python 3.10-3.12）自动运行全部测试。

| 步骤 | 命令 | 输入 → 输出 |
|------|------|-------------|
| 1. 分析 | `analyze` | 论文 PDF 文件夹 → Excel（摘要、关键词、按小节归类） |
| 2. 归类 | `organize` | Excel + 原 PDF 文件夹 → 章节目录结构（2.1/2.1.1/...） |
| 3. 摘抄 | `extract` | 章节目录 PDF → 每条摘抄带「用途说明」的 Markdown |
| 4. 导出 | `export` | 摘抄 Markdown → 宋体排版的 Word 文献综述 |

## 安装

```bash
# 1. 克隆后安装依赖
pip install -r requirements.txt

# 2. 配置 API key（不要提交到仓库）
cp .env.example .env   # 然后填入你的 DEEPSEEK_API_KEY
# 密钥获取: https://platform.deepseek.com/api_keys
```

## 使用

### 1. analyze — 批量分析论文生成 Excel 归类

```bash
python cli.py analyze \
  --pdf-dir "文献/第2章文献" \
  --output "第二章文献综述_归类.xlsx" \
  --sections-file examples/sections.example.json \
  --topic "你的论文主题"
```

### 2. organize — 按 Excel 归类结果复制 PDF 到章节目录

```bash
python cli.py organize \
  --excel "第二章文献综述_归类.xlsx" \
  --source-pdf "文献/第2章文献" \
  --target-root "文献/已归类"
```

生成结构：

```
文献/已归类/
└── 2.1 绪论与文献综述/
    └── 2.1.1 研究背景与问题提出/
        ├── 作者A - 2020 - 标题.pdf
        └── 作者B - 2021 - 标题.pdf
```

### 3. extract — 按章节逐篇摘抄为 Markdown

```bash
python cli.py extract \
  --pdf-root "文献/已归类" \
  --output-root "文献/摘抄" \
  --chapters "2.1,2.2,2.3" \
  --sections-file examples/sections.example.json \
  --topic "你的论文主题"
```

摘抄格式：每条原文用引用块，紧跟**用途**说明（标注用于哪个小节的哪句论证），条目间 `---` 分隔：

```markdown
> 近年来，相关领域的研究重心逐渐从单一方法探索转向多方法融合与协同应用。

**用途**：用于 2.1.1 研究背景与问题提出 的具体引用，说明研究演进脉络。
```

### 4. export — 摘抄导出为 Word

```bash
python cli.py export \
  --md-root "文献/摘抄" \
  --output "第二章文献综述_正式稿.docx"
```

输出：全宋体、三级标题（章节/小节/文献条目）、原文斜体缩进、用途说明加粗。

## 章节配置

`--sections-file` 接受 JSON：键为章节编号，值为标题。不传则用内置示例。参考 `examples/sections.example.json`，换论文时改这个文件即可。

## 设计说明

- **API key 只在环境变量 / .env 中读取**，源码永不出现密钥
- 文件名约定：`作者 - 年份 - 标题.pdf` 或 `作者 - 标题.pdf`（analyze/extract 自动解析作者、年份）
- 每篇 PDF 默认截取前 8000 字符（`--max-chars` 可调，成本控制）
- 摘抄间 `time.sleep(1)` 限速，避免触发 API 限流
- 输出格式约束：严格 JSON（analyze）、Markdown 引用块（extract）——已内置容错解析

## 目录结构

```
paper-litflow/
├── cli.py                    # 入口
├── paper_litflow/
│   ├── analyze.py            # 步骤 1: PDF → Excel 归类
│   ├── organize.py           # 步骤 2: Excel → 章节目录
│   ├── extract.py            # 步骤 3: 章节化摘抄 → Markdown
│   ├── export_docx.py        # 步骤 4: Markdown → Word
│   ├── pdf_utils.py          # PDF 文本提取 + 文件名元数据解析
│   └── config.py             # 配置加载（.env / 章节 JSON）
├── examples/sections.example.json
└── skill/literature-review/  # 配套 AI skill（包装本流水线）
```

## 配套 Skill

`skill/literature-review/` 是一个 Agentskills 标准的 skill，让 AI 编程助手（OpenCode / Claude Code / Codex 等）能直接驱动本流水线——说一句「帮我跑第二章文献综述」即可。

### extract-v2 —— 带页码与置信度的摘抄（推荐）

```bash
python cli.py extract-v2 \
  --pdf-root "文献/已归类" \
  --output-root "文献/摘抄" \
  --chapters "2.1,2.2" \
  --sections-file examples/sections.example.json \
  --keywords-file examples/keywords.json \
  --topic "你的论文主题"
```

相比 v1 的升级：文本按页注入【P页码】标记（模型必须回报出处页）；可选关键词预检（未命中小节关键词的 PDF 直接跳过，省 token）；返回严格 JSON 后**本地逐字校验**，转述/幻觉引文直接淘汰；模糊命中降级为低/中置信；`state.json` 断点续跑。

### from-list —— 从筛选清单直接建目录（跳过 analyze/organize）

```bash
python cli.py from-list \
  --list-file "相关文献筛选.xlsx" \
  --pdf-index pdf_index.json \
  --target-root "文献/已归类" \
  --grades "A,B" \
  --links-json zotero_links.json \
  --list-out "文献清单.md"
```

`--list-file` 需含「标题 / 相关小节 / 等级」三列；`--pdf-index` 为 `[{"标题":..., "path":...}]` 的标题→PDF 路径映射。加 `--skip-copy` 可不复制 PDF、只产出带 Zotero 跳转链接的清单（链接制交付）。

### 安装 skill

```bash
# OpenCode（全局或项目级）
cp -r skill/literature-review ~/.config/opencode/skills/
# Claude Code
cp -r skill/literature-review ~/.claude/skills/
```

确认 Skill: 在项目里向 AI 提问「提取当前 PDF，做文献综述摘抄」，看它是否加载了 `literature-review`。

## License

MIT