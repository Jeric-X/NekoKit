# NekoKit 🐱

AstrBot 插件工具仓库，为 AI 智能体提供开箱即用的实用工具。

## 快速安装

1. 在 AstrBot WebUI → 插件管理 → 上传插件 → 选择 `nekokit-0.0.3.zip`
2. 或从 Git 安装：`https://github.com/Inaiinaiba/NekoKit.git`
3. 启用插件后，前往 WebUI → 配置 → NekoKit 设置隔离选项

## 工具列表

| 工具 | 功能 | 文档 |
|------|------|------|
| `get_kv` | 根据键名读取存储的值 | [查看详情](docs/agent_guides/kv_store.md) |
| `set_kv` | 写入或更新键值对 | [查看详情](docs/agent_guides/kv_store.md) |
| `delete_kv` | 根据键名删除存储的值 | [查看详情](docs/agent_guides/kv_store.md) |
| `list_kv` | 列出当前作用域下的所有键 | [查看详情](docs/agent_guides/kv_store.md) |

> 以上工具由 AI 根据对话内容按需自动调用，无需手动操作。

## WebUI 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `ai_isolation` | 开关 | 开启 | 每个 AI 只能访问自己存储的数据 |
| `session_scope` | 开关 | 关闭 | 数据仅在当前会话内可见 |

## 系统要求

- AstrBot >= 4.16, < 5
- Python >= 3.10

## 版本

当前版本：**0.0.3** | [更新日志](CHANGELOG.md)

---

*面向开发者的架构文档：[ARCHITECTURE.md](ARCHITECTURE.md)*
