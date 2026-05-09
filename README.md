# AI TTRPG Simulator — AI 驱动的单人跑团模拟器

基于 LangGraph 多智能体架构的全栈跑团应用，支持 Pathfinder 2e、Daggerheart 和 SWADE/七物语。

## 架构概览

```
frontend/          → Next.js + React + Tailwind CSS (三模式 UI)
backend/           → Python FastAPI + LangGraph (多智能体编排 + 可插拔游戏系统)
docs/              → 技术文档
scripts/           → FVTT 数据抽取/处理脚本 (构建时使用)
```

### 支持的规则系统

| 系统 | 特性 | 车卡器 |
|------|------|--------|
| Pathfinder 2e | d20 四档成功度、完整规则库 | 12步向导 |
| Daggerheart | 二元骰 Hope/Fear 经济 | 多步向导 + 升级 |
| SWADE / 七物语 | 爆骰 + 双属性检定 | 属性/专长向导 |

### 多智能体角色

| 角色 | 职责 |
|------|------|
| 讲述者 (Narrator) | 引导剧情、描绘环境、扮演 NPC、展示交互控件 |
| 裁决者 (Referee) | 规则判定、投骰子、战斗管理、完全独立于叙事 |
| AI 队友 (Teammate) | 模拟其他玩家角色，独立人格与决策 |
| 书记员 (Notetaker) | 维护世界状态摘要与长期记忆 |
| 筹备 AI (Prep) | 团外资料整理、Skill/工具创建、角色引导 |
| 创作 AI (Creator) | 剧本/模组/NPC 创作 |

### 数据层

| 存储 | 用途 | 查询方式 |
|------|------|---------|
| SQLite (规则库) | PF2e 规则 (专长/法术/状态/装备/怪物) | 名称匹配 / FTS5 全文搜索 |
| SQLite (车卡索引) | PF2e 车卡数据 (含中文翻译) | 精确查询 |
| SQLite (知识库) | 上传的模组/剧本/参考资料 | 全文搜索 / 按章节浏览 |
| JSON (合集包) | DH / SWADE 默认数据 + 自定义扩展 | 内存加载 |
| JSON (角色卡) | 各系统角色 (FVTT 兼容格式) | ID 查找 |
| JSON (存档) | 完整游戏状态 + 聊天历史 + 交互控件 | 文件列表 |
| InMemoryStore | 结构化长期记忆 | 分类查询 |

### 工具集

| 工具 | 说明 |
|------|------|
| Dice Roller | 真实随机投骰 (PF2e d20 / DH 二元骰 / SWADE 爆骰) |
| Interactive Controls | 选项卡、骰子按钮、输入框、代币变动 |
| Rulebook Search | 三层递进：精确名称 → 全文检索 → 语义兜底 |
| Read Material | AI 按需浏览/搜索已上传的模组和剧本资料 |
| Encounter Manager | 战斗先攻、回合、HP 追踪 |
| Character Sheet | 角色属性读写，支持 FVTT 原生格式 |
| Character Builder | 各系统独立的 AI 车卡工具 |
| Skill / Tool Manager | AI 可自主创建/管理可复用的技能和工具 |
| Party Manager | 队伍管理、跨智能体协作 |

## 界面模式

### 团外准备 (Prep Mode)

10 个子面板：团管理、筹备AI、创作AI、资料库、角色卡、Skills、工具、存档、工作区、备份

### 团内游戏 (Game Mode)

多智能体协作的跑团聊天界面，支持交互控件（选项、骰子按钮、输入框等）。

### 调试面板 (Debug Dashboard)

独立端口 3001，实时监控事件日志、会话状态、记忆数据。

## 快速开始 (Windows)

| 脚本 | 用途 |
|------|------|
| `install.bat` | 首次安装：创建 Python 虚拟环境 + 安装全部依赖 |
| `ingest_rules.bat` | (可选) 导入 PF2e 规则到结构化数据库 |
| `start.bat` | 一键启动前后端 + 调试面板 |
| `stop.bat` | 一键停止所有服务 |

### 首次使用

1. 双击 **`install.bat`** — 自动创建虚拟环境并安装 Python 和 Node.js 依赖
2. (可选) 双击 **`ingest_rules.bat`** — 按提示输入 PF2e 数据路径，导入规则到 SQLite
3. 双击 **`start.bat`** — 启动后端 (8000)、前端 (3000)、调试面板 (3001)
4. 在设置页配置 API Key、模型名和 Base URL
5. 在设置页选择规则系统 (PF2e / Daggerheart / SWADE)
6. 在「团外准备」上传模组资料和角色卡
7. 切换到「团内游戏」，开始冒险

### 外部数据导入

PF2e 的完整规则库需要从外部 FVTT 数据导入。Daggerheart 和 SWADE 的默认数据已内置。

导入脚本通过 **CLI 参数或环境变量** 指定外部数据路径：

```bash
# PF2e 规则导入
cd backend
python -m app.systems.pf2e.ingest.ingest_charbuilder /path/to/pf2e-system/packs/pf2e
python -m app.systems.pf2e.ingest.ingest_rules /path/to/compendium/dir
python -m app.systems.pf2e.ingest.translations /path/to/translations/dir

# 或使用环境变量
set FVTT_PF2E_PACKS=/path/to/pf2e-system/packs/pf2e
set FVTT_PF2E_COMPENDIUM=/path/to/compendium/dir
set FVTT_PF2E_TRANSLATIONS=/path/to/translations/dir

# FVTT LevelDB 抽取 (任意系统)
node scripts/extract_fvtt_packs.mjs /path/to/fvtt-system output_dir
```

### 手动启动 (跨平台)

```bash
# 后端
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端 (另开终端)
cd frontend
npm install
npm run dev
```

### 配置说明

1. 打开 http://localhost:3000 的设置页
2. 输入你的 API Key、模型名称和 Base URL
3. 支持 OpenAI、DeepSeek、Anthropic (代理)、Ollama (本地) 等任何兼容 OpenAI 格式的 API
4. 在「规则系统」下拉框中选择要使用的 TTRPG 系统

## 支持的输入格式

| 格式 | 用途 | 处理方式 |
|------|------|---------|
| FVTT Compendium JSON | 规则数据 (entries{}) | 结构化解析 → SQLite / JSON 合集 |
| FVTT JournalEntry JSON | 模组剧本 (pages[]) | HTML 剥离 → SQLite 知识库 |
| FVTT Actor JSON | 角色卡 | 完整解析 → 角色系统 |
| FVTT Item JSON | 合集包条目 | 导入到对应系统合集包 |
| Markdown / TXT | 模组文档 / 参考资料 | 分块 → SQLite 知识库 |
| PDF | 模组文档 | 文本提取 → 分块 → 知识库 |

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Next.js 16, React 19, Tailwind CSS v4, Lucide Icons |
| 后端 | FastAPI, LangGraph, LangChain |
| 数据库 | SQLite (规则 + 知识库 + 车卡索引) + ChromaDB (语义兜底) |
| 骰子引擎 | d20 (Python) |
| LLM | 任意兼容 OpenAI API 格式的模型 |
| 通信 | SSE (Server-Sent Events) |

## 详细技术文档

参见 [docs/TECHNICAL.md](docs/TECHNICAL.md)。
