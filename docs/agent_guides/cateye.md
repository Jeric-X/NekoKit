# Cateye 图片识别工具 - 智能体使用指南

NekoKit 提供了 5 个图片识别工具，统称为 **cateye** 工具集。本指南帮助你选择和组合这些工具。

---

## 工具概览

| 工具 | 名称 | 类型 | 用途 |
|------|------|------|------|
| OCR | `cateye_ocr` | 核心 | 从图片中提取文字 |
| 以图搜图 | `cateye_search` | 核心 | 多供应商反向图片搜索 |
| 视觉理解 | `cateye_vision` | 核心 | 多模态大模型图片理解 |
| 预处理 | `cateye_preprocess` | 辅助 | 按任务类型优化图片尺寸和格式 |
| 缓存 | `cateye_cache` | 辅助 | 检查/存储缓存结果，避免重复 API 调用 |

---

## 工具参数

### cateye_ocr

使用 EasyOCR 从图片中提取文字。

```json
{
  "name": "cateye_ocr",
  "parameters": {
    "type": "object",
    "properties": {
      "image_url": { "type": "string", "description": "图片 URL 或本地文件路径" },
      "languages": { "type": "array", "items": { "type": "string" }, "description": "OCR 识别语言，如 ['ch_sim','en']。默认：简体中文 + 英文" }
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

---

## 最佳实践场景

### 场景一：提取图片中的文字

**用户说：** "帮我把这张图里的文字提取出来"

直接使用 `cateye_ocr`，无需其他工具。

```
cateye_ocr(image_url="...")
```

### 场景二：识别角色或人物

**用户说：** "这是谁？" / "这个角色是谁？"

组合使用 `cateye_search` + `cateye_vision`：

1. `cateye_search(image_url="...", scene="auto")` — 查找匹配来源
2. `cateye_vision(image_url="...", prompt="详细描述这个角色的外观", mode="daily")` — 获取视觉描述
3. 综合两个结果给出完整回答

### 场景三：查找番剧截图出处

**用户说：** "这是哪部番的？"

使用 `cateye_search` 的 anime 场景：

```
cateye_search(image_url="...", scene="anime")
```

### 场景四：理解表情包或颜文字

**用户说：** "这个表情包什么意思？"

使用 `cateye_vision` 的 daily 模式：

```
cateye_vision(image_url="...", prompt="解释这个表情包/颜文字的含义", mode="daily")
```

### 场景五：分析复杂图表或解题

**用户说：** "帮我分析这个图表" / "这道题怎么做？"

使用 `cateye_vision` 的 professional 模式：

```
cateye_vision(image_url="...", prompt="详细分析这个图表", mode="professional")
```

**注意：** 专业模式消耗更多 token，仅在真正复杂的任务时使用。

### 场景六：没有明确指令，通用图片

**用户说：** "看看这张图" / "这是什么？"

组合所有核心工具进行全面分析：

1. `cateye_ocr(image_url="...")` — 检查是否有文字
2. `cateye_search(image_url="...", scene="auto")` — 查找相似图片
3. `cateye_vision(image_url="...", prompt="全面描述这张图片", mode="daily")` — 获取 AI 理解

---

## 上下文感知

### 同一图片的后续提问

当用户对之前分享的图片提出后续问题时，你**不需要**重新运行所有工具。利用对话历史回忆之前的分析结果。

**示例流程：**
1. 用户发送图片 → 你运行 `cateye_vision` → 描述图片
2. 用户问"里面有什么文字？" → 你运行 `cateye_ocr` 处理同一张图
3. 用户问"能找到出处吗？" → 你运行 `cateye_search` 处理同一张图

### 多图片关联

当用户发送多张图片进行比较或关联时：
- 对每张图片独立运行工具
- 在回复中综合分析结果
- 如需比较，可使用 `cateye_vision` 并在 prompt 中引用两张图片

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
| "easyocr is not installed" | 缺少依赖 | 提示用户安装 easyocr |
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

## 工具组合总结

| 用户意图 | 主要工具 | 辅助工具 | 备注 |
|----------|----------|----------|------|
| 提取文字 | `cateye_ocr` | — | 直接使用 |
| 识别角色/人物 | `cateye_search` | `cateye_vision` | 组合使用效果最佳 |
| 查找番剧出处 | `cateye_search` (anime) | — | trace.moe 最准确 |
| 查找插画出处 | `cateye_search` (moe) | — | SauceNAO 最适合二次元 |
| 理解表情包 | `cateye_vision` (daily) | — | 快速高效 |
| 分析图表/解题 | `cateye_vision` (professional) | — | 谨慎使用 |
| 通用"这是什么" | `cateye_ocr` + `cateye_search` + `cateye_vision` | — | 全面分析 |
| 同一图片后续提问 | 使用对话历史 | 仅在需要新工具时调用 | 避免重复调用 |

---

> 📖 设计文档：[Cateye 图片识别工具集设计](../design/cateye.md)
