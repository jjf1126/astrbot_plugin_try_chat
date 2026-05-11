import os

with open('/AstrBot/data/plugins/astrbot_plugin_try_chat/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = """
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
"""

new_code = """
            req = ProviderRequest(
                prompt=full_trigger_prompt,
                system_prompt=sys_prompt if sys_prompt else ""
            )
            
            has_living_memory = False
            for star in self.context.get_all_stars():
                if star.name == "LivingMemory":
                    has_living_memory = True
                    break
            
            if has_living_memory:
                logger.info("TryChat: 检测到 LivingMemory 插件，正在调用记忆内容...")
                try:
                    await call_event_hook(fake_event, EventType.OnLLMRequestEvent, req)
                    logger.info("TryChat: 记忆内容调用完成。")
                except Exception as e:
                    logger.error(f"TryChat: OnLLMRequestEvent hook error: {e}")
            else:
                logger.info("TryChat: 未检测到 LivingMemory 插件，使用常规流程。")

            chat_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=req.prompt,
                system_prompt=req.system_prompt
            )
            if not chat_resp or not chat_resp.completion_text:
                return False
                
            if has_living_memory:
                try:
                    await call_event_hook(fake_event, EventType.OnLLMResponseEvent, chat_resp)
                except Exception as e:
                    logger.error(f"TryChat: OnLLMResponseEvent hook error: {e}")
"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('/AstrBot/data/plugins/astrbot_plugin_try_chat/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patch applied successfully.")
else:
    print("Old code not found.")
