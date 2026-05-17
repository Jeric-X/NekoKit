# KV Store 工具使用指南 🐱

（此为汇总文档，详细内容请参考 [src/neko_kit/tools/kv_store/agent_guide.md](../../src/neko_kit/tools/kv_store/agent_guide.md)）

## 快速开始

```python
# 存储数据
await kv_store.execute(
    action="set",
    key="my_key",
    value="my_value"
)

# 读取数据
result = await kv_store.execute(action="get", key="my_key")
```

## 工具信息

- **名称**: kv_store
- **版本**: 0.0.1
- **描述**: 键值存储工具，支持 AI 隔离与会话隔离
