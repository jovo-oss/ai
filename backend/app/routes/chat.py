from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.llm_service import llm_service
from app.services.tts_service import tts_service
from app.plugins.plugin_base import plugin_manager
from app.models.database import get_db, User, ChatMessage
import json

router = APIRouter(prefix="/api/chat", tags=["聊天"])

class ChatRequest(BaseModel):
    """聊天请求"""
    user_id: int
    message: str
    enable_tts: bool = True
    voice: Optional[str] = None

class ChatResponse(BaseModel):
    """聊天响应"""
    success: bool
    reply: str
    audio_base64: Optional[str] = None
    metadata: Dict[str, Any] = {}

@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest, db = Depends(get_db)):
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
        
        # 2. 获取用户历史消息（上下文）
        history = db.query(ChatMessage).filter(
            ChatMessage.user_id == request.user_id
        ).order_by(ChatMessage.created_at.desc()).limit(10).all()
        
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(history)
        ]
        
        # 3. 构建系统提示词（包含人格设定）
        system_prompt = """你是一个友好、有帮助的AI助手。
你的特点是：
- 语气温和、耐心
- 回答简洁明了
- 善于倾听和理解用户
- 会根据用户的偏好调整回复"""
        
        # 4. 调用LLM获取回复
        reply = await llm_service.chat_completion(
            messages=messages + [{"role": "user", "content": request.message}],
            system_prompt=system_prompt
        )
        
        # 5. 保存用户消息到数据库
        user_msg = ChatMessage(
            user_id=request.user_id,
            role="user",
            content=request.message
        )
        db.add(user_msg)
        
        # 6. 保存AI回复到数据库
        ai_msg = ChatMessage(
            user_id=request.user_id,
            role="assistant",
            content=reply
        )
        db.add(ai_msg)
        
        # 7. 如果需要语音，调用TTS
        audio_base64 = None
        if request.enable_tts:
            audio_base64 = await tts_service.text_to_speech_base64(
                reply,
                voice=request.voice
            )
        
        # 8. 提取并更新用户记忆（异步处理）
        user_info = await llm_service.extract_user_info(request.message)
        if user_info:
            print(f"提取到用户信息: {user_info}")
        
        # 9. 触发插件 - 消息发送
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
