import json
from typing import Any, Dict, Optional

from astrbot.api import logger

from ...core import BaseTool, ToolResult
from ...tools.kv_store.kv_store_tool import KVStoreTool

BUILTIN_PRESETS = {
    "extract_text": {
        "name": "文字提取",
        "description": "从图片中提取文字内容，适合截图、表情包配文、公告图片等场景",
        "tool_chain": ["nkit_ce_ocr"],
        "model_preference": "daily",
        "trigger_keywords": [
            "提取文字",
            "OCR",
            "识别文字",
            "图片里写了什么",
            "这写的什么",
            "截图文字",
            "图里说什么",
            "配文",
            "台词",
            "字幕",
            "公告",
            "通知",
            "文案",
        ],
        "is_preset": True,
    },
    "identify_character": {
        "name": "角色识别",
        "description": "识别图片中的动漫角色或游戏角色，结合搜图和视觉理解给出详细信息",
        "tool_chain": ["nkit_ce_search", "nkit_ce_vision"],
        "model_preference": "daily",
        "trigger_keywords": [
            "这是谁",
            "什么角色",
            "角色名",
            "认角色",
            "是谁",
            "人物",
            "角色出处",
            "出自哪个动漫",
            "哪个游戏",
            "角色识别",
            "认人",
            "这个角色",
            "动漫角色",
            "游戏角色",
            "虚拟主播",
            "Vtuber",
        ],
        "is_preset": True,
    },
    "find_anime_source": {
        "name": "番剧溯源",
        "description": "查找动漫截图的出处，识别番剧名称、集数、时间点，支持trace.moe识别",
        "tool_chain": ["nkit_ce_search"],
        "model_preference": "daily",
        "trigger_keywords": [
            "这是什么番",
            "番名",
            "动漫名称",
            "出自哪部番",
            "哪一集",
            "第几集",
            "番剧出处",
            "动画来源",
            "找番",
            "认番",
            "番剧识别",
            "动画截图",
            "新番",
            "老番",
            "剧场版",
            "OVA",
        ],
        "is_preset": True,
    },
    "understand_meme": {
        "name": "表情包解读",
        "description": "解读二次元表情包的含义、梗的来源和笑点，分析表情配文的语境",
        "tool_chain": ["nkit_ce_vision"],
        "model_preference": "daily",
        "trigger_keywords": [
            "什么梗",
            "梗图",
            "表情包",
            "什么意思",
            "笑点在哪",
            "梗出处",
            "玩梗",
            "表情包含义",
            "这个梗",
            "搞笑图片",
            "魔改图",
            "二创图",
            "颜艺",
            "表情",
            "斗图",
            "表情含义",
        ],
        "is_preset": True,
    },
    "analyze_chart": {
        "name": "图片分析",
        "description": (
            "分析图片内容。日常场景（游戏截图、活动图、地图、配装等）使用 daily 模式；"
            "涉及数据、图表、文字、复杂逻辑时使用 professional 模式"
        ),
        "tool_chain": ["nkit_ce_vision"],
        "model_preference": "",
        "trigger_keywords": [
            "分析一下",
            "看看这个",
            "游戏截图",
            "攻略图",
            "数据图",
            "面板",
            "属性",
            "伤害计算",
            "配装",
            "阵容",
            "抽卡",
            "概率",
            "活动",
            "任务",
            "地图",
            "机制",
        ],
        "is_preset": True,
    },
}


class ScenePresetTool(BaseTool):
    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._kv_tool: Optional[KVStoreTool] = None

    def initialize(
        self,
        data_dir: str,
        config: Dict[str, Any] = None,
        kv_tool: KVStoreTool = None,
        **kwargs,
    ) -> None:
        if config:
            self._config = config
        if kv_tool:
            self._kv_tool = kv_tool

    def get_name(self) -> str:
        return "nkit_ce_scene"

    def get_description(self) -> str:
        return (
            "场景预设工具。根据场景编码返回工具组合策略，"
            "指导按步骤调用 cateye 工具集。"
            "支持查看预设列表、获取具体方案、自定义修改方案。"
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": (
                        "操作类型：list（列出所有预设）、"
                        "get（获取指定预设的方案）、"
                        "update（更新预设方案，需提供 scene_code 和 preset_json）"
                    ),
                    "enum": ["list", "get", "update"],
                },
                "scene_code": {
                    "type": "string",
                    "description": (
                        "场景编码，如 extract_text、identify_character、"
                        "find_anime_source、understand_meme、analyze_chart 等"
                    ),
                },
                "preset_json": {
                    "type": "string",
                    "description": (
                        "预设方案的 JSON 字符串（update 操作时必填）。"
                        '格式: {"name": "场景名", "description": "描述", '
                        '"tool_chain": ["工具名"], "model_preference": "daily", '
                        '"trigger_keywords": ["关键词"], "is_preset": false}'
                    ),
                },
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        if not self._kv_tool:
            return ToolResult(success=False, message="KVStoreTool 未初始化")

        action = kwargs.get("action", "")
        if not action:
            return ToolResult(success=False, message="必须指定 action")

        if action == "list":
            return await self._list_presets()
        elif action == "get":
            scene_code = kwargs.get("scene_code", "")
            if not scene_code:
                return ToolResult(success=False, message="get 操作需要 scene_code")
            return await self._get_preset(scene_code)
        elif action == "update":
            scene_code = kwargs.get("scene_code", "")
            preset_json = kwargs.get("preset_json", "")
            if not scene_code:
                return ToolResult(success=False, message="update 操作需要 scene_code")
            if not preset_json:
                return ToolResult(success=False, message="update 操作需要 preset_json")
            return await self._update_preset(scene_code, preset_json)
        else:
            return ToolResult(success=False, message=f"未知操作: {action}")

    async def _list_presets(self) -> ToolResult:
        presets = {}
        for code, preset in BUILTIN_PRESETS.items():
            presets[code] = {
                "name": preset["name"],
                "description": preset["description"],
                "trigger_keywords": preset["trigger_keywords"],
                "is_preset": True,
            }

        if self._kv_tool:
            for code in list(presets.keys()):
                kv_key = f"cat_eye:scene:{code}"
                result = await self._kv_tool.execute(action="get", key=kv_key)
                if result.success:
                    try:
                        custom = json.loads(result.data.get("value", "{}"))
                        if not custom.get("is_preset", False):
                            presets[code] = {
                                "name": custom.get("name", code),
                                "description": custom.get("description", ""),
                                "trigger_keywords": custom.get("trigger_keywords", []),
                                "is_preset": False,
                            }
                    except (json.JSONDecodeError, AttributeError):
                        pass

            try:
                list_result = await self._kv_tool.execute(action="list")
                if list_result.success:
                    keys = list_result.data.get("keys", [])
                    for key in keys:
                        if key.startswith("cat_eye:scene:"):
                            code = key[len("cat_eye:scene:") :]
                            if code not in presets:
                                r = await self._kv_tool.execute(action="get", key=key)
                                if r.success:
                                    try:
                                        custom = json.loads(r.data.get("value", "{}"))
                                        presets[code] = {
                                            "name": custom.get("name", code),
                                            "description": custom.get(
                                                "description", ""
                                            ),
                                            "trigger_keywords": custom.get(
                                                "trigger_keywords", []
                                            ),
                                            "is_preset": custom.get("is_preset", False),
                                        }
                                    except (json.JSONDecodeError, AttributeError):
                                        pass
            except Exception as e:
                logger.warning(f"[nekokit.cateye] 列出自定义场景失败: {e}")

        return ToolResult(
            success=True,
            message=f"共 {len(presets)} 个场景预设",
            data={"presets": presets},
        )

    async def _get_preset(self, scene_code: str) -> ToolResult:
        if scene_code in BUILTIN_PRESETS:
            preset = BUILTIN_PRESETS[scene_code]
            kv_key = f"cat_eye:scene:{scene_code}"
            if self._kv_tool:
                result = await self._kv_tool.execute(action="get", key=kv_key)
                if result.success:
                    try:
                        custom = json.loads(result.data.get("value", "{}"))
                        if not custom.get("is_preset", False):
                            return ToolResult(
                                success=True,
                                message=f"场景预设: {scene_code}（自定义）",
                                data={"scene_code": scene_code, "preset": custom},
                            )
                    except (json.JSONDecodeError, AttributeError):
                        pass

            return ToolResult(
                success=True,
                message=f"场景预设: {scene_code}",
                data={"scene_code": scene_code, "preset": preset},
            )

        kv_key = f"cat_eye:scene:{scene_code}"
        if self._kv_tool:
            result = await self._kv_tool.execute(action="get", key=kv_key)
            if result.success:
                try:
                    custom = json.loads(result.data.get("value", "{}"))
                    return ToolResult(
                        success=True,
                        message=f"场景预设: {scene_code}（自定义）",
                        data={"scene_code": scene_code, "preset": custom},
                    )
                except (json.JSONDecodeError, AttributeError):
                    pass

        return ToolResult(
            success=False,
            message=f"未找到场景预设: {scene_code}",
        )

    async def _update_preset(self, scene_code: str, preset_json: str) -> ToolResult:
        try:
            preset_data = json.loads(preset_json)
        except json.JSONDecodeError as e:
            return ToolResult(success=False, message=f"JSON 格式错误: {str(e)}")

        if scene_code in BUILTIN_PRESETS and preset_data.get("is_preset", False):
            return ToolResult(
                success=False,
                message=f"内置预设 {scene_code} 不支持覆盖，请使用不同的场景编码",
            )

        preset_data["name"] = preset_data.get("name", scene_code)
        preset_data["is_preset"] = False

        kv_key = f"cat_eye:scene:{scene_code}"
        value_json = json.dumps(preset_data, ensure_ascii=False)

        if self._kv_tool:
            result = await self._kv_tool.execute(
                action="set", key=kv_key, value=value_json
            )
            if result.success:
                logger.info(f"[nekokit.cateye] 场景预设已更新: {scene_code}")
                return ToolResult(
                    success=True,
                    message=f"场景预设已更新: {scene_code}",
                    data={"scene_code": scene_code, "preset": preset_data},
                )

        return ToolResult(success=False, message="场景预设更新失败")
