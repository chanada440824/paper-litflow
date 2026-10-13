# paper-litflow 快速上手(给使用者)

> 把一堆文献 PDF → **自动分析归类 → 按章节摘抄 → 导出 Word**。
> 单篇处理时间从约 20 分钟降到 **2 分钟以内**。含本 skill,可被支持 Agent Skills 标准的 AI 助手直接调用。

---

## 你需要准备(就 3 样)

1. **一个能执行命令的 AI agent** —— 如 Claude Code / OpenCode / DeepSeek Harness / WorkBuddy(纯聊天网页版不行)
2. **一个 DeepSeek API key** —— 去 https://platform.deepseek.com 申请(按量付费,**处理几百篇文献也就几毛钱**)
3. **Python** —— 没装也行,**agent 能帮你装**

---

## ⚡ 一键装好(把下面这段话直接发给你的 AI agent)

> 帮我装好 paper-litflow 文献综述工具:
> 1. `git clone https://github.com/chanada440824/paper-litflow`,并 `cd` 进去
> 2. 装好 Python 依赖:`pip install -r requirements.txt`(Python 没装的话先帮我装 Python 3.9+)
> 3. 在项目根目录创建 `.env`,写入 `DEEPSEEK_API_KEY=...`(key 我待会给你)
> 4. 把 `skill/literature-review/` 这个文件夹放到你的 skills 目录里(如 `.agents/skills/`)
> 5. 装完告诉我:怎么用它跑一次文献综述

**你只需**:装好 agent → 申请好 key → 把上面这段话发给 agent → 它自己把环境全搭好。

---

## 🔧 手动安装(如果你想自己来)

```bash
# 1. 获取项目
git clone https://github.com/chanada440824/paper-litflow
cd paper-litflow

# 2. 装依赖(Python 3.9+)
pip install -r requirements.txt

# 3. 在项目根目录建 .env,写入:
# DEEPSEEK_API_KEY=你的key

# 4. 把 skill 放到你的 agent 的 skills 目录
#    (Claude Code/OpenCode: ~/.config/<agent>/skills/ ; DeepSeek Harness: .agents/skills/)
```

---

## ▶️ 怎么用

对 agent 说一句自然语言,例如:

> **"帮我跑文献综述 /path/to/我的PDF文件夹"**

或者按步骤手动跑(在项目目录里):

```bash
python cli.py analyze  --pdf-dir "<PDF文件夹>" --output "<归类.xlsx>" --sections-file "<章节配置>"
python cli.py organize --excel "<归类.xlsx>" --source-pdf "<PDF文件夹>" --target-root "<归类根目录>"
python cli.py extract  --pdf-root "<归类根目录>" --output-root "<摘抄目录>" --chapters "2.1,2.2" --sections-file "<章节配置>"
python cli.py export   --md-root "<摘抄目录>" --output "<综述.docx>"
```

- 章节配置参考 `examples/sections.example.json`
- 筛选标准在 `examples/screening_criteria.json`(可改)

---

## 💡 核心亮点

- **防幻觉**:每条摘抄强制带 **PDF 页码 + 逐字原文**,禁止转述;导出按 **置信度配色**,一眼看出哪些可信
- **两层筛选**:元数据初筛(便宜)+ 高置信全文摘抄,省钱又准
- **一键驱动**:附 Agent Skills 标准 skill,AI 助手说一句就能跑全流程

## 💰 费用参考

- 元数据初筛:约 **¥0.2 / 300 条**
- 全文摘抄:约 **¥0.02 / 篇**(deepseek-chat)

## ⚠️ 注意

- 只读你的输入目录,**绝不修改你的原始 PDF**,输出都是新建文件
- **不要把自己的 API key 给别人**——让对方自己申请(有成本 + 安全)
- 扫描版 PDF(无文本层)会被跳过,需先 OCR

---

*开源 MIT · https://github.com/chanada440824/paper-litflow*
