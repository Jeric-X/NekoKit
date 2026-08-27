from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass


HUMAN_AI_ID = "user"
"""特殊来源：人工 /nkit 命令写入的记录。所有 AI 均可读写，视为共享层。"""


@dataclass
class RecordScope:
    """数据访问作用域。

    每条记录写入时都会记录实际来源 ai_id / session_id 字段；
    读取时根据开关计算可见性，修改开关不需要迁移数据。
    ai_id 为 HUMAN_AI_ID 的记录（人工写入）对所有 AI 可见。
    private 记录无视共享开关，仅精确匹配来源 (ai_id, session_id) 时可见；
    管理员（is_admin）不受私有限制。
    """

    ai_id: str
    session_id: str
    ai_isolation: bool = True
    session_scope: bool = False
    is_admin: bool = False

    def matches(self, record: Dict[str, Any]) -> bool:
        """判断记录在当前开关组合下是否可见"""
        if record.get("private"):
            if self.is_admin:
                return True
            return (
                record.get("ai_id") == self.ai_id
                and record.get("session_id") == self.session_id
            )
        if self.ai_isolation and record.get("ai_id") not in (
            self.ai_id,
            HUMAN_AI_ID,
        ):
            return False
        if self.session_scope and record.get("session_id") != self.session_id:
            return False
        return True


class StorageBackend(ABC):
    """存储后端抽象基类，定义存储操作的统一接口"""

    @abstractmethod
    def get(self, key: str, scope: RecordScope) -> Optional[Any]:
        """获取键值，多条可见时返回最近更新的记录"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, scope: RecordScope, private: bool = False) -> None:
        """设置键值：更新可见记录（保留原来源字段），无可见记录则新建并记录当前来源。

        private=True 时仅命中/新建私有记录，不触碰其他可见记录。
        """
        pass

    @abstractmethod
    def delete(self, key: str, scope: RecordScope) -> bool:
        """删除可见记录，返回是否成功"""
        pass

    @abstractmethod
    def list_keys(self, scope: RecordScope) -> list:
        """列出可见记录的键（去重）"""
        pass

    @abstractmethod
    def list_records(self, scope: RecordScope) -> list:
        """列出可见记录（含 key 与来源字段，不去重），供管理员视角展示"""
        pass

    @abstractmethod
    def search(self, keyword: str, scope: RecordScope) -> list:
        """搜索键"""
        pass


@dataclass
class ToolResult:
    """工具执行结果封装"""

    success: bool
    message: str
    data: Any = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"success": self.success, "message": self.message}
        if self.data is not None:
            result["data"] = self.data
        return result


class BaseTool(ABC):
    """NekoKit 工具基类，所有工具必须继承此类"""

    @abstractmethod
    def get_name(self) -> str:
        """获取工具名称"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """获取工具描述"""
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """获取工具参数定义（JSON Schema 格式）"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具逻辑"""
        pass

    def initialize(self, **kwargs) -> None:
        """初始化工具（可选）"""
        pass


class ToolError(Exception):
    """工具基础异常类"""

    pass


class ValidationError(ToolError):
    """参数验证错误"""

    pass


class ExecutionError(ToolError):
    """执行错误"""

    pass
