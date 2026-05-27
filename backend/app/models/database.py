from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chat_system.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    preferences = Column(JSON, default=dict)

class ChatMessage(Base):
    """聊天消息模型"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    character_id = Column(String, index=True, nullable=True)  # 关联的角色ID
    role = Column(String)
    content = Column(Text)
    audio_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserMemory(Base):
    """用户记忆模型"""
    __tablename__ = "user_memories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    memory_type = Column(String)
    content = Column(Text)
    embedding = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserApiKey(Base):
    """用户API密钥模型"""
    __tablename__ = "user_api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    provider = Column(String, index=True)
    env_name = Column(String)
    api_key = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ApiConfig(Base):
    """API配置模型 - 存储完整的API配置信息"""
    __tablename__ = "api_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    name = Column(String, default="默认配置")
    api_spec = Column(String, default="OpenAI")
    api_key = Column(Text)
    base_url = Column(String)
    
    chat_model = Column(String, nullable=True)
    embedding_model = Column(String, nullable=True)
    summary_model = Column(String, nullable=True)
    tts_model = Column(String, nullable=True)
    image_model = Column(String, nullable=True)
    vision_model = Column(String, nullable=True)
    speech_model = Column(String, nullable=True)
    
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=1000)
    top_p = Column(Float, default=1.0)
    system_prompt = Column(Text, nullable=True)
    
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CharacterVoiceConfig(Base):
    """角色语音配置模型 - 存储每个角色的个性化语音设置"""
    __tablename__ = "character_voice_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    character_id = Column(String, index=True)  # 角色ID
    
    # 语音模型配置
    tts_model = Column(String, default="tts-1")  # TTS模型
    tts_voice = Column(String, default="nova")  # 音色 (alloy, echo, fable, onyx, nova, shimmer)
    
    # 语音参数
    speed = Column(Float, default=1.0)  # 语速 (0.25-4.0)
    volume = Column(Float, default=1.0)  # 音量 (0.0-1.0)
    pitch = Column(Float, default=1.0)  # 音调 (0.5-2.0)
    
    # 语音格式
    audio_format = Column(String, default="mp3")  # 音频格式 (mp3, opus, aac, flac)
    response_format = Column(String, default="mp3")  # 响应格式
    
    # 其他设置
    enable_tts = Column(Boolean, default=True)  # 是否启用语音
    auto_play = Column(Boolean, default=False)  # 是否自动播放
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TtsConfig(Base):
    """TTS服务配置模型 - 存储TTS API配置"""
    __tablename__ = "tts_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    name = Column(String, default="默认TTS配置")  # 配置名称
    
    # API配置
    api_key = Column(Text)  # API密钥
    base_url = Column(String)  # API基础URL
    api_spec = Column(String, default="OpenAI")  # API规范
    
    # 模型配置
    tts_model = Column(String, default="tts-1")  # TTS模型
    tts_voice = Column(String, default="nova")  # 默认音色
    
    # 状态
    is_active = Column(Boolean, default=True)  # 是否启用
    is_default = Column(Boolean, default=False)  # 是否为默认配置
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlarmReminder(Base):
    """闹钟提醒模型 - 存储用户的闹钟提醒设置"""
    __tablename__ = "alarm_reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    
    # 闹钟基本信息
    title = Column(String, default="提醒")  # 闹钟标题
    message = Column(Text, nullable=True)  # 提醒消息内容
    
    # 时间设置
    alarm_time = Column(String)  # 闹钟时间 (HH:MM格式)
    repeat_type = Column(String, default="once")  # 重复类型: once(一次), daily(每天), weekly(每周), custom(自定义)
    repeat_days = Column(JSON, nullable=True)  # 重复的星期 [0,1,2,3,4,5,6] 0=周一
    
    # 角色设置
    character_id = Column(String, nullable=True)  # 提醒角色ID
    character_name = Column(String, nullable=True)  # 提醒角色名称
    
    # 开关状态
    is_enabled = Column(Boolean, default=True)  # 是否启用
    is_active = Column(Boolean, default=True)  # 是否激活
    
    # 其他设置
    enable_tts = Column(Boolean, default=True)  # 是否使用语音提醒
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)  # 上次触发时间

class GreetingSchedule(Base):
    """问候时间表 - 存储用户的定时问候设置"""
    __tablename__ = "greeting_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    
    # 问候类型
    greeting_type = Column(String)  # morning(早安), noon(午安), evening(晚安), custom(自定义)
    
    # 时间设置
    greeting_time = Column(String)  # 问候时间 (HH:MM格式)
    
    # 角色设置
    character_id = Column(String, nullable=True)  # 问候角色ID
    character_name = Column(String, nullable=True)  # 问候角色名称
    
    # 问候内容
    custom_message = Column(Text, nullable=True)  # 自定义问候消息（为空则自动生成）
    
    # 开关状态
    is_enabled = Column(Boolean, default=True)  # 是否启用
    
    # 其他设置
    enable_tts = Column(Boolean, default=True)  # 是否使用语音问候
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)  # 上次触发时间

class SpecialDate(Base):
    """特殊日期 - 存储用户的重要日期（生日、纪念日等）"""
    __tablename__ = "special_dates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    
    # 日期信息
    title = Column(String)  # 日期标题（如"我的生日"、"恋爱纪念日"）
    date_type = Column(String)  # 日期类型：birthday(生日), anniversary(纪念日), custom(自定义)
    month = Column(Integer)  # 月份 (1-12)
    day = Column(Integer)  # 日期 (1-31)
    year = Column(Integer, nullable=True)  # 年份（可选，生日通常不需要）
    
    # 相关人物
    related_person = Column(String, nullable=True)  # 相关人物（如"妈妈"、"男朋友"）
    
    # 角色设置
    character_id = Column(String, nullable=True)  # 祝福角色ID
    character_name = Column(String, nullable=True)  # 祝福角色名称
    
    # 提醒设置
    remind_days_before = Column(Integer, default=0)  # 提前几天提醒
    is_enabled = Column(Boolean, default=True)  # 是否启用
    
    # 其他设置
    enable_tts = Column(Boolean, default=True)  # 是否使用语音祝福
    custom_message = Column(Text, nullable=True)  # 自定义祝福消息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)  # 上次触发时间

class CareReminder(Base):
    """习惯关怀提醒 - 存储用户的关怀偏好设置"""
    __tablename__ = "care_reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    
    # 关怀类型
    care_type = Column(String)  # water(喝水), rest(休息), exercise(运动), eye(护眼), meal(用餐), sleep(睡眠)
    
    # 时间设置
    reminder_time = Column(String)  # 提醒时间 (HH:MM格式)
    repeat_type = Column(String, default="daily")  # 重复类型: once(一次), daily(每天), weekly(每周), custom(自定义)
    repeat_days = Column(JSON, nullable=True)  # 重复的星期 [0,1,2,3,4,5,6] 0=周一
    
    # 角色设置
    character_id = Column(String, nullable=True)  # 提醒角色ID
    character_name = Column(String, nullable=True)  # 问候角色名称
    
    # 关怀内容
    custom_message = Column(Text, nullable=True)  # 自定义关怀消息
    
    # 开关状态
    is_enabled = Column(Boolean, default=True)  # 是否启用
    
    # 其他设置
    enable_tts = Column(Boolean, default=True)  # 是否使用语音提醒
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)  # 上次触发时间

class CharacterMemory(Base):
    """角色记忆模型 - 存储角色的记忆树节点"""
    __tablename__ = "character_memories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    character_id = Column(String, index=True)  # 关联的角色ID
    
    # 记忆内容
    title = Column(String)  # 记忆标题
    content = Column(Text)  # 记忆详细内容
    memory_type = Column(String, default="general")  # 记忆类型: general(一般), fact(事实), preference(偏好), event(事件), relationship(关系)
    
    # 树状结构
    parent_id = Column(Integer, ForeignKey('character_memories.id'), nullable=True)  # 父节点ID
    level = Column(Integer, default=0)  # 层级深度
    
    # 记忆属性
    importance = Column(Integer, default=1)  # 重要程度 1-5
    is_active = Column(Boolean, default=True)  # 是否激活（可引用）
    tags = Column(JSON, nullable=True)  # 标签列表
    access_count = Column(Integer, default=0)  # 访问次数
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)  # 最后访问时间

class MemoryEvent(Base):
    """角色记忆事件模型 - 存储角色与用户聊天的事件分支"""
    __tablename__ = "memory_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    character_id = Column(String, index=True)  # 关联的角色ID
    
    # 事件基本信息
    event_type = Column(String, default="main")  # 事件类型: main(主线), side(支线)
    title = Column(String)  # 事件标题
    description = Column(Text)  # 事件描述
    chat_context = Column(Text, nullable=True)  # 触发该事件的聊天内容
    
    # 树状分支结构
    parent_event_id = Column(Integer, ForeignKey('memory_events.id'), nullable=True)  # 父事件ID
    level = Column(Integer, default=0)  # 层级深度
    
    # 事件状态和属性
    status = Column(String, default="active")  # 事件状态: active(进行中), completed(已完成), archived(已归档)
    importance = Column(Integer, default=5)  # 重要程度 1-10
    tags = Column(JSON, nullable=True)  # 标签列表
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    occurred_at = Column(DateTime, nullable=True)  # 事件发生时间

class FootprintConfig(Base):
    """足迹配置模型 - 存储每个角色的足迹自动提取配置"""
    __tablename__ = "footprint_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    character_id = Column(String, index=True)  # 关联的角色ID
    
    # 配置项
    auto_extract_enabled = Column(Boolean, default=False)  # 是否启用自动提取
    context_limit = Column(Integer, default=50)  # 读取的聊天记录条数
    extract_interval = Column(Integer, default=5)  # 触发间隔：聊多少轮后触发一次自动提取
    
    # 计数器
    chat_count = Column(Integer, default=0)  # 当前聊天轮数计数器
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ContextLog(Base):
    """上下文日志模型 - 存储AI自动提取足迹的日志记录"""
    __tablename__ = "context_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    character_id = Column(String, index=True)  # 关联的角色ID
    
    # 日志内容
    log_type = Column(String, default="auto_extract")  # 日志类型: auto_extract(自动提取), manual_extract(手动提取)
    status = Column(String, default="success")  # 状态: success(成功), failed(失败), processing(处理中)
    message = Column(Text)  # 日志消息
    context_count = Column(Integer, nullable=True)  # 读取的上下文条数
    extracted_count = Column(Integer, default=0)  # 提取的足迹数量
    updated_count = Column(Integer, default=0)  # 更新的足迹数量
    error_message = Column(Text, nullable=True)  # 错误信息
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)

class PromptTemplate(Base):
    """提示词模板模型 - 存储用于提升聊天体验感的提示词"""
    __tablename__ = "prompt_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    character_id = Column(String, index=True, nullable=True)  # 关联的角色ID，为空表示全局模板
    
    # 提示词基本信息
    name = Column(String)  # 提示词名称
    description = Column(Text, nullable=True)  # 提示词描述
    
    # 提示词内容
    content = Column(Text)  # 提示词内容
    
    # 提示词类型
    template_type = Column(String, default="experience")  # 类型: experience(体验感), roleplay(角色扮演), emotion(情感表达), action(动作描写), dialogue(对话风格)
    
    # 状态和属性
    is_enabled = Column(Boolean, default=True)  # 是否启用
    is_active = Column(Boolean, default=True)  # 是否激活
    priority = Column(Integer, default=1)  # 优先级 1-5，数字越大优先级越高
    tags = Column(JSON, nullable=True)  # 标签列表
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuthorNoteConfig(Base):
    """Author's Note（作者注释）配置模型 - 存储每个角色的作者注释设置"""
    __tablename__ = "author_note_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    character_id = Column(String, index=True)  # 关联的角色ID
    
    # 注释内容
    content = Column(Text)  # Author's Note内容
    
    # 插入配置
    depth = Column(Integer, default=3)  # 插入深度（倒数第N条消息后）
    interval = Column(Integer, default=4)  # 循环间隔（每N条用户消息重复一次）
    position = Column(String, default="after")  # 插入位置: before(前), after(后)
    
    # 状态
    is_enabled = Column(Boolean, default=False)  # 是否启用
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WorldBookEntryDB(Base):
    """世界书条目数据库模型 - 增强版，支持智能激活"""
    __tablename__ = "worldbook_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    
    # 基本信息
    title = Column(String)  # 条目标题
    content = Column(Text)  # 条目内容
    category = Column(String, default="general")  # 分类: general, character, location, item, lore, rule
    tags = Column(JSON, nullable=True)  # 标签列表
    
    # 角色关联
    character_id = Column(String, index=True, nullable=True)  # 绑定的角色ID，空表示全局共享
    collection = Column(String, nullable=True)  # 集合标识，用于分组
    
    # 激活控制（新增字段 - 基于SillyTavern）
    keywords = Column(JSON, nullable=True)  # 触发关键词列表
    selective_type = Column(String, default="normal")  # 选择类型: always(始终), normal(正常), conditional(条件), scan_depth(深度扫描)
    constant = Column(Integer, default=0)  # 位置常数 (-1000 ~ 1000)，控制插入顺序
    scan_depth = Column(Integer, default=5)  # 扫描深度（检查最近N条消息）
    token_budget = Column(Integer, default=512)  # Token预算（该条目最大消耗）
    
    # 状态
    is_active = Column(Boolean, default=True)  # 是否激活
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
