from astrbot.api import logger
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.astr_agent_context import AstrAgentContext


async def get_ai_id(context: ContextWrapper[AstrAgentContext]) -> str:
    """获取当前 AI 的唯一标识"""
    try:
        event = context.context.event
        ctx = context.context.context

        umo = event.unified_msg_origin
        provider_id = await ctx.get_current_chat_provider_id(umo=umo)
        provider_id = provider_id or "default_provider"

        persona_id = "default_persona"
        try:
            conv_mgr = ctx.conversation_manager
            curr_cid = await conv_mgr.get_curr_conversation_id(umo)
            if curr_cid:
                conv = await conv_mgr.get_conversation(umo, curr_cid)
                if conv and conv.persona_id:
                    persona_id = conv.persona_id
        except Exception as e:
            logger.debug(f"[KVStore] 获取persona_id失败: {e}")

        ai_id = f"{provider_id}:{persona_id}"
        return "".join(c if c.isalnum() or c in "-_:" else "_" for c in ai_id)
    except Exception as e:
        logger.warning(f"[KVStore] 获取AI标识异常: {e}")
        return "default_ai"


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
