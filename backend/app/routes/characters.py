from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from app.services.character_manager import character_manager, CharacterPreset
from app.services.llm_service import llm_service
from app.models.database import get_db, ChatMessage, CharacterMemory, MemoryEvent, ContextLog, AuthorNoteConfig, WorldBookEntryDB, CharacterVoiceConfig
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
async def delete_character(character_id: str, db: Session = Depends(get_db)):
    """删除角色预设及其所有关联数据"""
    try:
        success = character_manager.delete_character(character_id)
        if not success:
            return {"success": False, "message": "角色不存在或是默认角色，无法删除"}

        deleted_counts = {}

        # 1. 删除聊天记录
        chat_messages = db.query(ChatMessage).filter(ChatMessage.character_id == character_id).all()
        chat_count = len(chat_messages)
        for msg in chat_messages:
            db.delete(msg)
        deleted_counts["chat_messages"] = chat_count

        # 2. 删除角色记忆
        memories = db.query(CharacterMemory).filter(CharacterMemory.character_id == character_id).all()
        memory_count = len(memories)
        for mem in memories:
            db.delete(mem)
        deleted_counts["memories"] = memory_count

        # 3. 删除足迹记录（MemoryEvent）
        events = db.query(MemoryEvent).filter(MemoryEvent.character_id == character_id).all()
        event_count = len(events)
        for event in events:
            db.delete(event)
        deleted_counts["memory_events"] = event_count

        # 4. 删除上下文日志
        context_logs = db.query(ContextLog).filter(ContextLog.character_id == character_id).all()
        context_count = len(context_logs)
        for log in context_logs:
            db.delete(log)
        deleted_counts["context_logs"] = context_count

        # 5. 删除Author's Note配置
        author_notes = db.query(AuthorNoteConfig).filter(AuthorNoteConfig.character_id == character_id).all()
        author_note_count = len(author_notes)
        for note in author_notes:
            db.delete(note)
        deleted_counts["author_notes"] = author_note_count

        # 6. 删除关联的世界书条目
        worldbook_entries = db.query(WorldBookEntryDB).filter(WorldBookEntryDB.character_id == character_id).all()
        worldbook_count = len(worldbook_entries)
        for entry in worldbook_entries:
            db.delete(entry)
        deleted_counts["worldbook_entries"] = worldbook_count

        # 7. 删除语音配置
        voice_configs = db.query(CharacterVoiceConfig).filter(CharacterVoiceConfig.character_id == character_id).all()
        voice_count = len(voice_configs)
        for config in voice_configs:
            db.delete(config)
        deleted_counts["voice_configs"] = voice_count

        # 提交所有删除操作
        db.commit()

        total_deleted = sum(deleted_counts.values())
        print(f"[删除角色] 已删除角色 {character_id} 的所有关联数据: {deleted_counts}")

        return {
            "success": True,
            "message": f"角色已删除，共清理 {total_deleted} 条关联数据",
            "deleted_details": deleted_counts,
            "total_deleted": total_deleted
        }

    except Exception as e:
        db.rollback()
        print(f"[删除角色] 清理关联数据失败: {e}")
        return {"success": False, "message": f"清理关联数据失败: {str(e)}"}

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
        import re
        content = response.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # 增强的JSON解析，处理AI返回的各种格式问题
        try:
            character_data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"[AI生成角色] JSON解析失败，尝试修复: {e}")
            
            # 尝试修复JSON
            fixed = content
            
            # 1. 替换单引号为双引号（但保留转义的单引号）
            fixed = re.sub(r"(?<!\\)'", '"', fixed)
            
            # 2. 为未加引号的键名添加引号
            fixed = re.sub(r'(?<=[\[{,])\s*([a-zA-Z_]\w*)\s*:', r' "\1":', fixed)
            
            # 3. 移除尾随逗号
            fixed = re.sub(r',\s*}', '}', fixed)
            fixed = re.sub(r',\s*]', ']', fixed)
            
            # 4. 修复未闭合的字符串 - 查找未闭合的引号并添加闭合引号
            lines = fixed.split('\n')
            fixed_lines = []
            for line in lines:
                quote_count = line.count('"') - line.count('\\"')
                if quote_count % 2 == 1:
                    line = line.rstrip() + '"'
                fixed_lines.append(line)
            fixed = '\n'.join(fixed_lines)
            
            # 5. 尝试从内容中提取JSON对象
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', fixed, re.DOTALL)
            if json_match:
                try:
                    character_data = json.loads(json_match.group())
                    print("[AI生成角色] JSON提取成功")
                except:
                    raise Exception(f"AI返回的JSON格式错误，无法解析")
            else:
                try:
                    character_data = json.loads(fixed)
                    print("[AI生成角色] JSON修复成功")
                except json.JSONDecodeError as e2:
                    print(f"[AI生成角色] JSON修复后仍然失败: {e2}")
                    raise Exception(f"AI返回的JSON格式错误，无法正确解析。请重试或手动输入信息。")
        
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

class ChatAnalyzeRequest(BaseModel):
    """聊天对话分析请求"""
    chat_messages: str  # 聊天记录文本
    target_role: str = "ai"  # 要分析的角色：ai 或 user

@router.post("/ai-analyze-chat")
async def ai_analyze_chat(request: ChatAnalyzeRequest):
    """AI分析聊天对话 - 从聊天记录中自动识别并生成角色预设"""
    try:
        prompt = f"""你是一个专业的角色分析师。请仔细分析以下聊天对话记录，提取其中指定角色的特征，并生成完整的角色预设。

聊天记录：
{request.chat_messages}

请分析聊天记录中"{request.target_role}"角色的以下特征：
1. 说话风格和语气特点
2. 性格特征和行为模式
3. 知识背景和专业领域
4. 常用表达方式和习惯用语
5. 与其他角色的互动方式

根据分析结果，生成一个完整的角色预设（必须是合法的JSON格式）：
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
4. 保持角色的独特性和一致性
5. 根据聊天记录中的实际表现来生成，不要凭空想象"""

        response = await llm_service.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        # 提取JSON
        import re
        content = response.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # 增强的JSON解析，处理AI返回的各种格式问题
        try:
            character_data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"[AI分析角色] JSON解析失败，尝试修复: {e}")
            
            fixed = content
            fixed = re.sub(r"(?<!\\)'", '"', fixed)
            fixed = re.sub(r'(?<=[\[{,])\s*([a-zA-Z_]\w*)\s*:', r' "\1":', fixed)
            fixed = re.sub(r',\s*}', '}', fixed)
            fixed = re.sub(r',\s*]', ']', fixed)
            
            lines = fixed.split('\n')
            fixed_lines = []
            for line in lines:
                quote_count = line.count('"') - line.count('\\"')
                if quote_count % 2 == 1:
                    line = line.rstrip() + '"'
                fixed_lines.append(line)
            fixed = '\n'.join(fixed_lines)
            
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', fixed, re.DOTALL)
            if json_match:
                try:
                    character_data = json.loads(json_match.group())
                    print("[AI分析角色] JSON提取成功")
                except:
                    raise Exception(f"AI返回的JSON格式错误，无法解析")
            else:
                try:
                    character_data = json.loads(fixed)
                    print("[AI分析角色] JSON修复成功")
                except json.JSONDecodeError as e2:
                    print(f"[AI分析角色] JSON修复后仍然失败: {e2}")
                    raise Exception(f"AI返回的JSON格式错误，无法正确解析。请重试或手动输入信息。")
        
        return {
            "success": True,
            "character": character_data
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"AI分析失败: {str(e)}"
        }

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
        import re
        content = response.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # 增强的JSON解析，处理AI返回的各种格式问题
        try:
            character_data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"[AI修改角色] JSON解析失败，尝试修复: {e}")
            
            fixed = content
            fixed = re.sub(r"(?<!\\)'", '"', fixed)
            fixed = re.sub(r'(?<=[\[{,])\s*([a-zA-Z_]\w*)\s*:', r' "\1":', fixed)
            fixed = re.sub(r',\s*}', '}', fixed)
            fixed = re.sub(r',\s*]', ']', fixed)
            
            lines = fixed.split('\n')
            fixed_lines = []
            for line in lines:
                quote_count = line.count('"') - line.count('\\"')
                if quote_count % 2 == 1:
                    line = line.rstrip() + '"'
                fixed_lines.append(line)
            fixed = '\n'.join(fixed_lines)
            
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', fixed, re.DOTALL)
            if json_match:
                try:
                    character_data = json.loads(json_match.group())
                    print("[AI修改角色] JSON提取成功")
                except:
                    raise Exception(f"AI返回的JSON格式错误，无法解析")
            else:
                try:
                    character_data = json.loads(fixed)
                    print("[AI修改角色] JSON修复成功")
                except json.JSONDecodeError as e2:
                    print(f"[AI修改角色] JSON修复后仍然失败: {e2}")
                    raise Exception(f"AI返回的JSON格式错误，无法正确解析。请重试或手动输入信息。")
        
        return {
            "success": True,
            "character": character_data
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"AI修改失败: {str(e)}"
        }
