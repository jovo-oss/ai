from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.models.database import get_db, CharacterMemory
from app.services.llm_service import llm_service

router = APIRouter(prefix="/api/memories", tags=["memories"])

class MemoryCreate(BaseModel):
    """创建记忆请求"""
    user_id: int
    character_id: str
    title: str
    content: str
    memory_type: str = "general"
    parent_id: Optional[int] = None
    importance: int = 1
    tags: Optional[List[str]] = None

class MemoryUpdate(BaseModel):
    """更新记忆请求"""
    title: Optional[str] = None
    content: Optional[str] = None
    memory_type: Optional[str] = None
    importance: Optional[int] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None

class MemoryAnalyzeRequest(BaseModel):
    """AI分析记忆请求"""
    user_id: int
    character_id: str
    chat_messages: str

@router.post("/create")
async def create_memory(request: MemoryCreate, db: Session = Depends(get_db)):
    """创建新的记忆节点"""
    try:
        parent = None
        level = 0
        if request.parent_id:
            parent = db.query(CharacterMemory).filter(
                CharacterMemory.id == request.parent_id,
                CharacterMemory.character_id == request.character_id
            ).first()
            if not parent:
                return {"success": False, "message": "父节点不存在"}
            level = parent.level + 1
        
        memory = CharacterMemory(
            user_id=request.user_id,
            character_id=request.character_id,
            title=request.title,
            content=request.content,
            memory_type=request.memory_type,
            parent_id=request.parent_id,
            level=level,
            importance=request.importance,
            tags=request.tags or []
        )
        
        db.add(memory)
        db.commit()
        db.refresh(memory)
        
        return {
            "success": True,
            "memory": {
                "id": memory.id,
                "title": memory.title,
                "content": memory.content,
                "memory_type": memory.memory_type,
                "parent_id": memory.parent_id,
                "level": memory.level,
                "importance": memory.importance,
                "is_active": memory.is_active,
                "tags": memory.tags,
                "created_at": memory.created_at.isoformat()
            }
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"创建失败: {str(e)}"}

@router.get("/list/{character_id}")
async def get_memory_tree(character_id: str, user_id: int = 1, db: Session = Depends(get_db)):
    """获取角色的完整记忆树"""
    try:
        memories = db.query(CharacterMemory).filter(
            CharacterMemory.character_id == character_id,
            CharacterMemory.user_id == user_id
        ).order_by(CharacterMemory.level, CharacterMemory.created_at).all()
        
        def build_tree(memories_list, parent_id=None):
            tree = []
            for m in memories_list:
                if m.parent_id == parent_id:
                    node = {
                        "id": m.id,
                        "title": m.title,
                        "content": m.content,
                        "memory_type": m.memory_type,
                        "parent_id": m.parent_id,
                        "level": m.level,
                        "importance": m.importance,
                        "is_active": m.is_active,
                        "tags": m.tags,
                        "created_at": m.created_at.isoformat(),
                        "children": build_tree(memories_list, m.id)
                    }
                    tree.append(node)
            return tree
        
        tree = build_tree(memories)
        
        return {
            "success": True,
            "tree": tree,
            "total": len(memories)
        }
    except Exception as e:
        return {"success": False, "message": f"获取失败: {str(e)}"}

@router.post("/update/{memory_id}")
async def update_memory(memory_id: int, request: MemoryUpdate, db: Session = Depends(get_db)):
    """更新记忆节点"""
    try:
        memory = db.query(CharacterMemory).filter(CharacterMemory.id == memory_id).first()
        if not memory:
            return {"success": False, "message": "记忆节点不存在"}
        
        if request.title is not None:
            memory.title = request.title
        if request.content is not None:
            memory.content = request.content
        if request.memory_type is not None:
            memory.memory_type = request.memory_type
        if request.importance is not None:
            memory.importance = request.importance
        if request.is_active is not None:
            memory.is_active = request.is_active
        if request.tags is not None:
            memory.tags = request.tags
        
        db.commit()
        db.refresh(memory)
        
        return {
            "success": True,
            "message": "更新成功",
            "memory": {
                "id": memory.id,
                "title": memory.title,
                "content": memory.content,
                "memory_type": memory.memory_type,
                "parent_id": memory.parent_id,
                "level": memory.level,
                "importance": memory.importance,
                "is_active": memory.is_active,
                "tags": memory.tags,
                "created_at": memory.created_at.isoformat()
            }
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"更新失败: {str(e)}"}

@router.post("/delete/{memory_id}")
async def delete_memory(memory_id: int, db: Session = Depends(get_db)):
    """删除记忆节点及其子节点"""
    try:
        def get_all_children(parent_id):
            children = db.query(CharacterMemory).filter(
                CharacterMemory.parent_id == parent_id
            ).all()
            result = [c.id for c in children]
            for c in children:
                result.extend(get_all_children(c.id))
            return result
        
        ids_to_delete = [memory_id] + get_all_children(memory_id)
        
        db.query(CharacterMemory).filter(
            CharacterMemory.id.in_(ids_to_delete)
        ).delete(synchronize_session=False)
        
        db.commit()
        
        return {"success": True, "message": f"已删除 {len(ids_to_delete)} 个记忆节点"}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"删除失败: {str(e)}"}

@router.post("/ai-analyze")
async def ai_analyze_memories(request: MemoryAnalyzeRequest, db: Session = Depends(get_db)):
    """AI分析聊天记录，自动生成记忆节点"""
    try:
        prompt = f"""你是一个专业的记忆分析师。请分析以下聊天记录，提取重要的信息点并生成结构化的记忆节点。

聊天记录：
{request.chat_messages}

请提取以下类型的记忆：
1. 事实类（fact）：用户提到的客观事实
2. 偏好类（preference）：用户的喜好和偏好
3. 事件类（event）：发生的重要事件
4. 关系类（relationship）：人物关系

为每个记忆点生成（必须是合法的JSON格式数组）：
[
    {{
        "title": "记忆标题（简短明确）",
        "content": "记忆详细内容",
        "memory_type": "fact/preference/event/relationship",
        "importance": 重要程度1-5,
        "tags": ["标签1", "标签2"]
    }}
]

注意：
1. 只输出JSON数组，不要有其他内容
2. 提取真正重要的信息，不要提取琐碎细节
3. 重要程度根据信息的重要性来评定
4. 标签要有助于分类和搜索"""

        response = await llm_service.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        content = response.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        import json
        memories_data = json.loads(content)
        
        created_memories = []
        for mem_data in memories_data:
            memory = CharacterMemory(
                user_id=request.user_id,
                character_id=request.character_id,
                title=mem_data["title"],
                content=mem_data["content"],
                memory_type=mem_data.get("memory_type", "general"),
                parent_id=None,
                level=0,
                importance=mem_data.get("importance", 1),
                tags=mem_data.get("tags", [])
            )
            db.add(memory)
            created_memories.append({
                "id": memory.id,
                "title": memory.title,
                "content": memory.content,
                "memory_type": memory.memory_type,
                "importance": memory.importance,
                "tags": memory.tags
            })
        
        db.commit()
        
        return {
            "success": True,
            "memories": created_memories,
            "count": len(created_memories)
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"AI分析失败: {str(e)}"}

@router.get("/active/{character_id}")
async def get_active_memories(character_id: str, user_id: int = 1, db: Session = Depends(get_db)):
    """获取角色所有激活的记忆（用于聊天引用）"""
    try:
        memories = db.query(CharacterMemory).filter(
            CharacterMemory.character_id == character_id,
            CharacterMemory.user_id == user_id,
            CharacterMemory.is_active == True
        ).order_by(CharacterMemory.importance.desc()).all()
        
        return {
            "success": True,
            "memories": [
                {
                    "id": m.id,
                    "title": m.title,
                    "content": m.content,
                    "memory_type": m.memory_type,
                    "importance": m.importance,
                    "tags": m.tags
                }
                for m in memories
            ]
        }
    except Exception as e:
        return {"success": False, "message": f"获取失败: {str(e)}"}


class ClearMemoriesRequest(BaseModel):
    """清空记忆请求"""
    user_id: int
    character_id: str


@router.post("/clear")
async def clear_character_memories(request: ClearMemoriesRequest, db: Session = Depends(get_db)):
    """清空指定角色的所有记忆（用于重启角色功能）"""
    try:
        deleted = db.query(CharacterMemory).filter(
            CharacterMemory.user_id == request.user_id,
            CharacterMemory.character_id == request.character_id
        ).delete()
        
        db.commit()
        
        print(f"已清空用户 {request.user_id} 角色 {request.character_id} 的记忆，共删除 {deleted} 条记录")
        
        return {
            "success": True,
            "message": f"已清空角色记忆，共删除 {deleted} 条记录",
            "deleted_count": deleted
        }
    except Exception as e:
        db.rollback()
        print(f"清空记忆失败: {e}")
        return {"success": False, "message": f"清空记忆失败: {str(e)}"}
