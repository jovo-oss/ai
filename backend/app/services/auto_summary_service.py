import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.database import ChatMessage, CharacterMemory, get_db
from app.services.llm_service import llm_service
import logging

logger = logging.getLogger(__name__)

class AutoSummaryService:
    """
    自动摘要服务 - 基于SillyTavern架构的长期记忆管理
    
    功能：
    1. 监控聊天消息数量，达到阈值时触发自动摘要
    2. 调用LLM提取关键信息生成摘要
    3. 删除已摘要的旧消息，释放Token空间
    4. 将摘要存储为记忆节点，供后续引用
    """
    
    def __init__(self):
        self.max_messages_before_summary = 30  # 触发摘要的消息阈值
        self.keep_recent_messages = 10          # 保留最近N条原始消息
        self.messages_to_summarize = 20         # 每次摘要的消息数量
        self.summary_model_temperature = 0.3    # 摘要模型温度（低温度确保准确性）
        
    async def check_and_summarize(
        self,
        character_id: str,
        user_id: int,
        db: Session,
        force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        检查是否需要生成摘要
        
        Args:
            character_id: 角色ID
            user_id: 用户ID
            db: 数据库会话
            force: 是否强制执行摘要（忽略阈值）
            
        Returns:
            摘要结果字典，或None（未触发摘要）
        """
        try:
            # 1. 统计当前角色的消息数量
            message_count = db.query(ChatMessage).filter(
                ChatMessage.character_id == character_id,
                ChatMessage.user_id == user_id
            ).count()
            
            logger.info(f"[自动摘要] 角色 {character_id} 当前消息数: {message_count}")
            
            # 检查是否需要触发摘要
            if not force and message_count < self.max_messages_before_summary:
                logger.debug(f"[自动摘要] 未达阈值 ({message_count}/{self.max_messages_before_summary})")
                return None
            
            if message_count <= self.keep_recent_messages:
                logger.debug(f"[自动摘要] 消息数太少，无需摘要")
                return None
            
            # 2. 获取需要被摘要的消息（排除最近保留的消息）
            all_messages = db.query(ChatMessage).filter(
                ChatMessage.character_id == character_id,
                ChatMessage.user_id == user_id
            ).order_by(ChatMessage.created_at.asc()).all()
            
            messages_to_keep = all_messages[-self.keep_recent_messages:]
            messages_to_summarize = all_messages[:-self.keep_recent_messages]
            
            if len(messages_to_summarize) < 5:
                logger.debug("[自动摘要] 可摘要消息太少（<5条）")
                return None
            
            # 只取最近的messages_to_summarize_count条进行摘要
            messages_for_summary = messages_to_summarize[-self.messages_to_summarize:]
            
            logger.info(
                f"[自动摘要] 开始处理: 总计{message_count}条, "
                f"保留{len(messages_to_keep)}条, 摘要{len(messages_for_summary)}条"
            )
            
            # 3. 调用LLM生成摘要
            summary_text = await self._generate_summary(messages_for_summary)
            
            if not summary_text:
                logger.error("[自动摘要] LLM返回空摘要")
                return None
            
            # 4. 删除已摘要的消息
            deleted_ids = []
            for msg in messages_for_summary:
                deleted_ids.append(msg.id)
                db.delete(msg)
            
            # 5. 创建摘要记忆节点
            summary_memory = CharacterMemory(
                user_id=user_id,
                character_id=character_id,
                title=f"📝 自动摘要-{datetime.now().strftime('%m/%d %H:%M')}",
                content=summary_text,
                memory_type="auto_summary",
                importance=3,
                is_active=True,
                tags=["auto_summary", "compressed", f"messages_{len(messages_for_summary)}"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_accessed=datetime.utcnow()
            )
            db.add(summary_memory)
            db.commit()
            
            result = {
                "success": True,
                "summary": summary_text,
                "deleted_count": len(deleted_ids),
                "deleted_ids": deleted_ids,
                "memory_id": summary_memory.id,
                "remaining_messages": len(messages_to_keep),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(
                f"[自动摘要] ✅ 完成! 删除{result['deleted_count']}条消息, "
                f"创建记忆ID={summary_memory.id}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[自动摘要] ❌ 失败: {str(e)}", exc_info=True)
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_summary(self, messages: List[ChatMessage]) -> Optional[str]:
        """调用LLM生成对话摘要"""
        try:
            # 构建对话文本
            chat_parts = []
            for msg in messages[-20:]:  # 最多取最后20条
                role_display = "用户" if msg.role == "user" else "AI"
                content_preview = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                chat_parts.append(f"{role_display}: {content_preview}")
            
            chat_text = "\n".join(chat_parts)
            
            prompt = f"""请总结以下AI角色扮演对话的关键信息。

【要求】
1. 提取重要的事实、事件、决定和计划
2. 记录人物关系变化和情感状态
3. 保持简洁（150-250字）
4. 使用第三人称客观描述
5. 保留关键细节（名字、地点、时间等）

【对话内容】
{chat_text}

【输出格式】
请直接输出摘要内容，不需要任何前缀或解释："""

            # 调用LLM
            response = await llm_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.summary_model_temperature,
                max_tokens=500
            )
            
            if response and response.get("choices"):
                summary = response["choices"][0]["message"]["content"].strip()
                
                # 清理可能的格式标记
                summary = re.sub(r'^[（(【[]*摘要[】\])]?\s*:?\s*', '', summary)
                
                logger.debug(f"[自动摘要] 生成摘要长度: {len(summary)} 字符")
                return summary
            
            return None
            
        except Exception as e:
            logger.error(f"[自动摘要] LLM调用失败: {str(e)}")
            return None
    
    async def summarize_all_characters(
        self,
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        对用户所有角色的聊天记录执行批量摘要
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            
        Returns:
            批量摘要结果统计
        """
        results = {
            "total_processed": 0,
            "total_summaries": 0,
            "total_deleted": 0,
            "details": []
        }
        
        try:
            # 获取该用户有消息的所有角色
            characters_with_messages = db.query(
                ChatMessage.character_id
            ).filter(
                ChatMessage.user_id == user_id
            ).distinct().all()
            
            for (character_id,) in characters_with_messages:
                result = await self.check_and_summarize(
                    character_id=character_id[0],
                    user_id=user_id,
                    db=db
                )
                
                results["total_processed"] += 1
                
                if result and result.get("success"):
                    results["total_summaries"] += 1
                    results["total_deleted"] += result.get("deleted_count", 0)
                    results["details"].append({
                        "character_id": character_id[0],
                        "deleted_count": result.get("deleted_count", 0),
                        "memory_id": result.get("memory_id")
                    })
                    
            logger.info(
                f"[自动摘要-批量] 完成! 处理{results['total_processed']}个角色, "
                f"生成{results['total_summaries']}个摘要, "
                f"删除{results['total_deleted']}条消息"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"[自动摘要-批量] 失败: {str(e)}")
            results["error"] = str(e)
            return results
    
    def get_summary_status(
        self,
        character_id: str,
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        获取某个角色的摘要状态信息
        
        Returns:
            包含消息计数、距离下次摘要还有多少条等信息的字典
        """
        try:
            message_count = db.query(ChatMessage).filter(
                ChatMessage.character_id == character_id,
                ChatMessage.user_id == user_id
            ).count()
            
            summary_count = db.query(CharacterMemory).filter(
                CharacterMemory.character_id == character_id,
                CharacterMemory.user_id == user_id,
                CharacterMemory.memory_type == "auto_summary"
            ).count()
            
            remaining_until_summary = max(0, self.max_messages_before_summary - message_count)
            percentage = min(100, (message_count / self.max_messages_before_summary) * 100)
            
            return {
                "current_messages": message_count,
                "threshold": self.max_messages_before_summary,
                "remaining_until_summary": remaining_until_summary,
                "percentage": round(percentage, 1),
                "existing_summaries": summary_count,
                "should_trigger": message_count >= self.max_messages_before_summary,
                "keep_recent": self.keep_recent_messages
            }
            
        except Exception as e:
            logger.error(f"[自动摘要-状态查询] 失败: {str(e)}")
            return {"error": str(e)}


# 全局实例
auto_summary_service = AutoSummaryService()

import re
