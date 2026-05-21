import os
from typing import Any, Dict

from astrbot.api import logger

from ...core import BaseTool, ToolResult
from ._internal import download_image, preprocess_image


class PreprocessTool(BaseTool):
    def __init__(self):
        self._data_dir: str = ""
        self._config: Dict[str, Any] = {}

    def initialize(
        self, data_dir: str, config: Dict[str, Any] = None, **kwargs
    ) -> None:
        self._data_dir = data_dir
        if config:
            self._config = config

    def get_name(self) -> str:
        return "nkit_ce_preprocess"

    def get_description(self) -> str:
        return (
            "图片预处理工具。根据任务类型（OCR/搜图/大模型）自动调整图片尺寸和格式，"
            "以优化速度和 token 消耗。"
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
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

    async def execute(self, **kwargs) -> ToolResult:
        image_url = kwargs.get("image_url", "")
        task_type = kwargs.get("task_type", "vision")

        if not image_url:
            return ToolResult(success=False, message="必须提供 image_url")

        if task_type not in ("ocr", "search", "vision"):
            return ToolResult(
                success=False,
                message=f"无效的 task_type: {task_type}，必须为 ocr/search/vision",
            )

        if not self._config.get("preprocess_enabled", True):
            return ToolResult(
                success=True,
                message="预处理已在配置中禁用",
                data={"image_url": image_url, "preprocessed": False},
            )

        try:
            img_dir = os.path.join(self._data_dir, "cateye", "images")
            image_path = await download_image(image_url, img_dir)

            output_dir = os.path.join(self._data_dir, "cateye", "preprocessed")
            processed_path = preprocess_image(image_path, task_type, output_dir)

            logger.info(
                f"[nekokit.cateye] 已为 {task_type} 预处理图片: {processed_path}"
            )
            return ToolResult(
                success=True,
                message=f"图片已为 {task_type} 任务预处理",
                data={
                    "original_path": image_path,
                    "preprocessed_path": processed_path,
                    "task_type": task_type,
                },
            )
        except Exception as e:
            logger.error(f"[nekokit.cateye] 预处理失败: {e}")
            return ToolResult(success=False, message=f"预处理失败: {str(e)}")
