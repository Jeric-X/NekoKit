# KV Store 工具使用指南 🐱

## 快速开始

### 存储数据

```python
# 使用 set_kv 工具写入数据
await set_kv(key="my_key", value="my_value")

# 存储 JSON 数据
await set_kv(key="user_info", value='{"name": "Alice", "age": 18}')
```

### 读取数据

```python
# 使用 get_kv 工具读取数据
result = await get_kv(key="my_key")
# 返回: {"success": true, "data": {"key": "my_key", "value": "my_value"}}
```

### 删除数据

```python
# 使用 delete_kv 工具删除数据
result = await delete_kv(key="my_key")
# 返回: {"success": true, "message": "已删除喵~ 🗑️"}
```

### 列出所有键

```python
# 使用 list_kv 工具列出当前作用域下的所有键
result = await list_kv()
# 返回: {"success": true, "data": {"keys": ["my_key", "user_info"], ...}}
```

## 工具列表

插件注册了 **4 个独立工具**，AI 会根据需要自动选择调用：

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `get_kv` | 根据键名获取存储的值 | `key` |
| `set_kv` | 设置或更新键值对 | `key`, `value` |
| `delete_kv` | 根据键名删除存储的值 | `key` |
| `list_kv` | 列出当前作用域下的所有键 | 无 |

## 数据隔离说明

AI 隔离和会话隔离由管理员在 WebUI 中配置，AI 无法自行修改。

- **AI 隔离（默认开启）**：每个 AI 只能访问自己存储的数据
- **会话隔离（默认关闭）**：数据仅在当前会话内可见

## 数据存储

- 统一使用 **SQLite** 数据库存储
- 数据文件保存在 `data/nekokit/kvstore.db`

## 版本

0.0.3
