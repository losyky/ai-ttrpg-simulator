# AI TTRPG Simulator — 技术文档

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 16 + React 19 + Tailwind CSS v4)                │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ 三模式界面                                                      │ │
│  │  [团外准备]  团管理 | 筹备AI | 创作AI | 资料库 | 角色卡          │ │
│  │             Skills | 工具 | 存档 | 工作区 | 备份                │ │
│  │  [团内游戏]  聊天界面 + 交互控件 + 侧边栏 + 记忆面板            │ │
│  │  [调试面板]  事件日志 | 会话状态 | 实时数据 (端口 3001)          │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │ 设置页  →  API Key / 模型 / Base URL / 规则系统切换              │ │
│  │ 动态主题  →  PF2e 深绿 | Daggerheart 紫蓝 | 七物语 琥珀        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                          ↕ HTTP / SSE                               │
├─────────────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + LangGraph + LangChain)                          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ 可插拔游戏系统 (GameSystem ABC)                                  │ │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐         │ │
│  │  │  PF2e    │  │  Daggerheart │  │  SWADE / 七物语   │         │ │
│  │  │ 完整规则库│  │ 二元骰+Hope  │  │ 爆骰+双属性检定  │         │ │
│  │  │ 12步车卡器│  │ Fear 经济    │  │ 七元素世界观      │         │ │
│  │  └──────────┘  └──────────────┘  └──────────────────┘         │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │ 多智能体编排 (LangGraph StateGraph)                              │ │
│  │  意图分析 → 裁决者 → 队友 → 讲述者 → 书记员                    │ │
│  │  团外筹备AI | 团外创作AI (独立流式对话)                          │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │ API 路由层 (16+ Router 模块)                                    │ │
│  │  /api/sessions  /api/chat  /api/saves  /api/characters          │ │
│  │  /api/documents /api/rules /api/skills /api/tools               │ │
│  │  /api/dice      /api/memories  /api/workspace  /api/backup      │ │
│  │  /api/compendium  /api/prep-chat  /api/creator-chat             │ │
│  │  /api/debug  /api/{system}/charbuilder  /api/{system}/rules     │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │ 数据层                                                          │ │
│  │  SQLite  ←── 结构化规则库 (PF2e feats/spells/actions/...)       │ │
│  │  SQLite  ←── 通用知识库 (上传文档/JournalEntry/剧本)            │ │
│  │  SQLite  ←── 车卡器索引库 (PF2e ancestry/class/feat/...)       │ │
│  │  ChromaDB ←── 语义向量搜索兜底 (MD/PDF)                         │ │
│  │  JSON    ←── 角色卡 / 存档 / Skills / 工具 / 合集包             │ │
│  │  JSON    ←── 筹备/创作 AI 对话历史                              │ │
│  │  InMemoryStore ←── 结构化长期记忆                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. 多规则系统架构

### 2.1 可插拔游戏系统 (GameSystem)

系统采用抽象基类 + 注册表模式，支持热插拔不同 TTRPG 规则：

```python
# backend/app/systems/base.py
class GameSystem(ABC):
    system_id: str          # "pf2e" | "daggerheart" | "swade"
    display_name: str       # 显示名称
    description: str        # 系统描述

    def get_prompts() -> dict      # 各智能体的系统提示词
    def get_tools() -> dict        # 系统专属工具集
    def get_routers() -> list      # 系统专属 API 路由
    def get_dice_rules()           # 骰子判定规则
    def get_character_class()      # 角色卡模型
```

### 2.2 已实现的规则系统

| 系统 | ID | 骰子机制 | 车卡器 | 默认数据库 | 主题色 |
|------|----|----------|--------|-----------|--------|
| Pathfinder 2e | `pf2e` | d20 四档成功度 | 12步向导 | 完整 (SQLite) | 深绿 |
| Daggerheart | `daggerheart` | 二元骰 (Hope/Fear) | 多步向导 + 升级 | 完整 (JSON 合集包) | 紫蓝 |
| SWADE / 七物语 | `swade` | 爆骰 + 双属性检定 | 属性/专长向导 | 基础 (JSON) | 琥珀 |

### 2.3 系统级资源隔离

所有资源按 `system_id` 隔离：
- **角色卡**：`data/characters/{system_id}/`
- **存档**：存档文件内含 `state.system_id`，列表 API 按系统过滤
- **会话**：`SessionState.system_id` 字段区分
- **合集包**：`/api/compendium/{system_id}/{collection}`
- **车卡器**：每个系统有独立的 charbuilder 路由和数据库
- **提示词**：各系统在 `systems/{id}/prompts.py` 定义专属提示

部分资源支持跨系统共享（需标记 `shared=true`）：Skills、自定义工具。

## 3. 多智能体工作流

### 3.1 团内游戏 — LangGraph StateGraph

```
用户输入
   │
   ▼
┌──────────────┐
│ analyze_intent│  判断需要裁决者 / 队友 / 纯叙事
└──────┬───────┘
       │
  ┌────┼─────────────────────┐
  │    │                     │
  ▼    ▼                     ▼
裁决者  队友              讲述者
  │    │                     │
  └────┘                     │
       │                     │
       ▼                     │
    讲述者  ←────────────────┘
       │
       ▼
    书记员 → 更新世界状态/记忆 → 输出给玩家
```

### 3.2 各智能体职责

| 智能体 | 模块 | 温度 | 工具 |
|--------|------|------|------|
| 意图分析 | `agents/narrator.py::analyze_intent` | 0.0 | 无 |
| 裁决者 | `agents/referee.py::referee_judge` | 0.0 | dice_roller, rulebook 系列, encounter 系列, search_material, request_player_roll, 交互工具 |
| 队友 | `agents/teammate.py::teammates_act` | 0.9 | 无 |
| 讲述者 | `agents/narrator.py::narrate` | 0.8 | present_choices, request_dice_roll, request_player_input, 系统专属交互工具 |
| 书记员 | `agents/notetaker.py::update_notes` | 0.1 | 无 |
| 筹备 AI | `agents/prep_agent.py` | 0.7 | 文档管理, Skill CRUD, 工具 CRUD, 工作区操作, 系统 prep 工具 |
| 创作 AI | `agents/creator_agent.py` | 0.8 | 文档检索, 工作区操作, 发布到资料库, NPC 构建工具 |

### 3.3 LLM 兼容性

通过 `SafeChatOpenAI` 封装（`agents/compat.py`）确保兼容各主流 LLM：

- **推理模型支持**：自动处理 `reasoning_content` 回传（DeepSeek-R1 等）
- **工具调用兜底**：当模型不原生支持 function calling 时，通过文本解析 JSON 块
- **OpenAI 兼容协议**：支持任意 `base_url`，兼容 OpenAI / DeepSeek / Anthropic / 本地模型等
- **流式输出**：SSE 实时推送叙事 token，narrator token queue 机制保证低延迟

### 3.4 交互控件系统

讲述者和裁决者可通过工具调用向玩家展示交互 UI：

| 控件类型 | 工具函数 | 前端组件 | 说明 |
|----------|----------|----------|------|
| 选项卡 | `present_choices` | `ChoiceCard` | 多选一分支选择 |
| 骰子按钮 | `request_dice_roll` | `DiceRollButton` | 玩家点击投骰 |
| 二元骰 | `request_duality_roll` | `DualityDiceButton` | Daggerheart 专属 |
| 输入框 | `request_player_input` | `InputPrompt` | 自由文本输入 |
| 代币变动 | `announce_token_change` | `TokenUpdateCard` | Hope/Fear 经济 |

**状态持久化**：交互结果通过 `resolved` / `resolved_value` / `resolved_dice` 字段保存在消息结构中，确保切换标签页和存读档后控件状态不丢失。

**实时渲染**：交互控件在 SSE 流中即时到达即时挂载，无需等待整条消息完成。使用 `seenInteractiveIds` 去重，避免后端多节点重复发送。

### 3.5 AgentState 结构

```python
class AgentState(TypedDict, total=False):
    session_id: str
    user_message: str
    api_key: str
    model: str
    base_url: str
    game_phase: str           # exploration | combat | social | downtime
    needs_referee: bool
    needs_teammates: bool
    needs_combat: bool
    referee_output: str
    teammate_output: str
    notetaker_output: str
    narrator_response: str
    dice_results: Annotated[list[dict], operator.add]
    interactive_elements: Annotated[list[dict], operator.add]
    pending_dice_request: dict | None
```

### 3.6 记忆层

采用 LangGraph `InMemoryStore` 实现结构化长期记忆：

- **自动抽取**：书记员在每轮对话后自动提取关键信息
- **分类存储**：世界状态、NPC 关系、玩家决策、战斗历史等
- **按需检索**：各智能体根据当前上下文自动查询相关记忆
- **管理 API**：`/api/memories/{session_id}` 支持查看、创建、删除

## 4. 数据架构

### 4.1 结构化规则库 (PF2e)

PF2e FVTT Compendium 数据采用三层递进查询：

1. **SQLite 精确查询** — 名称 LIKE 匹配（中/英文）
2. **SQLite FTS5 全文检索** — 对 name + description 分词搜索
3. **ChromaDB 向量语义搜索** — 仅作为兜底

**`compendium_entries`** — 专长/法术/动作/状态/装备等

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | `{filename}::{key}` |
| key | TEXT | 英文原始 key |
| name_zh | TEXT | 中文名 |
| name_en | TEXT | 英文名 |
| category | TEXT | 自动分类 (feat/spell/action/condition/...) |
| description | TEXT | 纯文本描述 (HTML 已清洗) |
| extra_json | TEXT | 其余字段 JSON |

**`creatures`** — 怪物/NPC

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | `{filename}::{key}` |
| name_zh / name_en | TEXT | 名称 |
| public_notes | TEXT | 怪物描述 |
| items_json / extra_json | TEXT | 嵌套结构 JSON |

### 4.2 车卡器索引库 (PF2e)

独立 SQLite 数据库，含中文翻译：

| 表名 | 内容 |
|------|------|
| `ancestries` | 血统 (HP/速度/体型/增减值) |
| `heritages` | 传承 |
| `backgrounds` | 背景 (技能/学识/增减值) |
| `classes` | 职业 (HP/关键属性/技能数/升级进度) |
| `feats` | 专长 (含职业/血统/通用/技能分类) |
| `spells` | 法术 |
| `equipment` | 装备 |
| `skills` | 技能列表 |

### 4.3 合集包系统 (Daggerheart / SWADE)

轻量级 JSON 合集包，支持默认数据 + 自定义扩展：

```
backend/app/systems/{system_id}/default_packs/processed/
├── _index.json              # 集合索引
├── classes.json             # 职业
├── ancestries.json          # 血统
├── weapons.json             # 武器
├── domain_cards.json        # 领域卡 (DH)
├── edges.json               # 专长 (SWADE)
└── ...
```

- 默认数据内置在代码库中
- 自定义数据存储在 `data/compendium/{system_id}/`
- 支持从 FVTT 导出 JSON 导入（单条 + 批量）
- 所有条目含 `name_cn` 中文翻译字段

### 4.4 通用知识库

所有上传的非规则类文档（模组、剧本等）存入知识库：

| 表 | 说明 |
|----|------|
| `documents` | 文档元数据 (doc_id, filename, doc_type, chunk_count) |
| `doc_chunks` | 内容片段 (section, content, chunk_index) |
| `chunks_fts` | FTS5 全文索引 |

支持格式：FVTT JournalEntry JSON / Markdown / PDF / 纯文本

### 4.5 角色卡系统

角色以 FVTT 兼容 JSON 格式存储：

```
data/characters/{system_id}/{char_id}.json
```

- **导入**：从 FVTT Actor JSON 解析为 `CharacterSheet` 模型
- **创建**：通过各系统车卡器向导创建
- **编辑**：前端编辑器（每个系统独立 UI）
- **导出**：可导出为 FVTT 兼容格式
- **AI 引导**：通过筹备 AI 对话引导车卡

### 4.6 存档系统

```json
{
  "save_id": "session_xxx_20260429_153000",
  "session_id": "session_xxx",
  "label": "第三章 - 战斗前夕",
  "state": { "system_id": "pf2e", "phase": "combat", ... },
  "chat_history": [
    { "role": "narrator", "content": "...", "interactive": [...] },
    { "role": "referee", "content": "", "dice": {...} },
    { "role": "user", "content": "..." }
  ],
  "memories": [...]
}
```

- 存档按 `system_id` 过滤，各规则独立
- 对话历史包含交互控件和骰子结果（可完整还原界面状态）
- 支持导出/导入存档文件、导出 Markdown 团 log

### 4.7 Skill 系统

Markdown 文件，存储在 `data/skills/{system_id}/`（共享 Skill 在 `data/skills/shared/`）：

```markdown
# Skill Title
> One-line description
*Created: 2026-04-29 15:30*

## Instructions
Step-by-step instructions for the AI...
```

AI 可自主创建和管理 Skills：`skill_list` / `skill_read` / `skill_create` / `skill_update` / `skill_delete`

### 4.8 自定义工具系统

工具元数据 JSON 存储在 `data/tools/`：

```json
{
  "tool_id": "xxx",
  "name": "战场地图分析",
  "description": "分析当前战场状态并给出战术建议",
  "instructions": "...",
  "category": "combat",
  "system_id": "pf2e",
  "shared": false,
  "builtin": false
}
```

- 内置工具不可删除
- 自定义工具支持 CRUD
- 标记 `shared` 可跨系统使用

## 5. 工具集

### 5.1 骰子工具

| 系统 | 实现 | 特性 |
|------|------|------|
| PF2e | `pf2e/dice_rules.py` | d20 四档成功度 (大成功/成功/失败/大失败) |
| Daggerheart | `daggerheart/dice_rules.py` | 二元骰 (Hope d12 + Fear d12)，duality_outcome |
| SWADE | `swade/dice_rules.py` | 爆骰机制，双属性取高，Raises 计算 |

基于 Python `d20` 库实现真随机，骰子结果绝不由 LLM 生成。

### 5.2 规则书查询 (PF2e)

- `rulebook_lookup(name)` — 按名称精确查找
- `rulebook_search(query, category)` — 三层递进搜索

### 5.3 参考资料阅读

- `list_materials()` — 列出所有已上传资料
- `browse_material(doc_id, start, count)` — 按顺序浏览文档
- `search_material(query, doc_id)` — 全文搜索资料内容

### 5.4 遭遇管理

- `start_combat` — 初始化战斗，按先攻排序
- `next_turn` — 推进回合
- `apply_damage` — 对目标施加伤害
- `get_combat_status` — 获取战场概览
- `end_combat` — 结束战斗

### 5.5 角色表

- `get_player_info` / `get_full_character_sheet` — 获取角色信息
- `update_player_hp` — 修改 HP
- `add_condition` / `remove_condition` — 管理状态

### 5.6 队伍管理

- `list_available_characters` — 列出可用角色卡
- `suggest_add_teammate` — 建议添加队友
- `request_prep_work` — 请求团外 AI 协助制作内容

### 5.7 车卡工具 (AI 使用)

各系统提供独立的 AI 车卡工具：

| 系统 | 工具 |
|------|------|
| PF2e | `cb_search_*` (ancestry/heritage/background/class/feat/spell/equipment)、`cb_validate_build`、`cb_assemble_character`、`cb_assemble_npc` |
| Daggerheart | `dh_assemble_character`、`dh_assemble_npc` |
| SWADE | `swade_assemble_character`、`swade_assemble_npc` |

## 6. 前端架构

### 6.1 界面模式

| 模式 | 说明 |
|------|------|
| 团外准备 (Prep) | 10 个子面板，管理所有团外事务 |
| 团内游戏 (Game) | 多智能体跑团聊天 + 交互控件 |
| 调试面板 (Debug) | 独立端口 3001，实时监控 |

### 6.2 团外准备子面板

| 面板 | 组件 | 功能 |
|------|------|------|
| 团管理 | `CampaignManager` | 新建/切换/删除团，角色选择，队友管理，按系统过滤 |
| 筹备 AI | `PrepChat` | 团外智能体对话，引导资料整理、车卡、Skill 创建 |
| 创作 AI | `CreatorChat` | 剧本/模组/世界内容创作，成果可发布到资料库 |
| 资料库 | `MaterialsPanel` | 上传/删除/搜索文档 |
| 角色卡 | `CharactersPanel` | 导入/管理/车卡器 (各系统独立 UI) |
| Skills | `SkillsPanel` | Skill CRUD |
| 工具 | `ToolsPanel` | 自定义工具管理 |
| 存档 | `SaveLoadPanel` | 存读档/导出导入，按当前系统过滤 |
| 工作区 | `WorkspacePanel` | AI 可操作的隔离文件目录 |
| 备份 | `BackupPanel` | 全量数据导出/导入 |

### 6.3 车卡器组件

**PF2e** — 12 步向导 (`charbuilder/CharBuilderWizard.tsx`)：
- 血统 → 传承 → 背景 → 职业 → 属性分配 → 技能 → 专长 → 法术 → 装备 → 细节 → 预览

共享组件：`OptionBrowser`、`BoostAllocator`、`AbilityScorePreview`、`FeatSlotList`、`PF2eDescription`、`RarityBadge`

**Daggerheart** — 多步向导 (`charbuilder-dh/DHCharBuilderWizard.tsx`)：
- 职业/子职业 → 社群 → 血统 → 领域卡 → 武器/护甲 → 细节
- 升级面板 (`DHLevelUpPanel.tsx`)

**SWADE / 七物语** — 属性向导 (`charbuilder-swade/SWADECharBuilderWizard.tsx`)：
- 种族 → 属性 → 元素 → 专长/障碍 → 奇术 → 装备 → 细节

### 6.4 交互控件组件

| 组件 | 路径 | 功能 |
|------|------|------|
| `InteractiveRenderer` | `interactive/` | 按类型分发渲染交互控件 |
| `ChoiceCard` | `interactive/` | 选项卡片，支持 resolved 状态恢复 |
| `DiceRollButton` | `interactive/` | 骰子投掷按钮 + 动画 |
| `DualityDiceButton` | `interactive/` | Daggerheart 二元骰 |
| `InputPrompt` | `interactive/` | 文本输入交互 |
| `DiceResultCard` | `interactive/` | 标准骰结果展示 |
| `DualityDiceCard` | `interactive/` | 二元骰结果 (Hope/Fear 分色) |
| `TokenUpdateCard` | `interactive/` | 代币变动公告 |

### 6.5 角色卡编辑器

| 系统 | 组件 | 功能 |
|------|------|------|
| PF2e | `CharacterSheetEditor` | 属性/技能/专长/法术/装备编辑 |
| Daggerheart | `DHCharacterSheetEditor` | HP/属性/领域卡/装备编辑 |
| SWADE | `SWADECharacterSheetEditor` | 属性/技能/专长/奇术编辑 |

### 6.6 数据流

```
用户输入
   │
   ▼
ChatInput.onSend()
   │
   ▼
streamChat() ─── POST /api/chat ──→ SSE 流
   │
   ├─ type: "text"        → 追加到当前 ChatBubble (实时流式)
   ├─ type: "dice"        → 插入 DiceResultCard (裁判暗骰)
   ├─ type: "interactive"  → 即时挂载交互控件 (去重)
   ├─ type: "state_update" → 更新 Sidebar 状态
   └─ type: "error"       → 显示错误消息

交互控件操作
   │
   ├─ ChoiceCard.onSelect   → handleResolveInteractive + handleSend
   ├─ DiceRollButton.onClick → POST /api/dice/roll → resolve + handleSend
   └─ InputPrompt.onSubmit  → handleResolveInteractive + handleSend
```

### 6.7 客户端持久化

通过 localStorage 存储：
- `ttrpg_llm_config` — API Key、模型名、Base URL
- `ttrpg_session_id` — 当前会话 ID

## 7. 通信协议

### 7.1 SSE 事件格式

```json
{"type": "text",         "content": "叙事文本..."}
{"type": "dice",         "dice": {"expression": "1d20+5", "rolls": [17], "total": 22, "detail": "1d20 (17) + 5", "success_level": "success", "dc": 15}}
{"type": "interactive",  "interactive": {"element_type": "choices", "id": "xxx", "prompt": "你选择...", "options": [...]}}
{"type": "interactive",  "interactive": {"element_type": "dice_request", "id": "xxx", "prompt": "进行感知检定", "expression": "1d20+3", "dc": 15, "skill_name": "感知"}}
{"type": "interactive",  "interactive": {"element_type": "duality_dice_request", "id": "xxx", "prompt": "敏捷检定", "trait_name": "Agility"}}
{"type": "interactive",  "interactive": {"element_type": "token_update", "id": "xxx", "token_type": "fear", "token_change": 1, "token_total": 3}}
{"type": "state_update", "state": {"session_id": "...", "system_id": "pf2e", "phase": "combat", ...}}
{"type": "error",        "content": "错误信息"}
```

### 7.2 聊天历史持久化格式

后端 `append_history` 的消息结构：

```json
{"role": "user", "content": "我要搜索这个房间"}
{"role": "narrator", "content": "你仔细查看...", "interactive": [{"element_type": "choices", "id": "xxx", ...}]}
{"role": "referee", "content": "", "dice": {"expression": "1d20+5", "total": 22, ...}}
{"role": "teammate", "content": "我来掩护你！"}
```

## 8. API 路由总览

### 8.1 核心路由

| 前缀 | 模块 | 主要端点 |
|------|------|----------|
| `/api/sessions` | `sessions.py` | CRUD、队友管理、按 system_id 过滤 |
| `/api/chat` | `chat.py` | `POST /` SSE 流式聊天、`POST /resume` 恢复中断 |
| `/api/saves` | `saves.py` | 存读档、导出导入、按 system_id 过滤 |
| `/api/characters` | `characters.py` | FVTT 导入、CRUD、HP/状态管理 |
| `/api/documents` | `documents.py` | 文档上传/搜索/浏览/删除 |
| `/api/dice` | `dice_roll.py` | `POST /roll` 玩家前端骰子投掷 |
| `/api/skills` | `skills.py` | Skill CRUD |
| `/api/tools` | `tools.py` | 自定义工具 CRUD |
| `/api/memories` | `memories.py` | 记忆查看/创建/删除 |
| `/api/workspace` | `workspace.py` | AI 工作区文件操作 |
| `/api/backup` | `backup.py` | 全量导出/导入 |
| `/api/compendium` | `compendium.py` | 合集包 CRUD、FVTT 导入 |

### 8.2 团外 AI 路由

| 前缀 | 模块 | 说明 |
|------|------|------|
| `/api/prep-chat` | `prep_chat.py` | 筹备 AI 流式对话、会话管理 |
| `/api/creator-chat` | `creator_chat.py` | 创作 AI 流式对话、会话管理 |

### 8.3 系统专属路由

| 前缀 | 系统 | 说明 |
|------|------|------|
| `/api/pf2e/rules` | PF2e | 规则搜索/怪物/分类/统计 |
| `/api/pf2e/charbuilder` | PF2e | 车卡数据查询/属性计算/校验/组装 |
| `/api/daggerheart/charbuilder` | DH | 车卡数据/组装/升级 |
| `/api/swade/charbuilder` | SWADE | 车卡数据/组装 |

### 8.4 调试路由

| 前缀 | 说明 |
|------|------|
| `/api/debug/events` | 事件日志 |
| `/api/debug/stats` | 系统统计 |
| `/api/debug/sessions` | 所有会话状态 |
| `/api/debug/memories/{session_id}` | 会话记忆 |
| `/api/debug/data/summary` | 数据摘要 |

### 8.5 全局设置

| 端点 | 说明 |
|------|------|
| `GET/PUT /api/settings/system` | 当前规则系统切换 |
| `GET/PUT /api/settings/reasoning-strategy` | 推理策略配置 |
| `GET /api/systems` | 列出所有可用规则系统 |
| `GET /api/health` | 健康检查 |

## 9. 目录结构

```
跑团系统/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI 入口 + 全局设置路由
│   │   ├── config.py                # 全局配置
│   │   ├── agents/                  # LangGraph 多智能体
│   │   │   ├── graph.py             # 状态图编排 + SSE 流式输出
│   │   │   ├── state.py             # 共享状态 TypedDict (Annotated reducers)
│   │   │   ├── prompts.py           # 通用系统提示
│   │   │   ├── narrator.py          # 讲述者 + 意图分析
│   │   │   ├── referee.py           # 裁决者
│   │   │   ├── teammate.py          # AI 队友
│   │   │   ├── notetaker.py         # 书记员 (记忆更新)
│   │   │   ├── prep_agent.py        # 团外筹备 AI
│   │   │   ├── creator_agent.py     # 团外创作 AI
│   │   │   ├── combat_graph.py      # 战斗子图
│   │   │   ├── dice_interrupt.py    # 骰子中断机制
│   │   │   └── compat.py            # LLM 兼容层 (SafeChatOpenAI)
│   │   ├── tools/                   # LangChain Tools
│   │   │   ├── dice.py              # 真实骰子
│   │   │   ├── interactive.py       # 交互控件工具 (选项/骰子/输入)
│   │   │   ├── party_manage.py      # 队伍管理工具
│   │   │   ├── character_sheet.py   # 角色表操作
│   │   │   ├── encounter.py         # 遭遇管理
│   │   │   ├── read_material.py     # 知识库阅读
│   │   │   ├── skills.py            # Skill 管理
│   │   │   ├── charbuilder.py       # 车卡兼容层
│   │   │   └── rulebook.py          # 规则书兼容层
│   │   ├── systems/                 # 可插拔游戏系统
│   │   │   ├── base.py              # GameSystem 抽象基类
│   │   │   ├── registry.py          # 系统注册表
│   │   │   ├── pf2e/                # Pathfinder 2e
│   │   │   │   ├── system.py        # PF2eSystem 实现
│   │   │   │   ├── prompts.py       # PF2e 系统提示
│   │   │   │   ├── tools.py         # PF2e 规则书 + 车卡工具
│   │   │   │   ├── dice_rules.py    # 四档成功度判定
│   │   │   │   ├── routers.py       # /api/pf2e/rules
│   │   │   │   ├── charbuilder_router.py  # /api/pf2e/charbuilder
│   │   │   │   ├── charbuilder_db.py      # 车卡 SQLite
│   │   │   │   ├── build_validator.py     # 构筑校验
│   │   │   │   ├── ruledb.py        # 规则 SQLite
│   │   │   │   ├── markup.py        # FVTT @UUID 解析
│   │   │   │   ├── character.py     # PF2e 角色模型
│   │   │   │   └── ingest/          # 数据导入脚本
│   │   │   ├── daggerheart/         # Daggerheart
│   │   │   │   ├── system.py        # DaggerheartSystem 实现
│   │   │   │   ├── prompts.py       # DH 系统提示
│   │   │   │   ├── dice_rules.py    # 二元骰判定
│   │   │   │   ├── charbuilder.py   # DH 车卡工具
│   │   │   │   ├── charbuilder_router.py  # /api/daggerheart/charbuilder
│   │   │   │   └── default_packs/   # 默认合集包 (含中文翻译)
│   │   │   └── swade/               # SWADE / 七物语
│   │   │       ├── system.py        # SWADESystem 实现
│   │   │       ├── prompts.py       # 七物语系统提示
│   │   │       ├── dice_rules.py    # 爆骰 + Raises
│   │   │       ├── charbuilder.py   # SWADE 车卡工具
│   │   │       ├── charbuilder_router.py  # /api/swade/charbuilder
│   │   │       └── default_packs/   # 默认合集包
│   │   ├── models/
│   │   │   ├── schemas.py           # Pydantic 数据模型
│   │   │   ├── game_state.py        # 会话状态 + 存档管理
│   │   │   └── character.py         # 通用角色模型
│   │   ├── routers/                 # API 路由 (16 个)
│   │   │   ├── sessions.py          # 会话管理
│   │   │   ├── chat.py              # SSE 流式聊天
│   │   │   ├── saves.py             # 存读档
│   │   │   ├── characters.py        # 角色卡 CRUD
│   │   │   ├── documents.py         # 文档上传/知识库
│   │   │   ├── rules.py             # 规则查询
│   │   │   ├── dice_roll.py         # 前端骰子
│   │   │   ├── skills.py            # Skill CRUD
│   │   │   ├── tools.py             # 工具 CRUD
│   │   │   ├── memories.py          # 记忆管理
│   │   │   ├── workspace.py         # AI 工作区
│   │   │   ├── backup.py            # 全量备份
│   │   │   ├── compendium.py        # 合集包管理
│   │   │   ├── prep_chat.py         # 筹备 AI
│   │   │   ├── creator_chat.py      # 创作 AI
│   │   │   └── debug.py             # 调试面板
│   │   ├── services/
│   │   │   ├── llm.py               # LLM 工厂
│   │   │   ├── ruledb.py            # SQLite 结构化规则库
│   │   │   ├── knowledge_base.py    # SQLite 通用知识库
│   │   │   ├── charbuilder_db.py    # 车卡索引 SQLite
│   │   │   ├── build_validator.py   # 构筑校验
│   │   │   ├── vectorstore.py       # ChromaDB 向量库
│   │   │   ├── compendium.py        # 合集包服务
│   │   │   ├── chat_history.py      # Prep/Creator 对话历史持久化
│   │   │   ├── memory_store.py      # 长期记忆
│   │   │   ├── skill_manager.py     # Skill 文件管理
│   │   │   ├── tool_registry.py     # 工具注册表
│   │   │   └── event_log.py         # 事件日志 (调试)
│   │   └── parsers/                 # 文档解析器
│   │       ├── fvtt_json.py         # FVTT JSON 解析
│   │       ├── markdown_parser.py
│   │       ├── pdf_parser.py
│   │       └── pipeline.py          # 统一路由
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/
│       │   └── page.tsx             # 主页面 (双模式 + 聊天 + 交互)
│       ├── components/
│       │   ├── ChatBubble.tsx       # 消息气泡 (Markdown 渲染)
│       │   ├── ChatInput.tsx        # 输入框
│       │   ├── Sidebar.tsx          # 侧边栏导航
│       │   ├── CampaignManager.tsx  # 团管理
│       │   ├── SaveLoadPanel.tsx    # 存档管理
│       │   ├── MemoryPanel.tsx      # 记忆面板
│       │   ├── BackupPanel.tsx      # 备份管理
│       │   ├── WorkspacePanel.tsx   # AI 工作区
│       │   ├── DiceDisplay.tsx      # 骰子展示
│       │   ├── interactive/         # 交互控件 (8 个组件)
│       │   ├── prep/               # 团外准备面板
│       │   │   ├── PrepChat.tsx     # 筹备 AI
│       │   │   ├── CreatorChat.tsx  # 创作 AI
│       │   │   ├── MaterialsPanel.tsx
│       │   │   ├── CharactersPanel.tsx
│       │   │   ├── SkillsPanel.tsx
│       │   │   ├── ToolsPanel.tsx
│       │   │   ├── CompendiumManager.tsx
│       │   │   ├── CharacterSheetEditor.tsx      # PF2e
│       │   │   ├── DHCharacterSheetEditor.tsx    # Daggerheart
│       │   │   └── SWADECharacterSheetEditor.tsx # SWADE
│       │   ├── charbuilder/         # PF2e 车卡器 (12 步 + 共享)
│       │   ├── charbuilder-dh/      # Daggerheart 车卡器
│       │   └── charbuilder-swade/   # SWADE 车卡器
│       └── lib/
│           ├── api.ts               # 后端 API 客户端
│           ├── types.ts             # TypeScript 类型定义
│           ├── store.ts             # localStorage 持久化
│           └── utils.ts             # 工具函数
├── scripts/
│   ├── extract_fvtt_packs.mjs       # FVTT LevelDB 导出
│   ├── process_dh_packs.mjs         # DH 合集包处理
│   ├── process_swade_packs.mjs      # SWADE 合集包处理
│   └── apply_dh_cn.mjs             # DH 中文翻译应用
├── docs/
│   └── TECHNICAL.md                 # 本文档
├── install.bat                      # Windows 安装脚本
├── start.bat                        # 一键启动 (后端 + 前端 + 调试面板)
├── stop.bat                         # 一键停止
├── ingest_rules.bat                 # PF2e 规则数据导入
└── README.md
```

## 10. 开发与部署

### 10.1 环境要求

- Python 3.11+
- Node.js 18+
- 外部 OpenAI 兼容 API Key

### 10.2 安装

```bat
install.bat
```

自动执行：Python venv 创建、pip install、npm install、PF2e 数据导入。

### 10.3 启动

```bat
start.bat
```

启动三个服务：
- 后端 FastAPI (uvicorn, 端口 8000)
- 前端 Next.js (端口 3000)
- 调试面板 (端口 3001)

### 10.4 配置

首次使用需在前端设置页配置：
- **API Key**：OpenAI 兼容 API 密钥
- **模型名称**：如 `gpt-4o`、`deepseek-chat`、`claude-3.5-sonnet` 等
- **Base URL**：API 端点（默认 `https://api.openai.com/v1`）
- **规则系统**：在配置中切换 PF2e / Daggerheart / SWADE
