"""pytest 共享夹具：mock AstrBot 依赖，使插件代码可独立加载。

提供：
- astrbot mock 模块体系（conftest 导入时即注入 sys.modules）
- fake_context(persona_id, session_id)：模拟 AstrBot 事件上下文
- kv_tool / kv_tool_sqlite / file_tool：初始化好的工具实例（tmp 数据目录）
"""

import sys
import tempfile
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, TypeVar

import pytest

# 包根的父目录加入 sys.path（NekoKit 包本身即仓库根，需从其上级导入）
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ---------------------------------------------------------------------------
# AstrBot 依赖 mock
# ---------------------------------------------------------------------------

_T = TypeVar("_T")


class _Logger:
    def __getattr__(self, name):
        def _log(msg, *args, **kwargs):
            pass

        return _log


def _install_astrbot_mocks() -> None:
    if "astrbot" in sys.modules:
        return

    astrbot = types.ModuleType("astrbot")
    api = types.ModuleType("astrbot.api")
    api.logger = _Logger()
    astrbot.api = api

    run_context = types.ModuleType("astrbot.core.agent.run_context")

    @dataclass
    class ContextWrapper(Generic[_T]):
        context: Any
        messages: list = field(default_factory=list)

    run_context.ContextWrapper = ContextWrapper

    agent_context = types.ModuleType("astrbot.core.astr_agent_context")

    @dataclass
    class AstrAgentContext:
        context: Any
        event: Any
        extra: dict = field(default_factory=dict)

    agent_context.AstrAgentContext = AstrAgentContext

    astrbot_path = types.ModuleType("astrbot.core.utils.astrbot_path")
    astrbot_path.get_astrbot_temp_path = lambda: tempfile.gettempdir()

    agent = types.ModuleType("astrbot.core.agent")
    agent.run_context = run_context
    utils = types.ModuleType("astrbot.core.utils")
    utils.astrbot_path = astrbot_path
    core = types.ModuleType("astrbot.core")
    core.agent = agent
    core.utils = utils

    for name, mod in {
        "astrbot": astrbot,
        "astrbot.api": api,
        "astrbot.core": core,
        "astrbot.core.agent": agent,
        "astrbot.core.agent.run_context": run_context,
        "astrbot.core.astr_agent_context": agent_context,
        "astrbot.core.utils": utils,
        "astrbot.core.utils.astrbot_path": astrbot_path,
    }.items():
        sys.modules[name] = mod


_install_astrbot_mocks()


def _stub_image_analyzer() -> None:
    """Stub 掉 image_analyzer（依赖 aiohttp/PIL 等重依赖，测试用不到）。

    必须在导入 NekoKit.tools 之前注册，因为 tools/__init__.py 会导入它。
    """
    name = "NekoKit.tools.image_analyzer"
    if name in sys.modules:
        return
    stub = types.ModuleType(name)
    for attr in (
        "OCRTool",
        "ImageSearchTool",
        "VisionTool",
        "PreprocessTool",
        "CacheTool",
        "ScenePresetTool",
        "CateyeServices",
        "ImageContextManager",
    ):
        setattr(stub, attr, type(attr, (), {}))
    sys.modules[name] = stub


_stub_image_analyzer()

# mock 完成后再导入被测模块
from NekoKit.tools.file_store.file_store_tool import FileStoreTool  # noqa: E402
from NekoKit.tools.kv_store.kv_store_tool import KVStoreTool  # noqa: E402


# ---------------------------------------------------------------------------
# 测试用上下文构造
# ---------------------------------------------------------------------------


class _FakeConversationManager:
    def __init__(self, persona_id: str):
        self._persona_id = persona_id

    async def get_curr_conversation_id(self, umo: str) -> str:
        return "cid-1"

    async def get_conversation(self, umo: str, conversation_id: str):
        manager = self

        class _Conversation:
            persona_id = manager._persona_id

        return _Conversation()


class _FakeStarContext:
    def __init__(self, persona_id: str):
        self.conversation_manager = _FakeConversationManager(persona_id)


class _FakeEvent:
    def __init__(self, session_id: str):
        self.unified_msg_origin = f"test:GroupMessage:{session_id}"
        self.session_id = session_id


class _FakeInner:
    def __init__(self, persona_id: str, session_id: str):
        self.event = _FakeEvent(session_id)
        self.context = _FakeStarContext(persona_id)


class FakeContext:
    """模拟 ContextWrapper[AstrAgentContext]"""

    def __init__(self, persona_id: str, session_id: str):
        self.context = _FakeInner(persona_id, session_id)


@pytest.fixture
def fake_context():
    """构造 (persona_id, session_id) -> FakeContext 的工厂"""

    def _make(persona_id: str, session_id: str) -> FakeContext:
        return FakeContext(persona_id, session_id)

    return _make


# ---------------------------------------------------------------------------
# 工具实例夹具
# ---------------------------------------------------------------------------


@pytest.fixture
def kv_tool(tmp_path):
    tool = KVStoreTool()
    tool.initialize(str(tmp_path / "kv"))
    tool.set_config({"ai_isolation": True, "session_scope": False})
    return tool


@pytest.fixture
def kv_tool_sqlite(tmp_path):
    tool = KVStoreTool()
    tool.initialize(str(tmp_path / "kv_sqlite"), use_sqlite=True)
    tool.set_config({"ai_isolation": True, "session_scope": False})
    return tool


@pytest.fixture
def file_tool(tmp_path):
    tool = FileStoreTool()
    tool.initialize(str(tmp_path / "files"))
    tool.set_config({"ai_isolation": True, "session_scope": False})
    return tool


# 常用身份缩写
CAT = ("catgirl", "group1")
CAT_G2 = ("catgirl", "group2")
MAID = ("maid", "group1")
HUMAN = ("catgirl", "group1")  # persona 无所谓，admin 会盖 user 来源
