import json
from typing import Any, Dict, Optional

from astrbot.api import logger
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.astr_agent_context import AstrAgentContext

from ...core import (
    BaseTool,
    ToolResult,
    StorageBackend,
    RecordScope,
    HUMAN_AI_ID,
)
from .storage import create_storage_backend
from .context import resolve_identity


def describe_scope(
    ai_isolation: bool, session_scope: bool, ai_id: str, session_id: str
) -> str:
    """描述当前可见范围"""
    if ai_isolation and session_scope:
        return f"AI '{ai_id}' 的会话 '{session_id}' 内（含用户共享记录）"
    if ai_isolation:
        return f"AI '{ai_id}' 专属（含用户共享记录）"
    if session_scope:
        return f"会话 '{session_id}' 内（所有AI共享）"
    return "全局（所有AI共享）"


class KVStoreTool(BaseTool):
    """🐱 KV 存储工具 - 轻量级键值存储，支持 AI 隔离与会话隔离"""

    def __init__(self):
        self._storage: Optional[StorageBackend] = None
        self._context: Optional[ContextWrapper[AstrAgentContext]] = None
        self._config = {"ai_isolation": True, "session_scope": False}
        self._store_name = "kvstore"

    def initialize(
        self,
        data_dir: str,
        store_name: str = "kvstore",
        use_sqlite: bool = False,
    ) -> None:
        """初始化工具，默认使用 JSON 文件后端"""
        self._store_name = store_name
        self._storage = create_storage_backend(
            data_dir, use_sqlite=use_sqlite, store_name=store_name
        )
        logger.info(
            f"[KVStoreTool] 已初始化，数据目录: {data_dir}, 存储: {store_name}"
        )

    def set_config(self, config: Dict[str, Any]) -> None:
        """设置配置"""
        self._config.update(config)
        logger.info(f"[KVStoreTool] 配置已更新: {self._config}")

    def get_name(self) -> str:
        return "kv_store"

    def get_description(self) -> str:
        return (
            "键值存储工具，用于持久化保存和读取数据。默认开启 AI 隔离，"
            "每个 AI 只能访问自己存储的数据。支持会话隔离模式。"
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型：get(读取)、set(写入)、delete(删除)、list(列出键)、search(搜索)",
                    "enum": ["get", "set", "delete", "list", "search"],
                },
                "key": {
                    "type": "string",
                    "description": "键名，用于唯一标识数据（get、set、delete、search 操作需要）",
                },
                "value": {
                    "type": "string",
                    "description": "值（set 操作需要），任意字符串内容",
                },
                "prefix": {
                    "type": "string",
                    "description": "键名前缀（list 操作可选），用于只列出匹配前缀的键",
                },
                "private": {
                    "type": "boolean",
                    "description": (
                        "（set 操作可选）是否为私有记录：仅写入时的 AI 在写入会话内可见，"
                        "即使开启 AI 共享/会话共享也不会暴露给其他 AI 或会话。"
                        "默认 false（普通记录）。"
                    ),
                    "default": False,
                },
            },
            "required": ["action"],
        }

    def set_context(self, context: ContextWrapper[AstrAgentContext]) -> None:
        """设置当前执行上下文"""
        self._context = context

    async def execute(self, **kwargs) -> ToolResult:
        """LLM 工具调用入口：按配置的隔离开关访问"""
        return await self._run(kwargs, admin=False)

    async def execute_admin(self, **kwargs) -> ToolResult:
        """人工命令入口：管理员视角，忽略 AI 隔离（可见所有 AI 的记录），
        新写入的记录盖 user 来源，所有 AI 可读写"""
        return await self._run(kwargs, admin=True)

    async def _run(self, kwargs: Dict, admin: bool = False) -> ToolResult:
        """执行工具逻辑"""
        if not self._storage:
            return ToolResult(success=False, message="KVStore 未初始化")

        action = kwargs.get("action", "")
        if not action:
            return ToolResult(success=False, message="必须指定操作类型")

        ai_id, session_id = await resolve_identity(self._context)

        ai_isolation = self._config.get("ai_isolation", True)
        if admin:
            ai_isolation = False
            ai_id = HUMAN_AI_ID
        session_scope = self._config.get("session_scope", False)

        scope = RecordScope(
            ai_id=ai_id,
            session_id=session_id,
            ai_isolation=ai_isolation,
            session_scope=session_scope,
            is_admin=admin,
        )

        return await self._handle_action(action, kwargs, scope)

    async def _handle_action(
        self, action: str, kwargs: Dict, scope: RecordScope
    ) -> ToolResult:
        if action == "get":
            return self._handle_get(kwargs, scope)
        elif action == "set":
            return self._handle_set(kwargs, scope)
        elif action == "delete":
            return self._handle_delete(kwargs, scope)
        elif action == "list":
            return self._handle_list(kwargs, scope)
        elif action == "search":
            return self._handle_search(kwargs, scope)
        else:
            return ToolResult(
                success=False,
                message=f"未知操作: {action}，支持的操作: get、set、delete、list、search",
            )

    def _handle_get(self, kwargs: Dict, scope: RecordScope) -> ToolResult:
        key = kwargs.get("key", "")
        if not key:
            return ToolResult(success=False, message="获取数据需要提供键名")

        value = self._storage.get(key, scope)
        if value is None:
            return ToolResult(success=False, message=f"喵~ 找不到键 '{key}'")

        return ToolResult(
            success=True,
            message="找到了哦 😸",
            data={"key": key, "value": self._stringify_value(value)},
        )

    def _handle_set(self, kwargs: Dict, scope: RecordScope) -> ToolResult:
        key = kwargs.get("key", "")
        if not key:
            return ToolResult(success=False, message="设置数据需要提供键名")

        value = kwargs.get("value")
        if value is None:
            return ToolResult(success=False, message="设置数据需要提供值")

        private = bool(kwargs.get("private", False))
        self._storage.set(key, str(value), scope, private=private)

        scope_desc = describe_scope(
            scope.ai_isolation, scope.session_scope, scope.ai_id, scope.session_id
        )
        if private:
            return ToolResult(
                success=True,
                message="✅ 已保存为私有记录，仅本 AI 在当前会话可见喵~ 😺",
                data={"key": key, "private": True},
            )

        return ToolResult(
            success=True,
            message=f"✅ 已保存到 {scope_desc} 喵~ 😺",
            data={"key": key, "scope": scope_desc},
        )

    def _handle_delete(self, kwargs: Dict, scope: RecordScope) -> ToolResult:
        key = kwargs.get("key", "")
        if not key:
            return ToolResult(success=False, message="删除数据需要提供键名")

        success = self._storage.delete(key, scope)
        if success:
            return ToolResult(success=True, message="已删除喵~ 🗑️", data={"key": key})

        return ToolResult(success=False, message=f"找不到键 '{key}' 喵~ 😿")

    def _handle_list(self, kwargs: Dict, scope: RecordScope) -> ToolResult:
        prefix = str(kwargs.get("prefix") or "").strip()
        scope_desc = describe_scope(
            scope.ai_isolation, scope.session_scope, scope.ai_id, scope.session_id
        )

        # 返回所有符合的记录（含来源标注）；keys 为去重键名，供内部工具兼容使用
        records = self._storage.list_records(scope)
        if prefix:
            records = [
                r for r in records if str(r.get("key", "")).startswith(prefix)
            ]
        keys = sorted({str(r.get("key")) for r in records})

        data: Dict[str, Any] = {
            "keys": keys,
            "records": records,
            "scope": scope_desc,
        }
        if prefix:
            data["prefix"] = prefix

        if not records:
            if prefix:
                return ToolResult(
                    success=True,
                    message=f"{scope_desc} 没有匹配前缀 '{prefix}' 的记录喵~ 📦",
                    data=data,
                )
            return ToolResult(
                success=True,
                message=f"{scope_desc} 还没有存储任何数据喵~ 📦",
                data=data,
            )

        if prefix:
            return ToolResult(
                success=True,
                message=f"找到 {len(records)} 条匹配前缀 '{prefix}' 的记录喵~ 📋",
                data=data,
            )

        return ToolResult(
            success=True,
            message=f"找到 {len(records)} 条记录喵~ 📋",
            data=data,
        )

    def _handle_search(self, kwargs: Dict, scope: RecordScope) -> ToolResult:
        key = kwargs.get("key", "")
        if not key:
            return ToolResult(success=False, message="搜索需要提供关键词")

        results = self._storage.search(key, scope)
        if not results:
            return ToolResult(
                success=True,
                message=f"没有找到包含 '{key}' 的数据喵~ 🔍",
                data={"keyword": key, "results": []},
            )

        return ToolResult(
            success=True,
            message=f"找到 {len(results)} 条相关记录喵~ ✨",
            data={
                "keyword": key,
                "results": [
                    {**item, "value": self._stringify_value(item.get("value"))}
                    for item in results
                ],
            },
        )

    @staticmethod
    def _stringify_value(value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)
