from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.services.memory_event_service import memory_event_service
from app.services.llm_service import llm_service
from datetime import datetime
import json
import re

# 🔧 增强版智能JSON提取和修复工具函数
def extract_json_from_response(response_text):
    """
    从AI响应中智能提取JSON内容（增强版）
    支持多种格式：纯JSON、markdown代码块、带说明文字的混合格式、编号列表等
    """
    if not response_text:
        return None

    text = response_text.strip()
    print(f"[JSON提取] 原始文本长度: {len(text)}")
    print(f"[JSON提取] 前100字符: {repr(text[:100])}")

    # 策略0: 完全空检查
    if not text or len(text) < 2:
        print("[JSON提取] ⚠️ 文本太短或为空")
        return None

    # 策略1: 查找markdown代码块中的JSON（最常见）
    json_pattern = r'```(?:json)?\s*\n?(.*?)```'
    matches = re.findall(json_pattern, text, re.DOTALL)

    for match in matches:
        match = match.strip()
        if (match.startswith('[') and match.endswith(']')) or \
           (match.startswith('{') and match.endswith('}')):
            print(f"[JSON提取] ✅ 策略1成功: 从markdown代码块提取, 长度={len(match)}")
            return match

    # 策略2: 查找第一个 [ 或 { 并提取到匹配的 ] 或 }
    # 这能处理 "这是结果：[...]" 这样的格式
    first_bracket_pos = -1
    bracket_char = None

    for i, char in enumerate(text):
        if char == '[':
            first_bracket_pos = i
            bracket_char = '['
            break
        elif char == '{':
            first_bracket_pos = i
            bracket_char = '{'
            break

    if first_bracket_pos >= 0:
        # 找到开始位置，现在找到结束位置
        start_pos = first_bracket_pos
        search_text = text[start_pos:]

        if bracket_char == '[':
            # 找匹配的 ]
            end_pos = search_text.rfind(']')
            if end_pos > 0:
                extracted = search_text[:end_pos+1]
                print(f"[JSON提取] ✅ 策略2成功: 提取方括号内容, 位置={start_pos}-{start_pos+end_pos}, 长度={len(extracted)}")
                return extracted
        else:  # {
            # 找匹配的 }
            end_pos = search_text.rfind('}')
            if end_pos > 0:
                extracted = f"[{search_text[:end_pos+1]}]"  # 包装成数组
                print(f"[JSON提取] ✅ 策略2成功: 提取花括号内容并包装为数组, 长度={len(extracted)}")
                return extracted

    # 策略3: 使用正则表达式查找JSON数组或对象
    array_pattern = r'\[[\s\S]*?\]'
    obj_pattern = r'\{[\s\S]*?\}'

    # 优先查找数组
    array_match = re.search(array_pattern, text)
    if array_match:
        result = array_match.group(0)
        print(f"[JSON提取] ✅ 策略3a成功: 正则查找数组, 长度={len(result)}")
        return result

    # 其次查找对象（单个实体）
    obj_match = re.search(obj_pattern, text)
    if obj_match:
        result = f"[{obj_match.group(0)}]"
        print(f"[JSON提取] ✅ 策略3b成功: 正则查找对象并包装, 长度={len(result)}")
        return result

    # 策略4: 如果整个文本看起来像JSON，直接返回
    text_clean = text.strip()
    if (text_clean.startswith('[') and text_clean.endswith(']')) or \
       (text_clean.startswith('{') and text_clean.endswith('}')):
        print(f"[JSON提取] ✅ 策略4成功: 整个文本就是JSON, 长度={len(text_clean)}")
        return text_clean

    # 策略5: 尝试修复常见的非JSON格式
    # 例如："1. xxx\n2. xxx" 这种列表格式
    if re.search(r'^\s*\d+\.', text, re.MULTILINE):
        print("[JSON提取] ⚠️ 检测到可能是编号列表格式，无法自动转换为JSON")
        return None

    print(f"[JSON提取] ❌ 所有策略都失败, 无法提取有效JSON")
    print(f"[JSON提取] 文本前200字符: {repr(text[:200])}")
    return None


def smart_fix_json(json_str):
    """
    智能修复损坏的JSON字符串（增强版）
    处理常见的AI生成错误：单引号、未加引号的键、尾随逗号、未闭合字符串等
    """
    if not json_str:
        print("[JSON修复] ❌ 输入为空")
        return None

    fixed = json_str
    original_len = len(fixed)
    print(f"[JSON修复] 开始修复, 原始长度: {original_len}")

    try:
        # 测试是否能直接解析
        json.loads(fixed)
        print("[JSON修复] ✅ 无需修复, JSON格式正确")
        return fixed
    except json.JSONDecodeError as e:
        print(f"[JSON修复] ⚠️ 检测到错误: {e}")

    # 修复步骤0: 移除BOM和其他不可见字符
    fixed = fixed.replace('\ufeff', '').replace('\ufffe', '')
    fixed = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', fixed)

    # 修复步骤1: 替换单引号为双引号（保留转义的单引号）
    if "'" in fixed:
        fixed = re.sub(r"(?<!\\)'", '"', fixed)
        print("[JSON修复] 步骤1: 单引号→双引号")

    # 修复步骤2: 为未加引号的键名添加引号
    if re.search(r'(?<=[\[{,])\s*[a-zA-Z_]\w*\s*:', fixed):
        fixed = re.sub(r'(?<=[\[{,])\s*([a-zA-Z_]\w*)\s*:', r' "\1":', fixed)
        print("[JSON修复] 步骤2: 未加引号的键名添加引号")

    # 修复步骤3: 移除尾随逗号
    if ',\s*([}\]])' in fixed or re.search(r',\s*[}\]]', fixed):
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
        print("[JSON修复] 步骤3: 移除尾随逗号")

    # 修复步骤4: 修复未闭合的字符串
    lines = fixed.split('\n')
    fixed_lines = []
    in_string = False

    for line in lines:
        quote_count = len(re.findall(r'(?<!\\)"', line))

        if in_string:
            if quote_count > 0:
                in_string = False

        if not in_string and quote_count % 2 == 1:
            line = line.rstrip()
            if not line.endswith('"') and not line.endswith(','):
                line += '"'
            elif line.endswith(','):
                line = line[:-1] + '",'
            in_string = True

        fixed_lines.append(line)

    fixed = '\n'.join(fixed_lines)

    # 修复步骤5: 处理注释（如果有的话）
    if '//' in fixed or '/*' in fixed:
        fixed = re.sub(r'//.*$', '', fixed, flags=re.MULTILINE)
        fixed = re.sub(r'/\*.*?\*/', '', fixed, flags=re.DOTALL)
        print("[JSON修复] 步骤5: 移除注释代码")

    # 修复步骤6: 修复未闭合的括号
    open_brackets = fixed.count('[') + fixed.count('{')
    close_brackets = fixed.count(']') + fixed.count('}')
    if open_brackets > close_brackets:
        # 缺少闭合括号
        missing_close = open_brackets - close_brackets
        for _ in range(missing_close):
            if fixed.count('[') > fixed.count(']'):
                fixed += ']'
            else:
                fixed += '}'
        print(f"[JSON修复] 步骤6: 补全 {missing_close} 个闭合括号")
    elif close_brackets > open_brackets:
        # 多余的闭合括号，截断到最后一个有效的位置
        print("[JSON修复] ⚠️ 检测到多余的闭合括号，尝试截断...")
        # 找到最后一个完整的对象或数组
        last_valid_pos = max(fixed.rfind(']'), fixed.rfind('}'))
        if last_valid_pos > 0:
            fixed = fixed[:last_valid_pos+1]
            print(f"[JSON修复] 步骤6: 截断到位置 {last_valid_pos}")

    # 验证修复结果
    try:
        json.loads(fixed)
        print(f"[JSON修复] ✅ 修复成功! 最终长度: {len(fixed)} (原始: {original_len})")
        return fixed
    except json.JSONDecodeError as e:
        print(f"[JSON修复] ❌ 标准修复失败: {e}")
        print(f"[JSON修复] 当前内容前300字符: {repr(fixed[:300])}")

        # 最终尝试：使用更激进的方法
        try:
            import ast
            result = ast.literal_eval(fixed)
            final_json = json.dumps(result, ensure_ascii=False)
            print("[JSON修复] ✅ 使用ast.literal_eval成功!")
            return final_json
        except Exception as e2:
            print(f"[JSON修复] ❌ 所有修复方法都失败: {e2}")
            return None


def attempt_fix_truncated_json(text):
    """
    尝试修复被截断的JSON（用于最后的回退方案）
    处理AI响应被token限制截断的情况
    """
    if not text:
        print("[截断修复] ❌ 输入为空")
        return None

    print(f"[截断修复] 开始尝试修复截断的文本, 长度: {len(text)}")

    # 策略1: 查找最后一个完整的对象或数组
    # 找到最后一个 } 或 ]
    last_brace = text.rfind('}')
    last_bracket = text.rfind(']')

    # 使用更靠后的那个作为截止点
    end_pos = max(last_brace, last_bracket)

    if end_pos > 0:
        # 截断到这个位置
        truncated = text[:end_pos+1]

        # 尝试补全缺失的括号
        open_count = truncated.count('[') + truncated.count('{')
        close_count = truncated.count(']') + truncated.count('}')

        if open_count > close_count:
            # 需要补全闭合括号
            missing = open_count - close_count
            for _ in range(missing):
                if truncated.count('[') > truncated.count(']'):
                    truncated += ']'
                else:
                    truncated += '}'
            print(f"[截断修复] ✅ 成功: 截断并补全了 {missing} 个括号")
            return truncated

    print("[截断修复] ❌ 无法找到有效的截断点")
    return None


# ============================================
# 🆕 新方案：多策略降级系统的辅助函数
# ============================================

def parse_simple_table_format(text):
    """
    解析简单的表格格式：名称|类型|父节点|关系|重要度
    这是第2级降级策略使用的格式
    """
    if not text:
        return None

    print(f"[表格解析] 开始解析简单表格格式, 长度: {len(text)}")

    entities = []
    lines = text.strip().split('\n')

    for line in lines:
        line = line.strip()

        # 跳过空行和注释
        if not line or line.startswith('#') or line.startswith('示例'):
            continue

        # 尝试用 | 分割
        parts = [p.strip() for p in line.split('|')]

        # 至少需要名称和类型（2个字段）
        if len(parts) >= 2 and parts[0]:
            title = parts[0]
            entity_type = parts[1] if len(parts) > 1 else "discovery"

            # 验证实体类型
            valid_types = ["location", "person", "item", "discovery", "main"]
            if entity_type not in valid_types:
                # 尝试映射中文
                type_map = {
                    "地点": "location", "人物": "person", "物品": "item",
                    "发现": "discovery", "主线": "main"
                }
                entity_type = type_map.get(entity_type, "discovery")

            parent_title = parts[2] if len(parts) > 2 and parts[2] else None
            hierarchy_relation = parts[3] if len(parts) > 3 and parts[3] else None

            # 转换空字符串为None
            if parent_title == "":
                parent_title = None
            if hierarchy_relation == "":
                hierarchy_relation = None

            try:
                importance = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 5
            except:
                importance = 5

            entity = {
                "title": title,
                "entity_type": entity_type,
                "description": f"{title} - 从对话中提取的{entity_type}类型实体",
                "parent_title": parent_title,
                "hierarchy_relation": hierarchy_relation,
                "relations": [],
                "importance": importance,
                "tags": [entity_type]
            }

            entities.append(entity)
            print(f"[表格解析] ✅ 解析实体: {title} ({entity_type})")

    if len(entities) > 0:
        print(f"[表格解析] ✅ 成功! 共解析 {len(entities)} 个实体")
        return entities
    else:
        print("[表格解析] ⚠️ 未找到有效实体")
        return None


def extract_entities_from_text(ai_response, chat_text):
    """
    第3级后备策略：从任意文本中提取实体信息
    使用正则表达式和关键词匹配，保证100%不会失败
    """
    print(f"[文本提取] 开始从文本中提取实体...")
    print(f"[文本提取] AI响应长度: {len(ai_response) if ai_response else 0}")
    print(f"[文本提取] 聊天文本长度: {len(chat_text) if chat_text else 0}")

    entities = []

    # 合并所有文本进行分析
    all_text = f"{ai_response}\n\n{chat_text}" if ai_response else chat_text

    if not all_text or len(all_text) < 10:
        print("[文本提取] ⚠️ 文本太短，无法提取")
        return []

    # 定义关键词模式（用于识别实体类型）
    location_keywords = ['村庄', '城镇', '城市', '城堡', '铁匠铺', '商店', '酒馆', '客栈',
                         '森林', '山洞', '河流', '山脉', '宫殿', '神殿', '市场', '港口']
    person_keywords = ['老王', '村长', '商人', '铁匠', '店主', '守卫', '公主', '国王',
                       '巫师', '骑士', '盗贼', '精灵', '矮人', 'NPC', '老板', '主人']
    item_keywords = ['剑', '刀', '弓', '盾', '甲', '药水', '宝石', '钥匙', '地图',
                     '金币', '宝物', '武器', '装备', '道具', '卷轴']

    found_entities = set()  # 用于去重

    # 提取地点实体
    for keyword in location_keywords:
        if keyword in all_text and keyword not in found_entities:
            entities.append({
                "title": keyword,
                "entity_type": "location",
                "description": f"在对话中提到的地点：{keyword}",
                "parent_title": None,
                "hierarchy_relation": None,
                "relations": [],
                "importance": 6,
                "tags": ["location"]
            })
            found_entities.add(keyword)

    # 提取人物实体
    for keyword in person_keywords:
        if keyword in all_text and keyword not in found_entities:
            entities.append({
                "title": keyword,
                "entity_type": "person",
                "description": f"在对话中提到的人物：{keyword}",
                "parent_title": None,
                "hierarchy_relation": None,
                "relations": [],
                "importance": 7,
                "tags": ["person"]
            })
            found_entities.add(keyword)

    # 提取物品实体
    for keyword in item_keywords:
        if keyword in all_text and keyword not in found_entities:
            entities.append({
                "title": keyword,
                "entity_type": "item",
                "description": f"在对话中提到的物品：{keyword}",
                "parent_title": None,
                "hierarchy_relation": None,
                "relations": [],
                "importance": 5,
                "tags": ["item"]
            })
            found_entities.add(keyword)

    # 使用正则提取可能的专有名词（大写开头的词或带引号的词）
    import re

    # 匹配引号中的内容
    quoted_pattern = r'[""「」『』《》](.+?)[""「」『』《》]'
    quoted_matches = re.findall(quoted_pattern, all_text)
    for match in quoted_matches:
        if len(match) >= 2 and len(match) <= 20 and match not in found_entities:
            entities.append({
                "title": match,
                "entity_type": "discovery",
                "description": f"从对话中发现的重要信息：{match}",
                "parent_title": None,
                "hierarchy_relation": None,
                "relations": [],
                "importance": 5,
                "tags": ["discovery"]
            })
            found_entities.add(match)

    # 限制最大数量，避免太多噪音
    if len(entities) > 15:
        entities = entities[:15]

    print(f"[文本提取] ✅ 完成! 共提取 {len(entities)} 个实体")

    if len(entities) == 0:
        print("[文本提取] ⚠️ 未找到任何实体，返回空列表")

    return entities


router = APIRouter(prefix="/api/memory-events", tags=["记忆事件"])


def build_tree_preview(hierarchy_tree):
    """
    将层级数据转换为树形文本预览
    输入：[{"title": "铁匠铺", "parent_title": "村庄", "hierarchy_relation": "属于"}, ...]
    输出：
    神圣村庄 (location)
     └─ [属于] 铁匠铺 (location)
            ├─ [工作于] 铁匠老王 (person)
    """
    if not hierarchy_tree:
        return ""

    # 构建父子映射
    children_map = {}
    node_info = {}

    for node in hierarchy_tree:
        title = node["title"]
        parent = node.get("parent_title")
        node_info[title] = node

        if parent:
            if parent not in children_map:
                children_map[parent] = []
            children_map[parent].append(title)

    # 找到根节点（没有父节点的）
    root_nodes = [n["title"] for n in hierarchy_tree if not n.get("parent_title")]

    def build_node_text(title, level=0):
        """递归构建节点文本"""
        node = node_info.get(title, {})
        entity_type = node.get("entity_type", "unknown")
        hierarchy_rel = node.get("hierarchy_relation", "")

        indent = "   " * level + ("└─ " if level > 0 else "")
        relation_prefix = f"[{hierarchy_rel}] " if hierarchy_rel and level > 0 else ""

        text = f"{indent}{relation_prefix}{title} ({entity_type})"

        # 递归处理子节点
        children = children_map.get(title, [])
        for i, child_title in enumerate(children):
            is_last = (i == len(children) - 1)
            child_text = build_node_text(child_title, level + 1)
            connector = "├─" if not is_last else "└─"
            child_text = child_text.replace("   ", f"{' ' * 3 * (level + 1)}{connector}", 1)
            text += "\n" + child_text

        return text

    # 构建完整树形文本
    lines = []
    for root in root_nodes:
        lines.append(build_node_text(root))

    return "\n".join(lines)


class EventCreateRequest(BaseModel):
    character_id: str
    title: str
    description: str
    event_type: str = "main"
    parent_event_id: Optional[int] = None
    chat_context: Optional[str] = None
    importance: int = 5
    tags: Optional[List[str]] = None
    user_id: int = 1


class EventUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    importance: Optional[int] = None
    tags: Optional[List[str]] = None


class SmartParseRequest(BaseModel):
    character_id: str
    user_id: int = 1
    mode: str = "auto"
    message_count: int = 20


class EventResponse(BaseModel):
    success: bool
    message: str
    event: Optional[dict] = None
    events: Optional[list] = None
    event_tree: Optional[list] = None
    graph_data: Optional[dict] = None  # 新增：返回图谱数据用于实时更新


@router.post("/create", response_model=EventResponse)
async def create_event(request: EventCreateRequest, db: Session = Depends(get_db)):
    """创建新的事件节点"""
    try:
        event = memory_event_service.create_event(
            db=db,
            user_id=request.user_id,
            character_id=request.character_id,
            title=request.title,
            description=request.description,
            event_type=request.event_type,
            parent_event_id=request.parent_event_id,
            chat_context=request.chat_context,
            importance=request.importance,
            tags=request.tags
        )
        
        return {
            "success": True,
            "message": "事件创建成功",
            "event": {
                "id": event.id,
                "title": event.title,
                "event_type": event.event_type,
                "status": event.status,
                "level": event.level
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建事件失败: {str(e)}")


@router.get("/list/{character_id}", response_model=EventResponse)
async def get_events(
    character_id: str,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """获取角色的事件列表"""
    try:
        events = memory_event_service.get_events_by_character(
            db=db,
            user_id=user_id,
            character_id=character_id,
            event_type=event_type,
            status=status
        )
        
        events_data = [
            {
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "event_type": event.event_type,
                "status": event.status,
                "importance": event.importance,
                "tags": event.tags or [],
                "level": event.level,
                "parent_event_id": event.parent_event_id,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None
            }
            for event in events
        ]
        
        return {
            "success": True,
            "message": "获取事件列表成功",
            "events": events_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取事件列表失败: {str(e)}")


@router.get("/tree/{character_id}", response_model=EventResponse)
async def get_event_tree(
    character_id: str,
    event_type: Optional[str] = None,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """获取事件树结构"""
    try:
        event_tree = memory_event_service.get_event_tree(
            db=db,
            user_id=user_id,
            character_id=character_id,
            event_type=event_type
        )
        
        return {
            "success": True,
            "message": "获取事件树成功",
            "event_tree": event_tree
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取事件树失败: {str(e)}")


@router.post("/clear/{character_id}", response_model=EventResponse)
async def clear_all_events(
    character_id: str,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """清空指定角色的所有事件"""
    try:
        success = memory_event_service.clear_all_events(db, user_id, character_id)
        
        if not success:
            return {
                "success": False,
                "message": "清空事件失败"
            }
        
        return {
            "success": True,
            "message": "已清空所有足迹"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空事件失败: {str(e)}")


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    character_id: str,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """获取单个事件详情"""
    try:
        event = memory_event_service.get_event(db, event_id, user_id, character_id)
        
        if not event:
            return {
                "success": False,
                "message": "事件不存在"
            }
        
        return {
            "success": True,
            "message": "获取事件成功",
            "event": {
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "event_type": event.event_type,
                "status": event.status,
                "importance": event.importance,
                "tags": event.tags or [],
                "level": event.level,
                "parent_event_id": event.parent_event_id,
                "chat_context": event.chat_context,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取事件失败: {str(e)}")


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    request: EventUpdateRequest,
    character_id: str,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """更新事件信息"""
    try:
        event = memory_event_service.update_event(
            db=db,
            event_id=event_id,
            user_id=user_id,
            character_id=character_id,
            title=request.title,
            description=request.description,
            status=request.status,
            importance=request.importance,
            tags=request.tags
        )
        
        if not event:
            return {
                "success": False,
                "message": "事件不存在"
            }
        
        return {
            "success": True,
            "message": "事件更新成功",
            "event": {
                "id": event.id,
                "title": event.title,
                "status": event.status,
                "importance": event.importance
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新事件失败: {str(e)}")


@router.delete("/{event_id}", response_model=EventResponse)
async def delete_event(
    event_id: int,
    character_id: str,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """删除事件及其所有子事件"""
    try:
        success = memory_event_service.delete_event(db, event_id, user_id, character_id)
        
        if not success:
            return {
                "success": False,
                "message": "事件不存在"
            }
        
        return {
            "success": True,
            "message": "事件删除成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除事件失败: {str(e)}")


@router.get("/{event_id}/children", response_model=EventResponse)
async def get_child_events(
    event_id: int,
    character_id: str,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """获取子事件列表"""
    try:
        child_events = memory_event_service.get_child_events(
            db=db,
            parent_event_id=event_id,
            user_id=user_id,
            character_id=character_id
        )
        
        events_data = [
            {
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "event_type": event.event_type,
                "status": event.status,
                "importance": event.importance,
                "tags": event.tags or [],
                "level": event.level,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None
            }
            for event in child_events
        ]
        
        return {
            "success": True,
            "message": "获取子事件成功",
            "events": events_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取子事件失败: {str(e)}")


@router.post("/smart-parse", response_model=EventResponse)
async def smart_parse_footprints(request: SmartParseRequest, db: Session = Depends(get_db)):
    try:
        from app.models.database import ChatMessage

        limit = request.message_count if request.mode == "auto" else (200 if request.mode == "full" else 50)
        chat_messages = db.query(ChatMessage).filter(
            ChatMessage.user_id == request.user_id,
            ChatMessage.character_id == request.character_id,
            ChatMessage.role.in_(["user", "assistant"])
        ).order_by(ChatMessage.created_at.desc()).limit(limit).all()

        if not chat_messages:
            return {
                "success": False,
                "message": "暂无聊天记录，请先与角色对话后再使用智能提取"
            }

        message_count = len(chat_messages)

        if message_count < 3:
            return {
                "success": False,
                "message": f"聊天记录不足（仅 {message_count} 条），建议至少进行3轮对话后再提取"
            }

        chat_text = "\n".join([
            f"{'用户' if msg.role == 'user' else '角色'}: {msg.content}"
            for msg in reversed(chat_messages)
        ])

        if message_count <= 8:
            max_tokens = 1500
            detail_hint = "简洁：description 20-60字，最多2个关系"
        elif message_count <= 20:
            max_tokens = 2500
            detail_hint = "标准：description 30-100字，2-3个关系"
        else:
            max_tokens = 4000
            detail_hint = "详细：description 50-150字，完整关系链"

        mode_hint = {
            "auto": f"增量解析最近{request.message_count}条消息，重点识别新实体",
            "full": "全量深度解析，重建完整知识图谱",
            "manual": "分析指定范围的聊天内容"
        }

        prompt = f"""从角色扮演对话中提取实体并构建层级知识图谱。

{mode_hint.get(request.mode, mode_hint['auto'])}

实体类型：location(地点) person(人物) item(物品) discovery(发现) main(主线事件)
关系类型：属于 工作于 打造者 获得于 位于 关联

层级规则：大地点→小地点→人物→物品，主事件→子事件

严格输出JSON数组，不要其他文字：
[
  {{"title":"名称","entity_type":"类型","description":"描述","parent_title":"父节点或null","hierarchy_relation":"关系或null","importance":1到10,"tags":["标签"]}}
]

要求：{detail_hint}。同名实体只出现一次。重要度9-10关键/7-8重要/5-6普通/1-4次要。

对话：
{chat_text}

JSON数组："""

        ai_response = await llm_service.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=max_tokens
        )

        content = (ai_response or "").strip()
        if not content:
            return {
                "success": False,
                "message": "AI返回了空内容，请稍后重试"
            }

        footprints_data = None

        json_str = extract_json_from_response(content)
        if json_str:
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, list) and len(parsed) > 0:
                    footprints_data = parsed
            except json.JSONDecodeError:
                fixed = smart_fix_json(json_str)
                if fixed:
                    try:
                        parsed = json.loads(fixed)
                        if isinstance(parsed, list) and len(parsed) > 0:
                            footprints_data = parsed
                    except Exception:
                        pass

        if not footprints_data:
            retry_prompt = f"""从以下对话中提取实体，严格输出JSON数组。

格式：[{{"title":"名称","entity_type":"location|person|item|discovery|main","description":"描述","parent_title":null,"hierarchy_relation":null,"importance":5,"tags":["标签"]}}]

对话：
{chat_text}

JSON："""
            retry_response = await llm_service.chat_completion(
                messages=[{"role": "user", "content": retry_prompt}],
                temperature=0.2,
                max_tokens=max_tokens
            )
            retry_content = (retry_response or "").strip()
            if retry_content:
                retry_json = extract_json_from_response(retry_content)
                if retry_json:
                    try:
                        parsed = json.loads(retry_json)
                        if isinstance(parsed, list) and len(parsed) > 0:
                            footprints_data = parsed
                    except json.JSONDecodeError:
                        fixed = smart_fix_json(retry_json)
                        if fixed:
                            try:
                                parsed = json.loads(fixed)
                                if isinstance(parsed, list) and len(parsed) > 0:
                                    footprints_data = parsed
                            except Exception:
                                pass

        if not footprints_data:
            return {
                "success": False,
                "message": "AI解析失败，请稍后重试或增加更多对话内容"
            }

        existing_events = memory_event_service.get_events_by_character(
            db=db, user_id=request.user_id, character_id=request.character_id
        )
        title_to_event = {ev.title: ev for ev in existing_events}

        created_count = 0
        updated_count = 0
        relations_count = 0

        sorted_data = sorted(footprints_data, key=lambda x: (x.get("parent_title") is not None, x.get("importance", 5)), reverse=False)

        for fp in sorted_data:
            entity_type = fp.get("entity_type", "discovery")
            if entity_type not in ("location", "person", "item", "discovery", "main"):
                entity_type = "discovery"

            parent_event_id = None
            parent_title = fp.get("parent_title")
            if parent_title and parent_title in title_to_event:
                parent_event_id = title_to_event[parent_title].id

            base_tags = [entity_type]
            custom_tags = [t for t in (fp.get("tags") or []) if t != entity_type]
            tags = base_tags + custom_tags

            description = fp.get("description", "")
            hierarchy_rel = fp.get("hierarchy_relation")
            if hierarchy_rel and parent_title:
                description = f"[{hierarchy_rel} {parent_title}] {description}"

            relations_info = fp.get("relations", [])
            if relations_info:
                rel_lines = []
                for r in relations_info:
                    r_type = r.get("type", r.get("relation_type", "关联"))
                    r_target = r.get("target", r.get("target_title", ""))
                    r_desc = r.get("desc", r.get("relation_desc", ""))
                    if r_target:
                        rel_lines.append(f"- [{r_type}] → {r_target}" + (f": {r_desc}" if r_desc else ""))
                if rel_lines:
                    description = f"{description}\n\n【关联】\n" + "\n".join(rel_lines)
                    relations_count += len(rel_lines)

            if fp["title"] in title_to_event:
                memory_event_service.update_event(
                    db=db,
                    event_id=title_to_event[fp["title"]].id,
                    user_id=request.user_id,
                    character_id=request.character_id,
                    description=description,
                    importance=fp.get("importance", 5),
                    tags=tags
                )
                updated_count += 1
            else:
                event = memory_event_service.create_event(
                    db=db,
                    user_id=request.user_id,
                    character_id=request.character_id,
                    title=fp["title"],
                    description=description,
                    event_type=entity_type,
                    parent_event_id=parent_event_id,
                    importance=fp.get("importance", 5),
                    tags=tags
                )
                title_to_event[fp["title"]] = event
                created_count += 1

        mode_names = {"auto": "增量解析", "full": "全量解析", "manual": "手动解析"}
        return {
            "success": True,
            "message": f"提取完成！新建 {created_count} 个节点，更新 {updated_count} 个，建立 {relations_count} 条关系",
            "events": {
                "created": created_count,
                "updated": updated_count,
                "relations": relations_count
            },
            "parse_info": {
                "mode": request.mode,
                "messages_analyzed": message_count,
                "entities_processed": len(footprints_data)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "auth" in error_msg.lower():
            detail = "AI服务连接失败：API密钥无效或已过期，请检查设置"
        elif "timeout" in error_msg.lower():
            detail = "AI响应超时，建议使用增量解析模式"
        else:
            detail = f"智能提取失败: {error_msg}"
        raise HTTPException(status_code=500, detail=detail)


@router.get("/graph/{character_id}", response_model=EventResponse)
async def get_footprint_graph(
    character_id: str,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """获取足迹图谱数据 - 电路图风格知识网络"""
    try:
        events = memory_event_service.get_events_by_character(
            db=db,
            user_id=user_id,
            character_id=character_id
        )
        
        if not events:
            return {
                "success": True,
                "message": "暂无足迹数据",
                "nodes": [],
                "links": [],
                "layers": {},
                "statistics": {}
            }
        
        LAYER_ORDER = ['location', 'person', 'item', 'discovery', 'main', 'side']
        LAYER_LABELS = {
            'location': '地点',
            'person': '人物',
            'item': '物品',
            'discovery': '发现',
            'main': '主线事件',
            'side': '支线事件'
        }
        
        type_config = {
            'location': {'color': '#fbbf24', 'icon': '📍', 'baseSize': 18, 'label': '地点'},
            'person': {'color': '#60a5fa', 'icon': '👤', 'baseSize': 15, 'label': '人物'},
            'item': {'color': '#34d399', 'icon': '📦', 'baseSize': 13, 'label': '物品'},
            'discovery': {'color': '#a78bfa', 'icon': '💡', 'baseSize': 13, 'label': '发现'},
            'main': {'color': '#f87171', 'icon': '🎯', 'baseSize': 16, 'label': '主线'},
            'side': {'color': '#94a3b8', 'icon': '📌', 'baseSize': 11, 'label': '支线'}
        }
        
        relation_config = {
            'crafted_by': {'label': '打造者', 'color': '#34d399', 'dashed': False},
            'located_at': {'label': '位于', 'color': '#fbbf24', 'dashed': False},
            'belongs_to': {'label': '属于', 'color': '#fbbf24', 'dashed': True},
            'obtained_at': {'label': '获得于', 'color': '#34d399', 'dashed': False},
            'works_at': {'label': '工作于', 'color': '#60a5fa', 'dashed': False},
            'related_to': {'label': '关联', 'color': '#475569', 'dashed': True},
            'parent_child': {'label': '包含', 'color': '#64748b', 'dashed': False},
            'hierarchy': {'label': '层级', 'color': '#64748b', 'dashed': True}
        }
        
        nodes = []
        links = []
        title_to_node = {}
        id_to_node = {}
        
        def determine_node_type(event):
            tags = event.tags or []
            entity_types = ['location', 'person', 'item', 'discovery']
            if event.event_type in entity_types:
                return event.event_type
            for et in entity_types:
                if et in tags:
                    return et
            if event.event_type == 'main':
                return 'main'
            return 'side'
        
        def create_node(event, node_type):
            if event.id in id_to_node:
                return id_to_node[event.id]['id']
            
            config = type_config.get(node_type, type_config['side'])
            size_multiplier = 1 + (event.importance / 10) * 0.8
            node_size = config['baseSize'] * size_multiplier
            
            node_id = f"node_{event.id}"
            node_data = {
                "id": node_id,
                "eventId": event.id,
                "title": event.title,
                "type": node_type,
                "layer": LAYER_ORDER.index(node_type) if node_type in LAYER_ORDER else 5,
                "size": round(node_size, 1),
                "color": config['color'],
                "icon": config['icon'],
                "typeLabel": config['label'],
                "importance": event.importance,
                "description": (event.description[:150] + '...') if event.description and len(event.description) > 150 else (event.description or ''),
                "tags": event.tags or [],
                "parentId": event.parent_event_id,
                "createdAt": event.created_at.isoformat() if event.created_at else None,
                "occurredAt": event.occurred_at.isoformat() if event.occurred_at else None
            }
            
            nodes.append(node_data)
            title_to_node[event.title] = node_data
            id_to_node[event.id] = node_data
            return node_id
        
        def add_link(source_id, target_id, relation_type):
            if source_id == target_id:
                return
            exists = any(
                l["source"] == source_id and l["target"] == target_id and l["relationType"] == relation_type
                for l in links
            )
            if not exists:
                rc = relation_config.get(relation_type, relation_config['related_to'])
                links.append({
                    "source": source_id,
                    "target": target_id,
                    "relationType": relation_type,
                    "relationLabel": rc['label'],
                    "color": rc['color'],
                    "value": 1.5,
                    "dashed": rc.get('dashed', False)
                })
        
        for event in events:
            node_type = determine_node_type(event)
            current_node_id = create_node(event, node_type)
            
            if event.parent_event_id:
                parent_event = next((e for e in events if e.id == event.parent_event_id), None)
                if parent_event:
                    parent_type = determine_node_type(parent_event)
                    parent_node_id = create_node(parent_event, parent_type)
                    
                    if node_type == 'location' and parent_type == 'location':
                        add_link(current_node_id, parent_node_id, 'belongs_to')
                    elif node_type == 'person' and parent_type == 'location':
                        add_link(current_node_id, parent_node_id, 'works_at')
                    elif node_type == 'item' and parent_type == 'person':
                        add_link(current_node_id, parent_node_id, 'crafted_by')
                    elif node_type == 'item' and parent_type == 'location':
                        add_link(current_node_id, parent_node_id, 'obtained_at')
                    else:
                        add_link(parent_node_id, current_node_id, 'parent_child')
            
            if event.description:
                desc = event.description
                for other_event in events:
                    if other_event.id == event.id:
                        continue
                    if other_event.title in desc and other_event.title not in title_to_node.get(event.title, {}).get('_linked_titles', set()):
                        other_type = determine_node_type(other_event)
                        other_node_id = create_node(other_event, other_type)
                        
                        if node_type == 'location' and other_type == 'location':
                            add_link(current_node_id, other_node_id, 'belongs_to')
                        elif node_type == 'person' and other_type == 'location':
                            add_link(current_node_id, other_node_id, 'works_at')
                        elif node_type == 'item' and other_type == 'person':
                            add_link(current_node_id, other_node_id, 'crafted_by')
                        elif node_type == 'item' and other_type == 'location':
                            add_link(current_node_id, other_node_id, 'obtained_at')
                        else:
                            add_link(current_node_id, other_node_id, 'related_to')
        
        layers = {}
        for lt in LAYER_ORDER:
            layer_nodes = [n for n in nodes if n['type'] == lt]
            if layer_nodes:
                layers[lt] = {
                    "label": LAYER_LABELS[lt],
                    "color": type_config[lt]['color'],
                    "icon": type_config[lt]['icon'],
                    "count": len(layer_nodes),
                    "nodeIds": [n['id'] for n in layer_nodes]
                }
        
        statistics = {
            "totalNodes": len(nodes),
            "totalLinks": len(links),
            "nodeTypes": {},
            "relationTypes": {},
            "avgImportance": round(sum(n['importance'] for n in nodes) / len(nodes), 1) if nodes else 0
        }
        for node in nodes:
            statistics["nodeTypes"][node['type']] = statistics["nodeTypes"].get(node['type'], 0) + 1
        for link in links:
            statistics["relationTypes"][link["relationType"]] = statistics["relationTypes"].get(link["relationType"], 0) + 1
        
        return {
            "success": True,
            "message": "获取足迹图谱成功",
            "nodes": nodes,
            "links": links,
            "layers": layers,
            "statistics": statistics,
            "legend": {
                "types": {k: {"color": v["color"], "icon": v["icon"], "label": v["label"]} 
                         for k, v in type_config.items()},
                "relations": {k: {"label": v["label"], "color": v["color"], "dashed": v.get("dashed", False)} 
                             for k, v in relation_config.items()}
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取足迹图谱失败: {str(e)}")
