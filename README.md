# paper-litflow — 文献综述自动化流水线

![tests](https://github.com/chanada440824/paper-litflow/actions/workflows/test.yml/badge.svg)

把「读 PDF → 按论文章节归类 → 摘抄原文 → 排版成 Word」这条文献综述流水线做成一个命令行工具。

> 作者用它把每篇文献的处理时间从约 20 分钟缩短到 2 分钟以内（配合 DeepSeek API）。

## 安装

```bash
# 1. 克隆后安装依赖
pip install -r requirements.txt

# 2. 配置 API key（不要提交到仓库）
cp .env.example .env   # 然后填入你的 DEEPSEEK_API_KEY
# 密钥获取: https://platform.deepseek.com/api_keys
```

## 快速开始：3 个输入 → 1 个输出

一句话：**给 3 样东西，出 1 样东西。**

| # | 输入 | 是什么 | 必需? |
|---|------|--------|-------|
| ① | **章节目录** | `sections.json`：编号 → 标题（**论文的章节结构**） | ✅ 必需 |
| ② | **文献信息表** | 含**标题 / 作者 / 年份 / 摘要**的表（供 `screen` 筛） | 文献多时必需；少量可省 |
| ③ | **PDF 文件夹** | 有**文字层**的 PDF（建议命名 `作者 - 年份 - 标题.pdf`） | ✅ 必需 |

**产出**：按章节 / 小节 / 文献组织的**摘抄段落**——每条 = **逐字原文 + 出处页码 + 用途 + 置信度**；再 `export` 成 Word。

> `①` 是**你论文的章节**（决定"按哪些小节归类/摘抄"），不是文献目录。`②` 的关键是**要有摘要**——有摘要才能便宜地筛；且要与 `③` 的 PDF 对得上（标题 → 文件路径）。

### 全程总流程图

> 💰 = 调 API（花钱） · 🆓 = 零成本

```
                    ┌─────────────  准 备 输 入  ─────────────┐
                    │                                        │
   ① 章节目录              ② 文献信息表             ③ PDF 文件夹
   sections.json          (标题/作者/年份/摘要)       (有"文字层"的 PDF)
   (论文章节编号→标题)      zotero_meta.json           建议命名: 作者-年份-标题.pdf
        │                  pdf_index.json                │
        │                     │                          │
        └────────┬────────────┴──────────────┬───────────┘
                 │                           │
      ┌──────────▼───────────┐    ┌──────────▼──────────────┐
      │   路线 A：无清单       │    │   路线 B：有清单（大库必用） │
      │                      │    │                         │
      │  analyze             │    │  screen                 │
      │  AI 读全文→判断归类    │    │  AI 只读「标题+摘要」筛选   │
      │  💰 每篇调一次 API     │    │  💰 ≈¥0.3/300 条（极便宜） │
      │        │             │    │        │                │
      │  organize            │    │  筛选清单.xlsx           │
      │  Excel→复制进章节目录  │    │  (标题/相关小节/等级 A,B,C) │
      │  🆓                  │    │        │                │
      │        │             │    │  from-list              │
      │        │             │    │  读清单→直接复制 PDF       │
      │        │             │    │  🆓 零 API（替代 A 的 analyze+organize）│
      └────────┼─────────────┘    └────────┼────────────────┘
               │                           │
               └─────────────┬─────────────┘
                             ▼
              📁 文献/已归类/<小节>/作者-年份-标题.pdf
                             │
                             ▼
                       摘抄 · 二选一
          ┌──────────────────┴──────────────────┐
   extract-v2（推荐）                   extract（旧版）
   • 逐字原文 + 出处页码 → 可溯源         • 只出「原文 + 用途」
   • 本地逐字校验 + 反证校验             • 少一次反证调用，更便宜
   • 断点续跑 / 关键词预检               • 无页码 / 逐字校验
   💰 每篇 1~2 次                       💰 每篇 1 次
   → 学位论文 · 要溯源                  → 简单期刊论文 · 够用
          └──────────────────┬──────────────────┘
                             │
                             ▼
              📄 文献/摘抄/<小节>/xxx.md
              （每条 = > 逐字原文 + 出处页码 + 用途 + [置信度]）
                             │
                             ▼
                        export
                        按章节/小节/文献排版成 Word
                        🆓 零 API
                             │
                             ▼
                 📘 第二章文献综述_正式稿.docx
```

**三点记忆**：
1. 两条路在「文献/已归类」处**汇合**——A 用 `analyze`（AI 读全文判断），B 用 `screen` + `from-list`（读摘要筛 + 免费复制）。
2. 只有 **3 处花钱**：`analyze`、`screen`、`extract-v2`；`organize` / `from-list` / `export` 全是 🆓。
3. **大库走 B**：先便宜筛 → 只对 A/B 摘 → 省 5~10 倍。

### 推荐流程（大库：几十 ~ 上百篇）——"先筛后摘"

```bash
screen  →  from-list  →  extract-v2  →  export
```

`screen` 只读"标题 + 摘要"（约 ¥0.3/300 条）先筛掉不相关的，`from-list` 只把 A/B 级归类，再对它们做全文摘抄——比"每篇直接读全文"**省 5~10 倍**。

## 命令一览

> 共 7 个命令：`analyze` / `screen` / `organize` / `from-list` / `extract-v2`（**推荐**）/ `extract`（旧版）/ `export`。
> 前四个负责"归类"，`extract*` 负责"摘抄"，`export` 负责"出 Word"。

### analyze — 批量分析 PDF，生成 Excel 归类

```bash
python cli.py analyze \
  --pdf-dir "文献/第2章文献" \
  --output "第二章文献综述_归类.xlsx" \
  --sections-file examples/sections.example.json \
  --topic "你的论文主题"
```

- 每篇 PDF 调用一次 DeepSeek，返回严格 JSON（摘要 / 关键词 / 各小节内容）
- 有内置 JSON 容错和逐篇 1s 限速；失败条目会打印 **跳过**，不要当成错误

### screen — 全库元数据筛选（便宜快速，先全库过一遍）

```bash
python cli.py screen \
  --meta zotero_meta.json \
  --sections-file examples/sections.example.json \
  --topic "你的论文主题" \
  --output 筛选清单.xlsx
```

- 输入是元数据 JSON（标题 / 年份 / 作者 / 摘要），约 ¥0.3/300 条
- 输出 `标题 / 相关小节 / 等级 (A/B/C)` 三列，直接喂 `from-list`；不相关条目不进清单

### organize — 按 Excel 归类结果复制 PDF 到章节目录

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

- 标题匹配是模糊匹配（去符号 / 空格 / 小写）
- 多个匹配 / 无匹配会打印 **警告** 并跳过该行，属于预期行为

### from-list — 从筛选清单直接建目录（跳过 analyze/organize）

```bash
python cli.py from-list \
  --list-file "相关文献筛选.xlsx" \
  --pdf-index pdf_index.json \
  --target-root "文献/已归类" \
  --grades "A,B" \
  --links-json zotero_links.json \
  --list-out "文献清单.md"
```

- `--list-file` 需含「标题 / 相关小节 / 等级」三列；`--pdf-index` 为 `[{"标题":..., "path":...}]` 的标题 → PDF 路径映射
- 按 `--grades` 过滤（如 A,B），把 PDF **直接复制**到对应小节目录——**不调 API（零成本）**
- 加 `--skip-copy` 可不复制 PDF、只产出带 Zotero 跳转链接的清单（链接制交付）

### extract-v2 — 章节化摘抄（**推荐**）

```bash
python cli.py extract-v2 \
  --pdf-root "文献/已归类" \
  --output-root "文献/摘抄" \
  --chapters "2.1,2.2" \
  --sections-file examples/sections.example.json \
  --keywords-file examples/keywords.example.json \
  --topic "你的论文主题"
```

相比 v1 的升级：
- 文本按页注入 **【P页码】** 标记（模型必须回报出处页）
- 可选**关键词预检**（未命中小节关键词的 PDF 直接跳过，省 token）
- 返回严格 JSON 后**本地逐字校验**，转述 / 幻觉引文直接淘汰；模糊命中降级为低 / 中置信
- `state.json` **断点续跑**

👉 **适合学位论文、要求严、要溯源**的场景。

### extract — 章节化摘抄（旧版，更便宜）

```bash
python cli.py extract \
  --pdf-root "文献/已归类" \
  --output-root "文献/摘抄" \
  --chapters "2.1,2.2,2.3" \
  --sections-file examples/sections.example.json \
  --topic "你的论文主题"
```

- 每条摘抄 = 原文引用块 + **用途**说明（用于哪个小节的哪句论证），条目间 `---` 分隔
- 比 v2 **少一次反证校验调用**，**更便宜、更快**；无页码 / 逐字校验
- 👉 **适合内容简单的期刊论文（"便宜够用"）**

```markdown
> 近年来，相关领域的研究重心逐渐从单一方法探索转向多方法融合与协同应用。

**用途**：用于 2.1.1 研究背景与问题提出 的具体引用，说明研究演进脉络。
```

### export — 摘抄导出为 Word

```bash
python cli.py export \
  --md-root "文献/摘抄" \
  --output "第二章文献综述_正式稿.docx"
```

- 输出：全宋体、三级标题（章节 / 小节 / 文献条目）、原文斜体缩进、用途说明加粗
- 文献条目编号自动给「文献一、文献二…」前缀

## 章节配置

`--sections-file` 接受 JSON：键为章节编号，值为标题。不传则用内置示例。参考 `examples/sections.example.json`，换论文时改这个文件即可。

```json
{ "2.1": "协作学习空间的理论基础", "2.1.1": "协作学习机制", "2.2": "空间演变" }
```

> `①` 是**你论文的章节**（决定"按哪些小节归类 / 摘抄"），**不是文献目录**。

## 成本与批量技巧

### 成本控制

- `--keywords-file` 关键词预检：未命中小节关键词的 PDF **直接跳过**（最省）
- 别对全库无关文献跑摘抄——**先 `screen` 筛**，只对 A/B 摘
- 调小 `--max-chars`、`--max-excerpts`
- 先小批量试 3~5 篇看成本，再放量
- 断点续跑：`extract-v2` 自带 `state.json`，中断重跑只处理未完成条目

### 长文 / 学位论文

- 每条摘抄**强制逐字原文 + 页码**，转述 / 编造本地淘汰，可回溯核对
- 但 `--max-chars`（`extract-v2` 默认 9000 字符）会**截断长文**：学位论文几十上百页时只读到开头几页 → 需**调大 `--max-chars`** 或**只送相关章节**

## 配套 Skill（给 AI agent 用）

`skill/literature-review/` 是一个 Agentskills 标准的 skill，让 AI 编程助手（OpenCode / Claude Code / Codex 等）能直接驱动本流水线——说一句「帮我跑第二章文献综述」即可。

```bash
# OpenCode（全局或项目级）
cp -r skill/literature-review ~/.config/opencode/skills/
# Claude Code
cp -r skill/literature-review ~/.claude/skills/
```

确认 Skill：在项目里向 AI 提问「提取当前 PDF，做文献综述摘抄」，看它是否加载了 `literature-review`。

## 目录结构

```
paper-litflow/
├── cli.py                        # 入口: analyze / screen / organize / from-list / extract / extract-v2 / export
├── paper_litflow/
│   ├── config.py                 # 章节配置 JSON 加载（BOM 兼容）+ API key 读取（.env）
│   ├── pdf_utils.py              # PDF 文本提取 + 文件名元数据解析（作者-年份-标题）
│   ├── analyze.py                # analyze: 批量分析 → Excel
│   ├── screen.py                 # screen: 元数据筛选 → 清单
│   ├── organize.py               # organize: 按 Excel 归类复制 PDF
│   ├── from_list.py              # from-list: 从清单直接建目录（零 API）
│   ├── extract.py                # extract: 章节化摘抄 v1
│   ├── extract_v2.py             # extract-v2: 页码 + 逐字校验 + 断点
│   ├── verify.py                 # 逐字校验 / 置信度
│   └── export_docx.py            # export: Markdown → 宋体排版 Word
├── examples/                     # sections / keywords / screening_criteria 示例
├── tests/                        # pytest 单元测试（CI 自动运行）
└── skill/literature-review/      # 配套 AI skill（包装本流水线）
```

## 设计说明

- **API key 只在环境变量 / .env 中读取**，源码永不出现密钥
- 文件名约定：`作者 - 年份 - 标题.pdf` 或 `作者 - 标题.pdf`（analyze/extract 自动解析作者、年份）
- 每篇 PDF 默认截取前 8000 字符（`--max-chars` 可调，成本控制）
- 摘抄间 `time.sleep(1)` 限速，避免触发 API 限流
- 输出格式约束：严格 JSON（analyze）、Markdown 引用块（extract）——已内置容错解析

## 测试

```bash
pip install pytest
pytest
```

每次推送到 GitHub 都会由 CI（GitHub Actions, Python 3.10-3.12）自动运行全部测试。

## License

MIT
