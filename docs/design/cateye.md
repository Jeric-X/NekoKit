# CatEye 图片识别工具集设计文档

## 设计理念

### 第一原则：轻与重结合

90% 的日常场景通过预设方案直接完成；10% 的复杂场景，智能体可自行组合原子工具应对。

### 第二原则：工具内聚，边界清晰

CatEye 的 Prompt 指令、工具描述与操作逻辑完全封装在工具箱内部，调用时由工具自身注入，不写入智能体的全局系统上下文。

### 第三原则：融入记忆生态

缓存条目可由记忆模块直接管理，分析结果可纳入已有记忆系统。

### 第四原则：DAG 驱动复杂任务

复杂任务通过类 DAG（有向无环图）描述工具链路，执行后链路与结果一并存入缓存，为后续调用提供参考。

---

## 实现方式

缓存存储基于 NekoKit 的 kv_store 工具，场景预设硬编码在初始化模块中，工具类继承 BaseTool 并通过注册表注册。

### 工具清单

| 工具 | 类型 | 职责边界 |
|------|------|---------|
| `cateye_ocr` | 核心 | 文字提取，只负责把图中的文字读出来 |
| `cateye_search` | 核心 | 以图搜图，只负责找到图片的来源或相似图 |
| `cateye_vision` | 核心 | 视觉理解，只负责用大模型解读图片内容 |
| `cateye_preprocess` | 辅助 | 图片预处理，按任务类型优化尺寸和格式 |
| `cateye_cache` | 辅助 | 缓存管理，内部调用 kv_store 管理图片分析缓存 |

核心工具专注于识别逻辑，不内置缓存和预处理。辅助工具由智能体根据场景预设方案按需调用。

---

## 缓存管理

缓存 Key 基于图片哈希值生成（`cat_eye:cache:{image_hash}`），Value 存储分析结果、工具链路、场景上下文和任务评价。生命周期 48 小时，超期可清除。缓存条目可被记忆模块管理。

### Value 结构

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

### 操作

`cateye_cache` 提供三种操作：

- `check`：查询缓存，自动检查过期，命中返回完整条目
- `store`：写入新缓存条目，自动计算图片哈希，设置 48 小时过期
- `update`：合并新结果到已有条目，刷新过期时间，写入评价

---

## 场景预设

场景预设通过 `cateye_scene` 工具管理，内置 3 个预设硬编码在 `BUILTIN_PRESETS` 字典中，自定义预设通过 kv_store 存储（Key: `cat_eye:scene:{scene_name}`）。

### 内置预设

| 编码 | 名称 | 工具链路 | 触发关键词 |
|------|------|---------|-----------|
| `general_ocr` | 纯文字提取 | preprocess → ocr | 提取文字、OCR、识别文字 |
| `identify_subject` | 物体/人物识别 | preprocess → search → preprocess → vision | 这是谁、识别、认出 |
| `general_vision` | 综合理解 | preprocess → ocr → preprocess → search → preprocess → vision | 看看这是什么、描述一下 |

### 预设 Value 结构

```json
{
  "name": "general_ocr",
  "description": "适用于纯文字提取场景",
  "tool_chain": ["cateye_preprocess", "cateye_ocr"],
  "model_preference": "daily",
  "trigger_keywords": ["提取文字", "OCR", "识别文字"],
  "is_preset": true
}
```

内置预设不可被 `is_preset=true` 的数据覆盖。智能体可通过 `update` 操作添加自定义预设。

---

## 具体原理

### 图片缓存去重

MD5 一级索引 + dHash（hash_size=8，阈值≤5）二级相似匹配。

### 图片分场景预处理

OCR 模式输出 PNG 无损；搜图/大模型模式缩放至 1568px JPEG。

### 搜图供应商路由

根据场景自动选择免费供应商（华为云通用、trace.moe 番剧、SauceNAO 插画），API Key 从插件配置的 `cateye_search` 分组注入。支持用户通过 `custom_providers` JSON 编辑器添加自定义供应商。

### 大模型 Prompt 注入

调用 cateye_vision 时动态注入场景描述、工具链路与蒸馏后的上下文摘要，作用域仅限本次调用。

### 上下文蒸馏

智能体从会话历史中提取关键词和意图，压缩后传入视觉模型。

### 评价闭环

每次任务结束后，智能体评估效果（-2 到 2），写入缓存条目。

---

## 核心工具设计

### OCR（cateye_ocr）

引擎：RapidOCR（基于 ONNX Runtime）。无需 GPU，默认模型支持中英文，通过 `text_score` 配置项控制识别精度。同步调用委托给线程池，引擎实例懒加载并缓存。

### 搜图（cateye_search）

供应商信息由内置常量 `BUILTIN_PROVIDERS` 和运行时动态合并的自定义供应商组成。`initialize` 时调用 `_merge_custom_providers` 解析用户配置的 `custom_providers` JSON 数组，合并到 `_providers` 实例字典中。`BUILTIN_SCENE_MAP` 定义内置场景映射，自定义供应商的 `scene` 字段触发新场景注册。

每个供应商的 API 调用逻辑封装在独立的 `_call_xxx` 方法中，自定义供应商通过通用 `_call_custom` 方法处理（支持 GET/POST、form/json 请求格式、binary/base64 图片编码、嵌套 JSON 路径字段注入、`{api_key}` 占位符替换）。所有供应商调用失败时返回空结果，由 AI 尝试其他工具降级。

### 视觉理解（cateye_vision）

双模式设计：`daily` 模式用于日常场景，`professional` 模式用于复杂分析。模型选择由配置驱动，`professional_model` 留空时自动降级为 `daily_model`。支持上下文注入参数（`scene_name`、`scene_description`、`tool_chain_dag`、`user_intent_keywords`、`distilled_context`、`cached_results`），动态构建增强系统 Prompt。

---

## 扩展性

### 新增搜图供应商

内置供应商在 `BUILTIN_PROVIDERS` 字典中添加信息，在 `BUILTIN_SCENE_MAP` 中添加场景映射，实现 `_call_xxx` 方法，在 `_call_provider` 中添加分发分支。
自定义供应商无需修改代码，用户直接在 WebUI 配置页的 `custom_providers` JSON 编辑器中添加即可。配置项遵循 `CUSTOM_PROVIDER_SPEC` 定义的接口规范，通过通用 `_call_custom` 方法自动处理。

### 新增视觉理解模式

在 `VisionTool._build_system_prompt` 中添加新的模式分支，在参数定义的 `enum` 中添加新模式名称，在配置 Schema 中添加对应的模型配置项。

### 新增图片理解能力

在 `tools/image_analyzer/` 下创建新的工具模块，继承 `BaseTool` 实现业务逻辑，在 `__init__.py` 中导出，在 `main.py` 中创建对应的 FunctionTool 子类并注册。

### 新增场景预设

通过 `cateye_scene(action="update")` 动态添加，或修改 `scene_preset_tool.py` 中的 `BUILTIN_PRESETS` 字典添加内置预设。

---

## 未来任务

- **记忆模块 API 规范**：定义缓存与记忆模块之间的通用接口，实现缓存条目到长期记忆的标准化流转。
- **天使之魂插件适配**：完成与天使之魂记忆体系的集成，使 CatEye 缓存可被其直接索引和调用。
- **内部评价体系**：在工具箱内部建立简易的评价统计功能，基于历史评价数据为智能体提供工具组合偏好参考。
- **场景预设自动推荐**：根据历史任务的评价数据和场景匹配度，自动向智能体推荐最优场景预设。
- **工具链自动优化**：分析缓存中存储的历史 DAG 链路和执行结果，自动精简低效节点，生成优化后的链路建议。
- **跨图片关联分析**：支持多张图片的缓存条目关联检索，实现序列图片的对比分析。
- **日志压缩实现**：完成预留的 compress_logs 接口，实现插件日志的自动压缩归档。
