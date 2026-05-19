from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.services.worldbook_manager import worldbook_manager, WorldBookEntry
from app.services.llm_service import llm_service
import json

router = APIRouter(prefix="/api/worldbook", tags=["世界书"])

class WorldBookListResponse(BaseModel):
    success: bool
    entries: List[dict]
    categories: List[str]

class WorldBookCreateRequest(BaseModel):
    id: str
    title: str
    content: str
    category: str = "general"
    tags: List[str] = []
    is_active: bool = True

class WorldBookUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

class WorldBookResponse(BaseModel):
    success: bool
    message: str
    entry: Optional[dict] = None

@router.get("/list", response_model=WorldBookListResponse)
async def list_entries(category: Optional[str] = None, active_only: bool = False):
    """获取世界书条目列表"""
    entries = worldbook_manager.list_entries(category=category, active_only=active_only)
    categories = worldbook_manager.get_categories()
    
    return WorldBookListResponse(
        success=True,
        entries=[
            {
                "id": e.id,
                "title": e.title,
                "content": e.content,
                "category": e.category,
                "tags": e.tags,
                "is_active": e.is_active,
                "created_at": e.created_at,
                "updated_at": e.updated_at
            }
            for e in entries
        ],
        categories=categories
    )

@router.get("/search")
async def search_entries(keyword: str):
    """搜索世界书条目"""
    entries = worldbook_manager.search_entries(keyword)
    return {
        "success": True,
        "entries": [
            {
                "id": e.id,
                "title": e.title,
                "content": e.content,
                "category": e.category,
                "tags": e.tags,
                "is_active": e.is_active
            }
            for e in entries
        ],
        "count": len(entries)
    }

@router.get("/context")
async def get_context():
    """获取激活的世界书上下文"""
    context = worldbook_manager.get_active_context()
    return {
        "success": True,
        "context": context
    }

@router.get("/{entry_id}")
async def get_entry(entry_id: str):
    """获取指定条目"""
    entry = worldbook_manager.get_entry(entry_id)
    if entry:
        return {
            "success": True,
            "entry": {
                "id": entry.id,
                "title": entry.title,
                "content": entry.content,
                "category": entry.category,
                "tags": entry.tags,
                "is_active": entry.is_active,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at
            }
        }
    else:
        return {"success": False, "message": "条目不存在"}

@router.post("/create", response_model=WorldBookResponse)
async def create_entry(request: WorldBookCreateRequest):
    """创建新条目"""
    if worldbook_manager.get_entry(request.id):
        return WorldBookResponse(
            success=False,
            message=f"条目 ID {request.id} 已存在",
            entry=None
        )
    
    entry = WorldBookEntry(
        id=request.id,
        title=request.title,
        content=request.content,
        category=request.category,
        tags=request.tags,
        is_active=request.is_active
    )
    
    entry = worldbook_manager.add_entry(entry)
    return WorldBookResponse(
        success=True,
        message="条目创建成功",
        entry={
            "id": entry.id,
            "title": entry.title,
            "category": entry.category
        }
    )

@router.put("/update/{entry_id}", response_model=WorldBookResponse)
async def update_entry(entry_id: str, request: WorldBookUpdateRequest):
    """更新条目"""
    updates = request.dict(exclude_unset=True)
    entry = worldbook_manager.update_entry(entry_id, updates)
    
    if entry:
        return WorldBookResponse(
            success=True,
            message="条目更新成功",
            entry={
                "id": entry.id,
                "title": entry.title,
                "category": entry.category
            }
        )
    else:
        return WorldBookResponse(
            success=False,
            message=f"条目 {entry_id} 不存在",
            entry=None
        )

@router.delete("/delete/{entry_id}")
async def delete_entry(entry_id: str):
    """删除条目"""
    success = worldbook_manager.delete_entry(entry_id)
    if success:
        return {"success": True, "message": "条目已删除"}
    else:
        return {"success": False, "message": "条目不存在"}

@router.post("/toggle/{entry_id}")
async def toggle_entry(entry_id: str):
    """切换条目激活状态"""
    entry = worldbook_manager.get_entry(entry_id)
    if entry:
        entry.is_active = not entry.is_active
        worldbook_manager.update_entry(entry_id, {"is_active": entry.is_active})
        return {
            "success": True,
            "message": f"条目已{'激活' if entry.is_active else '停用'}",
            "is_active": entry.is_active
        }
    else:
        return {"success": False, "message": "条目不存在"}

class WorldBookAIRequest(BaseModel):
    """AI辅助创建世界书请求"""
    story: str

@router.post("/ai-generate")
async def ai_generate_worldbook(request: WorldBookAIRequest):
    """AI辅助创建世界书 - 根据用户输入的故事自动生成世界书条目"""
    try:
        prompt = f"""你是一个专业的世界构建师。请根据用户提供的故事描述，创建一个详细的世界书条目。

用户的故事/想法：
{request.story}

请根据这个故事，构建一个世界书条目。你需要输出以下信息（必须是合法的JSON格式）：
{{
    "id": "条目ID，用英文和下划线，简短好记",
    "title": "条目标题",
    "category": "分类（只能是以下之一：general, character, location, item, lore, rule）",
    "content": "详细的世界背景描述（内容丰富，至少200字）",
    "tags": ["标签1", "标签2", "标签3"]
}}

注意：
1. 只输出JSON，不要有其他内容
2. 所有字段都要填写
3. content要详细丰富，让AI能充分了解这个世界背景
4. category必须从给定的分类中选择"""

        response = await llm_service.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        
        # 提取JSON
        content = response.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        worldbook_data = json.loads(content)
        
        return {
            "success": True,
            "entry": worldbook_data
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"AI生成失败: {str(e)}"
        }

class WorldBookModifyRequest(BaseModel):
    current_entry: dict
    modify_prompt: str

@router.post("/ai-modify")
async def ai_modify_worldbook(request: WorldBookModifyRequest):
    """AI辅助修改世界书 - 根据用户输入的提示词修改现有世界书条目"""
    try:
        current = request.current_entry
        prompt = f"""你是一个专业的世界构建师。请根据用户提供的修改建议，更新现有的世界书条目。

当前世界书条目：
- 标题：{current.get('title', '')}
- 分类：{current.get('category', '')}
- 内容：{current.get('content', '')}
- 标签：{', '.join(current.get('tags', []))}

用户的修改建议：
{request.modify_prompt}

请根据用户的修改建议，更新世界书条目。你需要输出以下信息（必须是合法的JSON格式）：
{{
    "title": "条目标题",
    "category": "分类（只能是以下之一：general, character, location, item, lore, rule）",
    "content": "详细的世界背景描述（内容丰富，至少200字）",
    "tags": ["标签1", "标签2", "标签3"]
}}

注意：
1. 只输出JSON，不要有其他内容
2. 所有字段都要填写
3. 只修改用户要求的内容，其他内容保持不变
4. content要详细丰富，让AI能充分了解这个世界背景
5. category必须从给定的分类中选择"""

        response = await llm_service.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        
        # 提取JSON
        content = response.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        worldbook_data = json.loads(content)
        
        return {
            "success": True,
            "entry": worldbook_data
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"AI修改失败: {str(e)}"
        }
