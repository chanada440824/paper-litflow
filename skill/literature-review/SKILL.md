---
name: literature-review
description: Runs the paper-litflow literature-review pipeline (analyze → organize → extract → export) from a natural-language request. Use when the user says "run the literature review", "帮我跑文献综述", "摘抄论文", "按章节归类文献", or wants to convert a PDF folder into a sectioned literature-review Word document.
---

# literature-review — 文献综述自动化流水线驱动

本 skill 驱动 `paper-litflow` 工具（Python CLI）：批量分析论文 PDF → 按论文章节归类 → 章节化摘抄 → 导出 Word。全程只读用户指定的输入目录，输出到用户指定位置；**不自动执行任何命令之外的动作**。

## 前置条件

1. 项目已克隆并安装依赖：`pip install -r requirements.txt`
2. `.env` 已配置 `DEEPSEEK_API_KEY`（未配置时所有命令会报错提示，如实转达即可）
3. 目录结构约定（原样遵循，不自行发挥）：
   - 输入 PDF 文件夹：任意，文件名建议 `作者 - 年份 - 标题.pdf`
   - 章节配置 JSON：`sections.json` 形式，键=编号，值=标题（参考 `examples/sections.example.json`）

## 筛选标准（两层四维制，2026-08-24 起）

**标准文件：`examples/screening_criteria.json`**（维度定义、权重、期刊白名单、经典名单都在里面，改动只动这个文件）。

第一层·元数据初筛（标题+摘要，成本约 ¥0.2/300条）：

| 维度 | 权重 | 判定层 |
|---|---|---|
| D1 主题相关 | 40% | LLM 语义判断 |
| D2 研究对象匹配 | 25% | LLM（核心场景>相邻场景>泛化相关>无关） |
| D3 文献等级 | 25% | 规则比对核心期刊白名单；学位论文走单独通道不压分 |
| D4 时效或经典 | 10% | 规则（近5年 或 奠基经典名单） |

综合分100：A≥80 高置信优先精读 / B 65~79 可用 / C 45~64 备选 / D<45 淘汰。
无摘要的条目标「待定」，不自动排序，留给人工判。

第二层·全文摘抄（高置信度环节）：
- 每条摘抄强制带 **PDF 页码 + 逐字原文**，禁止转述
- PyMuPDF 关键词预检命中的 PDF 才送 LLM（省钱+防幻觉）
- 摘抄后做一次反证校验：「原文是否支持所标注用途」，不支持降级低置信
- 产出素材每条标 `[高/中/低]` 置信度标签

已知注意点：D2 会压低纯理论著作（如某领域奠基理论著作对理论综述小节是必引文献但对象得 0 分）——人工复核时理论综述小节的经典文献不要因 D2 低而漏掉。

## 常见坑（实战沉淀）

1. **模型爱转述**：LLM 给的"引文"常是改写而非原文——必须逐字约束 + 本地校验，extract-v2 已内置；看到「零有效摘抄」属正常防护
2. **理论类文献被 D2 误压**：纯理论著作研究对象得分低是设计使然，复核时人工兜底
3. **无摘要的条目**：元数据阶段无法可靠判断，标「待定」交人工，不要硬评
4. **扫描版 PDF**：无文本层会被自动跳过并记入重试清单，需 OCR 后重跑
5. **增量与重试**：`analyze --incremental` 只算新文件；extract-v2 的零摘抄条目不锁定状态、重跑即自动重试，失败明细见 `重试清单.csv`
6. **成本参考**：元数据初筛约 ¥0.2/300 条；全文摘抄约 ¥0.02/篇（deepseek-chat）

## 流程

### 0. 确认意图与输入

先向用户确认（一次性）：
- 输入 PDF 文件夹路径
- 论文章节配置（没有则用内置示例）
- 论文主题（可选，注入 prompt 提高质量）
- 输出位置（Excel / 归类目录 / 摘抄目录 / Word 路径）

用户提供不完整时，用默认值继续并说明。

### 1. analyze — 批量分析生成 Excel 归类

```bash
python cli.py analyze \
  --pdf-dir "<输入PDF文件夹>" \
  --output "<输出Excel路径>.xlsx" \
  --sections-file "<章节配置>" \
  --topic "<论文主题，可省略>"
```

- 每篇 PDF 调用一次 DeepSeek，返回严格 JSON（摘要/关键词/各小节内容）
- 有内置 JSON 容错和逐篇 1s 限速；失败条目会打印 **跳过**，不要当成错误

### 2. organize — 按小节归类复制 PDF

```bash
python cli.py organize \
  --excel "<上一步输出的Excel>" \
  --source-pdf "<原始PDF文件夹>" \
  --target-root "<输出归类根目录>"
```

- 标题匹配是模糊匹配（去符号/空格/小写）
- 多个匹配/无匹配会打印 **警告** 并跳过该行，属于预期行为

### 3. extract — 章节化摘抄为 Markdown

```bash
python cli.py extract \
  --pdf-root "<归类根目录>" \
  --output-root "<摘抄输出目录>" \
  --chapters "2.1,2.2,2.3" \
  --sections-file "<章节配置>" \
  --topic "<论文主题，可省略>"
```

- 输出结构镜像输入结构：`<输出根>/<章节>/<小节>/<文件名>.md`
- 每条摘抄 = `> 原文` + `**用途**：用于 xx 小节的具体引用`，条目间 `---`

### 4. export — 导出 Word

```bash
python cli.py export \
  --md-root "<摘抄目录>" \
  --output "<输出Word路径>.docx"
```

- 宋体全文、三级标题（章节/小节/文献条目）、原文斜体缩进、用途加粗
- 文献条目编号自动给「文献一、文献二…」前缀

### 5. 收尾汇报

向用户汇报：各步骤输出路径、处理的 PDF 数量、被跳过的条目（来自 analyze/extract 的打印）、总耗时估算。如有 API 报错，原样转述（含错误类型和触发条目），不臆测原因。

## 边界

- 绝不编辑用户的 PDF/论文原文；输出全部为新建文件
- 绝不把 API key 写入任何文件或日志；发现 `.env` 缺失时报错并给指引
- 步骤间有依赖（organize 依赖 analyze 的 Excel），用户只要求某几步时只跑那几步
- 谨慎地遵守用户给定路径，不要猜测不存在目录的「正确」位置