from fastapi import APIRouter, Query
from app.models.database import SessionLocal, ChatMessage, User, UserApiKey, ApiConfig, CharacterVoiceConfig, TtsConfig, AlarmReminder, CharacterMemory, MemoryEvent, FootprintConfig, ContextLog, PromptTemplate, AuthorNoteConfig, WorldBookEntryDB, GreetingSchedule, SpecialDate, CareReminder
from datetime import datetime, timedelta
import os
import sys
import platform
import sqlite3

router = APIRouter(prefix="/api/admin", tags=["管理站"])


def _get_db():
    db = SessionLocal()
    try:
        return db
    except Exception:
        return None


@router.get("/overview")
async def get_overview():
    db = _get_db()
    if not db:
        return {"success": False, "message": "数据库连接失败"}
    try:
        total_messages = db.query(ChatMessage).count()
        total_characters = len(set(
            row.character_id for row in db.query(ChatMessage.character_id).distinct()
            if row.character_id
        ))
        total_api_configs = db.query(ApiConfig).count()
        total_memories = db.query(CharacterMemory).count()
        total_events = db.query(MemoryEvent).count()
        total_worldbook = db.query(WorldBookEntryDB).count()
        total_alarms = db.query(AlarmReminder).count()
        total_prompt_templates = db.query(PromptTemplate).count()
        total_context_logs = db.query(ContextLog).count()
        total_tts_configs = db.query(TtsConfig).count()
        total_voice_configs = db.query(CharacterVoiceConfig).count()
        total_footprint_configs = db.query(FootprintConfig).count()
        total_author_notes = db.query(AuthorNoteConfig).count()
        total_greeting_schedules = db.query(GreetingSchedule).count()
        total_special_dates = db.query(SpecialDate).count()
        total_care_reminders = db.query(CareReminder).count()
        total_users = db.query(User).count()
        total_api_keys = db.query(UserApiKey).count()

        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        messages_today = db.query(ChatMessage).filter(ChatMessage.created_at >= today_start).count()
        messages_week = db.query(ChatMessage).filter(ChatMessage.created_at >= week_ago).count()
        messages_month = db.query(ChatMessage).filter(ChatMessage.created_at >= month_ago).count()

        active_api_configs = db.query(ApiConfig).filter(ApiConfig.is_active == 1).count()
        active_alarms = db.query(AlarmReminder).filter(AlarmReminder.is_enabled == True).count()
        active_worldbook = db.query(WorldBookEntryDB).filter(WorldBookEntryDB.is_active == True).count()
        active_memories = db.query(CharacterMemory).filter(CharacterMemory.is_active == True).count()
        active_prompt_templates = db.query(PromptTemplate).filter(PromptTemplate.is_enabled == True).count()

        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chat_system.db")
        db_size_mb = 0
        if os.path.exists(db_path):
            db_size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2)

        return {
            "success": True,
            "data": {
                "total_counts": {
                    "messages": total_messages,
                    "characters": total_characters,
                    "users": total_users,
                    "api_configs": total_api_configs,
                    "api_keys": total_api_keys,
                    "memories": total_memories,
                    "events": total_events,
                    "worldbook_entries": total_worldbook,
                    "alarms": total_alarms,
                    "prompt_templates": total_prompt_templates,
                    "context_logs": total_context_logs,
                    "tts_configs": total_tts_configs,
                    "voice_configs": total_voice_configs,
                    "footprint_configs": total_footprint_configs,
                    "author_notes": total_author_notes,
                    "greeting_schedules": total_greeting_schedules,
                    "special_dates": total_special_dates,
                    "care_reminders": total_care_reminders,
                },
                "active_counts": {
                    "api_configs": active_api_configs,
                    "alarms": active_alarms,
                    "worldbook_entries": active_worldbook,
                    "memories": active_memories,
                    "prompt_templates": active_prompt_templates,
                },
                "message_stats": {
                    "today": messages_today,
                    "week": messages_week,
                    "month": messages_month,
                    "total": total_messages,
                },
                "database": {
                    "size_mb": db_size_mb,
                    "path": db_path,
                },
            }
        }
    except Exception as e:
        return {"success": False, "message": f"获取概览失败: {str(e)}"}
    finally:
        db.close()


@router.get("/modules")
async def get_modules():
    db = _get_db()
    if not db:
        return {"success": False, "message": "数据库连接失败"}
    try:
        modules = [
            {
                "id": "chat",
                "name": "聊天系统",
                "icon": "💬",
                "description": "AI智能对话核心，支持多模型切换",
                "route": "/api/chat",
                "count": db.query(ChatMessage).count(),
                "status": "active",
                "category": "core",
                "version": "3.5.0",
            },
            {
                "id": "characters",
                "name": "角色预设",
                "icon": "👤",
                "description": "创建和管理AI角色，支持对话分析创建",
                "route": "/api/characters",
                "count": len(set(
                    row.character_id for row in db.query(ChatMessage.character_id).distinct()
                    if row.character_id
                )),
                "status": "active",
                "category": "core",
                "version": "3.5.0",
            },
            {
                "id": "worldbook",
                "name": "世界书",
                "icon": "📚",
                "description": "管理背景设定和知识库，支持智能激活",
                "route": "/api/worldbook",
                "count": db.query(WorldBookEntryDB).count(),
                "status": "active",
                "category": "core",
                "version": "3.5.0",
            },
            {
                "id": "models",
                "name": "模型广场",
                "icon": "🎯",
                "description": "发现和管理可用AI模型",
                "route": "/api/models",
                "count": db.query(ApiConfig).count(),
                "status": "active",
                "category": "core",
                "version": "3.5.0",
            },
            {
                "id": "configs",
                "name": "API配置",
                "icon": "🔑",
                "description": "管理API密钥和配置参数",
                "route": "/api/configs",
                "count": db.query(ApiConfig).count(),
                "status": "active",
                "category": "core",
                "version": "3.5.0",
            },
            {
                "id": "memories",
                "name": "角色记忆",
                "icon": "🧠",
                "description": "角色记忆树，支持层级结构",
                "route": "/api/memories",
                "count": db.query(CharacterMemory).count(),
                "status": "active",
                "category": "intelligence",
                "version": "3.5.0",
            },
            {
                "id": "memory_events",
                "name": "足迹系统",
                "icon": "👣",
                "description": "知识图谱模式，多维度关联关系",
                "route": "/api/memory-events",
                "count": db.query(MemoryEvent).count(),
                "status": "active",
                "category": "intelligence",
                "version": "3.5.0",
            },
            {
                "id": "footprint_config",
                "name": "足迹配置",
                "icon": "⚙️",
                "description": "自动提取足迹的配置管理",
                "route": "/api/footprint-config",
                "count": db.query(FootprintConfig).count(),
                "status": "active",
                "category": "intelligence",
                "version": "3.5.0",
            },
            {
                "id": "context_logs",
                "name": "上下文日志",
                "icon": "📋",
                "description": "记录AI自动提取足迹的完整过程",
                "route": "/api/context-logs",
                "count": db.query(ContextLog).count(),
                "status": "active",
                "category": "intelligence",
                "version": "3.5.0",
            },
            {
                "id": "prompt_templates",
                "name": "提示词模板",
                "icon": "📝",
                "description": "管理体验感提示词和角色扮演模板",
                "route": "/api/prompt-templates",
                "count": db.query(PromptTemplate).count(),
                "status": "active",
                "category": "intelligence",
                "version": "3.5.0",
            },
            {
                "id": "voice_configs",
                "name": "角色语音",
                "icon": "🔊",
                "description": "为每个角色单独设置语音参数",
                "route": "/api/voice-configs",
                "count": db.query(CharacterVoiceConfig).count(),
                "status": "active",
                "category": "voice",
                "version": "3.5.0",
            },
            {
                "id": "tts_configs",
                "name": "TTS配置",
                "icon": "🎙️",
                "description": "管理TTS服务API配置",
                "route": "/api/tts-configs",
                "count": db.query(TtsConfig).count(),
                "status": "active",
                "category": "voice",
                "version": "3.5.0",
            },
            {
                "id": "alarm_reminders",
                "name": "闹钟提醒",
                "icon": "⏰",
                "description": "定时提醒和问候服务",
                "route": "/api/alarm-reminders",
                "count": db.query(AlarmReminder).count(),
                "status": "active",
                "category": "interaction",
                "version": "3.5.0",
            },
            {
                "id": "proactive_interaction",
                "name": "主动交互",
                "icon": "🤝",
                "description": "AI主动发起对话和关怀",
                "route": "/api/proactive-interaction",
                "count": 0,
                "status": "active",
                "category": "interaction",
                "version": "3.5.0",
            },
            {
                "id": "environment",
                "name": "环境感知",
                "icon": "🌍",
                "description": "时间感知和天气感知服务",
                "route": "/api/environment",
                "count": 0,
                "status": "active",
                "category": "interaction",
                "version": "3.5.0",
            },
            {
                "id": "agent",
                "name": "Agent工具",
                "icon": "🛠️",
                "description": "AI智能工具集合（角色分析、世界书生成等）",
                "route": "/api/agent",
                "count": 0,
                "status": "active",
                "category": "tools",
                "version": "3.5.0",
            },
            {
                "id": "plugins",
                "name": "插件系统",
                "icon": "🧩",
                "description": "可扩展的插件管理框架",
                "route": "/api/plugins",
                "count": 0,
                "status": "active",
                "category": "tools",
                "version": "3.5.0",
            },
        ]
        return {"success": True, "data": modules}
    except Exception as e:
        return {"success": False, "message": f"获取模块列表失败: {str(e)}"}
    finally:
        db.close()


@router.get("/health")
async def health_check():
    db = _get_db()
    db_status = "disconnected"
    if db:
        try:
            db.query(User).first()
            db_status = "connected"
        except Exception:
            db_status = "error"
        finally:
            db.close()

    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chat_system.db")
    db_size_mb = 0
    if os.path.exists(db_path):
        db_size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2)

    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    env_exists = os.path.exists(env_file)

    plugins_dir = os.environ.get("PLUGINS_DIR", "")
    scripts_dir = os.environ.get("SCRIPTS_DIR", "")
    plugins_count = 0
    if plugins_dir and os.path.exists(plugins_dir):
        plugins_count = len([f for f in os.listdir(plugins_dir) if f.endswith(".py") and f != "__init__.py"])

    return {
        "success": True,
        "data": {
            "system": {
                "python_version": sys.version,
                "platform": platform.platform(),
                "cpu_count": os.cpu_count(),
            },
            "database": {
                "status": db_status,
                "size_mb": db_size_mb,
                "path": db_path,
            },
            "environment": {
                "env_file_exists": env_exists,
                "plugins_dir": plugins_dir,
                "scripts_dir": scripts_dir,
                "plugins_count": plugins_count,
            },
            "server": {
                "host": os.getenv("HOST", "0.0.0.0"),
                "port": os.getenv("PORT", "8000"),
                "debug": os.getenv("DEBUG", "True"),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.get("/message-chart")
async def get_message_chart(days: int = Query(default=7, ge=1, le=30)):
    db = _get_db()
    if not db:
        return {"success": False, "message": "数据库连接失败"}
    try:
        now = datetime.utcnow()
        chart_data = []
        for i in range(days - 1, -1, -1):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            count = db.query(ChatMessage).filter(
                ChatMessage.created_at >= day_start,
                ChatMessage.created_at < day_end
            ).count()
            chart_data.append({
                "date": day_start.strftime("%m-%d"),
                "count": count,
            })
        return {"success": True, "data": chart_data}
    except Exception as e:
        return {"success": False, "message": f"获取消息图表失败: {str(e)}"}
    finally:
        db.close()


@router.get("/character-stats")
async def get_character_stats():
    db = _get_db()
    if not db:
        return {"success": False, "message": "数据库连接失败"}
    try:
        from sqlalchemy import func
        char_stats = db.query(
            ChatMessage.character_id,
            func.count(ChatMessage.id).label("msg_count")
        ).filter(
            ChatMessage.character_id.isnot(None)
        ).group_by(
            ChatMessage.character_id
        ).order_by(
            func.count(ChatMessage.id).desc()
        ).limit(10).all()

        result = []
        for char_id, count in char_stats:
            memory_count = db.query(CharacterMemory).filter(CharacterMemory.character_id == char_id).count()
            event_count = db.query(MemoryEvent).filter(MemoryEvent.character_id == char_id).count()
            worldbook_count = db.query(WorldBookEntryDB).filter(WorldBookEntryDB.character_id == char_id).count()
            result.append({
                "character_id": char_id,
                "message_count": count,
                "memory_count": memory_count,
                "event_count": event_count,
                "worldbook_count": worldbook_count,
            })
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "message": f"获取角色统计失败: {str(e)}"}
    finally:
        db.close()


@router.get("/database/tables")
async def get_database_tables():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chat_system.db")
    if not os.path.exists(db_path):
        return {"success": False, "message": "数据库文件不存在"}
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        table_info = []
        for (table_name,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            row_count = cursor.fetchone()[0]
            cursor.execute(f"PRAGMA table_info([{table_name}])")
            columns = cursor.fetchall()
            table_info.append({
                "name": table_name,
                "row_count": row_count,
                "column_count": len(columns),
            })
        conn.close()
        return {"success": True, "data": table_info}
    except Exception as e:
        return {"success": False, "message": f"获取数据库表信息失败: {str(e)}"}


@router.post("/database/vacuum")
async def vacuum_database():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chat_system.db")
    try:
        size_before = os.path.getsize(db_path) / (1024 * 1024) if os.path.exists(db_path) else 0
        conn = sqlite3.connect(db_path)
        conn.execute("VACUUM")
        conn.close()
        size_after = os.path.getsize(db_path) / (1024 * 1024)
        return {
            "success": True,
            "message": "数据库优化完成",
            "size_before_mb": round(size_before, 2),
            "size_after_mb": round(size_after, 2),
            "saved_mb": round(size_before - size_after, 2),
        }
    except Exception as e:
        return {"success": False, "message": f"数据库优化失败: {str(e)}"}


@router.get("/recent-activity")
async def get_recent_activity(limit: int = Query(default=20, ge=1, le=100)):
    db = _get_db()
    if not db:
        return {"success": False, "message": "数据库连接失败"}
    try:
        activities = []
        recent_messages = db.query(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(limit).all()
        for msg in recent_messages:
            activities.append({
                "type": "message",
                "character_id": msg.character_id,
                "role": msg.role,
                "content_preview": msg.content[:80] if msg.content else "",
                "time": msg.created_at.isoformat() if msg.created_at else "",
            })

        recent_memories = db.query(CharacterMemory).order_by(CharacterMemory.created_at.desc()).limit(5).all()
        for mem in recent_memories:
            activities.append({
                "type": "memory",
                "character_id": mem.character_id,
                "title": mem.title,
                "time": mem.created_at.isoformat() if mem.created_at else "",
            })

        recent_events = db.query(MemoryEvent).order_by(MemoryEvent.created_at.desc()).limit(5).all()
        for evt in recent_events:
            activities.append({
                "type": "event",
                "character_id": evt.character_id,
                "title": evt.title,
                "time": evt.created_at.isoformat() if evt.created_at else "",
            })

        recent_logs = db.query(ContextLog).order_by(ContextLog.created_at.desc()).limit(5).all()
        for log in recent_logs:
            activities.append({
                "type": "log",
                "character_id": log.character_id,
                "status": log.status,
                "message": log.message[:80] if log.message else "",
                "time": log.created_at.isoformat() if log.created_at else "",
            })

        activities.sort(key=lambda x: x.get("time", ""), reverse=True)
        return {"success": True, "data": activities[:limit]}
    except Exception as e:
        return {"success": False, "message": f"获取最近活动失败: {str(e)}"}
    finally:
        db.close()


@router.get("/api-keys-status")
async def get_api_keys_status():
    db = _get_db()
    if not db:
        return {"success": False, "message": "数据库连接失败"}
    try:
        configs = db.query(ApiConfig).all()
        result = []
        for cfg in configs:
            result.append({
                "id": cfg.id,
                "name": cfg.name,
                "api_spec": cfg.api_spec,
                "base_url": cfg.base_url,
                "chat_model": cfg.chat_model,
                "is_active": cfg.is_active == 1,
                "has_key": bool(cfg.api_key),
                "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else "",
            })
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "message": f"获取API配置状态失败: {str(e)}"}
    finally:
        db.close()


@router.get("/version-info")
async def get_version_info():
    return {
        "success": True,
        "data": {
            "version": "3.5.0",
            "build_date": "2026-05-26",
            "features": [
                "素黑主题界面",
                "AI智能对话",
                "语音合成播放",
                "角色预设系统",
                "世界书功能",
                "世界书智能激活",
                "聊天频道",
                "上下文显示区块",
                "API配置管理",
                "模型广场",
                "角色语音配置",
                "Agent工具模块",
                "角色足迹系统",
                "智能主动记录",
                "多策略降级解析",
                "上下文日志",
                "智能上下文管理",
                "自动摘要服务",
                "Author's Note",
                "消息重说",
                "插件系统",
                "脚本系统",
                "闹钟提醒",
                "环境感知",
                "主动交互",
                "提示词模板",
                "管理站",
            ],
        }
    }
