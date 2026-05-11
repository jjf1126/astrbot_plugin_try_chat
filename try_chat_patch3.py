import os

with open('/AstrBot/data/plugins/astrbot_plugin_try_chat/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_decision_block = """
            decision_prompt = f"{prompt}\\n\\n【最近聊天记录】\\n{history_str}"
            
            provider_id = await self.context.get_current_chat_provider_id(umo)
            if not provider_id:
                return False
                
            decision_model_id = getattr(self.config, "decision_model_id", "")
            if not decision_model_id:
                decision_model_id = provider_id
                
            resp = await self.context.llm_generate(
                chat_provider_id=decision_model_id,
                prompt=decision_prompt
            )
"""

new_decision_block = """
            decision_prompt = f"{prompt}\\n\\n【最近聊天记录】\\n{history_str}"
            
            provider_id = await self.context.get_current_chat_provider_id(umo)
            if not provider_id:
                return False
                
            decision_model_id = getattr(self.config, "decision_model_id", "")
            if not decision_model_id:
                decision_model_id = provider_id

            from astrbot.core.message.message_event_result import MessageEventResult
            from astrbot.core.star.star_handler import EventType, star_handlers_registry
            from astrbot.core.platform.astrbot_message import AstrBotMessage
            from astrbot.core.platform.message_type import MessageType
            from astrbot.core.platform.astr_message_event import AstrMessageEvent
            from astrbot.core.provider.entities import ProviderRequest
            
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
            
            decision_keyword = getattr(self.config, "decision_memory_keyword", "最近的约定")
            
            fake_event = AstrMessageEvent(
                message_str=decision_keyword,
                message_obj=message_obj,
                platform_meta=platform_meta,
                session_id=message_obj.session_id
            )
            
            has_living_memory = False
            for star in self.context.get_all_stars():
                if star.name == "LivingMemory":
                    has_living_memory = True
                    break
                    
            decision_req = ProviderRequest(
                prompt=decision_prompt,
                system_prompt=""
            )
            
            if has_living_memory:
                logger.info(f"TryChat: 判定阶段 - 检测到 LivingMemory，使用关键词 '{decision_keyword}' 调用记忆...")
                try:
                    await call_event_hook(fake_event, EventType.OnLLMRequestEvent, decision_req)
                    logger.info("TryChat: 判定阶段 - 记忆调用完成。")
                except Exception as e:
                    logger.error(f"TryChat: 判定阶段 OnLLMRequestEvent error: {e}")
            else:
                logger.info("TryChat: 判定阶段 - 未检测到 LivingMemory 插件，使用常规流程。")
                
            resp = await self.context.llm_generate(
                chat_provider_id=decision_model_id,
                prompt=decision_req.prompt,
                system_prompt=decision_req.system_prompt
            )
"""

old_trigger_block = """
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
"""

new_trigger_block = """
            fake_event.message_str = "" # 恢复为空，以防影响后续
            
            req = ProviderRequest(
                prompt=full_trigger_prompt,
                system_prompt=sys_prompt if sys_prompt else ""
            )
"""

if old_decision_block in content and old_trigger_block in content:
    content = content.replace(old_decision_block, new_decision_block)
    content = content.replace(old_trigger_block, new_trigger_block)
    with open('/AstrBot/data/plugins/astrbot_plugin_try_chat/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patch 3 applied successfully.")
else:
    print("Old code not found.")
    if old_decision_block not in content:
        print("old_decision_block not found.")
    if old_trigger_block not in content:
        print("old_trigger_block not found.")

