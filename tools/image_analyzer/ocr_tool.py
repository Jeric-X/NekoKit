import asyncio
import os
from typing import Any, Dict, List

from astrbot.api import logger

from ...core import BaseTool, ToolResult
from ._internal import (
    ImageCache,
    compute_image_hashes,
    download_image,
    preprocess_image,
)


class OCRTool(BaseTool):
    def __init__(self):
        self._data_dir: str = ""
        self._config: Dict[str, Any] = {}
        self._cache: ImageCache = ImageCache()
        self._reader = None

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

    def _get_reader(self, languages: List[str]):
        if self._reader is None:
            try:
                import easyocr

                self._reader = easyocr.Reader(languages, verbose=False)
                logger.info(f"[nekokit.cateye] EasyOCR 已初始化，语言: {languages}")
            except ImportError:
                raise ImportError("easyocr 未安装，请执行: pip install easyocr")
        return self._reader

    def get_name(self) -> str:
        return "cateye_ocr"

    def get_description(self) -> str:
        return "OCR 文字识别工具。使用 EasyOCR 引擎提取图片中的文字，返回纯文本。"

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "图片 URL 或本地文件路径",
                },
                "languages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "OCR 识别语言，如 ['ch_sim','en']。默认：简体中文+英文"
                    ),
                },
            },
            "required": ["image_url"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        image_url = kwargs.get("image_url", "")
        languages = kwargs.get("languages")

        if not image_url:
            return ToolResult(success=False, message="必须提供 image_url")

        if not languages:
            languages = self._config.get("ocr_languages", ["ch_sim", "en"])

        try:
            img_dir = os.path.join(self._data_dir, "cateye", "images")
            image_path = await download_image(image_url, img_dir)

            md5, dhash_val = compute_image_hashes(image_path)

            cache_key = self._cache.find_similar(md5, dhash_val)
            if cache_key:
                cached = self._cache.get(cache_key, "ocr")
                if cached is not None:
                    logger.info("[nekokit.cateye] OCR 缓存命中")
                    return ToolResult(
                        success=True,
                        message="OCR 结果（缓存）",
                        data={"text": cached, "cached": True},
                    )

            if self._config.get("preprocess_enabled", True):
                output_dir = os.path.join(self._data_dir, "cateye", "preprocessed")
                image_path = preprocess_image(image_path, "ocr", output_dir)

            reader = self._get_reader(languages)
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, reader.readtext, image_path)

            text_parts = []
            for detection in results:
                if len(detection) >= 2:
                    text_parts.append(detection[1])

            full_text = "\n".join(text_parts)

            self._cache.store(md5, dhash_val, "ocr", full_text)

            logger.info(f"[nekokit.cateye] OCR 完成，提取了 {len(text_parts)} 个文本块")
            return ToolResult(
                success=True,
                message="OCR 完成",
                data={"text": full_text, "block_count": len(text_parts)},
            )

        except ImportError as e:
            logger.error(f"[nekokit.cateye] OCR 依赖缺失: {e}")
            return ToolResult(success=False, message=f"OCR 依赖缺失: {str(e)}")
        except Exception as e:
            logger.error(f"[nekokit.cateye] OCR 失败: {e}")
            return ToolResult(success=False, message=f"OCR 失败: {str(e)}")
