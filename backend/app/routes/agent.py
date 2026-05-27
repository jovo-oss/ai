from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from app.services.agent_service import agent_service

router = APIRouter(prefix="/api/agent", tags=["Agent Tools"])


class VoiceAnalysisResult(BaseModel):
    success: bool
    message: str
    analysis: Optional[dict] = None
    suggested_config: Optional[dict] = None


class CharacterAnalyzeRequest(BaseModel):
    chat_messages: str
    target_role: str = "ai"
    user_id: int = 1


class WorldBookGenerateRequest(BaseModel):
    story: str
    user_id: int = 1


class ChatSummarizeRequest(BaseModel):
    chat_messages: str
    user_id: int = 1


class MemoryExtractRequest(BaseModel):
    chat_messages: str
    user_id: int = 1


class CharacterOptimizeRequest(BaseModel):
    character_data: str
    optimization_prompt: str
    user_id: int = 1


class AffectionDesignRequest(BaseModel):
    character_name: str
    character_description: str
    affection_levels: int = 5
    user_id: int = 1


class RelationshipAnalyzeRequest(BaseModel):
    characters: str
    context: str = ""
    user_id: int = 1


class StoryBranchGenerateRequest(BaseModel):
    story_context: str
    branch_count: int = 3
    ending_count: int = 3
    user_id: int = 1


class SceneGenerateRequest(BaseModel):
    scene_description: str
    scene_type: str = "general"
    atmosphere: str = "neutral"
    user_id: int = 1


class DialogueStyleAnalyzeRequest(BaseModel):
    chat_messages: str
    target_character: str = ""
    user_id: int = 1


@router.post("/voice/analyze")
async def analyze_voice(
    file: UploadFile = File(...),
    character_id: Optional[str] = Form(None),
    user_id: int = Form(default=1)
):
    """Analyze uploaded voice file"""
    return await agent_service.analyze_voice(file, character_id, user_id)


@router.post("/voice/apply-config")
async def apply_voice_config(
    character_id: str = Form(...),
    config_data: str = Form(...),
    user_id: int = Form(default=1)
):
    """Apply AI-generated voice config to character"""
    import json
    config = json.loads(config_data)
    return await agent_service.apply_voice_config(character_id, config, user_id)


@router.get("/tools")
async def get_available_tools():
    """Get available agent tools list"""
    return agent_service.get_available_tools()


@router.post("/character/analyze")
async def analyze_character(request: CharacterAnalyzeRequest):
    """Analyze chat messages and generate character preset"""
    return await agent_service.analyze_character(request.chat_messages, request.target_role, request.user_id)


@router.post("/worldbook/generate")
async def generate_worldbook(request: WorldBookGenerateRequest):
    """Generate worldbook entry from story"""
    return await agent_service.generate_worldbook(request.story, request.user_id)


@router.post("/chat/summarize")
async def summarize_chat(request: ChatSummarizeRequest):
    """Summarize chat messages"""
    return await agent_service.summarize_chat(request.chat_messages, request.user_id)


@router.post("/memory/extract")
async def extract_memory(request: MemoryExtractRequest):
    """Extract memory nodes from chat messages"""
    return await agent_service.extract_memory(request.chat_messages, request.user_id)


@router.post("/character/optimize")
async def optimize_character(request: CharacterOptimizeRequest):
    """Optimize character settings"""
    return await agent_service.optimize_character(request.character_data, request.optimization_prompt, request.user_id)


@router.post("/affection/design")
async def design_affection(request: AffectionDesignRequest):
    """Design affection system for character"""
    return await agent_service.design_affection_system(request.character_name, request.character_description, request.affection_levels, request.user_id)


@router.post("/relationship/analyze")
async def analyze_relationship(request: RelationshipAnalyzeRequest):
    """Analyze character relationships"""
    return await agent_service.analyze_relationship(request.characters, request.context, request.user_id)


@router.post("/story/branch")
async def generate_story_branch(request: StoryBranchGenerateRequest):
    """Generate story branch routes"""
    return await agent_service.generate_story_branch(request.story_context, request.branch_count, request.ending_count, request.user_id)


@router.post("/scene/generate")
async def generate_scene(request: SceneGenerateRequest):
    """Generate scene description"""
    return await agent_service.generate_scene(request.scene_description, request.scene_type, request.atmosphere, request.user_id)


@router.post("/dialogue/style")
async def analyze_dialogue_style(request: DialogueStyleAnalyzeRequest):
    """Analyze dialogue style"""
    return await agent_service.analyze_dialogue_style(request.chat_messages, request.target_character, request.user_id)
