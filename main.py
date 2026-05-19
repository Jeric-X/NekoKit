import json

from astrbot.api import logger
from astrbot.api import star
from astrbot.api.star import StarTools
from astrbot.api import AstrBotConfig
from astrbot.core.agent.tool import FunctionTool
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.astr_agent_context import AstrAgentContext
from dataclasses import dataclass, field

from .tools import KVStoreTool
from .tools.image_analyzer import (
    OCRTool,
    ImageSearchTool,
    VisionTool,
    PreprocessTool,
    CacheTool,
    ImageCache,
)
from .core import ToolResult


@dataclass
class KVGetTool(FunctionTool[AstrAgentContext]):
    """获取键值对"""

    name: str = "get_kv"
    description: str = "根据键名获取存储的值"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "要获取的键名",
                },
            },
            "required": ["key"],
        }
    )

    _kv_tool: KVStoreTool = None

    @classmethod
    def create_with_tool(cls, kv_tool: KVStoreTool) -> "KVGetTool":
        tool = cls()
        tool._kv_tool = kv_tool
        return tool

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> str:
        if not self._kv_tool:
            return "KVStoreTool 未初始化"

        self._kv_tool.set_context(context)
        try:
            result: ToolResult = await self._kv_tool.execute(action="get", **kwargs)
            if result.success:
                return json.dumps(result.to_dict(), ensure_ascii=False)
            else:
                return result.message
        except Exception as e:
            logger.error(f"[KVGetTool] 执行失败: {e}")
            return f"执行失败: {str(e)}"


@dataclass
class KVSetTool(FunctionTool[AstrAgentContext]):
    """设置键值对"""

    name: str = "set_kv"
    description: str = "设置或更新键值对"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "键名",
                },
                "value": {
                    "type": "string",
                    "description": "值，可以是任意 JSON 兼容的数据",
                },
            },
            "required": ["key", "value"],
        }
    )

    _kv_tool: KVStoreTool = None

    @classmethod
    def create_with_tool(cls, kv_tool: KVStoreTool) -> "KVSetTool":
        tool = cls()
        tool._kv_tool = kv_tool
        return tool

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> str:
        if not self._kv_tool:
            return "KVStoreTool 未初始化"

        self._kv_tool.set_context(context)
        try:
            result: ToolResult = await self._kv_tool.execute(action="set", **kwargs)
            if result.success:
                return result.message
            else:
                return result.message
        except Exception as e:
            logger.error(f"[KVSetTool] 执行失败: {e}")
            return f"执行失败: {str(e)}"


@dataclass
class KVDeleteTool(FunctionTool[AstrAgentContext]):
    """删除键值对"""

    name: str = "delete_kv"
    description: str = "根据键名删除存储的值"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "要删除的键名",
                },
            },
            "required": ["key"],
        }
    )

    _kv_tool: KVStoreTool = None

    @classmethod
    def create_with_tool(cls, kv_tool: KVStoreTool) -> "KVDeleteTool":
        tool = cls()
        tool._kv_tool = kv_tool
        return tool

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> str:
        if not self._kv_tool:
            return "KVStoreTool 未初始化"

        self._kv_tool.set_context(context)
        try:
            result: ToolResult = await self._kv_tool.execute(action="delete", **kwargs)
            if result.success:
                return result.message
            else:
                return result.message
        except Exception as e:
            logger.error(f"[KVDeleteTool] 执行失败: {e}")
            return f"执行失败: {str(e)}"


@dataclass
class KVListTool(FunctionTool[AstrAgentContext]):
    """列出所有键"""

    name: str = "list_kv"
    description: str = "列出当前作用域下的所有键"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {},
        }
    )

    _kv_tool: KVStoreTool = None

    @classmethod
    def create_with_tool(cls, kv_tool: KVStoreTool) -> "KVListTool":
        tool = cls()
        tool._kv_tool = kv_tool
        return tool

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> str:
        if not self._kv_tool:
            return "KVStoreTool 未初始化"

        self._kv_tool.set_context(context)
        try:
            result: ToolResult = await self._kv_tool.execute(action="list", **kwargs)
            if result.success:
                return json.dumps(result.to_dict(), ensure_ascii=False)
            else:
                return result.message
        except Exception as e:
            logger.error(f"[KVListTool] 执行失败: {e}")
            return f"执行失败: {str(e)}"


@dataclass
class CateyeOCRTool(FunctionTool[AstrAgentContext]):
    """OCR 文字识别"""

    name: str = "cateye_ocr"
    description: str = (
        "使用 RapidOCR 引擎提取图片中的文字，返回纯文本。默认支持中文和英文。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "图片 URL 或本地文件路径",
                },
            },
            "required": ["image_url"],
        }
    )

    _ocr_tool: OCRTool = None

    @classmethod
    def create_with_tool(cls, ocr_tool: OCRTool) -> "CateyeOCRTool":
        tool = cls()
        tool._ocr_tool = ocr_tool
        return tool

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> str:
        if not self._ocr_tool:
            return "OCRTool 未初始化"
        try:
            result: ToolResult = await self._ocr_tool.execute(**kwargs)
            if result.success:
                return json.dumps(result.to_dict(), ensure_ascii=False)
            else:
                return result.message
        except Exception as e:
            logger.error(f"[nekokit.cateye] OCR 执行失败: {e}")
            return f"OCR 执行失败: {str(e)}"


@dataclass
class CateyeSearchTool(FunctionTool[AstrAgentContext]):
    """以图搜图"""

    name: str = "cateye_search"
    description: str = (
        "以图搜图工具，支持华为云、trace.moe、SauceNAO 等多个供应商，根据场景自动选择。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "图片 URL 或本地文件路径",
                },
                "scene": {
                    "type": "string",
                    "description": (
                        "场景类型，用于供应商选择："
                        "auto（尝试所有已启用的）、anime（番剧）、moe（萌系）、illustration（插画）、general（通用）"
                    ),
                    "enum": ["auto", "anime", "moe", "illustration", "general"],
                },
                "provider": {
                    "type": "string",
                    "description": "强制指定供应商：huawei、tracemoe、saucenao",
                    "enum": ["huawei", "tracemoe", "saucenao"],
                },
            },
            "required": ["image_url"],
        }
    )

    _search_tool: ImageSearchTool = None

    @classmethod
    def create_with_tool(cls, search_tool: ImageSearchTool) -> "CateyeSearchTool":
        tool = cls()
        tool._search_tool = search_tool
        return tool

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> str:
        if not self._search_tool:
            return "ImageSearchTool 未初始化"
        try:
            result: ToolResult = await self._search_tool.execute(**kwargs)
            if result.success:
                return json.dumps(result.to_dict(), ensure_ascii=False)
            else:
                return result.message
        except Exception as e:
            logger.error(f"[nekokit.cateye] Search 执行失败: {e}")
            return f"Search 执行失败: {str(e)}"


@dataclass
class CateyeVisionTool(FunctionTool[AstrAgentContext]):
    """大模型视觉理解"""

    name: str = "cateye_vision"
    description: str = (
        "调用多模态大模型对图片进行理解、描述或推理，支持日常模式和专业模式。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "图片 URL 或本地文件路径",
                },
                "prompt": {
                    "type": "string",
                    "description": "对图片的理解或描述需求",
                },
                "mode": {
                    "type": "string",
                    "description": (
                        "模式：daily（日常任务，如表情包、日常场景）"
                        "或 professional（专业任务，如复杂图表分析、习题解答）"
                    ),
                    "enum": ["daily", "professional"],
                },
            },
            "required": ["image_url", "prompt"],
        }
    )

    _vision_tool: VisionTool = None

    @classmethod
    def create_with_tool(cls, vision_tool: VisionTool) -> "CateyeVisionTool":
        tool = cls()
        tool._vision_tool = vision_tool
        return tool

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> str:
        if not self._vision_tool:
            return "VisionTool 未初始化"
        try:
            result: ToolResult = await self._vision_tool.execute(**kwargs)
            if result.success:
                return json.dumps(result.to_dict(), ensure_ascii=False)
            else:
                return result.message
        except Exception as e:
            logger.error(f"[nekokit.cateye] Vision 执行失败: {e}")
            return f"Vision 执行失败: {str(e)}"


@dataclass
class CateyePreprocessTool(FunctionTool[AstrAgentContext]):
    """图片预处理"""

    name: str = "cateye_preprocess"
    description: str = "根据任务类型自动调整图片尺寸和格式，优化速度和 token 消耗。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "图片 URL 或本地文件路径",
                },
                "task_type": {
                    "type": "string",
                    "description": "任务类型：ocr（文字识别）、search（搜图）或 vision（大模型）",
                    "enum": ["ocr", "search", "vision"],
                },
            },
            "required": ["image_url", "task_type"],
        }
    )

    _preprocess_tool: PreprocessTool = None

    @classmethod
    def create_with_tool(
        cls, preprocess_tool: PreprocessTool
    ) -> "CateyePreprocessTool":
        tool = cls()
        tool._preprocess_tool = preprocess_tool
        return tool

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> str:
        if not self._preprocess_tool:
            return "PreprocessTool 未初始化"
        try:
            result: ToolResult = await self._preprocess_tool.execute(**kwargs)
            if result.success:
                return json.dumps(result.to_dict(), ensure_ascii=False)
            else:
                return result.message
        except Exception as e:
            logger.error(f"[nekokit.cateye] Preprocess 执行失败: {e}")
            return f"Preprocess 执行失败: {str(e)}"


@dataclass
class CateyeCacheTool(FunctionTool[AstrAgentContext]):
    """图片缓存"""

    name: str = "cateye_cache"
    description: str = (
        "检测相似图片是否已被处理过，避免重复调用 API。使用 MD5 + dHash 相似度检测。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "图片 URL 或本地文件路径",
                },
                "task_type": {
                    "type": "string",
                    "description": "任务类型：ocr（文字识别）、search（搜图）或 vision（大模型）",
                    "enum": ["ocr", "search", "vision"],
                },
                "action": {
                    "type": "string",
                    "description": "操作：check（查询缓存）或 store（保存结果）",
                    "enum": ["check", "store"],
                },
                "result": {
                    "type": "string",
                    "description": "要存储的结果数据（store 操作时必填）",
                },
            },
            "required": ["image_url", "task_type", "action"],
        }
    )

    _cache_tool: CacheTool = None

    @classmethod
    def create_with_tool(cls, cache_tool: CacheTool) -> "CateyeCacheTool":
        tool = cls()
        tool._cache_tool = cache_tool
        return tool

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> str:
        if not self._cache_tool:
            return "CacheTool 未初始化"
        try:
            result: ToolResult = await self._cache_tool.execute(**kwargs)
            if result.success:
                return json.dumps(result.to_dict(), ensure_ascii=False)
            else:
                return result.message
        except Exception as e:
            logger.error(f"[nekokit.cateye] Cache 执行失败: {e}")
            return f"Cache 执行失败: {str(e)}"


class Main(star.Star):
    """NekoKit 插件主类"""

    def __init__(self, context: star.Context, config: AstrBotConfig = None) -> None:
        super().__init__(context)
        self.context = context

        self.data_dir = str(StarTools.get_data_dir("nekokit"))

        self._kv_tool = KVStoreTool()
        self._kv_tool.initialize(self.data_dir)

        if config:
            kvstore_config = {}
            if config.get("ai_isolation") is not None:
                kvstore_config["ai_isolation"] = config.get("ai_isolation")
            if config.get("session_scope") is not None:
                kvstore_config["session_scope"] = config.get("session_scope")
            self._kv_tool.set_config(kvstore_config)
            logger.info(f"[NekoKit] 已加载配置: {kvstore_config}")

        self._cateye_cache = ImageCache()
        self._init_cateye_tools(config)

        self._register_tools()

        logger.info("[NekoKit] 插件已加载，已注册 KV 存储工具和 Cateye 图片识别工具集")

    def _init_cateye_tools(self, config: AstrBotConfig = None) -> None:
        cateye_config = self._build_cateye_config(config)

        ttl = cateye_config.get("cache_ttl_hours", 1.0)
        self._cateye_cache.set_ttl(ttl)

        self._ocr_tool = OCRTool()
        self._ocr_tool.initialize(
            self.data_dir, cateye_config, cache=self._cateye_cache
        )

        self._search_tool = ImageSearchTool()
        self._search_tool.initialize(
            self.data_dir, cateye_config, cache=self._cateye_cache
        )

        self._vision_tool = VisionTool()
        self._vision_tool.initialize(
            self.data_dir,
            cateye_config,
            cache=self._cateye_cache,
            star_context=self.context,
        )

        self._preprocess_tool = PreprocessTool()
        self._preprocess_tool.initialize(self.data_dir, cateye_config)

        self._cache_tool = CacheTool()
        self._cache_tool.initialize(
            self.data_dir, cateye_config, cache=self._cateye_cache
        )

    def _build_cateye_config(self, config: AstrBotConfig = None) -> dict:
        cateye_config = {}
        if not config:
            return cateye_config

        image_general = config.get("image_general", {})
        cateye_config["log_level"] = image_general.get("log_level", "INFO")
        cateye_config["custom_prompt_enabled"] = image_general.get(
            "custom_prompt_enabled", False
        )
        cateye_config["custom_prompt"] = image_general.get("custom_prompt", "")

        image_ocr = config.get("image_ocr", {})
        cateye_config["ocr_text_score"] = image_ocr.get("text_score", 0.5)

        image_search = config.get("image_search", {})
        search_providers = {
            "huawei_enabled": image_search.get("huawei_enabled", False),
            "huawei_api_key": image_search.get("huawei_api_key", ""),
            "huawei_project_id": image_search.get("huawei_project_id", ""),
            "tracemoe_enabled": image_search.get("tracemoe_enabled", True),
            "tracemoe_api_key": image_search.get("tracemoe_api_key", ""),
            "saucenao_enabled": image_search.get("saucenao_enabled", True),
            "saucenao_api_key": image_search.get("saucenao_api_key", ""),
            "custom_providers": image_search.get("custom_providers", ""),
        }
        cateye_config["search_providers"] = search_providers

        image_vision = config.get("image_vision", {})
        vision_models = {
            "daily_model": image_vision.get("daily_model", ""),
            "professional_model": image_vision.get("professional_model", ""),
        }
        cateye_config["vision_models"] = vision_models

        image_cache = config.get("image_cache", {})
        cateye_config["cache_ttl_hours"] = image_cache.get("cache_ttl_hours", 1.0)
        cateye_config["preprocess_enabled"] = image_cache.get(
            "preprocess_enabled", True
        )

        logger.info("[nekokit.cateye] 已加载图片识别配置")
        return cateye_config

    def _register_tools(self):
        """注册工具"""
        tools = [
            KVGetTool.create_with_tool(self._kv_tool),
            KVSetTool.create_with_tool(self._kv_tool),
            KVDeleteTool.create_with_tool(self._kv_tool),
            KVListTool.create_with_tool(self._kv_tool),
            CateyeOCRTool.create_with_tool(self._ocr_tool),
            CateyeSearchTool.create_with_tool(self._search_tool),
            CateyeVisionTool.create_with_tool(self._vision_tool),
            CateyePreprocessTool.create_with_tool(self._preprocess_tool),
            CateyeCacheTool.create_with_tool(self._cache_tool),
        ]
        self.context.add_llm_tools(*tools)

    async def terminate(self):
        """插件卸载时调用，清理资源"""
        if hasattr(self, "_kv_tool") and self._kv_tool:
            logger.info("[NekoKit] 插件卸载，清理资源")
