# NekoKit 🐱

AstrBot 插件工具仓库，为 AI 智能体提供各种实用工具。

## 特性

- 🧩 **模块化工具**：每个功能独立注册，AI 按需调用
- 🔒 **AI 隔离**：每个 AI 只能访问自己存储的数据（可在 WebUI 配置开关）
- 🗂️ **会话隔离**：可选限制数据仅在当前会话内可见（可在 WebUI 配置开关）
- 🗄️ **统一 SQLite 存储**：持久化存储，无需额外配置
- 😸 **猫系风格**：轻松有趣的交互体验

## 安装

1. 在 AstrBot WebUI → 插件管理中上传 `nekokit-0.0.3.zip`
2. 或从 Git 安装：`https://github.com/Inaiinaiba/NekoKit.git`
3. 启用插件后在 WebUI → 配置中设置 AI 隔离/会话隔离选项

## 架构概览

```
nekokit/
├── _conf_schema.json            # 插件配置 Schema（WebUI 可编辑）
├── core.py                      # 核心抽象层（BaseTool, ToolResult 等）
├── main.py                      # AstrBot 插件入口 + FunctionTool 定义
├── metadata.yaml                # 插件元数据
├── tools/
│   ├── __init__.py              # 统一导出
│   ├── context.py               # 上下文工具
│   ├── kv_store.py              # KV 存储核心实现
│   └── storage.py               # SQLite 存储后端
└── README.md
```

## 工具列表

插件注册了 **4 个独立工具**，AI 会根据需要自动选择调用：

### 1. `get_kv` — 获取键值

根据键名读取已存储的数据。

| 参数 | 类型 | 说明 |
|------|------|------|
| `key` | string | 要获取的键名 |

### 2. `set_kv` — 设置键值

写入或更新一个键值对。

| 参数 | 类型 | 说明 |
|------|------|------|
| `key` | string | 键名 |
| `value` | string | 值，支持任意 JSON 兼容数据 |

### 3. `delete_kv` — 删除键值

根据键名删除已存储的数据。

| 参数 | 类型 | 说明 |
|------|------|------|
| `key` | string | 要删除的键名 |

### 4. `list_kv` — 列出所有键

列出当前作用域下的所有键名，无需参数。

## 配置

在 AstrBot WebUI → 插件配置中可修改以下选项（需要重载插件后生效）：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `ai_isolation` | bool | true | 启用后，每个 AI 只能访问自己存储的数据 |
| `session_scope` | bool | false | 启用后，数据仅在当前会话内可见 |

> 这些配置由管理员在 WebUI 中设置，AI 无法自行修改。

## 数据存储

- 统一使用 **SQLite** 数据库存储
- 数据文件保存在 `data/nekokit/kvstore.db`
- 按命名空间（AI 隔离/会话隔离）自动分区

## 扩展新工具

1. 继承 `nekokit.core.BaseTool` 实现业务逻辑
2. 在 `main.py` 中创建对应的 `FunctionTool` 子类
3. 在 `Main._register_tools()` 中注册

## 版本

0.0.3
