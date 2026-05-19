from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass


class StorageBackend(ABC):
    """存储后端抽象基类，定义存储操作的统一接口"""

    @abstractmethod
    def get(self, key: str, namespace: Optional[str] = None) -> Optional[Any]:
        """获取键值"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, namespace: Optional[str] = None) -> None:
        """设置键值"""
        pass

    @abstractmethod
    def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """删除键值，返回是否成功"""
        pass

    @abstractmethod
    def list_keys(self, namespace: Optional[str] = None) -> list:
        """列出命名空间下的所有键"""
        pass

    @abstractmethod
    def search(self, keyword: str, namespace: Optional[str] = None) -> list:
        """搜索键"""
        pass

    @abstractmethod
    def clear_namespace(self, namespace: str) -> None:
        """清空命名空间"""
        pass


class NamespaceStrategy(ABC):
    """命名空间策略抽象基类"""

    @abstractmethod
    def build(self, ai_id: Optional[str], session_id: Optional[str]) -> Optional[str]:
        """构建命名空间字符串"""
        pass

    @abstractmethod
    def describe(
        self, ai_isolation: bool, session_scope: bool, ai_id: str, session_id: str
    ) -> str:
        """描述命名空间范围"""
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
