import os
from typing import Any, Dict

from astrbot.api import logger

from ...core import BaseTool, ToolResult
from ._internal import (
    ImageCache,
    compute_image_hashes,
    download_image,
)


class CacheTool(BaseTool):
    def __init__(self):
        self._data_dir: str = ""
        self._config: Dict[str, Any] = {}
        self._cache: ImageCache = ImageCache()

    def initialize(
        self,
        data_dir: str,
        config: Dict[str, Any] = None,
        cache: ImageCache = None,
        **kwargs,
    ) -> None:
        self._data_dir = data_dir
        if config:
            self._config = config
        if cache:
            self._cache = cache
        ttl = self._config.get("cache_ttl_hours", 1.0)
        self._cache.set_ttl(ttl)

    def get_name(self) -> str:
        return "cateye_cache"

    def get_description(self) -> str:
        return (
            "图片缓存工具。检测相似图片是否已被处理过，避免重复调用 API。"
            "使用 MD5 + dHash 相似度检测。"
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

    async def execute(self, **kwargs) -> ToolResult:
        image_url = kwargs.get("image_url", "")
        task_type = kwargs.get("task_type", "vision")
        action = kwargs.get("action", "check")
        result_data = kwargs.get("result")

        if not image_url:
            return ToolResult(success=False, message="必须提供 image_url")

        if task_type not in ("ocr", "search", "vision"):
            return ToolResult(
                success=False,
                message=f"无效的 task_type: {task_type}，必须为 ocr/search/vision",
            )

        try:
            img_dir = os.path.join(self._data_dir, "cateye", "images")
            image_path = await download_image(image_url, img_dir)

            md5, dhash_val = compute_image_hashes(image_path)

            if action == "check":
                cache_key = self._cache.find_similar(md5, dhash_val)
                if cache_key:
                    cached_result = self._cache.get(cache_key, task_type)
                    if cached_result is not None:
                        logger.info(
                            f"[nekokit.cateye] {task_type} 缓存命中: {md5[:8]}..."
                        )
                        return ToolResult(
                            success=True,
                            message="缓存命中",
                            data={
                                "cached": True,
                                "task_type": task_type,
                                "result": cached_result,
                            },
                        )

                logger.info(f"[nekokit.cateye] {task_type} 缓存未命中: {md5[:8]}...")
                return ToolResult(
                    success=True,
                    message="缓存未命中",
                    data={"cached": False, "task_type": task_type},
                )

            elif action == "store":
                if result_data is None:
                    return ToolResult(
                        success=False,
                        message="store 操作需要提供 result",
                    )

                cache_key = md5
                self._cache.store(cache_key, dhash_val, task_type, result_data)
                logger.info(f"[nekokit.cateye] 已缓存 {task_type} 结果: {md5[:8]}...")
                return ToolResult(
                    success=True,
                    message="结果已缓存",
                    data={"cached": True, "task_type": task_type, "key": md5[:8]},
                )

            else:
                return ToolResult(
                    success=False,
                    message=f"无效的 action: {action}，必须为 check/store",
                )

        except Exception as e:
            logger.error(f"[nekokit.cateye] 缓存操作失败: {e}")
            return ToolResult(success=False, message=f"缓存操作失败: {str(e)}")
