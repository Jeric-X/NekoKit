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
            "支持日常模式和专业模式。可注入场景上下文以增强分析效果。"
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
                "scene_name": {
                    "type": "string",
                    "description": "场景预设名称（可选，用于上下文注入）",
                },
                "scene_description": {
                    "type": "string",
                    "description": "场景描述（可选，配合 scene_name 使用）",
                },
                "tool_chain_dag": {
                    "type": "string",
                    "description": "工具链路 DAG 描述，如 cateye_preprocess(ocr) → cateye_ocr（可选）",
                },
                "user_intent_keywords": {
                    "type": "string",
                    "description": "用户意图关键词，逗号分隔（可选，用于上下文注入）",
                },
                "distilled_context": {
                    "type": "string",
                    "description": "从会话上下文蒸馏的关键信息摘要（可选）",
                },
                "cached_results": {
                    "type": "string",
                    "description": "前序工具的缓存结果 JSON 字符串（可选，用于结果整合）",
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

            system_prompt = self._build_system_prompt(mode, **kwargs)
            b64_url = image_to_base64_url(image_path)

            user_prompt = prompt
            cached_results = kwargs.get("cached_results", "")
            if cached_results:
                user_prompt = f"{prompt}\n\n前序工具结果：\n{cached_results}"

            llm_resp = await self._star_context.llm_generate(
                chat_provider_id=provider_id,
                prompt=user_prompt,
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

    def _build_system_prompt(self, mode: str, **kwargs) -> str:
        if mode == "professional":
            base = (
                "你是一个专业的图片分析助手。"
                "请对复杂图片（如图表、技术图纸、学术问题等）提供详细、准确的分析。"
                "分析要全面且精确。"
            )
        else:
            base = (
                "你是一个友好的图片理解助手。"
                "请用自然、对话式的方式描述和分析图片。"
                "简洁但信息丰富。"
            )

        scene_name = kwargs.get("scene_name", "")
        scene_description = kwargs.get("scene_description", "")
        tool_chain_dag = kwargs.get("tool_chain_dag", "")
        user_intent_keywords = kwargs.get("user_intent_keywords", "")
        distilled_context = kwargs.get("distilled_context", "")

        has_context = any(
            [scene_name, tool_chain_dag, user_intent_keywords, distilled_context]
        )
        if not has_context:
            return base

        parts = ["你正在使用 CatEye 视觉分析工具。以下是当前任务的背景信息："]

        if scene_name:
            desc = f" — {scene_description}" if scene_description else ""
            parts.append(f"- 场景预设：{scene_name}{desc}")
        if tool_chain_dag:
            parts.append(f"- 工具链路：{tool_chain_dag}")
        if user_intent_keywords:
            parts.append(f"- 任务需求：{user_intent_keywords}")
        if distilled_context:
            parts.append(f"- 上下文摘要：{distilled_context}")

        parts.append(
            "请基于以上背景，结合图片内容进行分析。"
            "如有从缓存或前序工具获取的结果，请优先参考并整合。"
        )

        return base + "\n\n" + "\n".join(parts)
