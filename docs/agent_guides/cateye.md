# CatEye 图片识别工具 -- 智能体使用指南

> 本文档面向 AI 智能体，描述 CatEye 工具集的可用工具、参数说明、场景预设和最佳实践。

---

## 一、可用工具清单

CatEye 工具集共提供 4 个工具。核心工具（OCR/Search/Vision）内部自动完成预处理和缓存，无需额外调用辅助工具。

### 1. nkit_ce_ocr（核心 - 文字识别）

使用 RapidOCR 引擎提取图片中的文字，默认支持中文和英文。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_url` | string | 是 | 图片 URL 或本地文件路径 |

**返回示例：**

```json
{
  "success": true,
  "message": "OCR 完成",
  "data": {
    "text": "提取的文字内容",
    "block_count": 5
  }
}
```

---

### 2. nkit_ce_search（核心 - 以图搜图）

多供应商反向图片搜索，根据场景自动选择供应商。内置支持 trace.moe（番剧）、SauceNAO（萌系/插画）、华为云（通用）。管理员可在 WebUI 中配置自定义供应商，供应商列表和场景类型会动态扩展。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_url` | string | 是 | 图片 URL 或本地文件路径 |
| `scene` | string | 否 | `auto`（默认）或配置中存在的场景类型 |
| `provider` | string | 否 | 强制指定供应商（可在 WebUI 中获取列表） |

**内置场景-供应商映射：**

| scene | 供应商 | 适用场景 |
|-------|--------|---------|
| `auto` | 所有已启用供应商 | 不确定时使用 |
| `anime` | trace.moe | 番剧场景截图 |
| `moe` / `illustration` | SauceNAO | 二次元插画/漫画 |
| `general` | 华为云 | 通用图片搜索 |

**返回示例：**

```json
{
  "success": true,
  "message": "找到 3 条结果",
  "data": {
    "results": [
      {
        "provider": "trace.moe",
        "similarity": 0.92,
        "anime": "番剧名称",
        "episode": 3,
        "from_time": 754.2
      }
    ]
  }
}
```

---

### 3. nkit_ce_vision（核心 - 视觉理解）

调用多模态大模型对图片进行理解、描述或推理。支持日常模式和专业模式。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_url` | string | 是 | 图片 URL 或本地文件路径 |
| `prompt` | string | 是 | 对图片的理解或描述需求 |
| `mode` | string | 否 | `daily`（默认）/ `professional` |

**模式说明：**

| 模式 | 适用场景 | 说明 |
|------|---------|------|
| `daily` | 表情包、日常场景、游戏截图 | 自然、对话式的分析 |
| `professional` | 复杂图表、技术图纸、习题解答 | 详细、精确的分析 |

**返回示例：**

```json
{
  "success": true,
  "message": "视觉分析完成（daily 模式）",
  "data": {
    "analysis": "大模型的分析结果",
    "mode": "daily"
  }
}
```

---

### 4. nkit_ce_scene（场景预设管理）

场景预设工具。根据场景编码返回工具组合策略，指导按步骤调用 CatEye 工具集。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action` | string | 是 | `list` / `get` / `update` |
| `scene_code` | string | 否 | 场景编码（get/update 时必填） |
| `preset_json` | string | 否 | 预设方案 JSON（update 时必填） |

---

## 二、场景预设

### 内置预设

| 编码 | 名称 | 工具链路 | 触发关键词 |
|------|------|---------|-----------|
| `extract_text` | 文字提取 | ocr | 提取文字、OCR、识别文字、台词、字幕、公告、文案 |
| `identify_character` | 角色识别 | search -> vision | 这是谁、角色识别、认人、动漫角色、游戏角色、虚拟主播 |
| `find_anime_source` | 番剧溯源 | search | 这是什么番、番名、动漫名称、哪一集、找番、认番 |
| `understand_meme` | 表情包解读 | vision | 梗图、表情包、什么意思、笑点、玩梗、斗图 |
| `analyze_chart` | 图片分析 | vision | 分析一下、游戏截图、攻略、面板、配装、抽卡 |

通用内容（游戏截图、活动图、地图等）使用 daily 模式；涉及数据、图表、复杂逻辑时使用 professional 模式。

### 动态添加场景

通过 `nkit_ce_scene(action="update")` 写入自定义预设。内置预设不可被覆盖。

---

## 三、最佳实践

### 典型场景覆盖

| 用户意图 | 推荐场景 | 调用方式 |
|---------|---------|---------|
| 提取台词、字幕、公告文字 | `extract_text` | `nkit_ce_ocr(image_url="...")` |
| 识别动漫/游戏角色 | `identify_character` | `nkit_ce_search` -> `nkit_ce_vision` |
| 查找番剧出处 | `find_anime_source` | `nkit_ce_search(image_url="...", scene="anime")` |
| 解读表情包含义 | `understand_meme` | `nkit_ce_vision(image_url="...", prompt="解读这个表情包")` |
| 分析游戏截图/攻略（日常） | `analyze_chart` | `nkit_ce_vision(image_url="...", prompt="...", mode="daily")` |
| 分析数据图/表格/复杂场景 | `analyze_chart` | `nkit_ce_vision(image_url="...", prompt="...", mode="professional")` |

### 调用次数指南

核心工具内部自动完成预处理和缓存，大多数场景 1-3 次调用即可完成分析：

- **1 次调用**：纯文字提取、纯搜图、纯视觉理解
- **2 次调用**：先搜图再视觉理解（如角色识别）
- **3 次调用**：复杂场景需组合多个工具

### 错误处理

- 核心工具失败时，尝试替代工具（如 OCR 失败，尝试 vision）
- 特定供应商失败时，尝试其他供应商或使用 `scene="auto"`
- 所有工具都失败时，告知用户限制并说明可能的原因

---

## 四、完整工作流示例

### 示例 1：提取图片文字

用户发送一张截图问"这写的什么？"：

```
1. nkit_ce_ocr(image_url="...")
   -> 返回提取的文字内容

2. 向用户回复文字内容
```

### 示例 2：识别番剧出处

用户发送一张番剧截图问"这是哪部番？"：

```
1. nkit_ce_search(image_url="...", scene="anime")
   -> 搜索结果：番剧名称、集数、时间戳

2. nkit_ce_vision(
     image_url="...",
     prompt="请描述这张图片的内容，结合搜索结果分析",
     mode="daily"
   )
   -> 视觉分析结果

3. 向用户回复综合结果
```

### 示例 3：分析复杂数据图

用户发送一张数据图表问"帮我分析一下这个图"：

```
1. nkit_ce_vision(
     image_url="...",
     prompt="请详细分析这张数据图表，包括数据趋势和关键指标",
     mode="professional"
   )
   -> 专业模式分析结果

2. 向用户回复分析结果
```

---

> 设计文档：[CatEye 图片识别工具集设计](../design/cateye.md)
