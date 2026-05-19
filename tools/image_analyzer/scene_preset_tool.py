import json
import os
from typing import Any, Dict

from astrbot.api import logger

from ...core import BaseTool, ToolResult

DEFAULT_PRESETS = {
    "extract_text": {
        "name": "文字提取",
        "description": "从图片中提取文字，适合截图、文档、标牌等场景",
        "steps": [
            {"tool": "cateye_cache", "params": {"task_type": "ocr", "action": "check"}},
            {"tool": "cateye_preprocess", "params": {"task_type": "ocr"}},
            {"tool": "cateye_ocr", "params": {}},
            {"tool": "cateye_cache", "params": {"task_type": "ocr", "action": "store"}},
        ],
    },
    "identify_character": {
        "name": "角色识别",
        "description": "识别图片中的角色或人物，组合搜图和视觉理解",
        "steps": [
            {
                "tool": "cateye_cache",
                "params": {"task_type": "search", "action": "check"},
            },
            {"tool": "cateye_preprocess", "params": {"task_type": "search"}},
            {"tool": "cateye_search", "params": {"scene": "auto"}},
            {"tool": "cateye_preprocess", "params": {"task_type": "vision"}},
            {"tool": "cateye_vision", "params": {"mode": "daily"}},
            {
                "tool": "cateye_cache",
                "params": {"task_type": "search", "action": "store"},
            },
            {
                "tool": "cateye_cache",
                "params": {"task_type": "vision", "action": "store"},
            },
        ],
    },
    "find_anime_source": {
        "name": "番剧溯源",
        "description": "查找番剧截图的出处，适合动画场景截图",
        "steps": [
            {
                "tool": "cateye_cache",
                "params": {"task_type": "search", "action": "check"},
            },
            {"tool": "cateye_preprocess", "params": {"task_type": "search"}},
            {"tool": "cateye_search", "params": {"scene": "anime"}},
            {
                "tool": "cateye_cache",
                "params": {"task_type": "search", "action": "store"},
            },
        ],
    },
    "understand_meme": {
        "name": "表情包理解",
        "description": "理解表情包的含义和内容",
        "steps": [
            {
                "tool": "cateye_cache",
                "params": {"task_type": "vision", "action": "check"},
            },
            {"tool": "cateye_preprocess", "params": {"task_type": "vision"}},
            {"tool": "cateye_vision", "params": {"mode": "daily"}},
            {
                "tool": "cateye_cache",
                "params": {"task_type": "vision", "action": "store"},
            },
        ],
    },
    "analyze_chart": {
        "name": "图表分析",
        "description": "分析复杂图表、技术图纸或学术内容",
        "steps": [
            {
                "tool": "cateye_cache",
                "params": {"task_type": "vision", "action": "check"},
            },
            {"tool": "cateye_preprocess", "params": {"task_type": "vision"}},
            {"tool": "cateye_vision", "params": {"mode": "professional"}},
            {
                "tool": "cateye_cache",
                "params": {"task_type": "vision", "action": "store"},
            },
        ],
    },
    "full_analysis": {
        "name": "全面分析",
        "description": "对所有维度进行全面分析，适合不确定图片内容时使用",
        "steps": [
            {"tool": "cateye_cache", "params": {"task_type": "ocr", "action": "check"}},
            {
                "tool": "cateye_cache",
                "params": {"task_type": "search", "action": "check"},
            },
            {
                "tool": "cateye_cache",
                "params": {"task_type": "vision", "action": "check"},
            },
            {"tool": "cateye_preprocess", "params": {"task_type": "ocr"}},
            {"tool": "cateye_ocr", "params": {}},
            {"tool": "cateye_preprocess", "params": {"task_type": "search"}},
            {"tool": "cateye_search", "params": {"scene": "auto"}},
            {"tool": "cateye_preprocess", "params": {"task_type": "vision"}},
            {"tool": "cateye_vision", "params": {"mode": "daily"}},
            {"tool": "cateye_cache", "params": {"task_type": "ocr", "action": "store"}},
            {
                "tool": "cateye_cache",
                "params": {"task_type": "search", "action": "store"},
            },
            {
                "tool": "cateye_cache",
                "params": {"task_type": "vision", "action": "store"},
            },
        ],
    },
}


class ScenePresetTool(BaseTool):
    def __init__(self):
        self._data_dir: str = ""
        self._presets: Dict[str, Any] = {}
        self._presets_file: str = ""

    def initialize(
        self, data_dir: str, config: Dict[str, Any] = None, **kwargs
    ) -> None:
        self._data_dir = data_dir
        presets_dir = os.path.join(data_dir, "cateye", "presets")
        os.makedirs(presets_dir, exist_ok=True)
        self._presets_file = os.path.join(presets_dir, "scene_presets.json")
        self._load_presets()

    def _load_presets(self) -> None:
        if os.path.exists(self._presets_file):
            try:
                with open(self._presets_file, "r", encoding="utf-8") as f:
                    self._presets = json.load(f)
                logger.info(
                    f"[nekokit.cateye] 已加载自定义场景预设: {list(self._presets.keys())}"
                )
                return
            except Exception as e:
                logger.warning(f"[nekokit.cateye] 加载自定义预设失败，使用默认: {e}")

        self._presets = dict(DEFAULT_PRESETS)
        self._save_presets()

    def _save_presets(self) -> None:
        try:
            with open(self._presets_file, "w", encoding="utf-8") as f:
                json.dump(self._presets, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[nekokit.cateye] 保存预设失败: {e}")

    def get_name(self) -> str:
        return "cateye_scene"

    def get_description(self) -> str:
        return (
            "场景预设工具。根据场景编码返回工具组合策略，"
            "指导智能体按步骤调用 cateye 工具集。"
            "支持查看预设列表、获取具体方案、自定义修改方案。"
        )

    def get_parameters(self) -> Dict[str, Any]:
        preset_codes = list(self._presets.keys())
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
                    "description": f"场景编码，可选值: {', '.join(preset_codes)}",
                },
                "preset_json": {
                    "type": "string",
                    "description": (
                        "预设方案的 JSON 字符串（update 操作时必填）。"
                        '格式: {"name": "场景名", "description": "描述", '
                        '"steps": [{"tool": "工具名", "params": {参数}}]}'
                    ),
                },
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action", "list")
        scene_code = kwargs.get("scene_code", "")
        preset_json = kwargs.get("preset_json", "")

        if action == "list":
            return self._list_presets()
        elif action == "get":
            return self._get_preset(scene_code)
        elif action == "update":
            return self._update_preset(scene_code, preset_json)
        else:
            return ToolResult(
                success=False,
                message=f"无效的 action: {action}，必须为 list/get/update",
            )

    def _list_presets(self) -> ToolResult:
        presets_info = []
        for code, preset in self._presets.items():
            presets_info.append(
                {
                    "code": code,
                    "name": preset.get("name", code),
                    "description": preset.get("description", ""),
                    "step_count": len(preset.get("steps", [])),
                }
            )
        return ToolResult(
            success=True,
            message=f"共 {len(presets_info)} 个场景预设",
            data={"presets": presets_info},
        )

    def _get_preset(self, scene_code: str) -> ToolResult:
        if not scene_code:
            return ToolResult(success=False, message="必须提供 scene_code")

        preset = self._presets.get(scene_code)
        if not preset:
            available = ", ".join(self._presets.keys())
            return ToolResult(
                success=False,
                message=f"预设 '{scene_code}' 不存在。可用预设: {available}",
            )

        return ToolResult(
            success=True,
            message=f"场景预设: {preset.get('name', scene_code)}",
            data={"code": scene_code, "preset": preset},
        )

    def _update_preset(self, scene_code: str, preset_json: str) -> ToolResult:
        if not scene_code:
            return ToolResult(success=False, message="必须提供 scene_code")
        if not preset_json:
            return ToolResult(success=False, message="必须提供 preset_json")

        try:
            preset_data = json.loads(preset_json)
        except json.JSONDecodeError as e:
            return ToolResult(success=False, message=f"JSON 格式错误: {str(e)}")

        if "steps" not in preset_data:
            return ToolResult(success=False, message="预设必须包含 steps 字段")

        valid_tools = {
            "cateye_ocr",
            "cateye_search",
            "cateye_vision",
            "cateye_preprocess",
            "cateye_cache",
        }
        for i, step in enumerate(preset_data["steps"]):
            if "tool" not in step:
                return ToolResult(
                    success=False,
                    message=f"第 {i + 1} 步缺少 tool 字段",
                )
            if step["tool"] not in valid_tools:
                return ToolResult(
                    success=False,
                    message=f"第 {i + 1} 步工具名 '{step['tool']}' 无效，可用: {', '.join(sorted(valid_tools))}",
                )

        self._presets[scene_code] = preset_data
        self._save_presets()

        logger.info(f"[nekokit.cateye] 已更新场景预设: {scene_code}")
        return ToolResult(
            success=True,
            message=f"场景预设 '{scene_code}' 已更新",
            data={"code": scene_code, "preset": preset_data},
        )
