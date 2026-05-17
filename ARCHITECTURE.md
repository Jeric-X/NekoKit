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
│   └── agent_guides/
│       └── kv_store.md          # 工具使用指南（面向 AI）
└── tools/
    ├── __init__.py              # 统一导出
    ├── context.py               # 上下文工具（获取 AI ID、会话 ID）
    ├── kv_store.py              # KV 存储核心实现
    └── storage.py               # SQLite 存储后端
```

## 分层架构

```
┌─────────────────────────────────────────┐
│              FunctionTool 层             │  main.py
│   get_kv | set_kv | delete_kv | list_kv │
├─────────────────────────────────────────┤
│             KVStoreTool (BaseTool)       │  tools/kv_store.py
│    业务逻辑、命名空间策略、配置管理        │
├─────────────────────────────────────────┤
│            StorageBackend                │  tools/storage.py
│           SQLite 存储引擎                │
└─────────────────────────────────────────┘
```

### 各层职责

| 层次 | 文件 | 职责 |
|------|------|------|
| **FunctionTool** | `main.py` | 定义 4 个独立的 AstrBot FunctionTool，每个工具负责：参数校验、调用 KVStoreTool、结果转换 |
| **BaseTool** | `kv_store.py` | 实现 `KVStoreTool(BaseTool)`，包含核心业务逻辑：action 分发、命名空间构建、配置读取 |
| **StorageBackend** | `storage.py` | 实现 `SQLiteStorageBackend`，封装 SQLite 增删改查操作 |
| **Core 抽象** | `core.py` | 定义 `StorageBackend`、`NamespaceStrategy`、`BaseTool`、`ToolResult` 等抽象基类 |
| **Context** | `tools/context.py` | 从 AstrBot 运行时上下文提取 AI ID 和会话 ID |

## 核心类图

```
StorageBackend (ABC)        NamespaceStrategy (ABC)        BaseTool (ABC)
    └── SQLiteStorageBackend     └── DefaultNamespaceStrategy   └── KVStoreTool

FunctionTool (AstrBot)
    ├── KVGetTool      ──→  KVStoreTool.execute(action="get")
    ├── KVSetTool      ──→  KVStoreTool.execute(action="set")
    ├── KVDeleteTool   ──→  KVStoreTool.execute(action="delete")
    └── KVListTool     ──→  KVStoreTool.execute(action="list")
```

## 数据流

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

## 配置加载流程

```
AstrBot 启动
    │
    ├── 检测 _conf_schema.json → 生成 data/config/nekokit_config.json
    ├── 实例化 Main(context, config)
    │       │
    │       ├── 读取 config → ai_isolation / session_scope
    │       └── KVStoreTool.set_config()
    └── 注册工具至 AstrBot
```

## 扩展新工具

1. 在 `tools/` 下创建新模块，继承 `BaseTool` 实现业务逻辑
2. 在 `main.py` 中创建对应的 `FunctionTool` 子类
3. 在 `Main._register_tools()` 中添加注册

```python
# 示例：新增搜索工具
@dataclass
class SearchTool(FunctionTool[AstrAgentContext]):
    name: str = "search_kv"
    description: str = "搜索键名包含关键词的条目"
    parameters: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "搜索关键词"},
        },
        "required": ["keyword"],
    })
    # ... 实现 call 方法
```
