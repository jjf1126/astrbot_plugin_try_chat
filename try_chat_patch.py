import os
import re

with open('/AstrBot/data/plugins/astrbot_plugin_try_chat/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure imports are there
if 'ProviderRequest' not in content:
    content = content.replace('from astrbot.core.message.message_event_result import MessageChain',
        'from astrbot.core.message.message_event_result import MessageChain\nfrom astrbot.core.provider.entities import ProviderRequest\nfrom astrbot.core.pipeline.context_utils import call_event_hook')

old_code = """
            chat_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=full_trigger_prompt,
                system_prompt=sys_prompt if sys_prompt else None
            )
            if not chat_resp or not chat_resp.completion_text:
                return False
                
            reply_text = chat_resp.completion_text
            
            try:
                user_msg = {"role": "user", "content": f"【系统指令】{trigger_prompt}"}
                asst_msg = {"role": "assistant", "content": reply_text}
                await conv_mgr.add_message_pair(curr_cid, user_msg, asst_msg)
            except Exception as e:
                logger.error(f"TryChat: 保存历史记录失败: {e}")
            
            from astrbot.core.message.message_event_result import MessageEventResult
            from astrbot.core.star.star_handler import EventType, star_handlers_registry
            
            message_obj = AstrBotMessage()
            message_obj.type = MessageType.GROUP_MESSAGE if "group" in umo.lower() else MessageType.FRIEND_MESSAGE
            message_obj.session_id = umo.split(":")[-1] if ":" in umo else umo
            message_obj.sender_id = message_obj.session_id
            message_obj.message = []
            message_obj.message_str = ""
            message_obj.message_id = ""
            
            try:
                platform_id = umo.split(":")[0] if ":" in umo else "aiocqhttp"
                platform_inst = self.context.get_platform_inst(platform_id)
                platform_meta = platform_inst.meta()
            except Exception:
                from astrbot.core.platform.platform_metadata import PlatformMetadata
                platform_meta = PlatformMetadata(name="unknown", description="", id="unknown")
            
            fake_event = AstrMessageEvent(
                message_str="",
                message_obj=message_obj,
                platform_meta=platform_meta,
                session_id=message_obj.session_id
            )
"""

new_code = """
            from astrbot.core.message.message_event_result import MessageEventResult
            from astrbot.core.star.star_handler import EventType, star_handlers_registry
            
            message_obj = AstrBotMessage()
            message_obj.type = MessageType.GROUP_MESSAGE if "group" in umo.lower() else MessageType.FRIEND_MESSAGE
            message_obj.session_id = umo.split(":")[-1] if ":" in umo else umo
            message_obj.sender_id = message_obj.session_id
            message_obj.message = []
            message_obj.message_str = ""
            message_obj.message_id = ""
            
            try:
                platform_id = umo.split(":")[0] if ":" in umo else "aiocqhttp"
                platform_inst = self.context.get_platform_inst(platform_id)
                platform_meta = platform_inst.meta()
            except Exception:
                from astrbot.core.platform.platform_metadata import PlatformMetadata
                platform_meta = PlatformMetadata(name="unknown", description="", id="unknown")
            
            fake_event = AstrMessageEvent(
                message_str="",
                message_obj=message_obj,
                platform_meta=platform_meta,
                session_id=message_obj.session_id
            )

            req = ProviderRequest(
                prompt=full_trigger_prompt,
                system_prompt=sys_prompt if sys_prompt else ""
            )
            
            try:
                await call_event_hook(fake_event, EventType.OnLLMRequestEvent, req)
            except Exception as e:
                logger.error(f"TryChat: OnLLMRequestEvent hook error: {e}")

            chat_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=req.prompt,
                system_prompt=req.system_prompt
            )
            if not chat_resp or not chat_resp.completion_text:
                return False
                
            try:
                await call_event_hook(fake_event, EventType.OnLLMResponseEvent, chat_resp)
            except Exception as e:
                logger.error(f"TryChat: OnLLMResponseEvent hook error: {e}")
                
            reply_text = chat_resp.completion_text
            
            try:
                user_msg = {"role": "user", "content": f"【系统指令】{trigger_prompt}"}
                asst_msg = {"role": "assistant", "content": reply_text}
                await conv_mgr.add_message_pair(curr_cid, user_msg, asst_msg)
            except Exception as e:
                logger.error(f"TryChat: 保存历史记录失败: {e}")
"""

content = content.replace(old_code, new_code)

with open('/AstrBot/data/plugins/astrbot_plugin_try_chat/main.py', 'w', encoding='utf-8') as f:
    f.write(content)
