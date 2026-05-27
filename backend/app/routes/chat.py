from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.llm_service import llm_service
from app.services.tts_service import tts_service
from app.services.character_manager import character_manager
from app.services.time_awareness_service import time_awareness_service
from app.services.weather_awareness_service import weather_awareness_service
from app.services.context_manager import context_manager
from app.services.worldbook_manager import worldbook_manager
from app.services.auto_summary_service import auto_summary_service
from app.services.author_note_service import author_note_service
from app.plugins.plugin_base import plugin_manager
from app.models.database import get_db, User, ChatMessage, CharacterMemory, MemoryEvent, PromptTemplate, AuthorNoteConfig
import json
import base64
import re
import asyncio

router = APIRouter(prefix="/api/chat", tags=["聊天"])

class ChatRequest(BaseModel):
    """聊天请求"""
    user_id: int
    message: str
    enable_tts: bool = True
    voice: Optional[str] = None
    system_context: Optional[str] = None

class ImageChatRequest(BaseModel):
    """图片聊天请求"""
    user_id: int
    image_base64: str
    enable_tts: bool = True
    voice: Optional[str] = None

class ChatResponse(BaseModel):
    """聊天响应"""
    success: bool
    reply: str
    audio_base64: Optional[str] = None
    metadata: Dict[str, Any] = {}

@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest, background_tasks: BackgroundTasks, db = Depends(get_db)):
    """
    发送消息并获取AI回复
    这是核心接口，处理完整的聊天流程
    """
    try:
        # 1. 触发插件 - 消息接收
        await plugin_manager.execute_all(
            "on_message_received",
            message=request.message,
            user_id=str(request.user_id)
        )
        
        # 2. 获取当前角色
        current_character = character_manager.get_current_character()
        
        # 3. 获取用户历史消息（上下文）- 只获取当前角色的记录
        character_id = current_character.id if current_character else None
        query = db.query(ChatMessage).filter(
            ChatMessage.user_id == request.user_id
        )
        if character_id:
            query = query.filter(ChatMessage.character_id == character_id)
        history = query.order_by(ChatMessage.created_at.desc()).limit(10).all()
        
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(history)
        ]
        
        # 4.5 插入Author's Note（如果启用）
        if character_id:
            try:
                author_note_config = db.query(AuthorNoteConfig).filter(
                    AuthorNoteConfig.user_id == request.user_id,
                    AuthorNoteConfig.character_id == character_id,
                    AuthorNoteConfig.is_enabled == True
                ).first()
                
                if author_note_config:
                    config_dict = {
                        "content": author_note_config.content or "",
                        "depth": author_note_config.depth or 3,
                        "interval": author_note_config.interval or 4,
                        "position": author_note_config.position or "after",
                        "enabled": True
                    }
                    
                    # 调用服务插入Author's Note
                    messages = author_note_service.insert_author_note(messages, config_dict)
                    
            except Exception as e:
                print(f"[Author's Note] 加载配置失败: {str(e)}")
        
        # 5. 构建系统提示词（使用角色的 system_prompt）
        base_prompt = current_character.system_prompt if current_character else """你是一个友好、有帮助的AI助手。
你的特点是：
- 语气温和、耐心
- 回答简洁明了
- 善于倾听和理解用户
- 会根据用户的偏好调整回复"""
        
        # 添加环境感知信息到系统提示词
        time_info = time_awareness_service.get_current_time_info()
        env_context = f"""

【当前环境信息】
- 当前时间：{time_info['time_str']}（{time_info['weekday_name']} {time_info['period_name']}）
- 时段提示：{time_awareness_service.get_care_tip()}

请根据当前时间和时段，在回复中自然地体现对用户的关怀。例如：
- 早上可以问候早安，提醒用户新的一天开始了
- 中午可以提醒用户吃午饭
- 晚上可以提醒用户早点休息
- 深夜要关心用户是否还没睡，提醒注意身体

注意：环境信息只是参考，要自然地融入对话中，不要生硬地提及。"""
        
        # 获取世界书、记忆、足迹数据用于智能上下文
        character_id = current_character.id if current_character else None
        worldbook_entries = []
        memories = []
        footprints = []
        prompt_templates = []
        memory_ids_to_update = []  # 记录需要更新访问时间的记忆ID
        
        if character_id:
            # 获取激活的提示词模板（提升体验感）
            try:
                prompt_templates = db.query(PromptTemplate).filter(
                    PromptTemplate.user_id == request.user_id,
                    PromptTemplate.is_enabled == True,
                    PromptTemplate.is_active == True,
                    (PromptTemplate.character_id == character_id) | (PromptTemplate.character_id == None)
                ).order_by(PromptTemplate.priority.desc()).all()
            except:
                pass
            
            # 获取激活的世界书条目（只加载当前角色的条目 + 全局条目）
            try:
                worldbook_data = worldbook_manager.list_entries(active_only=True, character_id=character_id)
                worldbook_entries = [
                    {
                        'id': w.id,
                        'title': w.title,
                        'content': w.content,
                        'tags': w.tags or [],
                        'is_active': w.is_active,
                        'character_id': w.character_id
                    }
                    for w in worldbook_data
                ]
            except:
                pass
            
            # 获取角色记忆 - 优先获取重要的和最近访问的
            try:
                from sqlalchemy import desc
                memory_objs = db.query(CharacterMemory).filter(
                    CharacterMemory.character_id == character_id,
                    CharacterMemory.user_id == request.user_id,
                    CharacterMemory.is_active == True
                ).order_by(
                    desc(CharacterMemory.importance), 
                    desc(CharacterMemory.last_accessed)
                ).all()
                memories = [
                    {
                        'id': m.id,
                        'title': m.title,
                        'content': m.content,
                        'memory_type': m.memory_type,
                        'importance': m.importance,
                        'tags': m.tags or [],
                        'is_active': m.is_active,
                        'access_count': m.access_count if hasattr(m, 'access_count') else 0,
                        'last_accessed': m.last_accessed.isoformat() if hasattr(m, 'last_accessed') and m.last_accessed else None
                    }
                    for m in memory_objs
                ]
            except Exception as e:
                print(f"获取记忆出错: {e}")
                pass
            
            # 获取足迹
            try:
                footprints = db.query(MemoryEvent).filter(
                    MemoryEvent.character_id == character_id,
                    MemoryEvent.user_id == request.user_id
                ).order_by(MemoryEvent.importance.desc(), MemoryEvent.created_at.desc()).limit(30).all()
                footprints = [
                    {
                        'id': f.id,
                        'title': f.title,
                        'description': f.description,
                        'footprint_type': f.event_type,  # main/side -> 映射为足迹类型
                        'importance': f.importance,
                        'tags': f.tags or []
                    }
                    for f in footprints
                ]
            except:
                pass
        
        # 使用智能上下文管理器构建提示词 - 并获取被选中的记忆
        from sqlalchemy import desc
        
        # 先提取关键词，用于选择相关记忆
        keywords = context_manager.extract_keywords(request.message)
        
        # 选择相关记忆
        relevant_memories = context_manager.select_relevant_memories(keywords, memories)
        
        # 选择相关足迹
        relevant_footprints = context_manager.select_relevant_footprints(keywords, footprints)
        
        # 记录被选中的记忆ID，稍后更新访问时间
        selected_memory_ids = [m['id'] for m in relevant_memories]
        
        # 构建完整提示词
        system_prompt = context_manager.build_context_prompt(
            character_prompt=base_prompt + env_context,
            user_message=request.message,
            worldbook_entries=worldbook_entries,
            memories=memories,
            footprints=footprints,
            prompt_templates=prompt_templates
        )
        
        if request.system_context:
            system_prompt += request.system_context
        
        # 5. 调用LLM获取回复
        reply = await llm_service.chat_completion(
            messages=messages + [{"role": "user", "content": request.message}],
            system_prompt=system_prompt
        )
        
        # 6. 保存用户消息到数据库
        user_msg = ChatMessage(
            user_id=request.user_id,
            character_id=current_character.id if current_character else None,
            role="user",
            content=request.message
        )
        db.add(user_msg)
        
        # 7. 保存AI回复到数据库
        ai_msg = ChatMessage(
            user_id=request.user_id,
            character_id=current_character.id if current_character else None,
            role="assistant",
            content=reply
        )
        db.add(ai_msg)
        
        db.flush()  # 获取消息ID但不提交
        
        # 8. 将TTS和用户信息提取放到后台任务，不阻塞响应
        if request.enable_tts:
            background_tasks.add_task(
                generate_tts_background,
                reply=reply,
                voice=request.voice,
                user_id=request.user_id
            )
        
        # 9. 后台提取用户信息
        background_tasks.add_task(
            extract_user_info_background,
            message=request.message
        )
        
        # 10. 检查是否需要自动提取足迹（后台异步处理）
        if current_character:
            background_tasks.add_task(
                auto_extract_footprints_if_enabled,
                user_id=request.user_id,
                character_id=current_character.id,
                db=db
            )
        
        # 11. 更新被选中记忆的访问时间（后台）
        if current_character and selected_memory_ids:
            background_tasks.add_task(
                update_memory_access_time,
                db=db,
                user_id=request.user_id,
                character_id=current_character.id,
                memory_ids=selected_memory_ids
            )
        
        # 12. 检查是否需要自动提取记忆（后台异步处理）
        if current_character:
            background_tasks.add_task(
                auto_extract_memories_if_enabled,
                user_id=request.user_id,
                character_id=current_character.id,
                user_message=request.message,
                ai_response=reply,
                db=db
            )
        
        # 13. 检查是否需要自动摘要（后台异步处理，避免阻塞响应）
        if current_character:
            background_tasks.add_task(
                check_and_auto_summarize,
                character_id=current_character.id,
                user_id=request.user_id
            )
        
        db.commit()
        
        # 立即返回，不等待TTS和用户信息提取
        return ChatResponse(
            success=True,
            reply=reply,
            audio_base64=None,  # TTS在后台生成，本次不返回
            metadata={
                "user_msg_id": user_msg.id,
                "ai_msg_id": ai_msg.id
            }
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def generate_tts_background(reply: str, voice: Optional[str], user_id: int):
    """后台生成TTS语音"""
    try:
        audio_base64 = await tts_service.text_to_speech_base64(reply, voice=voice)
        if audio_base64:
            print(f"[TTS后台] 为用户 {user_id} 生成语音成功")
    except Exception as e:
        print(f"[TTS后台] 语音合成失败: {str(e)}")


async def extract_user_info_background(message: str):
    """后台提取用户信息"""
    try:
        user_info = await llm_service.extract_user_info(message)
        if user_info:
            print(f"[后台提取] 提取到用户信息: {user_info}")
    except Exception as e:
        print(f"[后台提取] 用户信息提取失败: {str(e)}")


async def auto_extract_footprints_if_enabled(user_id: int, character_id: str, db):
    """
    🚀 智能主动记录系统 - 升级版
    
    功能特性：
    1. ✅ 多策略降级解析（三级保险）
    2. ✅ 智能触发逻辑（轮数 + 内容检测）
    3. ✅ 避免重复处理
    4. ✅ 详细日志记录
    """
    from app.services.context_log_service import context_log_service
    from app.services.footprint_config_service import footprint_config_service
    from app.services.memory_event_service import memory_event_service
    from app.routes.memory_events import (
        parse_simple_table_format,
        extract_entities_from_text,
        smart_fix_json
    )
    
    import json
    import re
    
    try:
        # ===== 第1步：获取配置 =====
        config = footprint_config_service.get_config(db, user_id, character_id)
        
        # 🎯 默认启用自动提取（如果没有配置或未明确禁用）
        auto_enabled = True  # 默认启用
        if config:
            if hasattr(config, 'auto_extract_enabled') and config.auto_extract_enabled is not None:
                auto_enabled = config.auto_extract_enabled
        
        if not auto_enabled:
            return
        
        # ===== 第2步：智能触发判断 =====
        chat_count = footprint_config_service.increment_chat_count(db, user_id, character_id)
        extract_interval = config.extract_interval if config and config.extract_interval else 5
        
        # 获取最近的对话用于内容检测
        recent_messages = db.query(ChatMessage).filter(
            ChatMessage.user_id == user_id,
            ChatMessage.character_id == character_id,
            ChatMessage.role.in_(["user", "assistant"])
        ).order_by(ChatMessage.created_at.desc()).limit(6).all()
        
        # 🔍 内容检测：检查是否包含关键信息
        should_trigger = False
        trigger_reason = ""
        
        # 触发条件1：达到轮数间隔
        if chat_count >= extract_interval:
            should_trigger = True
            trigger_reason = f"轮数触发: {chat_count} >= {extract_interval}"
        
        # 触发条件2：检测到关键实体关键词（立即触发）
        if not should_trigger and recent_messages:
            keywords = [
                '村庄', '城镇', '城堡', '铁匠铺', '商店', '酒馆', '森林', '山洞',
                '老王', '村长', '商人', '公主', '国王', '精灵', '矮人',
                '剑', '刀', '弓', '盾', '药水', '宝石', '钥匙', '宝物',
                '发现', '秘密', '线索', '任务', '获得', '打造'
            ]
            
            recent_text = " ".join([msg.content for msg in recent_messages[:4]])
            found_keywords = [kw for kw in keywords if kw in recent_text]
            
            if len(found_keywords) >= 2:
                should_trigger = True
                trigger_reason = f"内容检测: 发现 {len(found_keywords)} 个关键词 ({', '.join(found_keywords[:3])})"
        
        if not should_trigger:
            print(f"[足迹自动] 跳过 - 轮数: {chat_count}/{extract_interval}, 无关键信息")
            return
        
        # ===== 第3步：执行智能解析 =====
        print(f"\n{'='*70}")
        print(f"🚀 [足迹自动] 开始主动记录")
        print(f"   角色 ID: {character_id}")
        print(f"   用户 ID: {user_id}")
        print(f"   触发原因: {trigger_reason}")
        print(f"   当前轮数: {chat_count}")
        print(f"{'='*70}\n")
        
        # 记录处理中的日志
        context_log_service.create_log(
            db=db,
            user_id=user_id,
            character_id=character_id,
            log_type="auto_extract",
            status="processing",
            message=f"[升级版] 自动触发: {trigger_reason}",
            context_count=len(recent_messages) if recent_messages else 0
        )
        
        # 获取聊天文本
        context_limit = config.context_limit if config and config.context_limit else 30
        
        chat_messages = db.query(ChatMessage).filter(
            ChatMessage.user_id == user_id,
            ChatMessage.character_id == character_id,
            ChatMessage.role.in_(["user", "assistant"])
        ).order_by(ChatMessage.created_at.desc()).limit(context_limit).all()
        
        if not chat_messages or len(chat_messages) < 3:
            context_log_service.create_log(
                db=db,
                user_id=user_id,
                character_id=character_id,
                log_type="auto_extract",
                status="success",
                message="聊天记录不足，跳过",
                context_count=len(chat_messages) if chat_messages else 0
            )
            return
        
        chat_text = "\n".join([
            f"{'用户' if msg.role == 'user' else '角色'}: {msg.content}"
            for msg in reversed(chat_messages)
        ])
        
        # ===== 多策略降级解析系统 =====
        footprints_data = None
        parse_method = "未知"
        
        # 【第1级】标准JSON模式（使用层级化知识图谱提示词）
        print("[第1级] 📋 尝试标准JSON解析...")
        try:
            prompt_v1 = f"""你是一个专业的**层级化知识图谱构建师**。从以下角色扮演对话中提取实体并构建**清晰的树形层级关系图**。

## 核心要求：生成树形层级结构
按照从大到小、从整体到局部建立父子关系：
- 大地点 → 小地点 → 人物 → 物品
- 主事件 → 子事件 → 相关发现

## 实体类型：
- location（地点）：村庄、城镇、城堡、商店等
- person（人物）：NPC、商人、村民等
- item（物品）：道具、装备、物品等
- discovery（发现）：秘密、线索、信息等
- main（主线事件）：关键剧情、重要进展

## 关系类型：
- 属于（belongs_to）：地点包含关系
- 工作于（works_at）：人物工作地点
- 打造者（crafted_by）：物品制造者
- 获得于（obtained_at）：物品获得地点
- 位于（located_at）：位置关系
- 关联（related_to）：一般关联

## 输出格式（必须是合法JSON数组）：
[
    {{
        "title": "名称",
        "entity_type": "location|person|item|discovery|main",
        "description": "详细描述",
        "parent_title": "父节点名称（没有则为null）",
        "hierarchy_relation": "关系类型（没有则为null）",
        "relations": [],
        "importance": 1-10,
        "tags": ["类型标签"]
    }}
]

## 对话内容：
{chat_text}

请输出JSON数组:"""

            response = await llm_service.chat_completion(
                messages=[{"role": "user", "content": prompt_v1}],
                temperature=0.3,
                max_tokens=2500
            )
            
            content = (response or "").strip()
            print(f"  AI响应长度: {len(content)}")
            print(f"  前150字符: {repr(content[:150])}")
            
            if content:
                import json as json_module
                
                # 尝试直接解析
                try:
                    footprints_data = json_module.loads(content)
                    if isinstance(footprints_data, list) and len(footprints_data) > 0:
                        parse_method = "✅ 标准JSON"
                        print(f"[第1级成功] {parse_method} - 共 {len(footprints_data)} 个实体")
                except json_module.JSONDecodeError:
                    # 尝试修复JSON
                    fixed_json = smart_fix_json(content)
                    if fixed_json:
                        try:
                            footprints_data = json_module.loads(fixed_json)
                            if isinstance(footprints_data, list) and len(footprints_data) > 0:
                                parse_method = "✅ 修复JSON"
                                print(f"[第1级成功] {parse_method} - 共 {len(footprints_data)} 个实体")
                        except:
                            pass
        except Exception as e:
            print(f"[第1级失败] {str(e)[:80]}")
        
        # 【第2级】简单表格格式（如果第1级失败）
        if not footprints_data:
            print("\n[第2级] 📊 降级到简单表格格式...")
            
            prompt_simple = f"""从以下角色扮演对话中提取实体信息。

请用简单的表格格式输出，每行一个实体，用竖线|分隔：
格式: 名称|类型|父节点|关系|重要度

示例:
神圣村庄|location|||8
铁匠铺|location|神圣村庄|属于|8
老王|person|铁匠铺|工作于|7
精钢剑|item|老王|打造者|6

类型只能是: location/person/item/discovery/main
重要度: 1-10的数字

对话内容:
{chat_text}

输出表格:"""
            
            try:
                response_simple = await llm_service.chat_completion(
                    messages=[{"role": "user", "content": prompt_simple}],
                    temperature=0.3,
                    max_tokens=1500
                )
                
                content_simple = (response_simple or "").strip()
                
                if content_simple:
                    footprints_data = parse_simple_table_format(content_simple)
                    if footprints_data and len(footprints_data) > 0:
                        parse_method = "✅ 简单表格"
                        print(f"[第2级成功] {parse_method} - 共 {len(footprints_data)} 个实体")
                    else:
                        print("[第2级失败] 无法从简单格式中提取有效数据")
            except Exception as e:
                print(f"[第2级异常] {str(e)[:80]}")
        
        # 【第3级】纯文本关键词提取（最终后备）
        if not footprints_data or len(footprints_data) == 0:
            print("\n[第3级] 🔍 最终后备：纯文本关键词提取...")
            
            try:
                footprints_data = extract_entities_from_text("", chat_text)
                if footprints_data and len(footprints_data) > 0:
                    parse_method = "✅ 文本提取"
                    print(f"[第3级成功] {parse_method} - 共 {len(footprints_data)} 个实体")
                else:
                    print("[第3级失败] 无法提取任何实体")
            except Exception as e:
                print(f"[第3级异常] {str(e)[:80]}")
        
        # ===== 第4步：保存结果 =====
        if not footprints_data or len(footprints_data) == 0:
            print("\n[足迹自动] ⚠️ 未提取到任何实体，跳过保存")
            context_log_service.create_log(
                db=db,
                user_id=user_id,
                character_id=character_id,
                log_type="auto_extract",
                status="success",
                message=f"未提取到实体（方法: {parse_method}）",
                extracted_count=0
            )
            return
        
        # 获取现有事件用于去重和更新
        existing_events = memory_event_service.get_events_by_character(
            db=db,
            user_id=user_id,
            character_id=character_id
        )
        
        title_to_event = {event.title: event for event in existing_events}
        
        created_count = 0
        updated_count = 0
        
        for fp_data in footprints_data:
            parent_event_id = None
            
            # 查找父节点
            if fp_data.get("parent_title"):
                parent_event = title_to_event.get(fp_data["parent_title"])
                if parent_event:
                    parent_event_id = parent_event.id
            
            # 判断是更新还是创建
            if fp_data["title"] in title_to_event:
                # 更新现有事件
                existing_event = title_to_event[fp_data["title"]]
                memory_event_service.update_event(
                    db=db,
                    event_id=existing_event.id,
                    user_id=user_id,
                    character_id=character_id,
                    description=fp_data.get("description", ""),
                    importance=fp_data.get("importance", 5),
                    tags=fp_data.get("tags", [])
                )
                updated_count += 1
            else:
                # 创建新事件
                entity_type = fp_data.get("entity_type", "discovery")
                
                event_type_mapping = {
                    "location": "side",
                    "person": "side",
                    "item": "side",
                    "discovery": "side",
                    "main": "main"
                }
                event_type = event_type_mapping.get(entity_type, "side")
                
                event = memory_event_service.create_event(
                    db=db,
                    user_id=user_id,
                    character_id=character_id,
                    title=fp_data["title"],
                    description=fp_data.get("description", f"{fp_data['title']} - 从对话中自动提取"),
                    event_type=event_type,
                    parent_event_id=parent_event_id,
                    chat_context=None,
                    importance=fp_data.get("importance", 5),
                    tags=fp_data.get("tags", [entity_type])
                )
                title_to_event[fp_data["title"]] = event
                created_count += 1
        
        # ===== 第5步：记录日志并重置计数器 =====
        print(f"\n{'='*70}")
        print(f"🎉 [足迹自动] 记录完成！")
        print(f"   使用方法: {parse_method}")
        print(f"   新建节点: {created_count} 个")
        print(f"   更新节点: {updated_count} 个")
        print(f"   总计处理: {len(footprints_data)} 个实体")
        print(f"{'='*70}\n")
        
        context_log_service.create_log(
            db=db,
            user_id=user_id,
            character_id=character_id,
            log_type="auto_extract",
            status="success",
            message=f"[升级版] 自动提取完成: 新建{created_count}, 更新{updated_count} (方法: {parse_method})",
            context_count=context_limit,
            extracted_count=created_count,
            updated_count=updated_count
        )
        
        # 重置聊天计数器
        footprint_config_service.reset_chat_count(db, user_id, character_id)
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ [足迹自动] 失败: {error_msg}")
        
        try:
            context_log_service.create_log(
                db=db,
                user_id=user_id,
                character_id=character_id,
                log_type="auto_extract",
                status="failed",
                message=f"自动提取失败: {error_msg}",
                error_message=error_msg
            )
        except:
            pass


async def update_memory_access_time(db, user_id: int, character_id: str, memory_ids: list):
    """更新记忆的访问时间和访问次数"""
    try:
        from datetime import datetime, UTC
        
        # 获取需要更新的记忆
        memories_to_update = db.query(CharacterMemory).filter(
            CharacterMemory.id.in_(memory_ids),
            CharacterMemory.user_id == user_id,
            CharacterMemory.character_id == character_id
        ).all()
        
        for memory in memories_to_update:
            # 更新访问时间和访问次数
            memory.last_accessed = datetime.now(UTC)
            memory.access_count = (memory.access_count or 0) + 1
        
        db.commit()
        print(f"[记忆更新] 更新了 {len(memories_to_update)} 条记忆的访问时间")
        
    except Exception as e:
        print(f"[记忆更新] 更新访问时间失败: {str(e)}")
        db.rollback()


async def check_and_auto_summarize(character_id: str, user_id: int):
    """
    后台任务：检查并执行自动摘要
    在每次发送消息后异步调用，不阻塞主流程
    """
    try:
        from app.models.database import SessionLocal
        
        # 创建新的数据库会话（因为原会话可能在主线程已关闭）
        db = SessionLocal()
        try:
            result = await auto_summary_service.check_and_summarize(
                character_id=character_id,
                user_id=user_id,
                db=db
            )
            
            if result and result.get("success"):
                print(
                    f"[自动摘要] ✅ 角色{character_id}: "
                    f"删除{result['deleted_count']}条消息, "
                    f"创建记忆ID={result.get('memory_id')}"
                )
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"[自动摘要] 后台任务失败: {str(e)}")


async def auto_extract_memories_if_enabled(
    user_id: int, 
    character_id: str, 
    user_message: str, 
    ai_response: str, 
    db
):
    """自动从对话中提取记忆（每10轮对话提取一次）"""
    try:
        # 先检查是否需要提取 - 简单的计数器（暂时不存数据库）
        # 先获取最近的对话历史
        chat_messages = db.query(ChatMessage).filter(
            ChatMessage.user_id == user_id,
            ChatMessage.character_id == character_id,
            ChatMessage.role.in_(["user", "assistant"])
        ).order_by(ChatMessage.created_at.desc()).limit(20).all()
        
        # 简单判断：如果用户消息中包含重要信息或者对话较长，则提取
        # 这里我们简化处理：每5-6条对话尝试提取一次，或者消息长度较长时
        should_extract = len(chat_messages) % 5 == 0 or len(user_message) > 100
        
        if not should_extract:
            return
        
        print("[记忆提取] 开始自动提取记忆...")
        
        # 准备对话文本
        chat_text = "\n".join([
            f"{'用户' if msg.role == 'user' else 'AI'}: {msg.content}"
            for msg in reversed(chat_messages[-10:])  # 最近10条
        ])
        
        prompt = f"""你是一个专业的记忆整理师。请分析以下对话，提取值得记忆的信息。

对话历史：
{chat_text}

请提取以下类型的记忆（JSON数组格式）：
[
    {{
        "title": "简短明确的标题",
        "content": "详细内容",
        "memory_type": "fact/preference/event/relationship",
        "importance": 1-5,
        "tags": ["标签1", "标签2"]
    }}
]

说明：
- fact: 客观事实（名字、地点、年龄、职业等）
- preference: 用户的喜好和偏好（喜欢什么、不喜欢什么）
- event: 重要事件或对话
- relationship: 人物关系

注意：
1. 只输出JSON数组，不要其他内容
2. 只提取真正重要、值得长期记住的信息
3. 如果没有值得提取的内容，返回空数组[]
4. 重要程度根据信息的重要性评定（核心信息给5，次要给1）"""
        
        response = await llm_service.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        content = response.strip() if response else ""
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        if not content or content == "[]":
            print("[记忆提取] 没有可提取的记忆")
            return
        
        # 解析JSON
        import re
        try:
            memories_data = json.loads(content)
        except json.JSONDecodeError as e:
            # 尝试修复JSON
            fixed = content
            fixed = re.sub(r"(?<!\\)'", '"', fixed)
            fixed = re.sub(r'(?<=[\[{,])\s*([a-zA-Z_]\w*)\s*:', r' "\1":', fixed)
            fixed = re.sub(r',\s*}', '}', fixed)
            fixed = re.sub(r',\s*]', ']', fixed)
            
            try:
                memories_data = json.loads(fixed)
            except:
                print(f"[记忆提取] JSON解析失败: {e}")
                return
        
        # 获取现有记忆，避免重复
        existing_memories = db.query(CharacterMemory).filter(
            CharacterMemory.user_id == user_id,
            CharacterMemory.character_id == character_id
        ).all()
        existing_titles = {m.title for m in existing_memories}
        
        created_count = 0
        for mem_data in memories_data:
            title = mem_data.get("title", "").strip()
            if not title or title in existing_titles:
                continue  # 跳过空标题或重复的
            
            # 创建新记忆
            new_memory = CharacterMemory(
                user_id=user_id,
                character_id=character_id,
                title=title,
                content=mem_data.get("content", ""),
                memory_type=mem_data.get("memory_type", "general"),
                importance=mem_data.get("importance", 3),
                tags=mem_data.get("tags", []),
                is_active=True,
                access_count=0
            )
            
            db.add(new_memory)
            existing_titles.add(title)
            created_count += 1
        
        db.commit()
        
        if created_count > 0:
            print(f"[记忆提取] 成功提取 {created_count} 条新记忆")
        
    except Exception as e:
        print(f"[记忆提取] 自动提取失败: {str(e)}")
        db.rollback()


@router.post("/send-image", response_model=ChatResponse)
async def send_image_message(request: ImageChatRequest, db = Depends(get_db)):
    """
    发送图片并获取AI分析回复
    """
    try:
        # 1. 触发插件 - 消息接收
        await plugin_manager.execute_all(
            "on_message_received",
            message="[图片]",
            user_id=str(request.user_id)
        )
        
        # 2. 获取当前角色
        current_character = character_manager.get_current_character()
        
        # 3. 获取用户历史消息（上下文）
        history = db.query(ChatMessage).filter(
            ChatMessage.user_id == request.user_id
        ).order_by(ChatMessage.created_at.desc()).limit(10).all()
        
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(history)
        ]
        
        # 4. 构建系统提示词
        base_prompt = current_character.system_prompt if current_character else """你是一个友好、有帮助的AI助手。
你的特点是：
- 语气温和、耐心
- 回答简洁明了
- 善于倾听和理解用户
- 会根据用户的偏好调整回复"""
        
        # 添加环境感知信息
        time_info = time_awareness_service.get_current_time_info()
        env_context = f"""

【当前环境信息】
- 当前时间：{time_info['time_str']}（{time_info['weekday_name']} {time_info['period_name']}）
- 时段提示：{time_awareness_service.get_care_tip()}

请根据当前时间和时段，在回复中自然地体现对用户的关怀。"""
        
        # 获取世界书、记忆、足迹数据用于智能上下文
        character_id = current_character.id if current_character else None
        worldbook_entries = []
        memories = []
        footprints = []
        
        if character_id:
            # 获取激活的世界书条目
            try:
                worldbook_data = worldbook_manager.list_entries(active_only=True)
                worldbook_entries = [
                    {
                        'id': w.id,
                        'title': w.title,
                        'content': w.content,
                        'tags': w.tags or [],
                        'is_active': w.is_active
                    }
                    for w in worldbook_data
                ]
            except:
                pass
            
            # 获取角色记忆
            try:
                memories = db.query(CharacterMemory).filter(
                    CharacterMemory.character_id == character_id,
                    CharacterMemory.user_id == request.user_id,
                    CharacterMemory.is_active == True
                ).order_by(CharacterMemory.importance.desc()).all()
                memories = [
                    {
                        'id': m.id,
                        'title': m.title,
                        'content': m.content,
                        'memory_type': m.memory_type,
                        'importance': m.importance,
                        'tags': m.tags or [],
                        'is_active': m.is_active
                    }
                    for m in memories
                ]
            except:
                pass
            
            # 获取足迹
            try:
                footprints = db.query(MemoryEvent).filter(
                    MemoryEvent.character_id == character_id,
                    MemoryEvent.user_id == request.user_id
                ).order_by(MemoryEvent.importance.desc()).limit(20).all()
                footprints = [
                    {
                        'id': f.id,
                        'title': f.title,
                        'description': f.description,
                        'footprint_type': f.event_type,
                        'importance': f.importance,
                        'tags': f.tags or []
                    }
                    for f in footprints
                ]
            except:
                pass
        
        # 使用智能上下文管理器构建提示词
        system_prompt = context_manager.build_context_prompt(
            character_prompt=base_prompt + env_context,
            user_message="[图片]",
            worldbook_entries=worldbook_entries,
            memories=memories,
            footprints=footprints
        )
        
        # 5. 处理图片base64
        image_base64 = request.image_base64
        # 移除data:image/xxx;base64,前缀
        if ',' in image_base64:
            image_base64 = image_base64.split(',', 1)[1]
        
        # 6. 调用LLM获取图片分析回复（使用视觉模型）
        reply = await llm_service.vision_completion(
            messages=messages,
            system_prompt=system_prompt,
            image_base64=image_base64
        )
        
        # 7. 保存用户消息到数据库
        user_msg = ChatMessage(
            user_id=request.user_id,
            role="user",
            content="[图片]"
        )
        db.add(user_msg)
        
        # 8. 保存AI回复到数据库
        ai_msg = ChatMessage(
            user_id=request.user_id,
            role="assistant",
            content=reply
        )
        db.add(ai_msg)
        
        # 9. 如果需要语音，调用TTS
        audio_base64 = None
        if request.enable_tts:
            try:
                audio_base64 = await tts_service.text_to_speech_base64(
                    reply,
                    voice=request.voice
                )
            except Exception as tts_error:
                print(f"TTS语音合成失败（已忽略）: {str(tts_error)}")
                audio_base64 = None
        
        # 10. 触发插件 - 消息发送
        await plugin_manager.execute_all(
            "on_message_sent",
            message=reply,
            user_id=str(request.user_id)
        )
        
        db.commit()
        
        return ChatResponse(
            success=True,
            reply=reply,
            audio_base64=audio_base64
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{user_id}")
async def get_chat_history(user_id: int, limit: int = 50, db = Depends(get_db)):
    """获取聊天历史"""
    messages = db.query(ChatMessage).filter(
        ChatMessage.user_id == user_id
    ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
    
    return {
        "success": True,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat()
            }
            for msg in reversed(messages)
        ]
    }

class TTSTestRequest(BaseModel):
    """TTS测试请求"""
    text: str
    voice: Optional[str] = None
    speed: float = 1.0

@router.post("/tts-test")
async def tts_test(request: TTSTestRequest):
    """测试TTS语音合成"""
    try:
        # 先尝试重新加载配置（从数据库）
        await tts_service.reload_config()
        
        audio_base64 = await tts_service.text_to_speech_base64(
            request.text,
            voice=request.voice,
            speed=request.speed
        )
        return {
            "success": True,
            "audio_base64": audio_base64
        }
    except ValueError as e:
        return {
            "success": False,
            "message": f"配置错误: {str(e)}"
        }
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            return {
                "success": False,
                "message": "TTS请求超时，请检查网络连接或API配置"
            }
        elif "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            return {
                "success": False,
                "message": "API密钥无效，请检查API配置"
            }
        else:
            return {
                "success": False,
                "message": f"TTS测试失败: {error_msg}"
            }

@router.post("/tts-reload")
async def tts_reload():
    """重新加载TTS配置（从数据库）"""
    try:
        success = await tts_service.reload_config()
        if success:
            return {
                "success": True,
                "message": "TTS配置已重新加载"
            }
        else:
            return {
                "success": False,
                "message": "TTS配置重新加载失败"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"TTS配置重新加载失败: {str(e)}"
        }


class MessageDeleteRequest(BaseModel):
    """消息删除请求"""
    user_id: int
    message_id: int  # 要回溯到的消息ID（保留这条消息，删除它之后的所有消息）


@router.post("/delete-messages-after")
async def delete_messages_after(request: MessageDeleteRequest, db = Depends(get_db)):
    """
    删除指定消息ID之后的所有消息（包括该消息本身）
    用于实现"回溯"功能：回到点击回溯的地方并删除之后的聊天记录
    """
    try:
        # 获取该用户的所有消息，按时间排序
        all_messages = db.query(ChatMessage).filter(
            ChatMessage.user_id == request.user_id
        ).order_by(ChatMessage.created_at.asc()).all()
        
        # 找到目标消息的索引
        target_index = None
        for i, msg in enumerate(all_messages):
            if msg.id == request.message_id:
                target_index = i
                break
        
        if target_index is None:
            return {
                "success": False,
                "message": "未找到指定的消息"
            }
        
        # 删除目标消息及其后的所有消息
        messages_to_delete = all_messages[target_index:]
        for msg in messages_to_delete:
            db.delete(msg)
        
        db.commit()
        
        return {
            "success": True,
            "message": f"已删除 {len(messages_to_delete)} 条消息",
            "deleted_count": len(messages_to_delete)
        }
        
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"删除消息失败: {str(e)}"
        }

class SingleMessageDeleteRequest(BaseModel):
    """删除单条消息请求"""
    user_id: int
    message_id: int


@router.post("/delete-message")
async def delete_single_message(request: SingleMessageDeleteRequest, db = Depends(get_db)):
    """
    删除单条消息（用于上下文模块的删除功能）
    只删除指定ID的那一条消息，不影响其他消息
    """
    try:
        message = db.query(ChatMessage).filter(
            ChatMessage.id == request.message_id,
            ChatMessage.user_id == request.user_id
        ).first()
        
        if not message:
            return {
                "success": False,
                "message": "未找到指定的消息"
            }
        
        db.delete(message)
        db.commit()
        
        print(f"已删除消息 ID={request.message_id}, 角色={message.character_id}")
        
        return {
            "success": True,
            "message": "消息已删除",
            "deleted_id": request.message_id
        }
        
    except Exception as e:
        db.rollback()
        print(f"删除单条消息失败: {e}")
        return {
            "success": False,
            "message": f"删除消息失败: {str(e)}"
        }

class ContextResponse(BaseModel):
    """上下文响应"""
    success: bool
    context: Dict[str, Any] = {}

class RelevantMemoriesRequest(BaseModel):
    """获取相关记忆的请求"""
    user_id: int
    character_id: str
    user_message: str


@router.post("/relevant-memories")
async def get_relevant_memories(request: RelevantMemoriesRequest, db = Depends(get_db)):
    """
    获取与用户消息相关的记忆
    这个接口用于前端在用户输入时就显示相关记忆
    """
    try:
        # 获取所有激活的记忆
        memories = db.query(CharacterMemory).filter(
            CharacterMemory.character_id == request.character_id,
            CharacterMemory.user_id == request.user_id,
            CharacterMemory.is_active == True
        ).order_by(
            CharacterMemory.importance.desc(),
            CharacterMemory.last_accessed.desc() if hasattr(CharacterMemory, 'last_accessed') else CharacterMemory.created_at.desc()
        ).all()
        
        # 转为字典
        memories_list = [
            {
                "id": m.id,
                "title": m.title,
                "content": m.content,
                "memory_type": m.memory_type,
                "importance": m.importance,
                "tags": m.tags or [],
                "access_count": m.access_count if hasattr(m, 'access_count') else 0,
                "last_accessed": m.last_accessed.isoformat() if hasattr(m, 'last_accessed') and m.last_accessed else None
            }
            for m in memories
        ]
        
        # 选择相关记忆
        keywords = context_manager.extract_keywords(request.user_message)
        relevant_memories = context_manager.select_relevant_memories(keywords, memories_list)
        
        return {
            "success": True,
            "all_memories": memories_list,
            "relevant_memories": relevant_memories,
            "keywords": keywords
        }
        
    except Exception as e:
        print(f"获取相关记忆失败: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "all_memories": [],
            "relevant_memories": []
        }


@router.get("/context", response_model=ContextResponse)
async def get_context(character_id: str, user_id: int = 1, db = Depends(get_db)):
    """
    获取指定角色的聊天上下文
    包括角色信息、最近对话、世界书参考、角色记忆、足迹信息等
    """
    try:
        context = {}
        
        # 1. 获取角色信息
        character = character_manager.get_character(character_id)
        if character:
            context["character_info"] = {
                "id": character.id,
                "name": character.name,
                "description": character.description,
                "personality": character.personality,
                "avatar": character.avatar,
                "tags": character.tags if hasattr(character, 'tags') and character.tags else []
            }
        
        # 2. 获取最近的对话记录（只查询当前角色的）
        recent_messages = db.query(ChatMessage).filter(
            ChatMessage.user_id == user_id,
            ChatMessage.character_id == character_id
        ).order_by(ChatMessage.created_at.desc()).limit(10).all()

        context["recent_messages"] = [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "time": msg.created_at.isoformat() if hasattr(msg, 'created_at') and msg.created_at else None
            }
            for msg in reversed(recent_messages)
        ]
        
        # 3. 获取世界书条目
        try:
            worldbook_entries = worldbook_manager.list_entries(active_only=True, character_id=character_id)
            context["worldbook_entries"] = [
                {
                    "id": w.id,
                    "title": w.title,
                    "content": w.content,
                    "category": w.category if hasattr(w, 'category') else None,
                    "tags": w.tags if hasattr(w, 'tags') else []
                }
                for w in worldbook_entries[:5]
            ]
        except:
            context["worldbook_entries"] = []
        
        # 4. 获取角色记忆 - 优先显示重要的和最近访问的
        try:
            from sqlalchemy import desc
            
            memories_query = db.query(CharacterMemory).filter(
                CharacterMemory.character_id == character_id,
                CharacterMemory.user_id == user_id,
                CharacterMemory.is_active == True
            )
            
            # 排序：先重要性，再最近访问时间
            if hasattr(CharacterMemory, 'last_accessed'):
                memories_query = memories_query.order_by(
                    desc(CharacterMemory.importance),
                    desc(CharacterMemory.last_accessed)
                )
            else:
                memories_query = memories_query.order_by(
                    desc(CharacterMemory.importance)
                )
            
            memories = memories_query.limit(10).all()
            
            context["memories"] = [
                {
                    "id": m.id,
                    "title": m.title,
                    "content": m.content,
                    "memory_type": m.memory_type if hasattr(m, 'memory_type') else 'general',
                    "importance": m.importance,
                    "tags": m.tags or [],
                    "access_count": m.access_count if hasattr(m, 'access_count') else 0,
                    "last_accessed": m.last_accessed.isoformat() if hasattr(m, 'last_accessed') and m.last_accessed else None
                }
                for m in memories
            ]
        except Exception as e:
            print(f"获取记忆出错: {e}")
            context["memories"] = []
        
        # 5. 获取足迹信息
        try:
            from app.services.memory_event_service import memory_event_service
            
            events = memory_event_service.get_events_by_character(
                db=db,
                user_id=user_id,
                character_id=character_id
            )
            
            footprint = {
                "locations": [],
                "persons": [],
                "items": [],
                "discoveries": [],
                "main_events": [],
                "side_events": [],
                "current_location": None,
                "key_items": []
            }
            
            for event in events:
                event_type = event.event_type if hasattr(event, 'event_type') else 'side'
                tags = event.tags if hasattr(event, 'tags') and event.tags else []
                
                event_data = {
                    "id": event.id,
                    "title": event.title,
                    "description": event.description,
                    "importance": event.importance,
                    "tags": tags
                }
                
                if event_type == 'main':
                    footprint["main_events"].append(event_data)
                else:
                    footprint["side_events"].append(event_data)
                
                # 从标签中提取类型信息
                for tag in tags:
                    if tag == 'location' and event.title not in footprint["locations"]:
                        footprint["locations"].append(event.title)
                        footprint["current_location"] = event.title
                    elif tag == 'person' and event.title not in footprint["persons"]:
                        footprint["persons"].append(event.title)
                    elif tag == 'item' and event.title not in footprint["items"]:
                        footprint["items"].append(event.title)
                        footprint["key_items"].append(event.title)
                    elif tag == 'discovery' and event.title not in footprint["discoveries"]:
                        footprint["discoveries"].append(event.title)
            
            context["footprint"] = footprint
        except:
            context["footprint"] = {"locations": []}
        
        return ContextResponse(
            success=True,
            context=context
        )
        
    except Exception as e:
        print(f"获取上下文失败: {str(e)}")
        return ContextResponse(
            success=False,
            context={}
        )

@router.post("/clear-history")
async def clear_chat_history(user_id: int, character_id: str, db = Depends(get_db)):
    """
    清空指定角色的所有聊天记录
    用于重启角色功能
    """
    try:
        # 删除该用户指定角色的所有聊天消息
        deleted = db.query(ChatMessage).filter(
            ChatMessage.user_id == user_id,
            ChatMessage.character_id == character_id
        ).delete()
        
        db.commit()
        
        print(f"已清空用户 {user_id} 角色 {character_id} 的聊天记录，共删除 {deleted} 条消息")
        
        return {
            "success": True,
            "message": f"已清空聊天记录，共删除 {deleted} 条消息",
            "deleted_count": deleted
        }
        
    except Exception as e:
        db.rollback()
        print(f"清空聊天记录失败: {str(e)}")
        return {
            "success": False,
            "message": f"清空聊天记录失败: {str(e)}"
        }


# ==================== 自动摘要相关API ====================

class SummaryStatusRequest(BaseModel):
    """摘要状态查询请求"""
    user_id: int
    character_id: str

class ForceSummaryRequest(BaseModel):
    """强制摘要请求"""
    user_id: int
    character_id: str


@router.get("/summary-status")
async def get_summary_status(user_id: int, character_id: str, db = Depends(get_db)):
    """
    获取自动摘要状态信息
    
    返回：
    - 当前消息数量
    - 距离下次摘要还有多少条消息
    - 是否应该触发摘要
    - 已有的摘要数量
    """
    try:
        status = auto_summary_service.get_summary_status(
            character_id=character_id,
            user_id=user_id,
            db=db
        )
        
        return {
            "success": True,
            **status
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"查询摘要状态失败: {str(e)}"
        }


@router.post("/force-summary")
async def force_trigger_summary(request: ForceSummaryRequest, db = Depends(get_db)):
    """
    强制触发自动摘要（忽略阈值限制）
    
    用于：
    - 手动清理聊天记录
    - 测试摘要功能
    - 紧急释放Token空间
    """
    try:
        result = await auto_summary_service.check_and_summarize(
            character_id=request.character_id,
            user_id=request.user_id,
            db=db,
            force=True  # 强制执行
        )
        
        if not result:
            return {
                "success": False,
                "message": "没有可摘要的消息"
            }
            
        if result.get("success"):
            return {
                "success": True,
                "message": f"摘要成功！删除了{result['deleted_count']}条消息",
                **result
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "摘要失败"),
                **result
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"强制摘要失败: {str(e)}"
        }


@router.post("/batch-summary")
async def batch_summarize_all(user_id: int, db = Depends(get_db)):
    """
    批量对所有角色执行摘要
    
    用于定期维护，释放数据库空间
    """
    try:
        result = await auto_summary_service.summarize_all_characters(
            user_id=user_id,
            db=db
        )
        
        return {
            "success": True,
            "message": (
                f"批量摘要完成！处理了{result['total_processed']}个角色, "
                f"生成{result['total_summaries']}个摘要, "
                f"删除{result['total_deleted']}条消息"
            ),
            **result
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"批量摘要失败: {str(e)}"
        }


# ==================== Author's Note相关API ====================

class AuthorNoteConfigRequest(BaseModel):
    """Author's Note配置请求"""
    user_id: int
    character_id: str
    content: str = ""
    depth: int = 3
    interval: int = 4
    position: str = "after"
    is_enabled: bool = False


@router.get("/author-note")
async def get_author_note_config(user_id: int, character_id: str, db = Depends(get_db)):
    """
    获取角色的Author's Note配置
    """
    try:
        config = db.query(AuthorNoteConfig).filter(
            AuthorNoteConfig.user_id == user_id,
            AuthorNoteConfig.character_id == character_id
        ).first()
        
        if not config:
            return {
                "success": True,
                "config": author_note_service.get_default_config(),
                "exists": False
            }
        
        return {
            "success": True,
            "config": {
                "content": config.content or "",
                "depth": config.depth,
                "interval": config.interval,
                "position": config.position,
                "is_enabled": config.is_enabled
            },
            "exists": True
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取Author's Note配置失败: {str(e)}"
        }


@router.post("/author-note")
async def save_author_note_config(request: AuthorNoteConfigRequest, db = Depends(get_db)):
    """
    保存或更新Author's Note配置
    """
    try:
        # 验证配置
        config_dict = request.dict()
        is_valid, error_msg = author_note_service.validate_config(config_dict)
        
        if not is_valid:
            return {
                "success": False,
                "message": f"配置验证失败: {error_msg}"
            }
        
        # 查找现有配置
        existing_config = db.query(AuthorNoteConfig).filter(
            AuthorNoteConfig.user_id == request.user_id,
            AuthorNoteConfig.character_id == request.character_id
        ).first()
        
        if existing_config:
            # 更新现有配置
            existing_config.content = request.content
            existing_config.depth = request.depth
            existing_config.interval = request.interval
            existing_config.position = request.position
            existing_config.is_enabled = request.is_enabled
            existing_config.updated_at = datetime.utcnow()
            
            print(f"[Author's Note] 更新配置: 角色={request.character_id}, 启用={request.is_enabled}")
        else:
            # 创建新配置
            new_config = AuthorNoteConfig(
                user_id=request.user_id,
                character_id=request.character_id,
                content=request.content,
                depth=request.depth,
                interval=request.interval,
                position=request.position,
                is_enabled=request.is_enabled
            )
            db.add(new_config)
            
            print(f"[Author's Note] 创建新配置: 角色={request.character_id}, 启用={request.is_enabled}")
        
        db.commit()
        
        return {
            "success": True,
            "message": "Author's Note配置已保存"
        }
        
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"保存Author's Note配置失败: {str(e)}"
        }


@router.delete("/author-note")
async def delete_author_note_config(user_id: int, character_id: str, db = Depends(get_db)):
    """
    删除角色的Author's Note配置
    """
    try:
        deleted = db.query(AuthorNoteConfig).filter(
            AuthorNoteConfig.user_id == user_id,
            AuthorNoteConfig.character_id == character_id
        ).delete()
        
        db.commit()
        
        if deleted > 0:
            print(f"[Author's Note] 删除配置: 角色={character_id}")
            return {
                "success": True,
                "message": "Author's Note配置已删除"
            }
        else:
            return {
                "success": False,
                "message": "未找到该角色的配置"
            }
        
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"删除Author's Note配置失败: {str(e)}"
        }
