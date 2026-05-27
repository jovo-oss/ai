from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.models.database import get_db, PromptTemplate

router = APIRouter(prefix="/api/prompt-templates", tags=["prompt_templates"])


class PromptTemplateCreate(BaseModel):
    """创建提示词模板请求"""
    name: str
    description: Optional[str] = None
    content: str
    template_type: str = "experience"
    character_id: Optional[str] = None
    priority: int = 1
    tags: Optional[List[str]] = None


class PromptTemplateUpdate(BaseModel):
    """更新提示词模板请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    template_type: Optional[str] = None
    character_id: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None


class PromptTemplateResponse(BaseModel):
    """提示词模板响应"""
    id: int
    user_id: int
    character_id: Optional[str]
    name: str
    description: Optional[str]
    content: str
    template_type: str
    is_enabled: bool
    is_active: bool
    priority: int
    tags: Optional[List[str]]
    created_at: str
    updated_at: str


@router.get("/")
def list_prompt_templates(
    user_id: int,
    character_id: Optional[str] = None,
    template_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取提示词模板列表"""
    query = db.query(PromptTemplate).filter(PromptTemplate.user_id == user_id)
    
    if character_id:
        query = query.filter(PromptTemplate.character_id == character_id)
    
    if template_type:
        query = query.filter(PromptTemplate.template_type == template_type)
    
    templates = query.order_by(PromptTemplate.priority.desc()).all()
    
    result = []
    for t in templates:
        result.append({
            "id": t.id,
            "user_id": t.user_id,
            "character_id": t.character_id,
            "name": t.name,
            "description": t.description,
            "content": t.content,
            "template_type": t.template_type,
            "is_enabled": t.is_enabled,
            "is_active": t.is_active,
            "priority": t.priority,
            "tags": t.tags,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None
        })
    
    return result


@router.get("/{template_id}", response_model=PromptTemplateResponse)
def get_prompt_template(
    template_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """获取单个提示词模板"""
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == template_id,
        PromptTemplate.user_id == user_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="提示词模板不存在")
    
    return {
        "id": template.id,
        "user_id": template.user_id,
        "character_id": template.character_id,
        "name": template.name,
        "description": template.description,
        "content": template.content,
        "template_type": template.template_type,
        "is_enabled": template.is_enabled,
        "is_active": template.is_active,
        "priority": template.priority,
        "tags": template.tags,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None
    }


@router.post("/", response_model=PromptTemplateResponse)
def create_prompt_template(
    request: PromptTemplateCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """创建提示词模板"""
    template = PromptTemplate(
        user_id=user_id,
        character_id=request.character_id,
        name=request.name,
        description=request.description,
        content=request.content,
        template_type=request.template_type,
        priority=request.priority,
        tags=request.tags
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return {
        "id": template.id,
        "user_id": template.user_id,
        "character_id": template.character_id,
        "name": template.name,
        "description": template.description,
        "content": template.content,
        "template_type": template.template_type,
        "is_enabled": template.is_enabled,
        "is_active": template.is_active,
        "priority": template.priority,
        "tags": template.tags,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None
    }


@router.put("/{template_id}", response_model=PromptTemplateResponse)
def update_prompt_template(
    template_id: int,
    request: PromptTemplateUpdate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """更新提示词模板"""
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == template_id,
        PromptTemplate.user_id == user_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="提示词模板不存在")
    
    update_data = request.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)
    
    db.commit()
    db.refresh(template)
    
    return {
        "id": template.id,
        "user_id": template.user_id,
        "character_id": template.character_id,
        "name": template.name,
        "description": template.description,
        "content": template.content,
        "template_type": template.template_type,
        "is_enabled": template.is_enabled,
        "is_active": template.is_active,
        "priority": template.priority,
        "tags": template.tags,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None
    }


@router.delete("/{template_id}")
def delete_prompt_template(
    template_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """删除提示词模板"""
    template = db.query(PromptTemplate).filter(
        PromptTemplate.id == template_id,
        PromptTemplate.user_id == user_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="提示词模板不存在")
    
    db.delete(template)
    db.commit()
    
    return {"message": "提示词模板已删除"}


@router.get("/active/{character_id}", response_model=List[PromptTemplateResponse])
def get_active_prompts(
    character_id: str,
    user_id: int,
    db: Session = Depends(get_db)
):
    """获取角色激活的提示词模板（包括全局和角色专属）"""
    templates = db.query(PromptTemplate).filter(
        PromptTemplate.user_id == user_id,
        PromptTemplate.is_enabled == True,
        PromptTemplate.is_active == True,
        (PromptTemplate.character_id == character_id) | (PromptTemplate.character_id == None)
    ).order_by(PromptTemplate.priority.desc()).all()
    
    return templates
