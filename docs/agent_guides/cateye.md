# CatEye 图片识别工具 — 智能体使用指南

> 本文档面向 AI 智能体，描述 CatEye 工具集的所有工具 Schema、场景预设、缓存管理、上下文蒸馏和任务评价机制。

---

## 一、可用工具清单

### 1. cateye_ocr（核心 · 文字识别）

使用 RapidOCR 引擎提取图片中的文字，默认支持中文和英文。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_url` | string | ✅ | 图片 URL 或本地文件路径 |

---

### 2. cateye_search（核心 · 以图搜图）

多供应商反向图片搜索，根据场景自动选择供应商。内置支持 trace.moe（番剧）、SauceNAO（萌系/插画）、华为云（通用）。管理员可在 WebUI 中配置自定义供应商，供应商列表和场景类型会动态扩展。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_url` | string | ✅ | 图片 URL 或本地文件路径 |
| `scene` | string | ❌ | `auto`（默认）或配置中存在的场景类型 |
| `provider` | string | ❌ | 强制指定供应商（可在 WebUI 中获取列表） |

**内置场景-供应商映射：**

| scene | 供应商 | 适用场景 |
|-------|--------|---------|
| `auto` | 所有已启用供应商 | 不确定时使用 |
| `anime` | trace.moe | 番剧场景截图 |
| `moe` / `illustration` | SauceNAO | 二次元插画/漫画 |
| `general` | 华为云 | 通用图片搜索 |

---

### 3. cateye_vision（核心 · 视觉理解）

调用多模态大模型对图片进行理解、描述或推理。支持上下文注入以增强分析效果。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_url` | string | ✅ | 图片 URL 或本地文件路径 |
| `prompt` | string | ✅ | 对图片的理解或描述需求 |
| `mode` | string | ❌ | `daily`（默认）/ `professional` |
| `scene_name` | string | ❌ | 场景预设名称（上下文注入） |
| `scene_description` | string | ❌ | 场景描述 |
| `tool_chain_dag` | string | ❌ | 工具链路 DAG 描述 |
| `user_intent_keywords` | string | ❌ | 用户意图关键词，逗号分隔 |
| `distilled_context` | string | ❌ | 从会话蒸馏的关键信息摘要 |
| `cached_results` | string | ❌ | 前序工具缓存结果 JSON |

上下文注入：提供 `scene_name`、`tool_chain_dag`、`user_intent_keywords` 或 `distilled_context` 中任一参数时，系统 Prompt 自动注入背景信息，引导大模型基于场景上下文进行分析。

---

### 4. cateye_preprocess（辅助 · 图片预处理）

根据任务类型自动调整图片尺寸和格式，优化识别速度和 token 消耗。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_url` | string | ✅ | 图片 URL 或本地文件路径 |
| `task_type` | string | ✅ | `ocr` / `search` / `vision` |

**预处理规则：**

| task_type | 最大尺寸 | 格式 | 特殊处理 |
|-----------|---------|------|---------|
| `ocr` | 2048px | PNG | 灰度化 |
| `search` | 1024px | JPEG 85% | — |
| `vision` | 2048px | JPEG 90% | — |

---

### 5. cateye_cache（辅助 · 缓存管理）

图片缓存管理工具。自动计算图片哈希，内部调用 kv_store 管理缓存。缓存有效期 48 小时。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_url` | string | ✅ | 图片 URL 或本地文件路径 |
| `action` | string | ✅ | `check` / `store` / `update` |
| `tool_chain_dag` | string | ❌ | 工具链路 DAG 描述（store/update 时必填） |
| `tool_chain_nodes` | string | ❌ | 工具节点列表 JSON（store/update 时必填） |
| `result` | string | ❌ | 各工具返回结果 JSON（store/update 时必填） |
| `context_scene` | string | ❌ | 场景预设名称 |
| `context_scene_description` | string | ❌ | 场景描述 |
| `context_user_intent` | string | ❌ | 用户意图关键词，逗号分隔 |
| `context_distilled` | string | ❌ | 蒸馏的上下文摘要 |
| `evaluation` | integer | ❌ | 任务评价 [-2, 2]（update 时可选） |

**操作说明：**

| action | 说明 |
|--------|------|
| `check` | 查询缓存，命中返回完整条目，过期自动清除 |
| `store` | 写入新缓存条目，自动计算图片哈希，设置 48h 过期 |
| `update` | 合并新结果到已有条目，刷新过期时间，写入评价 |

---

## 二、场景预设

通过 `cateye_scene` 工具管理场景预设。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action` | string | ✅ | `list` / `get` / `update` |
| `scene_code` | string | ❌ | 场景编码（get/update 时必填） |
| `preset_json` | string | ❌ | 预设方案 JSON（update 时必填） |

### 内置预设

| 编码 | 名称 | 工具链路 | 触发关键词 |
|------|------|---------|-----------|
| `extract_text` | 文字提取 | preprocess → ocr | 提取文字、OCR、识别文字、台词、字幕、公告、文案 |
| `identify_character` | 角色识别 | preprocess → search → preprocess → vision | 这是谁、角色识别、认人、动漫角色、游戏角色、虚拟主播 |
| `find_anime_source` | 番剧溯源 | preprocess → search | 这是什么番、番名、动漫名称、哪一集、找番、认番 |
| `understand_meme` | 表情包解读 | preprocess → vision | 梗图、表情包、什么意思、笑点、玩梗、斗图 |
| `analyze_chart` | 图片分析 | preprocess → vision（根据内容自动选择模式） | 分析一下、游戏截图、攻略、面板、配装、抽卡 |

通用内容（游戏截图、活动图、地图等）使用 daily 模式；涉及数据、图表、复杂逻辑时使用 professional 模式。

### 动态添加场景

通过 `cateye_scene(action="update")` 写入自定义预设。内置预设不可被覆盖。

---

## 三、缓存管理

### 缓存条目结构

缓存 Key = `cat_eye:cache:{image_hash}`，Value 为 JSON：

```json
{
  "tool_chain": {
    "dag": "cateye_preprocess(ocr) → cateye_ocr → cateye_vision(daily)",
    "nodes": [
      {"tool": "cateye_preprocess", "params": {"task_type": "ocr"}},
      {"tool": "cateye_ocr", "params": {}},
      {"tool": "cateye_vision", "params": {"mode": "daily"}}
    ]
  },
  "result": {
    "ocr_text": "提取的文字内容",
    "vision_response": "大模型分析结果",
    "search_result": null
  },
  "context": {
    "scene": "general_ocr",
    "scene_description": "用户要求提取图片文字并翻译",
    "user_intent_keywords": ["翻译", "提取文字"],
    "distilled_context": "用户在群聊中发了一张菜单截图，要求翻译成中文。"
  },
  "evaluation": 1,
  "created_at": "2026-05-20T10:30:00Z",
  "expires_at": "2026-05-22T10:30:00Z"
}
```

### 48 小时生命周期

- 缓存有效期固定为 48 小时
- `check` 操作自动检查过期，过期条目立即清除
- `store` 和 `update` 操作自动设置/刷新过期时间

### 缓存命中但结果不足

1. 复用缓存中的 `result` 字段内容
2. 调用缺失的核心工具补充分析
3. 通过 `cateye_cache(action="update")` 合并新旧结果，刷新过期时间

### 与记忆模块协作

缓存条目存储在 kv_store 中，记忆模块可直接通过 `get_kv`/`set_kv` 访问 `cat_eye:cache:` 前缀的条目。若记忆模块自行管理缓存，建议将缓存记录迁移到记忆模块的专用存储目录，避免重复存储。

---

## 四、上下文蒸馏指南

调用 `cateye_vision` 时，从会话上下文中提取关键信息并注入，以提升分析质量。

### 蒸馏步骤

1. 提取用户意图关键词（如"翻译"、"识别角色"、"这是什么"）
2. 判断当前适用的场景预设
3. 从会话历史中提取与当前任务相关的关键信息（用户语言偏好、之前讨论的话题、图片来源等）
4. 将上述信息填入 `cateye_vision` 的 `scene_name`、`scene_description`、`tool_chain_dag`、`user_intent_keywords`、`distilled_context` 参数

### 示例

用户在群聊中发了一张英文菜单截图，要求翻译成中文：

```
cateye_vision(
  image_url="...",
  prompt="请将图片中的英文菜单翻译成中文",
  mode="daily",
  scene_name="general_ocr",
  scene_description="适用于纯文字提取场景",
  tool_chain_dag="cateye_preprocess(ocr) → cateye_ocr",
  user_intent_keywords="翻译,提取文字,英文菜单",
  distilled_context="用户在群聊中发了一张英文菜单截图，此前已讨论过餐厅推荐，用户偏好中文表达。",
  cached_results='{"ocr_text": "Spaghetti Bolognese $12.99..."}'
)
```

---

## 五、任务评价指南

任务结束后，评估任务效果，将整数值写入缓存条目的 `evaluation` 字段。

### 评价标准

| 分值 | 含义 |
|------|------|
| `2` | 完美回答了用户问题，信息准确且完整 |
| `1` | 基本满足需求，有少量不足 |
| `0` | 不好不坏 |
| `-1` | 结果与用户需求偏差较大 |
| `-2` | 完全错误或无用的结果 |

### 写入方式

```
cateye_cache(image_url="...", action="update", evaluation=1)
```

---

## 六、最佳实践方案

### ≥90% 场景覆盖

| 用户意图 | 推荐场景 | 工具链路 |
|---------|---------|---------|
| 提取台词、字幕、公告文字 | `extract_text` | preprocess(ocr) → ocr |
| 识别动漫/游戏角色 | `identify_character` | preprocess(search) → search → preprocess(vision) → vision |
| 查找番剧出处 | `find_anime_source` | preprocess(search) → search |
| 解读表情包含义 | `understand_meme` | preprocess(vision) → vision |
| 分析游戏截图/攻略（日常） | `analyze_chart` | preprocess(vision) → vision（daily 模式） |
| 分析数据图/表格/复杂场景 | `analyze_chart` | preprocess(vision) → vision（professional 模式） |

### 复杂任务指南

当内置预设无法满足需求时，自行组装工具链路：

1. 规划 DAG：确定需要调用的工具及顺序
2. 逐步执行：按 DAG 顺序依次调用工具，将前序结果通过 `cached_results` 传递给后续工具
3. 存入缓存：通过 `cateye_cache(action="store")` 写入缓存

工具链路描述格式：`cateye_preprocess(ocr) → cateye_ocr → cateye_vision(daily)`

### 错误处理

- 核心工具失败时，尝试替代工具（如 OCR 失败，尝试 vision）
- 特定供应商失败时，尝试其他供应商或使用 `scene="auto"`
- 所有工具都失败时，告知用户限制并说明可能的原因
- 缓存查询失败时，跳过缓存直接执行工具链

---

## 七、完整工作流示例

用户发送一张番剧截图问"这是哪部番？"：

```
1. cateye_cache(image_url="...", action="check")
   → 缓存未命中

2. cateye_scene(action="get", scene_code="identify_subject")
   → 获取场景预设

3. cateye_preprocess(image_url="...", task_type="search")
   → 预处理后的图片路径

4. cateye_search(image_url="...", scene="anime")
   → 搜索结果：番剧名称、集数、时间戳

5. cateye_preprocess(image_url="...", task_type="vision")
   → 预处理后的图片路径

6. cateye_vision(
     image_url="...",
     prompt="请描述这张图片的内容",
     mode="daily",
     scene_name="identify_subject",
     scene_description="识别图片中的角色或物体",
     tool_chain_dag="cateye_preprocess(search) → cateye_search → cateye_preprocess(vision) → cateye_vision(daily)",
     user_intent_keywords="番剧,出处,这是哪部",
     distilled_context="用户发送了一张番剧截图，询问出处。搜索结果已获取。",
     cached_results='{"search_result": "番剧名称：XXX，第3集 12:34"}'
   )
   → 视觉分析结果

7. cateye_cache(
     image_url="...",
     action="store",
     tool_chain_dag="cateye_preprocess(search) → cateye_search → cateye_preprocess(vision) → cateye_vision(daily)",
     tool_chain_nodes='[...]',
     result='{"ocr_text": null, "search_result": "...", "vision_response": "..."}',
     context_scene="identify_subject",
     context_user_intent="番剧,出处,这是哪部"
   )

8. 向用户回复综合结果

9. 根据用户反馈：cateye_cache(image_url="...", action="update", evaluation=1)
```
