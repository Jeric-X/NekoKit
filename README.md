# NekoKit 🐱

AstrBot 插件工具仓库，为 AI 智能体提供开箱即用的实用工具。

## 快速安装

1. 在 AstrBot WebUI → 插件管理 → 上传插件 → 选择 `nekokit-0.0.4.zip`
2. 或从 Git 安装：`https://github.com/Inaiinaiba/NekoKit.git`
3. 启用插件后，前往 WebUI → 配置 → NekoKit 设置隔离选项和图片识别选项

## 工具列表

### KV 存储

| 工具 | 功能 | 文档 |
|------|------|------|
| `get_kv` | 根据键名读取存储的值 | [查看详情](docs/agent_guides/kv_store.md) |
| `set_kv` | 写入或更新键值对 | [查看详情](docs/agent_guides/kv_store.md) |
| `delete_kv` | 根据键名删除存储的值 | [查看详情](docs/agent_guides/kv_store.md) |
| `list_kv` | 列出当前作用域下的所有键 | [查看详情](docs/agent_guides/kv_store.md) |

### Cateye 图片识别

| 工具 | 功能 | 文档 |
|------|------|------|
| `cateye_ocr` | 从图片中提取文字 | [查看详情](docs/agent_guides/cateye.md) |
| `cateye_search` | 多供应商反向图片搜索 | [查看详情](docs/agent_guides/cateye.md) |
| `cateye_vision` | 多模态大模型图片理解 | [查看详情](docs/agent_guides/cateye.md) |
| `cateye_preprocess` | 按任务类型优化图片尺寸和格式 | [查看详情](docs/agent_guides/cateye.md) |
| `cateye_cache` | 检查/存储缓存结果 | [查看详情](docs/agent_guides/cateye.md) |

> 以上工具由 AI 根据对话内容按需自动调用，无需手动操作。

## WebUI 配置项

### KV 存储

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `ai_isolation` | 开关 | 开启 | 每个 AI 只能访问自己存储的数据 |
| `session_scope` | 开关 | 关闭 | 数据仅在当前会话内可见 |

### 图片识别 - 通用

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `custom_prompt_enabled` | 开关 | 关闭 | 启用自定义工具使用说明 Prompt |
| `custom_prompt` | 文本 | — | 自定义工具使用说明 Prompt（仅在启用时生效） |
| `log_level` | 选择 | INFO | 日志级别 |

### 图片识别 - OCR

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `languages` | 列表 | ["ch_sim", "en"] | OCR 识别语言列表 |

### 图片识别 - 搜图

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `huawei_enabled` | 开关 | 关闭 | 启用华为云通用搜索 |
| `huawei_api_key` | 字符串 | — | 华为云 API Key |
| `huawei_project_id` | 字符串 | — | 华为云项目 ID |
| `tracemoe_enabled` | 开关 | 开启 | 启用 trace.moe 番剧识别 |
| `tracemoe_api_key` | 字符串 | — | trace.moe API Key（可选） |
| `saucenao_enabled` | 开关 | 开启 | 启用 SauceNAO 萌系/插画识别 |
| `saucenao_api_key` | 字符串 | — | SauceNAO API Key（推荐） |
| `custom_providers` | 文本 | — | 自定义供应商配置（JSON 格式） |

### 图片识别 - 大模型

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `daily_model` | 字符串 | — | 日常任务模型 Provider ID |
| `professional_model` | 字符串 | — | 专业任务模型 Provider ID（留空则使用日常模型） |

### 图片识别 - 缓存

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `cache_ttl_hours` | 浮点数 | 1.0 | 缓存有效期（小时） |
| `preprocess_enabled` | 开关 | 开启 | 启用图片预处理 |

## 系统要求

- AstrBot >= 4.16, < 5
- Python >= 3.10

## 版本

当前版本：**0.0.4** | [更新日志](CHANGELOG.md)

---

*面向开发者的架构文档：[ARCHITECTURE.md](ARCHITECTURE.md)*
