from typing import List, Protocol, runtime_checkable

from .image_context_manager import KnowledgeEntry


@runtime_checkable
class MemoryBridge(Protocol):
    async def add_knowledge(
        self, image_url: str, image_hash: str, source: str, content: str, **meta
    ) -> None: ...

    async def get_knowledge(
        self, image_url: str, image_hash: str
    ) -> List[KnowledgeEntry]: ...

    async def update_scene(
        self,
        image_url: str,
        image_hash: str,
        scene: str,
        description: str = "",
    ) -> None: ...

    async def update_intent(
        self,
        image_url: str,
        image_hash: str,
        keywords: List[str],
        distilled: str = "",
    ) -> None: ...

    async def remove_context(self, image_url: str, image_hash: str) -> None: ...

    async def build_vision_context(
        self, image_url: str, image_hash: str, current_prompt: str
    ) -> str: ...
