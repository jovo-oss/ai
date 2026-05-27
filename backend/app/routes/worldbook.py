from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.services.worldbook_manager import worldbook_manager, WorldBookEntry
from app.services.llm_service import llm_service
from app.services.character_manager import character_manager
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
    collection: str = ""
    character_id: str = ""  # 绑定的角色ID，空表示全局共享

class WorldBookUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    collection: Optional[str] = None
    character_id: Optional[str] = None  # 绑定的角色ID

class WorldBookResponse(BaseModel):
    success: bool
    message: str
    entry: Optional[dict] = None

@router.get("/list", response_model=WorldBookListResponse)
async def list_entries(category: Optional[str] = None, active_only: bool = False, character_id: Optional[str] = None):
    """获取世界书条目列表"""
    entries = worldbook_manager.list_entries(category=category, active_only=active_only, character_id=character_id)
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
                "collection": e.collection,
                "character_id": e.character_id,
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
                "is_active": e.is_active,
                "character_id": e.character_id
            }
            for e in entries
        ],
        "count": len(entries)
    }

@router.get("/context")
async def get_context(character_id: Optional[str] = None):
    """获取激活的世界书上下文"""
    context = worldbook_manager.get_active_context(character_id=character_id)
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
                "collection": entry.collection,
                "character_id": entry.character_id,
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
        is_active=request.is_active,
        collection=request.collection,
        character_id=request.character_id
    )
    
    entry = worldbook_manager.add_entry(entry)
    return WorldBookResponse(
        success=True,
        message="条目创建成功",
        entry={
            "id": entry.id,
            "title": entry.title,
            "category": entry.category,
            "character_id": entry.character_id
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

class WorldBookGenerateFromCharacterRequest(BaseModel):
    character_id: str

@router.post("/generate-from-character")
async def generate_worldbook_from_character(request: WorldBookGenerateFromCharacterRequest):
    """根据角色预设自动生成世界书条目"""
    try:
        character = character_manager.get_character(request.character_id)
        if not character:
            return {
                "success": False,
                "message": "角色不存在"
            }
        
        prompt = f"""你是一个专业的世界构建师。请根据以下角色预设信息，生成一套完整的世界书条目。

角色信息：
- 名称：{character.name}
- 描述：{character.description}
- 性格：{character.personality}
- 系统提示词：{character.system_prompt}
- 标签：{', '.join(character.tags) if character.tags else '无'}

请根据这个角色，生成3-5个世界书条目。这些条目应该包括：
1. 角色背景故事（character分类）
2. 角色所在的世界/地点设定（location分类）
3. 角色相关的特殊物品或能力（item分类）
4. 世界规则或设定（rule分类）
5. 其他相关的背景知识（lore分类）

你需要输出以下JSON格式：
{{
    "entries": [
        {{
            "id": "条目ID，用英文和下划线，简短好记",
            "title": "条目标题",
            "category": "分类（只能是以下之一：general, character, location, item, lore, rule）",
            "content": "详细的世界背景描述（内容丰富，至少150字）",
            "tags": ["标签1", "标签2", "标签3"]
        }},
        ...
    ]
}}

注意：
1. 只输出JSON，不要有其他内容
2. 每个条目的id必须唯一
3. content要详细丰富，让AI能充分了解这个世界背景
4. category必须从给定的分类中选择
5. 生成的条目应该与角色高度相关，构建一个完整的世界观"""

        response = await llm_service.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=3000
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
        
        # 自动保存到世界书
        saved_entries = []
        collection_id = f"char_{request.character_id}"
        for entry_data in worldbook_data.get("entries", []):
            entry_id = entry_data.get("id")
            if entry_id and not worldbook_manager.get_entry(entry_id):
                entry = WorldBookEntry(
                    id=entry_id,
                    title=entry_data.get("title", ""),
                    content=entry_data.get("content", ""),
                    category=entry_data.get("category", "general"),
                    tags=entry_data.get("tags", []),
                    is_active=True,
                    collection=collection_id,
                    character_id=request.character_id  # 绑定到角色
                )
                worldbook_manager.add_entry(entry)
                saved_entries.append(entry_data)
        
        return {
            "success": True,
            "entries": saved_entries,
            "count": len(saved_entries)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"AI生成失败: {str(e)}"
        }

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
