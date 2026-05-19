# Cateye 图片识别工具 - 智能体使用指南

NekoKit 提供了 6 个图片识别工具，统称为 **cateye** 工具集。本指南帮助你选择和组合这些工具。

---

## 工具概览

| 工具 | 名称 | 类型 | 用途 |
|------|------|------|------|
| OCR | `cateye_ocr` | 核心 | 从图片中提取文字 |
| 以图搜图 | `cateye_search` | 核心 | 多供应商反向图片搜索 |
| 视觉理解 | `cateye_vision` | 核心 | 多模态大模型图片理解 |
| 预处理 | `cateye_preprocess` | 辅助 | 按任务类型优化图片尺寸和格式 |
| 缓存 | `cateye_cache` | 辅助 | 检查/存储缓存结果，避免重复 API 调用 |
| 场景预设 | `cateye_scene` | 编排 | 返回工具组合策略，指导按步骤调用工具 |

---

## 快速开始：场景预设

**推荐使用 `cateye_scene` 获取工具组合方案**，而非手动编排工具调用。

```json
{ "action": "list" }
```

返回所有可用场景预设。然后用 `get` 获取具体方案：

```json
{ "action": "get", "scene_code": "extract_text" }
```

方案会返回一个 `steps` 列表，按顺序调用即可。你也可以用 `update` 操作修改预设方案，实现任务自适应。

### 内置场景预设

| 编码 | 名称 | 工具组合 |
|------|------|---------|
| `extract_text` | 文字提取 | cache→preprocess→ocr→cache |
| `identify_character` | 角色识别 | cache→preprocess→search→preprocess→vision→cache |
| `find_anime_source` | 番剧溯源 | cache→preprocess→search→cache |
| `understand_meme` | 表情包理解 | cache→preprocess→vision→cache |
| `analyze_chart` | 图表分析 | cache→preprocess→vision(professional)→cache |

---

## 工具参数

### cateye_ocr

使用 RapidOCR 从图片中提取文字，默认支持中文和英文。

```json
{
  "name": "cateye_ocr",
  "parameters": {
    "type": "object",
    "properties": {
      "image_url": { "type": "string", "description": "图片 URL 或本地文件路径" }
    },
    "required": ["image_url"]
  }
}
```

**调用示例：**
```json
{ "image_url": "https://example.com/document.png" }
```

### cateye_search

多供应商反向图片搜索，支持自动选择供应商。

```json
{
  "name": "cateye_search",
  "parameters": {
    "type": "object",
    "properties": {
      "image_url": { "type": "string", "description": "图片 URL 或本地文件路径" },
      "scene": { "type": "string", "enum": ["auto", "anime", "moe", "illustration", "general"], "description": "场景类型，用于自动选择供应商" },
      "provider": { "type": "string", "enum": ["huawei", "tracemoe", "saucenao"], "description": "强制指定供应商" }
    },
    "required": ["image_url"]
  }
}
```

**调用示例：**
```json
{ "image_url": "https://example.com/anime_frame.jpg", "scene": "anime" }
{ "image_url": "https://example.com/illustration.png", "scene": "moe" }
{ "image_url": "https://example.com/photo.jpg", "scene": "auto" }
```

**供应商选择指南：**
- `anime` → trace.moe（番剧场景识别）
- `moe` / `illustration` → SauceNAO（插画/漫画/二次元）
- `general` → 华为云（通用图片搜索）
- `auto` → 依次尝试所有已启用的供应商

### cateye_vision

多模态大模型图片理解，支持双模式。

```json
{
  "name": "cateye_vision",
  "parameters": {
    "type": "object",
    "properties": {
      "image_url": { "type": "string", "description": "图片 URL 或本地文件路径" },
      "prompt": { "type": "string", "description": "你想了解或描述图片的什么内容" },
      "mode": { "type": "string", "enum": ["daily", "professional"], "description": "daily：表情包、日常场景；professional：复杂图表、解题分析" }
    },
    "required": ["image_url", "prompt"]
  }
}
```

**调用示例：**
```json
{ "image_url": "https://example.com/meme.jpg", "prompt": "这个表情包什么意思？", "mode": "daily" }
{ "image_url": "https://example.com/chart.png", "prompt": "分析这个图表的数据趋势", "mode": "professional" }
```

### cateye_preprocess

按任务类型优化图片尺寸和格式。

```json
{
  "name": "cateye_preprocess",
  "parameters": {
    "type": "object",
    "properties": {
      "image_url": { "type": "string", "description": "图片 URL 或本地文件路径" },
      "task_type": { "type": "string", "enum": ["ocr", "search", "vision"], "description": "任务类型" }
    },
    "required": ["image_url", "task_type"]
  }
}
```

**预设参数：**
- OCR：最大 2048px，PNG 格式，灰度化
- 搜图：最大 1024px，JPEG 质量 85
- 视觉理解：最大 2048px，JPEG 质量 90

### cateye_cache

检查或存储相似图片的缓存结果。

```json
{
  "name": "cateye_cache",
  "parameters": {
    "type": "object",
    "properties": {
      "image_url": { "type": "string", "description": "图片 URL 或本地文件路径" },
      "task_type": { "type": "string", "enum": ["ocr", "search", "vision"], "description": "任务类型" },
      "action": { "type": "string", "enum": ["check", "store"], "description": "check：查询缓存；store：保存结果" },
      "result": { "type": "string", "description": "要存储的结果数据（store 操作时必填）" }
    },
    "required": ["image_url", "task_type", "action"]
  }
}
```

### cateye_scene

场景预设工具，返回工具组合策略。

```json
{
  "name": "cateye_scene",
  "parameters": {
    "type": "object",
    "properties": {
      "action": { "type": "string", "enum": ["list", "get", "update"], "description": "操作类型" },
      "scene_code": { "type": "string", "description": "场景编码" },
      "preset_json": { "type": "string", "description": "预设方案 JSON（update 时必填）" }
    },
    "required": ["action"]
  }
}
```

**调用示例：**
```json
{ "action": "list" }
{ "action": "get", "scene_code": "extract_text" }
{ "action": "update", "scene_code": "my_scene", "preset_json": "{\"name\":\"自定义\",\"steps\":[{\"tool\":\"cateye_ocr\",\"params\":{}}]}" }
```

---

## 工具组合方式

核心工具（OCR / 搜图 / 视觉理解）专注于识别逻辑，**不内置缓存和预处理**。智能体需要按场景预设方案手动编排辅助工具的调用顺序。

典型流程：

1. `cateye_cache(action="check")` — 检查缓存
2. `cateye_preprocess()` — 预处理图片
3. 核心工具 — 执行识别
4. `cateye_cache(action="store")` — 存储结果

**推荐使用 `cateye_scene` 获取完整的步骤方案**，避免遗漏辅助步骤。

---

## 上下文感知

### 同一图片的后续提问

当用户对之前分享的图片提出后续问题时，你**不需要**重新运行所有工具。利用对话历史回忆之前的分析结果。

### 多图片关联

当用户发送多张图片进行比较或关联时：
- 对每张图片独立运行工具
- 在回复中综合分析结果

### 专业模式使用注意

仅在以下情况使用 `cateye_vision` 的 `mode="professional"`：
- 图片包含复杂的数据可视化（图表、图形、表格）
- 用户明确要求详细的技术分析
- 图片包含需要精确解读的学术或技术内容

其他所有情况使用 `mode="daily"` 以节省 token。

---

## 错误处理

| 错误 | 原因 | 建议操作 |
|------|------|----------|
| "rapidocr-onnxruntime 未安装" | 缺少依赖 | 提示用户安装 rapidocr-onnxruntime |
| "No daily_model configured" | 未配置视觉模型 | 提示用户在插件设置中配置模型 |
| "Huawei Cloud API key not configured" | 缺少 API Key | 建议使用其他供应商或配置 Key |
| "Failed to download image" | 无效 URL 或网络问题 | 请用户提供有效的图片 URL |
| "Image not found" | 无效本地路径 | 请用户提供有效的图片路径 |
| "Cache miss" | 无缓存结果 | 继续执行实际工具调用 |
| 供应商返回空结果 | 未找到匹配 | 尝试其他场景/供应商，或使用 `cateye_vision` 作为降级方案 |

**通用错误恢复模式：**
1. 核心工具失败时，尝试替代工具（如 OCR 失败，尝试 vision）
2. 特定供应商失败时，尝试其他供应商或使用 `scene="auto"`
3. 所有工具都失败时，告知用户限制并说明可能的原因

---

> 📖 设计文档：[Cateye 图片识别工具集设计](../design/cateye.md)
