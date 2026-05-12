import os

with open('/AstrBot/data/plugins/astrbot_plugin_try_chat/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_decision = """            resp = await self.context.llm_generate(
                chat_provider_id=decision_model_id,
                prompt=decision_req.prompt,
                system_prompt=decision_req.system_prompt
            )"""

new_decision = """            max_retries = getattr(self.config, "max_retries", 3)
            retry_count = 0
            resp = None
            while retry_count < max_retries:
                try:
                    resp = await self.context.llm_generate(
                        chat_provider_id=decision_model_id,
                        prompt=decision_req.prompt,
                        system_prompt=decision_req.system_prompt
                    )
                    break
                except Exception as e:
                    retry_count += 1
                    logger.error(f"TryChat: 判定阶段大模型请求失败 (第 {retry_count}/{max_retries} 次重试): {e}")
                    if retry_count >= max_retries:
                        raise e
                    await asyncio.sleep(2)"""

old_chat = """            chat_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=req.prompt,
                system_prompt=req.system_prompt
            )"""

new_chat = """            retry_count = 0
            chat_resp = None
            while retry_count < max_retries:
                try:
                    chat_resp = await self.context.llm_generate(
                        chat_provider_id=provider_id,
                        prompt=req.prompt,
                        system_prompt=req.system_prompt
                    )
                    break
                except Exception as e:
                    retry_count += 1
                    logger.error(f"TryChat: 触发阶段大模型请求失败 (第 {retry_count}/{max_retries} 次重试): {e}")
                    if retry_count >= max_retries:
                        raise e
                    await asyncio.sleep(2)"""

if old_decision in content and old_chat in content:
    content = content.replace(old_decision, new_decision)
    content = content.replace(old_chat, new_chat)
    with open('/AstrBot/data/plugins/astrbot_plugin_try_chat/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patch applied successfully.")
else:
    print("Old code not found!")
