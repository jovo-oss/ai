"""
智能上下文管理服务
负责动态构建AI对话的系统提示词，智能匹配世界书、记忆和足迹信息
"""
import re
import jieba
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session


class ContextConfig:
    """上下文配置"""
    def __init__(
        self,
        max_tokens: int = 4000,  # 最大Token预算（增加）
        character_weight: float = 0.20,  # 角色预设占比
        chat_weight: float = 0.35,  # 聊天上下文占比
        memory_weight: float = 0.30,  # 记忆/足迹占比（增加）
        worldbook_weight: float = 0.15,  # 世界书占比
        max_worldbook_entries: int = 5,  # 最多世界书条目（增加）
        max_memory_entries: int = 10,  # 最多记忆条目（大幅增加）
        max_footprint_entries: int = 8,  # 最多足迹条目（增加）
        keyword_match_threshold: float = 0.2,  # 关键词匹配阈值（大幅降低，让记忆更容易被选中）
        enable_smart_context: bool = True,  # 启用智能上下文
        enable_chain_of_thought: bool = True,  # 启用思维链引导
        enable_consistency_check: bool = True,  # 启用一致性检查
    ):
        self.max_tokens = max_tokens
        self.character_weight = character_weight
        self.chat_weight = chat_weight
        self.memory_weight = memory_weight
        self.worldbook_weight = worldbook_weight
        self.max_worldbook_entries = max_worldbook_entries
        self.max_memory_entries = max_memory_entries
        self.max_footprint_entries = max_footprint_entries
        self.keyword_match_threshold = keyword_match_threshold
        self.enable_smart_context = enable_smart_context
        self.enable_chain_of_thought = enable_chain_of_thought
        self.enable_consistency_check = enable_consistency_check


class ContextManager:
    """智能上下文管理器"""
    
    def __init__(self, config: Optional[ContextConfig] = None):
        self.config = config or ContextConfig()
        # 预加载jieba分词模型（优化：避免首次分词延迟）
        self._preload_jieba()
        # 常用停用词
        self.stop_words = set([
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
            '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有',
            '看', '好', '自己', '这', '他', '她', '它', '们', '啊', '呢', '吧', '吗',
            '哦', '嗯', '哎', '呀', '什么', '怎么', '为什么', '哪里', '谁', '多少',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought', 'used',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'between', 'out',
            'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there',
            'when', 'where', 'why', 'how', 'all', 'both', 'each', 'few', 'more', 'most',
            'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 's', 't', 'just', 'don', 'now', 'and', 'but', 'or',
        ])
    
    def _preload_jieba(self):
        """预加载jieba分词模型（优化：避免首次分词延迟）"""
        try:
            jieba.lcut("预加载")
        except:
            pass
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """从文本中提取关键词"""
        # 使用jieba分词
        words = jieba.lcut(text)
        
        # 过滤停用词和单字符
        keywords = []
        for word in words:
            word = word.strip().lower()
            if (len(word) > 1 and 
                word not in self.stop_words and
                not word.isdigit() and
                not re.match(r'^[^\w\u4e00-\u9fa5]+$', word)):
                keywords.append(word)
        
        # 去重并限制数量
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
                if len(unique_keywords) >= max_keywords:
                    break
        
        return unique_keywords
    
    def calculate_relevance_score(
        self,
        keywords: List[str],
        text: str,
        tags: Optional[List[str]] = None
    ) -> float:
        """计算文本与关键词的相关度分数（优化版本）"""
        if not keywords or not text:
            return 0.0
        
        text_lower = text.lower()
        score = 0.0
        matched_keywords = []
        
        # 关键词匹配得分
        for keyword in keywords:
            if keyword in text_lower:
                # 完全匹配得分更高
                score += 2.0
                matched_keywords.append(keyword)
            elif any(keyword in word or word in keyword for word in text_lower.split()):
                # 部分匹配
                score += 1.0
                matched_keywords.append(keyword)
        
        # 标签匹配得分
        if tags:
            for tag in tags:
                tag_lower = tag.lower()
                for keyword in keywords:
                    if keyword in tag_lower or tag_lower in keyword:
                        score += 1.5
                        if keyword not in matched_keywords:
                            matched_keywords.append(keyword)
        
        # 匹配覆盖率奖励：匹配的关键词占总关键词的比例
        coverage_bonus = len(matched_keywords) / len(keywords) if keywords else 0
        score += coverage_bonus * 2.0  # 覆盖率奖励
        
        # 归一化
        max_possible_score = len(keywords) * 2.0 + 2.0  # 包含覆盖率奖励
        if max_possible_score > 0:
            score = score / max_possible_score
        
        return min(score, 1.0)
    
    def estimate_tokens(self, text: str) -> int:
        """估算文本的token数量（粗略估算）"""
        # 中文约1.5 token/字，英文约0.25 token/词
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        return int(chinese_chars * 1.5 + english_words * 0.25)
    
    def select_relevant_worldbook(
        self,
        keywords: List[str],
        worldbook_entries: List[Dict],
        max_entries: Optional[int] = None
    ) -> List[Dict]:
        """选择相关的世界书条目（优化版本）"""
        if not keywords or not worldbook_entries:
            return []
        
        max_entries = max_entries or self.config.max_worldbook_entries
        
        # 计算每个条目的相关度
        scored_entries = []
        for entry in worldbook_entries:
            if not entry.get('is_active', True):
                continue
            
            # 综合标题、内容、标签计算相关度
            title = entry.get('title', '')
            content = entry.get('content', '')
            tags = entry.get('tags', [])
            
            # 标题权重更高（标题匹配说明更相关）
            title_relevance = self.calculate_relevance_score(keywords, title, tags)
            content_relevance = self.calculate_relevance_score(keywords, content[:500], tags)
            
            # 标题权重60%，内容权重40%
            relevance = title_relevance * 0.6 + content_relevance * 0.4
            
            # 激活的条目基础分+0.1
            if entry.get('is_active', False):
                relevance += 0.1
            
            scored_entries.append((relevance, entry))
        
        # 按相关度排序
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        
        # 选择相关度超过阈值的条目
        selected = []
        for score, entry in scored_entries:
            if score >= self.config.keyword_match_threshold:
                selected.append(entry)
                if len(selected) >= max_entries:
                    break
        
        return selected
    
    def select_relevant_memories(
        self,
        keywords: List[str],
        memories: List[Dict],
        max_entries: Optional[int] = None
    ) -> List[Dict]:
        """选择相关的记忆条目（大幅优化版本）"""
        if not memories:
            return []
        
        max_entries = max_entries or self.config.max_memory_entries
        
        # 计算每个记忆的相关度
        scored_memories = []
        for memory in memories:
            if not memory.get('is_active', True):
                continue
            
            title = memory.get('title', '')
            content = memory.get('content', '')
            tags = memory.get('tags', [])
            importance = memory.get('importance', 1)
            
            # 计算基础相关度
            base_relevance = 0.0
            if keywords:
                base_relevance = self.calculate_relevance_score(keywords, f"{title} {content}", tags)
            
            # 重要度加权（记忆重要度1-5）- 重要的记忆即使不匹配也有基础分
            importance_weight = (importance / 5.0) * 0.5  # 提高重要度权重
            
            # 综合评分：相关度 + 重要度权重
            # 重要记忆即使不相关也能得到基础分，确保它们有机会被选中
            if base_relevance > 0:
                relevance = base_relevance + importance_weight
            else:
                relevance = importance_weight * 0.5  # 不相关但重要的记忆也有分数
            
            scored_memories.append((relevance, importance, memory))
        
        # 优先按相关度排序，其次按重要度排序
        scored_memories.sort(key=lambda x: (x[0], x[1]), reverse=True)
        
        # 选择记忆 - 大幅降低门槛，确保总能选到一些记忆
        selected = []
        for score, importance, memory in scored_memories:
            # 只要分数 > 0 或者重要度 >= 3，就可以被选中
            if score > 0 or importance >= 3:
                selected.append(memory)
                if len(selected) >= max_entries:
                    break
        
        return selected
    
    def select_relevant_footprints(
        self,
        keywords: List[str],
        footprints: List[Dict],
        max_entries: Optional[int] = None
    ) -> List[Dict]:
        """选择相关的足迹条目（大幅优化版本）"""
        if not footprints:
            return []
        
        max_entries = max_entries or self.config.max_footprint_entries
        
        # 计算每个足迹的相关度
        scored_footprints = []
        for footprint in footprints:
            title = footprint.get('title', '')
            description = footprint.get('description', '')
            tags = footprint.get('tags', [])
            importance = footprint.get('importance', 1)
            
            # 计算基础相关度
            base_relevance = 0.0
            if keywords:
                base_relevance = self.calculate_relevance_score(keywords, f"{title} {description}", tags)
            
            # 重要度加权（足迹重要度1-10）- 提高权重
            importance_weight = (importance / 10.0) * 0.5
            
            # 综合评分
            if base_relevance > 0:
                relevance = base_relevance + importance_weight
            else:
                relevance = importance_weight * 0.5  # 不相关但重要的足迹也有分数
            
            scored_footprints.append((relevance, importance, footprint))
        
        # 优先按相关度排序，其次按重要度排序
        scored_footprints.sort(key=lambda x: (x[0], x[1]), reverse=True)
        
        # 选择足迹 - 大幅降低门槛
        selected = []
        for score, importance, footprint in scored_footprints:
            if score > 0 or importance >= 5:
                selected.append(footprint)
                if len(selected) >= max_entries:
                    break
        
        return selected
    
    def build_context_prompt(
        self,
        character_prompt: str,
        user_message: str,
        worldbook_entries: Optional[List[Dict]] = None,
        memories: Optional[List[Dict]] = None,
        footprints: Optional[List[Dict]] = None,
        prompt_templates: Optional[List] = None,
        config: Optional[ContextConfig] = None
    ) -> str:
        """
        构建智能上下文提示词（结构化版本）
        
        Args:
            character_prompt: 角色预设提示词
            user_message: 用户当前消息
            worldbook_entries: 世界书条目列表
            memories: 记忆条目列表
            footprints: 足迹条目列表
            prompt_templates: 提示词模板列表（提升体验感）
            config: 上下文配置
        
        Returns:
            构建好的完整系统提示词
        """
        cfg = config or self.config
        
        # 如果不启用智能上下文，直接返回角色提示
        if not cfg.enable_smart_context:
            return character_prompt
        
        # 提取关键词
        keywords = self.extract_keywords(user_message)
        
        # 选择相关内容
        relevant_worldbook = self.select_relevant_worldbook(keywords, worldbook_entries or [])
        relevant_memories = self.select_relevant_memories(keywords, memories or [])
        relevant_footprints = self.select_relevant_footprints(keywords, footprints or [])
        
        # ===== 构建结构化提示词 =====
        context_parts = []
        
        # 第一部分：角色身份
        context_parts.append("【角色身份】\n")
        context_parts.append(character_prompt)
        
        # 第二部分：对话规则（新增）
        context_parts.append(
            "\n\n【对话规则】\n"
            "1. 保持逻辑一致性：回复必须与前文连贯，不要跳跃或矛盾\n"
            "2. 遵循角色设定：严格按照角色的性格、背景、说话风格回复\n"
            "3. 不要编造信息：如果不确定，宁可不说也不要编造与设定矛盾的内容\n"
            "4. 自然融入上下文：将世界背景、记忆、足迹等信息自然地融入回复，不要生硬引用\n"
            "5. 回复要简洁有力：避免冗长啰嗦，每句话都要有意义\n"
            "6. 关注用户意图：理解用户真正想问什么，而不是机械回答字面意思"
        )
        
        # 第三部分：提示词模板（提升体验感）
        if prompt_templates:
            template_context = "\n\n【聊天体验要求】\n"
            for template in prompt_templates:
                template_context += f"{template.content}\n"
            context_parts.append(template_context)
        
        # 第四部分：世界背景参考
        if relevant_worldbook:
            worldbook_context = "\n\n【世界背景参考】\n"
            worldbook_context += "（以下信息仅供你参考，回复时自然融入，不要直接引用）\n\n"
            for entry in relevant_worldbook:
                worldbook_context += f"• {entry['title']}：{entry['content'][:200]}\n"
            context_parts.append(worldbook_context)
        
        # 第五部分：角色记忆参考
        if relevant_memories:
            memory_context = "\n\n【角色记忆参考】\n"
            memory_context += "（你记得这些事情，回复时要主动、自然地提及！这很重要！）\n\n"
            for memory in relevant_memories:
                memory_type_icons = {
                    'general': '📝',
                    'fact': '📌',
                    'preference': '❤️',
                    'event': '📅',
                    'relationship': '👥'
                }
                icon = memory_type_icons.get(memory.get('memory_type', 'general'), '📝')
                memory_context += f"• {icon} {memory['title']}：{memory['content'][:200]}\n"
            context_parts.append(memory_context)
        
        # 第六部分：冒险足迹参考
        if relevant_footprints:
            footprint_context = "\n\n【冒险足迹参考】\n"
            footprint_context += "（你和用户一起经历过这些事情，回复时要主动提及共同回忆！）\n\n"
            for footprint in relevant_footprints:
                type_icons = {
                    'location': '🏰',
                    'person': '👤',
                    'item': '🎒',
                    'discovery': '🔍',
                    'main_event': '🎯',
                    'side_event': '📌'
                }
                icon = type_icons.get(footprint.get('footprint_type', 'location'), '📍')
                footprint_context += f"• {icon} {footprint['title']}：{footprint['description'][:200]}\n"
            context_parts.append(footprint_context)
        
        # 第七部分：思维链引导（让AI先思考再回复）
        if cfg.enable_chain_of_thought:
            context_parts.append(
                "\n\n【回复前的思考步骤】\n"
                "（请在内部思考，不要输出思考过程）\n"
                "1. 理解用户意图：用户真正想问什么？情绪状态如何？\n"
                "2. 回顾相关上下文：世界背景、记忆、足迹中有哪些信息与当前对话相关？\n"
                "3. 检查角色设定：我的性格、说话风格、行为模式要求我如何回复？\n"
                "4. 组织回复内容：确保回复逻辑连贯、符合角色设定、自然流畅\n"
                "5. 验证一致性：回复是否与之前的对话和设定矛盾？"
            )
        
        # 第八部分：一致性检查约束
        if cfg.enable_consistency_check:
            context_parts.append(
                "\n\n【一致性检查】\n"
                "在回复前，请确认：\n"
                "✓ 我的回复与之前的对话历史一致\n"
                "✓ 我的回复符合角色设定，没有跳出角色\n"
                "✓ 我的回复没有编造与世界背景矛盾的信息\n"
                "✓ 我的回复简洁自然，没有过度引用背景知识\n"
                "✓ 我的回复关注了用户的真实意图，而不是机械回答"
            )
        
        # 第九部分：重要提示
        if relevant_worldbook or relevant_memories or relevant_footprints:
            context_parts.append(
                "\n\n【重要提示】\n"
                "• 以上参考信息是你的记忆和背景知识，要主动使用！\n"
                "• 对于【角色记忆参考】和【冒险足迹参考】，要在对话中自然地提及，让用户感觉到你记得过去的事情！\n"
                "• 可以主动问起相关的话题，或者在回复中自然地带出过去的回忆\n"
                "• 如果用户说的内容与某个记忆相关，一定要主动提及！\n"
                "• 回复要简洁自然，不要生硬地罗列记忆，但要让用户感受到你记得！"
            )
        
        full_prompt = ''.join(context_parts)
        
        # Token预算检查
        token_count = self.estimate_tokens(full_prompt)
        if token_count > cfg.max_tokens:
            # 如果超出预算，裁剪内容
            full_prompt = self._trim_to_budget(full_prompt, cfg.max_tokens)
        
        return full_prompt
    
    def _trim_to_budget(self, text: str, max_tokens: int) -> str:
        """裁剪文本到Token预算内"""
        current_tokens = self.estimate_tokens(text)
        
        if current_tokens <= max_tokens:
            return text
        
        # 按比例裁剪
        trim_ratio = max_tokens / current_tokens
        
        # 保留前面的部分
        char_limit = int(len(text) * trim_ratio)
        
        # 找到合适的截断点（句号或换行）
        trimmed = text[:char_limit]
        last_period = max(trimmed.rfind('。'), trimmed.rfind('\n'))
        
        if last_period > char_limit * 0.8:
            trimmed = trimmed[:last_period + 1]
        
        return trimmed + "\n\n（上下文已精简）"


# 全局单例
context_manager = ContextManager()
