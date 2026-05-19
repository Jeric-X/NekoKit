import os
from typing import Any, Dict, Optional

from astrbot.api import logger

from ...core import BaseTool, ToolResult
from ._internal import download_image, image_to_base64_url


class VisionTool(BaseTool):
    def __init__(self):
        self._data_dir: str = ""
        self._config: Dict[str, Any] = {}
        self._star_context = None

    def initialize(
        self,
        data_dir: str,
        config: Dict[str, Any] = None,
        star_context=None,
        **kwargs,
    ) -> None:
        self._data_dir = data_dir
        if config:
            self._config = config
        if star_context:
            self._star_context = star_context

    def get_name(self) -> str:
        return "cateye_vision"

    def get_description(self) -> str:
        return (
            "视觉理解工具。调用多模态大模型对图片进行理解、描述或推理。"
            "支持日常模式（表情包、日常场景）和专业模式（复杂图表分析、习题解答）。"
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
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

    async def execute(self, **kwargs) -> ToolResult:
        image_url = kwargs.get("image_url", "")
        prompt = kwargs.get("prompt", "")
        mode = kwargs.get("mode", "daily")

        if not image_url:
            return ToolResult(success=False, message="必须提供 image_url")
        if not prompt:
            return ToolResult(success=False, message="必须提供 prompt")

        if not self._star_context:
            return ToolResult(success=False, message="AstrBot 上下文不可用")

        try:
            img_dir = os.path.join(self._data_dir, "cateye", "images")
            image_path = await download_image(image_url, img_dir)

            provider_id = self._resolve_provider(mode)
            if not provider_id:
                return ToolResult(
                    success=False,
                    message=f"插件设置中未配置 {mode} 模型",
                )

            system_prompt = self._build_system_prompt(mode)
            b64_url = image_to_base64_url(image_path)

            llm_resp = await self._star_context.llm_generate(
                chat_provider_id=provider_id,
                prompt=prompt,
                image_urls=[b64_url],
                system_prompt=system_prompt,
            )

            analysis = llm_resp.completion_text if llm_resp else ""

            logger.info(f"[nekokit.cateye] 视觉分析完成（{mode} 模式）")
            return ToolResult(
                success=True,
                message=f"视觉分析完成（{mode} 模式）",
                data={"analysis": analysis, "mode": mode},
            )

        except Exception as e:
            logger.error(f"[nekokit.cateye] 视觉分析失败: {e}")
            return ToolResult(success=False, message=f"视觉分析失败: {str(e)}")

    def _resolve_provider(self, mode: str) -> Optional[str]:
        vision_config = self._config.get("vision_models", {})
        if mode == "professional":
            return vision_config.get("professional_model", "")
        return vision_config.get("daily_model", "")

    def _build_system_prompt(self, mode: str) -> str:
        if mode == "professional":
            return (
                "你是一个专业的图片分析助手。"
                "请对复杂图片（如图表、技术图纸、学术问题等）提供详细、准确的分析。"
                "分析要全面且精确。"
            )
        return (
            "你是一个友好的图片理解助手。"
            "请用自然、对话式的方式描述和分析图片。"
            "简洁但信息丰富。"
        )
