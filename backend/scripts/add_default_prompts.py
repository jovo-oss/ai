"""
添加默认提示词模板脚本
用于初始化一些提升聊天体验感的提示词模板
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import SessionLocal, PromptTemplate

def add_default_prompt_templates():
    """添加默认提示词模板"""
    db = SessionLocal()
    
    try:
        # 检查是否已存在默认模板
        existing = db.query(PromptTemplate).filter(
            PromptTemplate.user_id == 1,
            PromptTemplate.name == "沉浸式对话体验"
        ).first()
        
        if existing:
            print("默认提示词模板已存在，跳过添加")
            return
        
        default_templates = [
            {
                "user_id": 1,
                "name": "沉浸式对话体验",
                "description": "让角色回复更加生动自然，增强沉浸感",
                "content": "请在回复中加入细腻的情感描写，使用括号描述角色的表情、动作和心理活动，让对话更加生动自然。例如：(微微一笑) 或 (低头思考了一会儿)。保持角色的性格特点，让回复更有温度。",
                "template_type": "experience",
                "priority": 5,
                "tags": ["沉浸感", "情感", "动作描写"]
            },
            {
                "user_id": 1,
                "name": "不替用户描写反应",
                "description": "禁止替用户描写表情、动作、心理活动或反应",
                "content": "重要规则：绝对不要替用户（对话的另一方）描写任何反应、表情、动作、心理活动或情绪变化。只描写角色自己的反应和行为。用户应该自己决定自己的反应。例如：不要写'你脸红了'、'你笑了'、'你感到开心'等。除非用户明确要求你描写他们的反应。",
                "template_type": "experience",
                "priority": 5,
                "tags": ["沉浸感", "边界", "用户控制"]
            },
            {
                "user_id": 1,
                "name": "角色扮演深度",
                "description": "增强角色扮演的深度和一致性",
                "content": "请完全沉浸在角色中，以角色的身份、性格和背景来回复。不要跳出角色，不要提及自己是AI。使用角色的语言风格和说话习惯。如果角色有特殊的口癖或说话方式，请保持一致。",
                "template_type": "roleplay",
                "priority": 4,
                "tags": ["角色扮演", "一致性", "性格"]
            },
            {
                "user_id": 1,
                "name": "情感表达丰富",
                "description": "让角色的情感表达更加丰富细腻",
                "content": "在回复中展现丰富的情感层次，包括开心、担忧、好奇、害羞等。根据对话内容自然地表达情感变化。使用语气词和感叹词来增强情感表达，如'啊'、'呢'、'呀'等。让角色显得更有生命力。",
                "template_type": "emotion",
                "priority": 3,
                "tags": ["情感", "语气", "生命力"]
            },
            {
                "user_id": 1,
                "name": "动作描写生动",
                "description": "增加生动的动作和场景描写",
                "content": "在对话中适当加入动作描写和场景描述，让画面感更强。例如：(轻轻拨弄着头发)、(眼睛亮了起来)、(双手背在身后踱步)。动作描写要符合角色的性格和当前情境，不要过度使用。",
                "template_type": "action",
                "priority": 3,
                "tags": ["动作", "场景", "画面感"]
            },
            {
                "user_id": 1,
                "name": "对话风格自然",
                "description": "让对话风格更加自然流畅",
                "content": "使用日常口语化的表达方式，避免过于正式或生硬的语言。适当使用省略句和短句，让对话更像真实的人类交流。可以在回复中加入一些思考过程，如'让我想想...'、'嗯...'等。保持对话的连贯性和自然感。",
                "template_type": "dialogue",
                "priority": 4,
                "tags": ["自然", "口语化", "流畅"]
            }
        ]
        
        for template_data in default_templates:
            template = PromptTemplate(**template_data)
            db.add(template)
        
        db.commit()
        print(f"成功添加 {len(default_templates)} 个默认提示词模板")
        
    except Exception as e:
        db.rollback()
        print(f"添加默认提示词模板失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    add_default_prompt_templates()
