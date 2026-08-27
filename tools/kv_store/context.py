from astrbot.api import logger
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.astr_agent_context import AstrAgentContext


async def get_ai_id(context: ContextWrapper[AstrAgentContext]) -> str:
    """获取当前 AI 的唯一标识（persona_id）。

    只用 persona 而不含 provider：provider 是模型后端（含 fallback 切换），
    人格才是 AI 身份，混入 provider 会导致 fallback 时数据归属碎片化。
    """
    try:
        event = context.context.event
        ctx = context.context.context

        persona_id = "default_persona"
        try:
            umo = event.unified_msg_origin
            conv_mgr = ctx.conversation_manager
            curr_cid = await conv_mgr.get_curr_conversation_id(umo)
            if curr_cid:
                conv = await conv_mgr.get_conversation(umo, curr_cid)
                if conv and conv.persona_id:
                    persona_id = conv.persona_id
        except Exception as e:
            logger.debug(f"[KVStore] 获取persona_id失败: {e}")

        return "".join(c if c.isalnum() or c in "-_:" else "_" for c in persona_id)
    except Exception as e:
        logger.warning(f"[KVStore] 获取AI标识异常: {e}")
        return "default_persona"


def get_session_id(context: ContextWrapper[AstrAgentContext]) -> str:
    """获取当前会话的唯一标识"""
    event = context.context.event
    session_id = getattr(event, "session_id", None)
    if session_id:
        return str(session_id)
    umo = getattr(event, "unified_msg_origin", None)
    if umo:
        return str(umo)
    return "default_session"


async def resolve_identity(context) -> tuple:
    """一次性解析 (ai_id, session_id)，供 KV/文件存储构建作用域使用"""
    ai_id = "default_persona"
    session_id = "default_session"
    if context:
        try:
            ai_id = await get_ai_id(context)
        except Exception as e:
            logger.debug(f"[KVStore] 解析ai_id失败: {e}")
        try:
            session_id = get_session_id(context)
        except Exception as e:
            logger.debug(f"[KVStore] 解析session_id失败: {e}")
    return ai_id, session_id
