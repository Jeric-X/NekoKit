from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .preprocess_tool import PreprocessTool
    from .cache_tool import CacheTool
    from .image_context_manager import ImageContextManager


@dataclass
class CateyeServices:
    preprocess: "PreprocessTool"
    cache: "CacheTool"
    context: Optional["ImageContextManager"] = None
