
from astrbot.core.agent.message import (
    AssistantMessageSegment,
    TextPart,
    UserMessageSegment,
)
import asyncio
import json
import random
import time
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from astrbot.api import AstrBotConfig
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.provider.entities import ProviderRequest
from astrbot.core.pipeline.context_utils import call_event_hook
from astrbot.core.platform.astrbot_message import AstrBotMessage
from astrbot.core.platform.message_type import MessageType

class TryChatPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.data_file = "data/try_chat_state.json"
        self.last_active_time = {}
        self.task = asyncio.create_task(self.polling_task())

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_user_message(self, event: AstrMessageEvent):
        umo = event.unified_msg_origin
        self.last_active_time[umo] = time.time()
        state = self.get_state()
        base_prob = getattr(self.config, "base_probability", 0.05)
        if umo in state:
            state[umo]["prob"] = base_prob
        else:
            state[umo] = {"prob": base_prob, "last_trigger": 0}
        self.save_state(state)
        
    async def terminate(self):
        if self.task:
            self.task.cancel()

    def get_state(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_state(self, state):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    async def polling_task(self):
        await asyncio.sleep(10)
        while True:
            try:
                await asyncio.sleep(60)
                await self.run_polling()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"TryChat: 轮询任务发生异常: {e}")

    async def run_polling(self):
        enabled_sessions = getattr(self.config, "enabled_sessions", [])
        if not enabled_sessions:
            return
            
        state = self.get_state()
        base_prob = getattr(self.config, "base_probability", 0.05)
        step_prob = getattr(self.config, "probability_step", 0.02)
        interval = getattr(self.config, "polling_interval", 1800)
        fluctuation = getattr(self.config, "interval_fluctuation", 0)
        curr_time = time.time()
        
        for umo in enabled_sessions:
            umo_state = state.get(umo, {"prob": base_prob, "last_trigger": 0})
            
            last_active = self.last_active_time.get(umo, 0)
            last_trigger = umo_state.get("last_trigger", 0)
            
            # 加上设定的随机波动范围
            actual_interval = interval
            if fluctuation > 0:
                actual_interval += random.randint(-fluctuation, fluctuation)
            
            if curr_time - max(last_active, last_trigger) < actual_interval:
                continue
                
            prob = umo_state.get("prob", base_prob)
            
            if random.random() <= prob:
                triggered = await self.do_decision_and_trigger(umo)
                if triggered:
                    umo_state["prob"] = base_prob
                    umo_state["last_trigger"] = curr_time
                else:
                    umo_state["prob"] = min(1.0, prob + step_prob)
                    umo_state["last_trigger"] = curr_time
            else:
                umo_state["prob"] = min(1.0, prob + step_prob)
                umo_state["last_trigger"] = curr_time
                
            state[umo] = umo_state
            
        self.save_state(state)

    async def do_decision_and_trigger(self, umo: str, event=None):
        try:
            import os
            if os.path.exists("data/try_chat_error.txt"):
                os.remove("data/try_chat_error.txt")
            conv_mgr = self.context.conversation_manager
            curr_cid = await conv_mgr.get_curr_conversation_id(umo)
            if not curr_cid:
                curr_cid = await conv_mgr.new_conversation(umo)
            
            conv = await conv_mgr.get_conversation(umo, curr_cid)
            if not conv:
                return False
                
            history_list = []
            if conv.history:
                try:
                    if isinstance(conv.history, str):
                        history_list = json.loads(conv.history)
                    else:
                        history_list = conv.history
                except Exception:
                    pass
                    
            history_str = ""
            history_len = getattr(self.config, "history_len", 10)
            for msg in history_list[-history_len:]:
                if not isinstance(msg, dict):
                    continue
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role == "user":
                    history_str += f"用户: {content}\n"
                elif role == "assistant":
                    history_str += f"AI: {content}\n" 
                    
            tz = ZoneInfo('Asia/Shanghai')
            curr_time = datetime.now(tz).strftime("%Y年%m月%d日 %H:%M:%S")
            
            prompt_tmpl = getattr(self.config, "decision_prompt", "你是一个贴心的朋友。请阅读以下最近的聊天记录，并结合当前时间 {{current time}}，判断现在是否适合主动找我聊天。如果在深夜且之前已经互道晚安，请回复 NO。如果距离上次聊天已经过了很久，且现在是白天，请回复 YES。只能回复 YES 或 NO。")
            prompt = prompt_tmpl.replace("{{current time}}", curr_time).replace("{{current_time}}", curr_time)
            decision_prompt = f"{prompt}\n\n【最近聊天记录】\n{history_str}"
            
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
                if star.name and "livingmemory" in star.name.lower():
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
            if not resp or not resp.completion_text:
                return False
                
            decision_text = resp.completion_text.strip().upper()
            if "YES" not in decision_text:
                return False
                
            sys_prompt = ""
            if conv.persona_id:
                try:
                    persona = self.context.persona_manager.get_persona(conv.persona_id)
                    sys_prompt = persona.system_prompt
                except Exception:
                    pass
                    
            trigger_prompt = getattr(self.config, "trigger_prompt", "现在请根据当前时间和我们的关系，主动向我发起一次聊天。")
            if "{{current_time}}" in trigger_prompt:
                trigger_prompt = trigger_prompt.replace("{{current_time}}", curr_time)
            full_trigger_prompt = f"【背景提示：当前时间是 {curr_time}，请根据以下历史记录主动发话。】\n【历史记录】\n{history_str}\n\n【系统指令】{trigger_prompt}"
            
            if sys_prompt:
                pass

            # if event:
            #     return event.request_llm(prompt=full_trigger_prompt, conversation=conv)

            fake_event.message_str = "" # 恢复为空，以防影响后续
            
            req = ProviderRequest(
                prompt=full_trigger_prompt,
                system_prompt=sys_prompt if sys_prompt else ""
            )
            
            has_living_memory = False
            for star in self.context.get_all_stars():
                if star.name and "livingmemory" in star.name.lower():
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
                
            reply_text = chat_resp.completion_text
            
            try:
                user_msg = {"role": "user", "content": f"【系统指令】{trigger_prompt}"}
                asst_msg = {"role": "assistant", "content": reply_text}
                await conv_mgr.add_message_pair(curr_cid, user_msg, asst_msg)
            except Exception as e:
                logger.error(f"TryChat: 保存历史记录失败: {e}")
            
            res = MessageEventResult().message(reply_text)
            fake_event.set_result(res)
            
            handlers = star_handlers_registry.get_handlers_by_event_type(EventType.OnDecoratingResultEvent)
            for handler in handlers:
                try:
                    await handler.handler(fake_event)
                except Exception:
                    pass
                    
            final_res = fake_event.get_result()
            if final_res is not None:
                await self.context.send_message(umo, final_res)
                
                try:
                    platform_id = umo.split(":")[0] if ":" in umo else "aiocqhttp"
                    user_id = umo.split(":")[-1] if ":" in umo else umo
                    content_dict = {"type": "bot", "message": [{"type": "plain", "text": reply_text}]}
                    await self.context.message_history_manager.insert(
                        platform_id=platform_id,
                        user_id=user_id,
                        content=content_dict,
                        sender_id="bot",
                        sender_name="bot"
                    )
                except Exception as e:
                    logger.error(f"TryChat: 保存平台消息历史失败: {e}")
            
            return True
        except Exception as e:
            import traceback
            with open("data/try_chat_error.txt", "w") as f:
                f.write(traceback.format_exc())
            logger.error(f"TryChat: do_decision_and_trigger 发生异常: {e}")
            return False

    @filter.command("try_chat_status")
    async def try_chat_status(self, event: AstrMessageEvent):
        '''查看当前所有开启自动聊天会话的状态与下次触发的概率信息'''
        enabled_sessions = getattr(self.config, "enabled_sessions", [])
        if not enabled_sessions:
            yield event.plain_result("当前未在配置中启用任何自动聊天会话。")
            return
            
        state = self.get_state()
        base_prob = getattr(self.config, "base_probability", 0.05)
        
        lines = ["【自动聊天会话状态】"]
        for umo in enabled_sessions:
            umo_state = state.get(umo, {"prob": base_prob, "last_trigger": 0})
            prob = umo_state.get("prob", base_prob)
            last_t = umo_state.get("last_trigger", 0)
            last_a = self.last_active_time.get(umo, 0)
            
            tz = ZoneInfo('Asia/Shanghai')
            if last_t > 0:
                last_time_str = datetime.fromtimestamp(last_t, tz=tz).strftime("%m-%d %H:%M")
            else:
                last_time_str = "从未判定"
                
            if last_a > 0:
                last_active_str = datetime.fromtimestamp(last_a, tz=tz).strftime("%m-%d %H:%M")
            else:
                last_active_str = "暂无记录"
                
            lines.append(f"会话 [{umo}]\n- 当前概率: {prob * 100:.1f}%\n- 状态: 运行中\n- 上次判定: {last_time_str}\n- 最后活跃: {last_active_str}")
            
        yield event.plain_result("\n".join(lines))

    @filter.command("try_chat_force")
    async def try_chat_force(self, event: AstrMessageEvent):
        '''强制对当前会话进行一次主动聊天判定与触发'''
        umo = event.unified_msg_origin
        yield event.plain_result(f"已接收强制触发指令，开始对当前会话进行智能聊天判定...")
        
        try:
            result = await self.do_decision_and_trigger(umo, event)
            
            if result:
                state = self.get_state()
                base_prob = getattr(self.config, "base_probability", 0.05)
                if umo not in state:
                    state[umo] = {}
                state[umo]["prob"] = base_prob
                state[umo]["last_trigger"] = time.time()
                self.save_state(state)
                if isinstance(result, bool):
                    pass
                else:
                    yield result
            else:
                import os
                err_msg = ""
                if os.path.exists("data/try_chat_error.txt"):
                    with open("data/try_chat_error.txt", "r") as f:
                        err_msg = f.read()
                if err_msg:
                    yield event.plain_result(f"执行过程遭遇异常：\n{err_msg[:500]}")
                else:
                    yield event.plain_result("判定未通过：大模型认为当前时机不适合发送消息。")
        except Exception as e:
            import traceback
            yield event.plain_result(f"发生了未捕获异常：\n{traceback.format_exc()[:500]}")
