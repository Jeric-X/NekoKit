# Changelog

## 0.0.5 (2026-05-20)

### ✨ 新增
- 自定义搜图供应商：支持用户在 WebUI 中通过 JSON 配置自定义搜图服务商，定义统一的供应商接口规范（URL 模板、请求格式、响应解析、字段映射）
- 网络代理配置功能：`proxy_auth` 认证子分组、`proxy_rules` 规则子分组
- 搜图供应商嵌套 UI：trace.moe / SauceNAO / 华为云各自独立为 `object` 类型，内部包含 enabled / api_key / project_id 子字段
- 缓存管理重构：`cateye_cache` 内部调用 kv_store 管理缓存，缓存条目包含工具链路 DAG、分析结果、场景上下文和任务评价
- 场景预设重构：`cateye_scene` 内部调用 kv_store 管理场景预设，内置 3 个预设（general_ocr、identify_subject、general_vision）
- 视觉理解上下文注入：`cateye_vision` 新增 6 个上下文参数，动态构建增强系统 Prompt
- 缓存条目 Value 结构：tool_chain（DAG + 节点列表）、result、context、evaluation、48h 过期时间

### 🔄 变更
- 配置 UI 重构：`ai_isolation` / `session_scope` 归入 `kv_store` 分组，`image_*` 统一为 `cateye_*` 前缀
- 搜图供应商配置从扁平结构改为嵌套结构：`{provider}_enabled` / `{provider}_api_key` → `{provider}.enabled` / `{provider}.api_key`
- 代理认证配置从扁平字段改为 `proxy_auth` 子分组（username / password）
- 代理规则配置归入 `proxy_rules` 子分组（custom_rules / custom_rules_url）
- 移除 `image_cache` 配置节（缓存管理已迁移至 kv_store）
- `PROVIDERS` 重命名为 `BUILTIN_PROVIDERS`，`SCENE_PROVIDER_MAP` 重命名为 `BUILTIN_SCENE_MAP`
- OCR 引擎从 EasyOCR 替换为 RapidOCR（基于 ONNX Runtime，无需 GPU，默认支持中英文）
- 核心工具（OCR/搜图/视觉理解）移除内置缓存和预处理调用，与辅助工具完全解耦
- 缓存汉明距离计算从字符级改为比特级（XOR + 统计比特位），修正距离度量
- OCR 配置项从 `languages`（语言列表）改为 `text_score`（置信度阈值）

### 🐛 修复
- 修复缓存系统全局污染 BUG：空 dHash 导致所有图片互相匹配（返回 999999 距离值）
- 修复缓存系统全局污染 BUG：字符级汉明距离导致不同图片被误判为相似

---

## 0.0.4 (2026-05-20)

### ✨ 新增
- 新增 Cateye 图片识别工具集（OCR、以图搜图、大模型视觉理解、图片预处理、图片缓存）
- 新增智能体工具使用指南（cateye.md）
- 新增工具集设计文档（docs/design/）
- 新增图片识别配置项（通用/OCR/搜图/大模型/缓存五个分组）

### 🔄 变更
- KV 存储工具重构为子包结构（tools/kv_store/），与 Cateye 工具集结构一致
- 所有代码注释和文档统一为中文

---

## 0.0.3 (2026-05-17)

### ✨ 新增
- 将 kv_store 单工具拆分为 4 个独立工具：`get_kv`、`set_kv`、`delete_kv`、`list_kv`
- 新增插件配置 Schema（`_conf_schema.json`），AI 隔离与会话隔离可通过 WebUI 管理
- 新增 Git Tag `v0.0.3`，支持 AstrBot 自动更新

### 🔄 变更
- AI 隔离和会话隔离从 AI 可调参数改为管理员 WebUI 配置
- 存储后端统一使用 SQLite，移除 JSON 文件存储选项
- 插件元数据 `metadata.yaml` 添加 `repo` 字段

### 🐛 修复
- 修复 `Main.__init__` 缺少 `config` 参数导致只有 1 个工具注册的问题
- 修复导入错误 `No module named 'tools'`（改为相对导入）
- 修复 `FunctionTool` 缺少 `@dataclass` 装饰器导致的 pydantic 验证错误
- 修复 `tools/__init__.py` 导入已删除的 `JSONStorageBackend` 问题

### 📖 文档
- 重写 README.md，面向用户提供功能概览
- 重写工具指南，面向 AI 提供详细调用说明
- 新增 ARCHITECTURE.md，面向开发者说明目录架构

---

## 0.0.2 (2026-05-17)

### ✨ 新增
- 支持 SQLite 和 JSON 双存储后端

### 🔄 变更
- 移除废弃的 `@register` 装饰器，使用 `Star` 类自动注册

### 🐛 修复
- 修复插件名显示为 `neko_kit` 而非 `nekokit` 的问题
- 修复打包脚本误匹配 `astrbot_version` 字段的问题

---

## 0.0.1 (2026-05-17)

### ✨ 初始版本
- 基础 KV 存储功能
- AI 隔离与会话隔离
- 单工具注册模式（`kv_store` + `action` 参数）
- JSON 文件存储后端
