# KV Store 工具使用指南

NekoKit 插件提供 4 个独立的键值存储工具，用于持久化保存和读取数据。

---

## 工具列表

| 工具名 | 功能描述 |
|--------|----------|
| `nkit_kv_get` | 根据键名获取已存储的值 |
| `nkit_kv_set` | 存储或更新一个键值对 |
| `nkit_kv_delete` | 根据键名删除已存储的值 |
| `nkit_kv_list` | 列出当前作用域下的所有键名 |

---

## nkit_kv_get

根据键名读取已存储的值。

### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `key` | string | 是 | 要获取的键名 |

### 返回示例

```json
{
  "success": true,
  "data": {
    "key": "my_key",
    "value": "存储的数据内容"
  }
}
```

### 错误示例

```json
{
  "success": false,
  "message": "找不到键 'my_key'"
}
```

---

## nkit_kv_set

存储一个新的键值对，或更新已有的键值对。

### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `key` | string | 是 | 键名，用于唯一标识数据 |
| `value` | string | 是 | 值，支持任意 JSON 兼容的数据格式 |

### 说明

- 如果 `value` 是合法的 JSON 字符串（如 `{"name": "Alice"}` 或 `[1,2,3]`），会自动解析为结构化数据存储
- 如果 `value` 是普通字符串，则按原样存储
- 如果 `key` 已存在，会覆盖旧值

### 返回示例

```json
{
  "success": true,
  "data": {
    "key": "my_key",
    "scope": "AI 'provider:persona' 专属"
  }
}
```

---

## nkit_kv_delete

根据键名删除已存储的数据。

### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `key` | string | 是 | 要删除的键名 |

### 返回示例

```json
{
  "success": true,
  "data": {
    "key": "my_key"
  },
  "message": "已删除"
}
```

### 错误示例

```json
{
  "success": false,
  "message": "找不到键 'my_key'"
}
```

---

## nkit_kv_list

列出当前作用域下的所有键名。

### 参数

无参数。

### 返回示例

```json
{
  "success": true,
  "data": {
    "keys": ["key1", "key2", "key3"],
    "scope": "AI 'provider:persona' 专属"
  }
}
```

---

## 数据隔离说明

AI 隔离和会话隔离由**管理员在 WebUI 中配置**（位于 `KV 存储` 配置分组下），AI 工具调用时无法修改这些设置。

| 隔离模式 | 默认值 | 行为 |
|----------|--------|------|
| **AI 隔离** | 开启 | 每个 AI 只能访问自己存储的数据。不同 AI 之间数据完全隔离 |
| **会话隔离** | 关闭 | 开启后，数据仅在当前对话会话内可见。关闭时，同一 AI 的所有会话共享数据 |

## 数据存储

- 存储引擎：**SQLite**
- 数据文件位置：`data/nekokit/kvstore.db`
- 按 AI ID 和会话 ID 自动分区存储

---

> 设计文档：[KV 存储工具集设计](../design/kv_store.md)
