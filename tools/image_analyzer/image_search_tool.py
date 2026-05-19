import base64
import os
from typing import Any, Dict, List, Optional

import aiohttp
from astrbot.api import logger

from ...core import BaseTool, ToolResult
from ._internal import download_image

PROVIDERS = {
    "huawei": {
        "name": "华为云通用搜索",
        "url": "https://image.cn-north-4.myhuaweicloud.com/v2/{project_id}/images/search",
        "scene": "general",
    },
    "tracemoe": {
        "name": "trace.moe 番剧搜索",
        "url": "https://api.trace.moe/search",
        "scene": "anime",
    },
    "saucenao": {
        "name": "SauceNAO 萌系/插画搜索",
        "url": "https://saucenao.com/search.php",
        "scene": "moe",
    },
}

SCENE_PROVIDER_MAP = {
    "anime": "tracemoe",
    "moe": "saucenao",
    "illustration": "saucenao",
    "general": "huawei",
}


class ImageSearchTool(BaseTool):
    def __init__(self):
        self._data_dir: str = ""
        self._config: Dict[str, Any] = {}

    def initialize(
        self,
        data_dir: str,
        config: Dict[str, Any] = None,
        **kwargs,
    ) -> None:
        self._data_dir = data_dir
        if config:
            self._config = config

    def get_name(self) -> str:
        return "cateye_search"

    def get_description(self) -> str:
        return (
            "以图搜图工具。支持多个供应商：华为云（通用搜索）、trace.moe（番剧识别）、"
            "SauceNAO（萌系/插画识别）。根据场景自动选择供应商。"
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
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

    async def execute(self, **kwargs) -> ToolResult:
        image_url = kwargs.get("image_url", "")
        scene = kwargs.get("scene", "auto")
        provider = kwargs.get("provider")

        if not image_url:
            return ToolResult(success=False, message="必须提供 image_url")

        try:
            img_dir = os.path.join(self._data_dir, "cateye", "images")
            image_path = await download_image(image_url, img_dir)

            providers_to_try = self._resolve_providers(scene, provider)

            all_results = []
            for prov_key in providers_to_try:
                if not self._is_provider_enabled(prov_key):
                    continue
                try:
                    result = await self._call_provider(prov_key, image_path)
                    if result:
                        all_results.extend(result)
                except Exception as e:
                    logger.warning(f"[nekokit.cateye] 供应商 {prov_key} 失败: {e}")
                    continue

            if not all_results:
                return ToolResult(
                    success=True,
                    message="所有供应商均未找到结果",
                    data={"results": [], "providers_tried": providers_to_try},
                )

            logger.info(f"[nekokit.cateye] 搜图完成，找到 {len(all_results)} 条结果")
            return ToolResult(
                success=True,
                message=f"找到 {len(all_results)} 条结果",
                data={"results": all_results},
            )

        except Exception as e:
            logger.error(f"[nekokit.cateye] 以图搜图失败: {e}")
            return ToolResult(success=False, message=f"以图搜图失败: {str(e)}")

    def _resolve_providers(self, scene: str, provider: Optional[str]) -> List[str]:
        if provider:
            return [provider]

        if scene == "auto":
            enabled = []
            for key in PROVIDERS:
                if self._is_provider_enabled(key):
                    enabled.append(key)
            return enabled if enabled else ["tracemoe"]

        mapped = SCENE_PROVIDER_MAP.get(scene, "tracemoe")
        return [mapped]

    def _is_provider_enabled(self, provider_key: str) -> bool:
        search_config = self._config.get("search_providers", {})
        enabled_key = f"{provider_key}_enabled"
        return search_config.get(enabled_key, True)

    def _get_api_key(self, provider_key: str) -> str:
        search_config = self._config.get("search_providers", {})
        api_key_key = f"{provider_key}_api_key"
        return search_config.get(api_key_key, "")

    async def _call_provider(
        self, provider_key: str, image_path: str
    ) -> List[Dict[str, Any]]:
        if provider_key == "tracemoe":
            return await self._call_tracemoe(image_path)
        elif provider_key == "saucenao":
            return await self._call_saucenao(image_path)
        elif provider_key == "huawei":
            return await self._call_huawei(image_path)
        else:
            logger.warning(f"[nekokit.cateye] 未知供应商: {provider_key}")
            return []

    async def _call_tracemoe(self, image_path: str) -> List[Dict[str, Any]]:
        url = PROVIDERS["tracemoe"]["url"]
        with open(image_path, "rb") as f:
            image_data = f.read()

        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field(
                "image", image_data, filename="image.jpg", content_type="image/jpeg"
            )
            async with session.post(
                url, data=form, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"trace.moe API 错误: HTTP {resp.status}")
                data = await resp.json()

        results = []
        for item in data.get("result", [])[:5]:
            results.append(
                {
                    "provider": "trace.moe",
                    "similarity": item.get("similarity", 0),
                    "anime": item.get("anime", ""),
                    "episode": item.get("episode", ""),
                    "from_time": item.get("from", 0),
                    "to_time": item.get("to", 0),
                    "filename": item.get("filename", ""),
                    "video_url": item.get("video", ""),
                }
            )
        return results

    async def _call_saucenao(self, image_path: str) -> List[Dict[str, Any]]:
        api_key = self._get_api_key("saucenao")
        url = PROVIDERS["saucenao"]["url"]

        with open(image_path, "rb") as f:
            image_data = f.read()

        params = {
            "output_type": 2,
            "numres": 5,
        }
        if api_key:
            params["api_key"] = api_key

        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field(
                "file", image_data, filename="image.jpg", content_type="image/jpeg"
            )
            for k, v in params.items():
                form.add_field(k, str(v))
            async with session.post(
                url, data=form, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"SauceNAO API 错误: HTTP {resp.status}")
                data = await resp.json()

        results = []
        for item in data.get("results", [])[:5]:
            header = item.get("header", {})
            data_section = item.get("data", {})
            results.append(
                {
                    "provider": "SauceNAO",
                    "similarity": float(header.get("similarity", 0)),
                    "title": data_section.get(
                        "title", data_section.get("material", "")
                    ),
                    "source": data_section.get("source", ""),
                    "ext_urls": data_section.get("ext_urls", []),
                    "thumbnail": header.get("thumbnail", ""),
                }
            )
        return results

    async def _call_huawei(self, image_path: str) -> List[Dict[str, Any]]:
        api_key = self._get_api_key("huawei")
        if not api_key:
            logger.warning("[nekokit.cateye] 华为云 API Key 未配置")
            return []

        with open(image_path, "rb") as f:
            image_data = f.read()
        b64_image = base64.b64encode(image_data).decode("utf-8")

        project_id = self._config.get("search_providers", {}).get(
            "huawei_project_id", ""
        )
        if not project_id:
            logger.warning("[nekokit.cateye] 华为云 project_id 未配置")
            return []

        url = PROVIDERS["huawei"]["url"].format(project_id=project_id)
        headers = {"X-Auth-Token": api_key, "Content-Type": "application/json"}
        body = {"image": b64_image, "limit": 5}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"华为云 API 错误: HTTP {resp.status}")
                data = await resp.json()

        results = []
        for item in data.get("results", [])[:5]:
            results.append(
                {
                    "provider": "Huawei Cloud",
                    "similarity": item.get("similarity", 0),
                    "source": item.get("source", ""),
                    "description": item.get("description", ""),
                }
            )
        return results
