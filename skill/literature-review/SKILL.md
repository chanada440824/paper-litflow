---
name: literature-review
description: Runs the paper-litflow literature-review pipeline (screen/analyze → organize/from-list → extract-v2/extract → export) from a natural-language request. Use when the user says "run the literature review", "帮我跑文献综述", "摘抄论文", "按章节归类文献", or wants to convert a PDF folder (or a Zotero library) into a sectioned literature-review Word document.
---

# literature-review — 文献综述自动化流水线驱动

本 skill 驱动 `paper-litflow` 工具（Python CLI）：**筛/归类论文 → 章节化摘抄原文 → 导出 Word**。全程只读用户指定的输入目录，输出到用户指定位置；**不自动执行任何命令之外的动作**。

## 总览：3 个输入 → 1 个输出

| # | 输入 | 是什么 | 必需? |
|---|------|--------|-------|
| ① | **章节目录** | `sections.json`：编号 → 标题（**论文的章节结构**） | ✅ 必需 |
| ② | **文献信息表** | 含**标题 / 作者 / 年份 / 摘要**的表（供 `screen`） | 文献多时必需；少量可省 |
| ③ | **PDF 文件夹** | 有**文字层**的 PDF（建议命名 `作者 - 年份 - 标题.pdf`） | ✅ 必需 |

**产出**：按章节 / 小节 / 文献组织的**摘抄段落**——每条 = **逐字原文 + 出处页码 + 用途 + 置信度**；再 `export` 成 Word。

> `①` 是**用户论文的章节**（决定按哪些小节归类 / 摘抄），**不是文献目录**。`②` 的关键是**要有摘要**；且要与 `③` 的 PDF 对得上（标题 → 文件路径）。

## 命令一览（7 个）

| 命令 | 作用 | 花钱? |
|---|---|---|
| `screen` | 全库元数据筛选（读**标题+摘要**）→ 筛选清单 | 💰 便宜（≈¥0.3/300 条）|
| `analyze` | 批量分析 PDF（读**全文**）→ Excel 归类 | 💰 每篇一次 |
| `organize` | 按 Excel 归类结果**复制** PDF 到章节目录 | 🆓 |
| `from-list` | 从筛选清单**直接**建章节目录（跳过 analyze/organize）| 🆓 |
| `extract-v2` | 章节化摘抄（**推荐**：页码 + 逐字校验 + 断点）| 💰 每篇 1~2 次 |
| `extract` | 章节化摘抄（旧版，更便宜）| 💰 每篇 1 次 |
| `export` | 摘抄 Markdown → 宋体排版 Word | 🆓 |

## 摘抄方式：二选一

- **默认用 `extract-v2`（推荐）**：文本按页注入【P页码】，模型必须回报出处页；本地**逐字校验 + 反证校验**淘汰转述 / 幻觉；`state.json` 断点续跑。**适合学位论文、要求严、要溯源**。
- **`extract`（旧版）**：只出「原文 + 用途」，无页码 / 逐字校验，**少一次反证调用 → 更便宜、更快**。**适合内容简单的期刊短文**。

> 规则：**默认 `extract-v2`**；只有当用户**明确想省钱**、且文献是**简单期刊短文**时，才改用 `extract`。拿不准就用 v2。

## 摘抄 prompt（内置在 CLI；不用 CLI 时可直接照用）

> 下面两段是 CLI **内置、发给模型**的提示词（见 `paper_litflow/extract_v2.py` / `extract.py`）。
> **当你无法或不想跑 CLI（例如只有订阅额度、没有 API key）时**，可直接照此 prompt，**让 AI 自己读 PDF 完成摘抄**——格式与 CLI 输出一致。

### extract-v2（推荐）

```
你是专业的学术研究助手，正在协助撰写硕士论文《{论文主题}》，整理「文献综述」写作素材。

当前小节：{小节编号} {小节标题}
文献标题：{文献标题}

任务：从下方文献内容（带【P页码】标记）中，只摘取能支撑**当前小节**论述的**逐字原文**。

严格约束：
1. quote 必须与原文**逐字一致**（包括标点、全角半角、专有名词写法），像复印一样照抄；禁止改写、概括、缩写、拼接不相邻句子、增删任何字符；不要加省略号或引号。每条不超过 200 字。
2. page 必须是该段原文所在页的整数页码（对应【P数字】标记）；若引用跨页，填起始页码并在 use_for 开头注明"跨页"。
3. 共 1~{最多条数} 条；与当前小节无关则返回空数组。
4. use_for：一句话说明该原文可支撑小节中的哪个具体论点（≤40字）。
5. 只返回严格 JSON：{"excerpts":[{"quote":"...","page":1,"use_for":"..."}]}，无其他文字。

文献内容：
{带【P页码】标记的正文}
```

> 用法要点：先把 PDF 正文**按页加【P页码】标记**再注入 `{带页码的正文}`；拿到 JSON 后**逐条与原文比对**，转述 / 查不到的**丢弃**。

### extract（旧版，简版）

```
你是一位专业的学术研究助手，正在协助撰写硕士论文《{论文主题}》，负责整理文献综述。

当前正在分析文献，请仅摘取与该文献相关的原文段落。

重要约束：
- 只为本篇论文提取与 **当前小节**（{小节编号} {小节标题}）相关的原文句子。
- 每条摘抄的用途只能标注为「{小节编号} {小节标题}」中的具体用途。
- 与当前小节无关则不提取。
- 每篇最多 {最多条数} 条，每条 ≤200 字。
- 格式：每条 = `> 原文` + 空行 + `**用途**：…`，条目间用 `---` 分隔。

直接输出摘抄，不要解释和多余内容。
```

## 安装 / 获取项目（首次使用必看）

> 本 skill 只是"说明书"，真正干活的是 `paper-litflow` 项目（Python CLI）。别人要用，**必须先把项目和依赖装好**，光有 SKILL.md 跑不起来。

**第 1 步 · 获取项目（含本 skill）**
```bash
git clone https://github.com/chanada440824/paper-litflow
cd paper-litflow
```

**第 2 步 · 安装 Python 依赖**（建议 Python 3.9+）
```bash
pip install -r requirements.txt
```

**第 3 步 · 配置 API Key**：在项目根目录新建 `.env`，写入：
```
DEEPSEEK_API_KEY=你的key
```
（未配置时所有命令会报错提示，如实转达即可）

**第 4 步 · 把本 skill 装进 AI agent**
- 把 `skill/literature-review/` 整个文件夹，放到 agent 的 **skills 目录**中，例如：
  - OpenCode / Claude Code 等：`~/.config/<agent>/skills/`（Claude Code 为 `~/.claude/skills/`）
  - DeepSeek Harness（DSH）：`.agents/skills/`
- 放好后，agent 在你说"帮我跑文献综述"时就能自动加载本 skill。

## 前置条件

1. 已按上面完成安装（项目 + 依赖 + `.env` 里的 `DEEPSEEK_API_KEY`）
2. 目录结构约定（原样遵循，不自行发挥）：
   - 输入 PDF 文件夹：任意，文件名建议 `作者 - 年份 - 标题.pdf`
   - 章节配置 JSON：`sections.json` 形式，键=编号，值=标题（参考 `examples/sections.example.json`）
   - （走 `screen` + `from-list` 时）元数据 JSON（标题/作者/年份/摘要）+ `pdf_index.json`（`[{"标题":..., "path":...}]`）

## 筛选标准（两层四维制，2026-08-24 起）

**标准文件：`examples/screening_criteria.json`**（维度定义、权重、期刊白名单、经典名单都在里面，改动只动这个文件）。

第一层·元数据初筛（标题+摘要，成本约 ¥0.3/300 条）：

| 维度 | 权重 | 判定层 |
|---|---|---|
| D1 主题相关 | 40% | LLM 语义判断 |
| D2 研究对象匹配 | 25% | LLM（核心场景>相邻场景>泛化相关>无关） |
| D3 文献等级 | 25% | 规则比对核心期刊白名单；**学位论文走单独通道不压分** |
| D4 时效或经典 | 10% | 规则（近5年 或 奠基经典名单） |

综合分100：A≥80 高置信优先精读 / B 65~79 可用 / C 45~64 备选 / D<45 淘汰。
无摘要的条目标「待定」，不自动排序，留给人工判。

第二层·全文摘抄（高置信度环节，`extract-v2` 已内置）：
- 每条摘抄强制带 **PDF 页码 + 逐字原文**，禁止转述
- 关键词预检命中的 PDF 才送 LLM（省钱+防幻觉）
- 摘抄后做一次反证校验：「原文是否支持所标注用途」，不支持降级低置信
- 产出素材每条标 `[高/中/低]` 置信度标签

已知注意点：D2 会压低纯理论著作——人工复核时理论综述小节的经典文献不要因 D2 低而漏掉。

## 常见坑（实战沉淀）

1. **模型爱转述**：LLM 给的"引文"常是改写而非原文——`extract-v2` 已内置逐字约束 + 本地校验；看到「零有效摘抄」属正常防护
2. **理论类文献被 D2 误压**：纯理论著作研究对象得分低是设计使然，复核时人工兜底
3. **无摘要的条目**：元数据阶段无法可靠判断，标「待定」交人工，不要硬评
4. **扫描版 PDF**：无文本层会被自动跳过并记入重试清单，需 OCR 后重跑
5. **长文 / 学位论文**：`--max-chars`（`extract-v2` 默认 9000 字符）会**截断长文**——学位论文几十上百页时只读到开头几页，需**调大 `--max-chars`** 或**只送相关章节**
6. **增量与重试**：`analyze --incremental` 只算新文件；`extract-v2` 的零摘抄条目不锁定状态、重跑即自动重试，失败明细见 `重试清单.csv`
7. **成本参考**：元数据初筛约 ¥0.3/300 条；全文摘抄约 ¥0.05~0.1/篇（`deepseek-chat`，视篇幅/是否反证）

## 流程

### 0. 确认意图与输入

先向用户确认（一次性）：
- 输入：**PDF 文件夹**，或（大库）**文献信息表 / Zotero 元数据**
- **论文章节配置** `sections.json`（没有则用内置示例）
- 论文主题（可选，注入 prompt 提高质量）
- 输出位置（归类目录 / 摘抄目录 / Word 路径）

用户提供不完整时，用默认值继续并说明。

### 路线 A：小量、无清单（直接读 PDF）

```bash
# 1) analyze — PDF 文件夹 → Excel 归类（每篇调一次 API）
python cli.py analyze --pdf-dir "<PDF文件夹>" --output "<归类.xlsx>" \
  --sections-file "<章节配置>" --topic "<论文主题>"

# 2) organize — Excel → 章节目录（复制 PDF）
python cli.py organize --excel "<归类.xlsx>" --source-pdf "<PDF文件夹>" \
  --target-root "<已归类目录>"
```

### 路线 B：大库、有清单（先筛后摘，推荐）

```bash
# 1) screen — 元数据(标题+摘要) → 筛选清单.xlsx（便宜）
python cli.py screen --meta "<zotero_meta.json>" --sections-file "<章节配置>" \
  --topic "<论文主题>" --output "<筛选清单.xlsx>"

# 2) from-list — 筛选清单 → 章节目录（只取 A/B，零 API）
python cli.py from-list --list-file "<筛选清单.xlsx>" --pdf-index "<pdf_index.json>" \
  --target-root "<已归类目录>" --grades "A,B"
```

### 摘抄（二选一）然后导出

```bash
# 摘抄（默认 extract-v2；简单期刊短文可用 extract）
python cli.py extract-v2 --pdf-root "<已归类目录>" --output-root "<摘抄目录>" \
  --chapters "2.1,2.2" --sections-file "<章节配置>" \
  --keywords-file examples/keywords.example.json --topic "<论文主题>"

# 导出 Word
python cli.py export --md-root "<摘抄目录>" --output "<文献综述.docx>"
```

- 摘抄输出结构镜像输入：`<输出根>/<章节>/<小节>/<文件名>.md`
- 每条摘抄 = `> 原文`（+ 出处页码 / 用途 / 置信度），条目间 `---`

### 收尾汇报

向用户汇报：各步骤输出路径、处理的 PDF 数量、被跳过的条目（来自 analyze/extract 的打印）、总耗时估算。如有 API 报错，原样转述（含错误类型和触发条目），不臆测原因。

## 边界

- 绝不编辑用户的 PDF / 论文原文；输出全部为新建文件
- 绝不把 API key 写入任何文件或日志；发现 `.env` 缺失时报错并给指引
- 步骤间有依赖（organize 依赖 analyze 的 Excel；extract\* 依赖"已归类"目录），用户只要求某几步时只跑那几步
- 谨慎地遵守用户给定路径，不要猜测不存在目录的「正确」位置
