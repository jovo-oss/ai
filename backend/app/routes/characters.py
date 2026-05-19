from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.services.character_manager import character_manager, CharacterPreset
from app.services.llm_service import llm_service
import json

router = APIRouter(prefix="/api/characters", tags=["角色预设"])

class CharacterListResponse(BaseModel):
    success: bool
    characters: List[dict]
    current_character: str

class CharacterCreateRequest(BaseModel):
    id: str
    name: str
    description: str
    personality: str
    greeting: str
    system_prompt: str
    avatar: str = "🤖"
    tags: List[str] = []

class CharacterUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    personality: Optional[str] = None
    greeting: Optional[str] = None
    system_prompt: Optional[str] = None
    avatar: Optional[str] = None
    tags: Optional[List[str]] = None

class CharacterResponse(BaseModel):
    success: bool
    message: str
    character: Optional[dict] = None

@router.get("/list", response_model=CharacterListResponse)
async def list_characters():
    """获取所有角色预设列表"""
    characters = character_manager.list_characters()
    return CharacterListResponse(
        success=True,
        characters=[
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "personality": c.personality,
                "greeting": c.greeting,
                "system_prompt": c.system_prompt,
                "avatar": c.avatar,
                "tags": c.tags,
                "is_default": c.is_default
            }
            for c in characters
        ],
        current_character=character_manager.current_character_id
    )

@router.get("/current")
async def get_current_character():
    """获取当前使用的角色"""
    current = character_manager.get_current_character()
    return {
        "success": True,
        "character": {
            "id": current.id,
            "name": current.name,
            "description": current.description,
            "personality": current.personality,
            "greeting": current.greeting,
            "system_prompt": current.system_prompt,
            "avatar": current.avatar,
            "tags": current.tags
        }
    }

@router.post("/switch", response_model=CharacterResponse)
async def switch_character(character_id: str):
    """切换当前使用的角色"""
    success = character_manager.set_current_character(character_id)
    if success:
        current = character_manager.get_current_character()
        return CharacterResponse(
            success=True,
            message=f"已切换到 {current.name}",
            character={
                "id": current.id,
                "name": current.name,
                "avatar": current.avatar,
                "greeting": current.greeting
            }
        )
    else:
        return CharacterResponse(
            success=False,
            message=f"角色 {character_id} 不存在",
            character=None
        )

@router.post("/create", response_model=CharacterResponse)
async def create_character(request: CharacterCreateRequest):
    """创建新角色预设"""
    if character_manager.get_character(request.id):
        return CharacterResponse(
            success=False,
            message=f"角色 ID {request.id} 已存在",
            character=None
        )
    
    character = CharacterPreset(
        id=request.id,
        name=request.name,
        description=request.description,
        personality=request.personality,
        greeting=request.greeting,
        system_prompt=request.system_prompt,
        avatar=request.avatar,
        tags=request.tags
    )
    
    character_manager.add_character(character)
    return CharacterResponse(
        success=True,
        message="角色创建成功",
        character={
            "id": character.id,
            "name": character.name,
            "avatar": character.avatar
        }
    )

@router.put("/update/{character_id}", response_model=CharacterResponse)
async def update_character(character_id: str, request: CharacterUpdateRequest):
    """更新角色预设"""
    character = character_manager.get_character(character_id)
    if not character:
        return CharacterResponse(
            success=False,
            message=f"角色 {character_id} 不存在",
            character=None
        )
    
    updates = request.dict(exclude_unset=True)
    for key, value in updates.items():
        setattr(character, key, value)
    
    character_manager.add_character(character)
    return CharacterResponse(
        success=True,
        message="角色更新成功",
        character={
            "id": character.id,
            "name": character.name,
            "avatar": character.avatar
        }
    )

@router.delete("/delete/{character_id}")
async def delete_character(character_id: str):
    """删除角色预设"""
    success = character_manager.delete_character(character_id)
    if success:
        return {"success": True, "message": "角色已删除"}
    else:
        return {"success": False, "message": "角色不存在或是默认角色，无法删除"}

class CharacterAIRequest(BaseModel):
    """AI辅助创建角色请求"""
    story: str

@router.post("/ai-generate")
async def ai_generate_character(request: CharacterAIRequest):
    """AI辅助创建角色 - 根据用户输入的故事自动生成角色设定"""
    try:
        prompt = f"""你是一个专业的角色设计师。请根据用户提供的故事描述，创建一个完整的角色设定。

用户的故事/想法：
{request.story}

请根据这个故事，提取并创建一个角色。你需要输出以下信息（必须是合法的JSON格式）：
{{
    "id": "角色ID，用英文和下划线，简短好记",
    "name": "角色名称",
    "avatar": "一个合适的emoji头像",
    "description": "角色的简短描述（一句话）",
    "personality": "角色的性格特点（详细一些）",
    "greeting": "角色的开场白（用第一人称，符合角色性格）",
    "system_prompt": "系统提示词（详细告诉AI如何扮演这个角色，包括背景、性格、说话方式等）",
    "tags": ["标签1", "标签2", "标签3"]
}}

注意：
1. 只输出JSON，不要有其他内容
2. 所有字段都要填写
3. system_prompt要详细，让AI能很好地扮演这个角色
4. 保持角色的独特性和一致性"""

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
        
        character_data = json.loads(content)
        
        return {
            "success": True,
            "character": character_data
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"AI生成失败: {str(e)}"
        }

class CharacterModifyRequest(BaseModel):
    current_character: dict
    modify_prompt: str

@router.post("/ai-modify")
async def ai_modify_character(request: CharacterModifyRequest):
    """AI辅助修改角色 - 根据用户输入的提示词修改现有角色设定"""
    try:
        current = request.current_character
        prompt = f"""你是一个专业的角色设计师。请根据用户提供的修改建议，更新现有的角色设定。

当前角色设定：
- 名称：{current.get('name', '')}
- 头像：{current.get('avatar', '')}
- 描述：{current.get('description', '')}
- 性格特点：{current.get('personality', '')}
- 开场白：{current.get('greeting', '')}
- 系统提示词：{current.get('system_prompt', '')}
- 标签：{', '.join(current.get('tags', []))}

用户的修改建议：
{request.modify_prompt}

请根据用户的修改建议，更新角色设定。你需要输出以下信息（必须是合法的JSON格式）：
{{
    "name": "角色名称",
    "avatar": "一个合适的emoji头像",
    "description": "角色的简短描述（一句话）",
    "personality": "角色的性格特点（详细一些）",
    "greeting": "角色的开场白（用第一人称，符合角色性格）",
    "system_prompt": "系统提示词（详细告诉AI如何扮演这个角色，包括背景、性格、说话方式等）",
    "tags": ["标签1", "标签2", "标签3"]
}}

注意：
1. 只输出JSON，不要有其他内容
2. 所有字段都要填写
3. 只修改用户要求的内容，其他内容保持不变
4. system_prompt要详细，让AI能很好地扮演这个角色
5. 保持角色的独特性和一致性"""

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
        
        character_data = json.loads(content)
        
        return {
            "success": True,
            "character": character_data
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"AI修改失败: {str(e)}"
        }
