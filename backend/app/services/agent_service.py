import os
import tempfile
import base64
from typing import Optional, Dict, Any
from fastapi import UploadFile
from app.services.config_service import config_service
from app.services.voice_config_service import voice_config_service
from app.models.database import SessionLocal


class AgentService:
    """Agent工具服务 - 专注于角色扮演和GalGame元素"""
    
    async def analyze_voice(self, file: UploadFile, character_id: Optional[str], user_id: int) -> Dict[str, Any]:
        """分析语音文件，识别音色特征"""
        try:
            file_content = await file.read()
            
            if len(file_content) > 10 * 1024 * 1024:
                return {
                    "success": False,
                    "message": "文件过大，请上传小于10MB的音频文件"
                }
            
            allowed_types = ['audio/mpeg', 'audio/wav', 'audio/mp3', 'audio/webm', 'audio/ogg']
            if file.content_type not in allowed_types:
                return {
                    "success": False,
                    "message": f"不支持的文件类型: {file.content_type}，请上传MP3、WAV、WEBM或OGG格式"
                }
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tmp_file.write(file_content)
                tmp_file_path = tmp_file.name
            
            try:
                analysis_result = await self._mock_voice_analysis(tmp_file_path, file.filename)
                suggested_config = self._generate_voice_config(analysis_result)
                
                if character_id:
                    await self.apply_voice_config(character_id, suggested_config, user_id)
                
                return {
                    "success": True,
                    "message": "语音分析完成",
                    "analysis": analysis_result,
                    "suggested_config": suggested_config
                }
            finally:
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
                    
        except Exception as e:
            return {
                "success": False,
                "message": f"语音分析失败: {str(e)}"
            }
    
    async def _mock_voice_analysis(self, file_path: str, filename: str) -> Dict[str, Any]:
        """模拟语音分析（实际应用中应调用AI服务）"""
        import random
        speed = round(random.uniform(0.8, 1.5), 2)
        pitch = round(random.uniform(0.8, 1.3), 2)
        volume = round(random.uniform(0.7, 1.0), 2)
        
        voices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
        if pitch > 1.1:
            recommended_voice = random.choice(['nova', 'shimmer'])
        elif pitch < 0.9:
            recommended_voice = random.choice(['onyx', 'echo'])
        else:
            recommended_voice = random.choice(['alloy', 'fable'])
        
        return {
            "filename": filename,
            "duration_seconds": round(random.uniform(2.0, 10.0), 2),
            "detected_features": {
                "speed": speed,
                "pitch": pitch,
                "volume": volume,
                "emotion": random.choice(["平静", "兴奋", "温柔", "严肃", "活泼"]),
                "gender_tendency": "偏女声" if pitch > 1.0 else "偏男声" if pitch < 1.0 else "中性"
            },
            "recommended_voice": recommended_voice,
            "confidence": round(random.uniform(0.7, 0.95), 2)
        }
    
    def _generate_voice_config(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """根据分析结果生成语音配置"""
        features = analysis.get("detected_features", {})
        
        return {
            "tts_voice": analysis.get("recommended_voice", "nova"),
            "speed": features.get("speed", 1.0),
            "volume": features.get("volume", 1.0),
            "pitch": features.get("pitch", 1.0),
            "audio_format": "mp3",
            "enable_tts": True,
            "auto_play": False
        }
    
    async def apply_voice_config(self, character_id: str, config: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """应用语音配置到角色"""
        try:
            existing = voice_config_service.get_config(user_id, character_id)
            
            if existing.get("success"):
                result = voice_config_service.update_config(user_id, character_id, config)
            else:
                from app.services.voice_config_service import VoiceConfigCreate
                config_data = VoiceConfigCreate(
                    user_id=user_id,
                    character_id=character_id,
                    **config
                )
                result = voice_config_service.create_config(config_data)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "message": f"应用配置失败: {str(e)}"
            }
    
    def get_available_tools(self) -> Dict[str, Any]:
        """获取可用的Agent工具列表"""
        return {
            "success": True,
            "tools": [
                {
                    "id": "character_analyzer",
                    "name": "角色分析师",
                    "description": "从聊天记录中分析并生成角色预设",
                    "icon": "🎭",
                    "endpoint": "/api/agent/character/analyze"
                },
                {
                    "id": "worldbook_generator",
                    "name": "世界书生成器",
                    "description": "根据故事自动生成世界书条目",
                    "icon": "📚",
                    "endpoint": "/api/agent/worldbook/generate"
                },
                {
                    "id": "chat_summarizer",
                    "name": "聊天总结师",
                    "description": "总结聊天记录，提取关键信息",
                    "icon": "📝",
                    "endpoint": "/api/agent/chat/summarize"
                },
                {
                    "id": "memory_extractor",
                    "name": "记忆提取器",
                    "description": "从对话中自动提取记忆节点",
                    "icon": "🧠",
                    "endpoint": "/api/agent/memory/extract"
                },
                {
                    "id": "character_optimizer",
                    "name": "角色优化师",
                    "description": "优化现有角色的设定和表现",
                    "icon": "✨",
                    "endpoint": "/api/agent/character/optimize"
                },
                {
                    "id": "affection_designer",
                    "name": "好感度设计师",
                    "description": "为角色设计好感度系统，定义等级和触发条件",
                    "icon": "💕",
                    "endpoint": "/api/agent/affection/design"
                },
                {
                    "id": "relationship_analyzer",
                    "name": "角色关系分析",
                    "description": "分析多个角色之间的关系网络，生成关系图谱",
                    "icon": "🔗",
                    "endpoint": "/api/agent/relationship/analyze"
                },
                {
                    "id": "story_branch_generator",
                    "name": "剧情分支生成器",
                    "description": "生成多分支剧情路线，类似GalGame的多结局设计",
                    "icon": "🌿",
                    "endpoint": "/api/agent/story/branch"
                },
                {
                    "id": "scene_generator",
                    "name": "场景生成器",
                    "description": "生成精美的场景描述，可用于CG/立绘场景",
                    "icon": "🎬",
                    "endpoint": "/api/agent/scene/generate"
                },
                {
                    "id": "dialogue_style_analyzer",
                    "name": "对话风格分析",
                    "description": "分析角色对话风格，给出优化建议",
                    "icon": "💝",
                    "endpoint": "/api/agent/dialogue/style"
                }
            ]
        }
    
    async def analyze_character(self, chat_messages: str, target_role: str = "ai", user_id: int = 1) -> Dict[str, Any]:
        """从聊天记录中分析并生成角色预设"""
        try:
            from app.services.llm_service import llm_service
            
            if not chat_messages.strip():
                return {"success": False, "message": "请输入聊天记录"}
            
            if len(chat_messages) < 100:
                return {"success": False, "message": "聊天记录太短，至少需要100个字符"}
            
            prompt = f"""你是一个专业的角色分析师。请仔细分析以下聊天对话记录，提取其中指定角色的特征，并生成完整的角色预设。

聊天记录：
{chat_messages}

请分析聊天记录中"{target_role}"角色的以下特征：
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
                temperature=0.7,
                max_tokens=2000
            )
            
            import json
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
                "message": "角色分析完成",
                "character": character_data
            }
            
        except Exception as e:
            return {"success": False, "message": f"角色分析失败: {str(e)}"}
    
    async def generate_worldbook(self, story: str, user_id: int = 1) -> Dict[str, Any]:
        """根据故事自动生成世界书条目"""
        try:
            from app.services.llm_service import llm_service
            
            if not story.strip():
                return {"success": False, "message": "请输入故事或想法"}
            
            if len(story) < 50:
                return {"success": False, "message": "故事太短，至少需要50个字符"}
            
            prompt = f"""你是一个专业的世界构建师。请根据用户提供的故事描述，创建一个详细的世界书条目。

用户的故事/想法：
{story}

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
                temperature=0.8,
                max_tokens=2000
            )
            
            import json
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
                "message": "世界书生成完成",
                "worldbook": worldbook_data
            }
            
        except Exception as e:
            return {"success": False, "message": f"世界书生成失败: {str(e)}"}
    
    async def summarize_chat(self, chat_messages: str, user_id: int = 1) -> Dict[str, Any]:
        """总结聊天记录，提取关键信息"""
        try:
            from app.services.llm_service import llm_service
            
            if not chat_messages.strip():
                return {"success": False, "message": "请输入聊天记录"}
            
            if len(chat_messages) < 100:
                return {"success": False, "message": "聊天记录太短，至少需要100个字符"}
            
            prompt = f"""你是一个专业的聊天记录分析师。请仔细阅读以下聊天记录，并生成一个简洁但全面的总结。

要求：
1. 提取聊天中的核心话题和关键信息
2. 总结双方的主要观点和互动内容
3. 保持逻辑清晰，结构合理
4. 使用简洁明了的语言
5. 不要添加聊天中没有的信息

聊天记录：
{chat_messages}

请生成总结："""
            
            summary = await llm_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            return {
                "success": True,
                "message": "聊天总结完成",
                "summary": summary,
                "original_length": len(chat_messages),
                "summary_length": len(summary)
            }
            
        except Exception as e:
            return {"success": False, "message": f"聊天总结失败: {str(e)}"}
    
    async def extract_memory(self, chat_messages: str, user_id: int = 1) -> Dict[str, Any]:
        """从对话中自动提取记忆节点"""
        try:
            from app.services.llm_service import llm_service
            
            if not chat_messages.strip():
                return {"success": False, "message": "请输入聊天记录"}
            
            if len(chat_messages) < 100:
                return {"success": False, "message": "聊天记录太短，至少需要100个字符"}
            
            prompt = f"""你是一个专业的记忆分析师。请分析以下聊天记录，提取重要的信息点并生成结构化的记忆节点。

聊天记录：
{chat_messages}

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
                temperature=0.7,
                max_tokens=2000
            )
            
            import json
            import re
            content = response.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            try:
                memories = json.loads(content)
            except json.JSONDecodeError:
                fixed = content
                fixed = re.sub(r"(?<!\\)'", '"', fixed)
                fixed = re.sub(r'(?<=[\[{,])\s*([a-zA-Z_]\w*)\s*:', r' "\1":', fixed)
                fixed = re.sub(r',\s*}', '}', fixed)
                fixed = re.sub(r',\s*]', ']', fixed)
                memories = json.loads(fixed)
            
            return {
                "success": True,
                "message": "记忆提取完成",
                "memories": memories,
                "count": len(memories)
            }
            
        except Exception as e:
            return {"success": False, "message": f"记忆提取失败: {str(e)}"}
    
    async def optimize_character(self, character_data: str, optimization_prompt: str, user_id: int = 1) -> Dict[str, Any]:
        """优化现有角色的设定和表现"""
        try:
            from app.services.llm_service import llm_service
            
            if not character_data.strip():
                return {"success": False, "message": "请输入角色设定"}
            
            if not optimization_prompt.strip():
                return {"success": False, "message": "请输入优化要求"}
            
            prompt = f"""你是一个专业的角色设计师。请根据以下角色设定和优化要求，优化这个角色。

当前角色设定：
{character_data}

优化要求：
{optimization_prompt}

请优化这个角色设定，输出优化后的完整角色设定（必须是合法的JSON格式）：
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
5. 根据优化要求来改进角色设定"""
            
            response = await llm_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            import json
            content = response.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            optimized_character = json.loads(content)
            
            return {
                "success": True,
                "message": "角色优化完成",
                "character": optimized_character
            }
            
        except Exception as e:
            return {"success": False, "message": f"角色优化失败: {str(e)}"}

    async def design_affection_system(self, character_name: str, character_description: str, affection_levels: int = 5, user_id: int = 1) -> Dict[str, Any]:
        """为角色设计好感度系统"""
        try:
            from app.services.llm_service import llm_service
            
            if not character_name.strip():
                return {"success": False, "message": "请输入角色名称"}
            
            if not character_description.strip():
                return {"success": False, "message": "请输入角色描述"}
            
            prompt = f"""你是一个GalGame系统设计专家。请为以下角色设计一个完整的好感度系统。

角色名称：{character_name}
角色描述：{character_description}
好感度等级数量：{affection_levels}个等级

请设计好感度系统（必须是合法的JSON格式）：
{{
    "character_name": "角色名称",
    "affection_levels": [
        {{
            "level": 1,
            "name": "等级名称（如：陌生人、普通朋友、好友、密友、恋人）",
            "description": "这个等级的特征描述",
            "dialogue_style": "这个等级下的对话风格变化",
            "trigger_conditions": ["达到这个等级需要的条件"]
        }}
    ],
    "affection_actions": [
        {{
            "action": "可以增加好感度的行为",
            "points": 增加的点数,
            "description": "行为说明"
        }}
    ],
    "negative_actions": [
        {{
            "action": "会降低好感度的行为",
            "points": 减少的点数,
            "description": "行为说明"
        }}
    ],
    "special_events": [
        {{
            "event_name": "特殊事件名称",
            "required_level": 触发需要的最低好感等级,
            "description": "事件描述",
            "dialogue": "事件中的特殊对话"
        }}
    ]
}}

注意：
1. 只输出JSON，不要有其他内容
2. 好感度等级要有明显的递进关系
3. 行为和事件要符合角色性格
4. 特殊事件要有吸引力，类似GalGame的关键剧情"""
            
            response = await llm_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=3000
            )
            
            import json
            content = response.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            affection_system = json.loads(content)
            
            return {
                "success": True,
                "message": "好感度系统设计完成",
                "affection_system": affection_system
            }
            
        except Exception as e:
            return {"success": False, "message": f"好感度系统设计失败: {str(e)}"}

    async def analyze_relationship(self, characters: str, context: str = "", user_id: int = 1) -> Dict[str, Any]:
        """分析多个角色之间的关系网络"""
        try:
            from app.services.llm_service import llm_service
            
            if not characters.strip():
                return {"success": False, "message": "请输入角色信息"}
            
            prompt = f"""你是一个角色关系分析专家。请分析以下角色之间的关系网络，生成详细的关系图谱。

角色信息：
{characters}

{"背景信息：" + context if context else ""}

请分析角色之间的关系（必须是合法的JSON格式）：
{{
    "characters": [
        {{
            "name": "角色名称",
            "role": "角色在关系网中的定位",
            "personality": "性格特点"
        }}
    ],
    "relationships": [
        {{
            "from": "角色A",
            "to": "角色B",
            "relationship_type": "关系类型（如：朋友、恋人、师生、对手、家人等）",
            "closeness": "亲密程度1-10",
            "description": "关系详细描述",
            "history": "关系历史或背景",
            "dynamics": "互动动态和模式"
        }}
    ],
    "relationship_groups": [
        {{
            "group_name": "关系群组名称",
            "members": ["成员角色"],
            "description": "群组特征"
        }}
    ],
    "conflict_points": [
        {{
            "characters": ["涉及的角色"],
            "conflict": "冲突描述",
            "resolution": "可能的解决方式"
        }}
    ]
}}

注意：
1. 只输出JSON，不要有其他内容
2. 关系要符合角色性格和背景
3. 亲密程度要合理评定
4. 冲突点要有戏剧性，适合故事发展"""
            
            response = await llm_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=3000
            )
            
            import json
            content = response.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            relationship_data = json.loads(content)
            
            return {
                "success": True,
                "message": "角色关系分析完成",
                "relationship_data": relationship_data
            }
            
        except Exception as e:
            return {"success": False, "message": f"角色关系分析失败: {str(e)}"}

    async def generate_story_branch(self, story_context: str, branch_count: int = 3, ending_count: int = 3, user_id: int = 1) -> Dict[str, Any]:
        """生成多分支剧情路线"""
        try:
            from app.services.llm_service import llm_service
            
            if not story_context.strip():
                return {"success": False, "message": "请输入故事背景"}
            
            prompt = f"""你是一个GalGame剧情设计师。请根据以下故事背景，设计一个多分支剧情系统。

故事背景：
{story_context}

分支数量：{branch_count}个主要分支
结局数量：{ending_count}个不同结局

请设计剧情分支系统（必须是合法的JSON格式）：
{{
    "story_title": "故事标题",
    "main_plot": {{"summary": "主线剧情概要", "key_events": ["关键事件1", "关键事件2"]}},
    "branches": [
        {{
            "branch_id": "分支ID",
            "branch_name": "分支名称",
            "trigger_condition": "触发这个分支的条件",
            "plot_summary": "分支剧情概要",
            "key_scenes": ["关键场景1", "关键场景2"],
            "character_focus": "这个分支重点刻画的角色",
            "emotional_tone": "情感基调（如：温馨、悲伤、紧张、欢乐等）"
        }}
    ],
    "choice_points": [
        {{
            "scene": "出现选择的场景",
            "question": "向玩家提出的问题",
            "choices": [
                {{"text": "选项文本", "effect": "选择的影响", "leads_to": "导向的分支或结局"}}
            ]
        }}
    ],
    "endings": [
        {{
            "ending_id": "结局ID",
            "ending_name": "结局名称",
            "ending_type": "结局类型（如：True End, Good End, Normal End, Bad End）",
            "description": "结局描述",
            "required_conditions": ["达成这个结局需要的条件"],
            "emotional_impact": "结局的情感冲击力描述"
        }}
    ],
    "hidden_elements": [
        {{
            "element_name": "隐藏要素名称",
            "type": "类型（隐藏角色/隐藏剧情/隐藏结局等）",
            "unlock_condition": "解锁条件",
            "description": "描述"
        }}
    ]
}}

注意：
1. 只输出JSON，不要有其他内容
2. 分支要有明显的差异化
3. 结局要有情感冲击力
4. 选择要有意义，影响深远
5. 隐藏要素增加重玩价值"""
            
            response = await llm_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=4000
            )
            
            import json
            content = response.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            story_branch = json.loads(content)
            
            return {
                "success": True,
                "message": "剧情分支生成完成",
                "story_branch": story_branch
            }
            
        except Exception as e:
            return {"success": False, "message": f"剧情分支生成失败: {str(e)}"}

    async def generate_scene(self, scene_description: str, scene_type: str = "general", atmosphere: str = "neutral", user_id: int = 1) -> Dict[str, Any]:
        """生成精美的场景描述"""
        try:
            from app.services.llm_service import llm_service
            
            if not scene_description.strip():
                return {"success": False, "message": "请输入场景描述"}
            
            atmosphere_map = {
                "romantic": "浪漫温馨",
                "tense": "紧张刺激",
                "melancholy": "忧伤感伤",
                "joyful": "欢乐明快",
                "mysterious": "神秘诡异",
                "peaceful": "平静安宁",
                "neutral": "中性"
            }
            atmosphere_desc = atmosphere_map.get(atmosphere, "中性")
            
            prompt = f"""你是一个专业的场景设计师，擅长为GalGame创作精美的场景描述。请根据用户的需求，生成一个详细的场景描述。

场景要求：
{scene_description}
场景类型：{scene_type}
氛围基调：{atmosphere_desc}

请生成详细的场景描述，包括：
1. 场景概述（一句话概括）
2. 环境描写（详细的视觉描述，包括光线、色彩、空间感）
3. 氛围营造（如何营造指定的氛围）
4. 细节刻画（值得注意的小细节）
5. 角色互动建议（角色在这个场景中可能的互动方式）
6. CG构图建议（如果要画成CG，如何构图）

请以优美的文学性语言描述，让读者仿佛身临其境。描述要详细丰富，至少300字。"""
            
            scene_content = await llm_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=3000
            )
            
            return {
                "success": True,
                "message": "场景生成完成",
                "scene": {
                    "description": scene_content,
                    "scene_type": scene_type,
                    "atmosphere": atmosphere_desc
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"场景生成失败: {str(e)}"}

    async def analyze_dialogue_style(self, chat_messages: str, target_character: str = "", user_id: int = 1) -> Dict[str, Any]:
        """分析角色对话风格"""
        try:
            from app.services.llm_service import llm_service
            
            if not chat_messages.strip():
                return {"success": False, "message": "请输入聊天记录"}
            
            if len(chat_messages) < 100:
                return {"success": False, "message": "聊天记录太短，至少需要100个字符"}
            
            target_instruction = f'，特别是"{target_character}"的对话风格' if target_character else ""
            
            prompt = f"""你是一个专业的对话风格分析师。请分析以下聊天记录中角色{target_instruction}，给出详细的分析和优化建议。

聊天记录：
{chat_messages}

请从以下维度进行分析：
1. 语言特点（用词习惯、句式结构、口头禅等）
2. 情感表达（如何表达喜怒哀乐等情感）
3. 互动模式（如何与他人互动，回应方式）
4. 个性体现（对话中体现的性格特征）
5. 一致性评估（对话风格是否一致）

输出分析报告（必须是合法的JSON格式）：
{{
    "overall_style": {{
        "summary": "整体风格概述",
        "strengths": ["风格优点1", "风格优点2"],
        "weaknesses": ["风格不足1", "风格不足2"]
    }},
    "language_features": {{
        "vocabulary": "用词特点",
        "sentence_structure": "句式特点",
        "catchphrases": ["常用表达/口头禅"],
        "tone": "语气特点"
    }},
    "emotional_expression": {{
        "joy": "开心时的表现",
        "anger": "生气时的表现",
        "sadness": "伤心时的表现",
        "surprise": "惊讶时的表现"
    }},
    "interaction_patterns": {{
        "response_style": "回应方式",
        "initiative": "主动性程度",
        "empathy": "共情能力"
    }},
    "optimization_suggestions": [
        {{
            "aspect": "需要优化的方面",
            "current_issue": "当前存在的问题",
            "suggestion": "优化建议",
            "example": "优化后的示例对话"
        }}
    ]
}}

注意：
1. 只输出JSON，不要有其他内容
2. 分析要客观准确
3. 建议要具体可行
4. 示例要符合角色设定"""
            
            response = await llm_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=3000
            )
            
            import json
            content = response.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            style_analysis = json.loads(content)
            
            return {
                "success": True,
                "message": "对话风格分析完成",
                "style_analysis": style_analysis
            }
            
        except Exception as e:
            return {"success": False, "message": f"对话风格分析失败: {str(e)}"}


agent_service = AgentService()
