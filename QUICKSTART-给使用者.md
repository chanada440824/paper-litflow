# paper-litflow 快速上手（给使用者）

> 一句话：把一个 **PDF 文件夹**，自动 **按论文章节归类 → 摘抄原文 → 导出 Word**。
> 建议配合 AI agent 使用（一句话驱动）。

## 4 步装机

1. **获取项目**（含 skill）：
   ```bash
   git clone https://github.com/chanada440824/paper-litflow
   cd paper-litflow
   ```
2. **装依赖**（Python 3.9+）：
   ```bash
   pip install -r requirements.txt
   ```
3. **配 API key**：项目根目录新建 `.env`，写入：
   ```
   DEEPSEEK_API_KEY=你的key
   ```
   （key 在 https://platform.deepseek.com 申请；要充值，按量计费）
4. **装 skill 进 AI agent**（可选，装了才能"一句话驱动"）：
   - OpenCode：`cp -r skill/literature-review ~/.config/opencode/skills/`
   - Claude Code：`cp -r skill/literature-review ~/.claude/skills/`

## 怎么用

对 AI agent 说一句自然语言即可，例如：

> **"帮我跑第二章文献综述：PDF 在 `<PDF文件夹>`，章节配置用 `<sections.json>`，论文主题是「…」，输出到 `<目录>`。"**

## 需要准备什么（3 样）

1. **论文章节目录** `sections.json`（编号 → 标题）
2. **PDF 文件夹**（有文字层的 PDF，建议命名 `作者 - 年份 - 标题.pdf`）
3. （文献多时）**文献信息表**：含标题 / 作者 / 年份 / **摘要**（供 `screen` 筛）

## 详细说明 → 见 [README](README.md)

命令一览、输入/输出、**先筛后摘**、成本控制、**学位论文 / 长文**处理、常见坑，都在 README 里。
