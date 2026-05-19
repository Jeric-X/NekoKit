# NekoKit 架构说明

## 目录结构

```
nekokit/
├── _conf_schema.json            # 插件配置 Schema，用于 WebUI 可视化配置
├── CHANGELOG.md                 # 版本更新日志
├── README.md                    # 用户使用文档
├── ARCHITECTURE.md              # 本文件 — 开发者架构文档
├── metadata.yaml                # 插件元数据（名称、版本、仓库等）
├── main.py                      # AstrBot 插件入口 + FunctionTool 注册
├── core.py                      # 核心抽象层
├── __init__.py                  # 包标识
├── requirements.txt             # 依赖
├── docs/
│   ├── agent_guides/
│   │   ├── kv_store.md          # KV 存储工具使用指南（面向 AI）
│   │   └── cateye.md            # 图片识别工具使用指南（面向 AI）
│   └── design/
│       ├── kv_store.md          # KV 存储工具集设计文档
│       └── cateye.md            # Cateye 图片识别工具集设计文档
└── tools/
    ├── __init__.py              # 统一导出
    ├── kv_store/                # KV 存储子包
    │   ├── __init__.py          # 子包导出
    │   ├── context.py           # 上下文工具（获取 AI ID、会话 ID）
    │   ├── kv_store_tool.py     # KV 存储核心实现
    │   └── storage.py           # SQLite 存储后端
    └── image_analyzer/          # Cateye 图片识别子包
        ├── __init__.py          # 子包导出
        ├── _internal.py         # 内部共享工具（缓存、下载、预处理、哈希）
        ├── ocr_tool.py          # OCR 工具
        ├── image_search_tool.py # 以图搜图工具
        ├── vision_tool.py       # 视觉理解工具
        ├── preprocess_tool.py   # 预处理工具
        └── cache_tool.py        # 缓存工具
```

## 分层架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                         FunctionTool 层                              │  main.py
│  get_kv | set_kv | delete_kv | list_kv                              │
│  cateye_ocr | cateye_search | cateye_vision | cateye_preprocess     │
│  | cateye_cache                                                     │
├──────────────────────────────┬───────────────────────────────────────┤
│     KVStoreTool (BaseTool)   │     Cateye 工具集 (BaseTool)          │
│  业务逻辑、命名空间策略、     │  OCRTool | ImageSearchTool            │
│  配置管理                    │  VisionTool | PreprocessTool          │
│                              │  CacheTool                            │
│                              │  共享 ImageCache + _internal          │
├──────────────────────────────┼───────────────────────────────────────┤
│      StorageBackend          │           外部服务                     │
│     SQLite 存储引擎          │  EasyOCR | trace.moe | SauceNAO       │
│                              │  华为云 | AstrBot LLM                 │
└──────────────────────────────┴───────────────────────────────────────┘
```

### 各层职责

| 层次 | 文件 | 职责 |
|------|------|------|
| **FunctionTool** | `main.py` | 定义 9 个独立的 AstrBot FunctionTool，每个工具负责：参数校验、调用 BaseTool、结果转换 |
| **BaseTool - KV** | `tools/kv_store/kv_store_tool.py` | 实现 `KVStoreTool(BaseTool)`，包含核心业务逻辑：action 分发、命名空间构建、配置读取 |
| **BaseTool - OCR** | `tools/image_analyzer/ocr_tool.py` | 实现 `OCRTool(BaseTool)`，EasyOCR 文字识别 + 线程池异步 + 缓存 |
| **BaseTool - 搜图** | `tools/image_analyzer/image_search_tool.py` | 实现 `ImageSearchTool(BaseTool)`，多供应商搜图 + 场景自动选择 |
| **BaseTool - 视觉** | `tools/image_analyzer/vision_tool.py` | 实现 `VisionTool(BaseTool)`，双模式大模型视觉理解 |
| **BaseTool - 预处理** | `tools/image_analyzer/preprocess_tool.py` | 实现 `PreprocessTool(BaseTool)`，按任务类型预设参数表优化图片 |
| **BaseTool - 缓存** | `tools/image_analyzer/cache_tool.py` | 实现 `CacheTool(BaseTool)`，缓存查询与存储 |
| **StorageBackend** | `tools/kv_store/storage.py` | 实现 `SQLiteStorageBackend`，封装 SQLite 增删改查操作 |
| **Core 抽象** | `core.py` | 定义 `StorageBackend`、`NamespaceStrategy`、`BaseTool`、`ToolResult` 等抽象基类 |
| **Context** | `tools/kv_store/context.py` | 从 AstrBot 运行时上下文提取 AI ID 和会话 ID |
| **Internal** | `tools/image_analyzer/_internal.py` | 图片下载、预处理、哈希计算、缓存引擎、Base64 编码等共享工具 |

## 核心类图

```
StorageBackend (ABC)        NamespaceStrategy (ABC)        BaseTool (ABC)
    └── SQLiteStorageBackend     └── DefaultNamespaceStrategy   ├── KVStoreTool
                                                               ├── OCRTool
                                                               ├── ImageSearchTool
                                                               ├── VisionTool
                                                               ├── PreprocessTool
                                                               └── CacheTool

ImageCache                                                    ToolResult
  ├── MD5 精确匹配                                             ├── success
  ├── dHash 相似图检测                                          ├── message
  ├── TTL 过期机制                                              └── data
  └── 汉明距离阈值

FunctionTool (AstrBot)
    ├── KVGetTool      ──→  KVStoreTool.execute(action="get")
    ├── KVSetTool      ──→  KVStoreTool.execute(action="set")
    ├── KVDeleteTool   ──→  KVStoreTool.execute(action="delete")
    ├── KVListTool     ──→  KVStoreTool.execute(action="list")
    ├── CateyeOCRTool      ──→  OCRTool.execute()
    ├── CateyeSearchTool   ──→  ImageSearchTool.execute()
    ├── CateyeVisionTool   ──→  VisionTool.execute()
    ├── CateyePreprocessTool ──→  PreprocessTool.execute()
    └── CateyeCacheTool    ──→  CacheTool.execute()
```

## 数据流

### KV 存储数据流

```
AI 调用 (get_kv/set_kv/delete_kv/list_kv)
        │
        ▼
FunctionTool.call(context, **kwargs)
        │
        ▼
KVStoreTool.set_context(context)
KVStoreTool.execute(action=..., **kwargs)
        │
        ├── 1. 从 context 提取 ai_id, session_id
        ├── 2. 从 config 读取 ai_isolation, session_scope
        ├── 3. 构建 namespace
        └── 4. 调用 SQLiteStorageBackend 执行操作
                │
                ▼
        SQLite (data/nekokit/kvstore.db)
```

### Cateye 图片识别数据流

```
AI 调用 (cateye_ocr/cateye_search/cateye_vision)
        │
        ▼
FunctionTool.call(context, **kwargs)
        │
        ▼
BaseTool.execute(**kwargs)
        │
        ├── 1. 下载图片（URL/本地路径/Base64）
        ├── 2. 计算图片哈希（MD5 + dHash）
        ├── 3. 查询缓存（命中则直接返回）
        ├── 4. 预处理图片（按任务类型优化）
        ├── 5. 执行核心逻辑（OCR/搜图/视觉理解）
        └── 6. 存储缓存结果
                │
                ▼
        外部服务（EasyOCR / trace.moe / SauceNAO / 华为云 / AstrBot LLM）
```

## 配置加载流程

```
AstrBot 启动
    │
    ├── 检测 _conf_schema.json → 生成 data/config/nekokit_config.json
    ├── 实例化 Main(context, config)
    │       │
    │       ├── 读取 config → ai_isolation / session_scope
    │       ├── KVStoreTool.set_config()
    │       │
    │       ├── 构建 cateye_config（合并通用/OCR/搜图/大模型/缓存配置）
    │       ├── 初始化 ImageCache（设置 TTL）
    │       ├── 初始化 OCRTool（传入 config + cache）
    │       ├── 初始化 ImageSearchTool（传入 config + cache）
    │       ├── 初始化 VisionTool（传入 config + cache + star_context）
    │       ├── 初始化 PreprocessTool（传入 config）
    │       └── 初始化 CacheTool（传入 config + cache）
    └── 注册 9 个工具至 AstrBot
```

## 扩展新工具

NekoKit 采用子包模式组织工具集，每个工具集是一个独立的子包目录。

### 新增工具集

1. 在 `tools/` 下创建新的子包目录（如 `tools/new_toolset/`）
2. 在子包中创建 `__init__.py` 和工具模块，继承 `BaseTool` 实现业务逻辑
3. 如有内部共享逻辑，创建 `_internal.py` 模块
4. 在 `main.py` 中导入新工具，创建对应的 FunctionTool 子类
5. 在 `Main.__init__` 中初始化新工具
6. 在 `Main._register_tools()` 中添加注册
7. 在 `_conf_schema.json` 中添加配置项
8. 在 `docs/agent_guides/` 中添加 AI 使用指南
9. 在 `docs/design/` 中添加设计文档

### 子包结构模板

```
tools/new_toolset/
├── __init__.py          # 导出工具类
├── _internal.py         # 内部共享工具（可选）
├── tool_a.py            # 工具 A 实现
└── tool_b.py            # 工具 B 实现
```

### 新增搜图供应商

在 `ImageSearchTool` 中：
1. 在 `PROVIDERS` 字典中添加供应商信息
2. 在 `SCENE_PROVIDER_MAP` 中添加场景映射
3. 实现 `_call_xxx` 方法
4. 在 `_call_provider` 中添加分发分支
5. 在 `_conf_schema.json` 中添加供应商配置项
