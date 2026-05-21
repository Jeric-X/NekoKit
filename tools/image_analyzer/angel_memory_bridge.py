from typing import Any, Dict, List

from astrbot.api import logger

from .image_context_manager import KnowledgeEntry


class AngelMemoryBridge:
    NEKOKIT_DATA_TAG = "nekokit_data"
    CATEYE_CONTEXT_TAG = "cateye_context"

    DATA_REGISTRY: Dict[str, str] = {
        "cateye_context": "cateye_context",
    }

    def __init__(self, memory_runtime, plugin_context):
        self._runtime = memory_runtime
        self._plugin_context = plugin_context

    async def add_knowledge(
        self, image_url: str, image_hash: str, source: str, content: str, **meta
    ) -> None:
        judgment = f"[{source}] {content[:50]}"
        reasoning = meta.get("prompt", image_url)
        tags = [
            self.NEKOKIT_DATA_TAG,
            self.CATEYE_CONTEXT_TAG,
            source,
            f"img:{image_hash[:8]}",
        ]
        if meta.get("mode"):
            tags.append(f"mode:{meta['mode']}")
        try:
            await self._runtime.remember(
                memory_type="knowledge",
                judgment=judgment,
                reasoning=reasoning,
                tags=tags,
                strength=50,
                memory_scope="cateye",
            )
        except Exception as e:
            logger.warning(f"[nekokit] 天使之魂写入失败: {e}")

    async def get_knowledge(
        self, image_url: str, image_hash: str
    ) -> List[KnowledgeEntry]:
        try:
            memories = await self._runtime.chained_recall(
                query="图片分析历史记录",
                entities=[f"img:{image_hash[:8]}", self.CATEYE_CONTEXT_TAG],
                per_type_limit=10,
                final_limit=10,
                memory_scope="cateye",
            )
            return [self._memory_to_entry(m) for m in memories]
        except Exception as e:
            logger.warning(f"[nekokit] 天使之魂读取失败: {e}")
            return []

    async def update_scene(
        self,
        image_url: str,
        image_hash: str,
        scene: str,
        description: str = "",
    ) -> None:
        await self.add_knowledge(
            image_url,
            image_hash,
            source="scene",
            content=f"{scene}: {description}" if description else scene,
        )

    async def update_intent(
        self,
        image_url: str,
        image_hash: str,
        keywords: List[str],
        distilled: str = "",
    ) -> None:
        content = ", ".join(keywords)
        if distilled:
            content += f" | {distilled}"
        await self.add_knowledge(
            image_url,
            image_hash,
            source="intent",
            content=content,
        )

    async def remove_context(self, image_url: str, image_hash: str) -> None:
        logger.info("[nekokit] 天使之魂模式不支持单独移除 context")

    async def build_vision_context(
        self, image_url: str, image_hash: str, current_prompt: str
    ) -> str:
        entries = await self.get_knowledge(image_url, image_hash)
        if not entries:
            return ""
        parts = ["以下是这张图片的历史分析记录："]
        for entry in entries:
            parts.append(f"- [{entry.source}] {entry.content}")
        parts.append("请基于以上历史分析，结合当前问题进行分析。")
        return "\n".join(parts)

    @staticmethod
    def _memory_to_entry(memory: Any) -> KnowledgeEntry:
        judgment = getattr(memory, "judgment", "")
        tags = getattr(memory, "tags", [])
        source = "unknown"
        for tag in tags:
            if (
                tag not in ("nekokit_data", "cateye_context")
                and not tag.startswith("img:")
                and not tag.startswith("mode:")
            ):
                source = tag
                break
        content = judgment
        if judgment.startswith("[") and "]" in judgment:
            content = judgment[judgment.index("]") + 1 :].strip()
        return KnowledgeEntry(source=source, content=content)
