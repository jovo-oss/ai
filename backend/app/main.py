from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from app.models.database import init_db
from app.plugins.plugin_base import plugin_manager
from app.routes import chat, plugins, models, characters, worldbook, configs, voice_configs, agent, alarm_reminders, environment, proactive_interaction, tts_configs, memories, memory_events, footprint_config, context_logs, prompt_templates, admin
from app.services.alarm_scheduler import alarm_scheduler
from app.services.proactive_interaction_service import proactive_interaction_service
import os
import json
import asyncio

load_dotenv()

# 自定义JSON响应类,确保中文字符正确编码
class ChineseJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

# 初始化数据库
init_db()

# 加载插件
# 使用绝对路径，从项目根目录查找plugins文件夹
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
plugins_dir = os.getenv("PLUGINS_DIR", os.path.join(project_root, "plugins"))
scripts_dir = os.getenv("SCRIPTS_DIR", os.path.join(project_root, "scripts"))
frontend_dir = os.path.join(project_root, "frontend")

# 更新环境变量以便路由可以使用
os.environ["PLUGINS_DIR"] = plugins_dir
os.environ["SCRIPTS_DIR"] = scripts_dir

print(f"插件目录: {plugins_dir}")
print(f"脚本目录: {scripts_dir}")
print(f"前端目录: {frontend_dir}")

plugin_manager.load_plugins_from_directory(plugins_dir)

app = FastAPI(
    title="AI聊天系统",
    description="可扩展的AI聊天系统，支持插件和脚本",
    version="1.0.0",
    default_response_class=ChineseJSONResponse
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router)
app.include_router(plugins.router)
app.include_router(models.router)
app.include_router(characters.router)
app.include_router(worldbook.router)
app.include_router(configs.router)
app.include_router(voice_configs.router)
app.include_router(agent.router)
app.include_router(alarm_reminders.router)
app.include_router(environment.router)
app.include_router(proactive_interaction.router)
app.include_router(tts_configs.router)
app.include_router(memories.router)
app.include_router(memory_events.router)
app.include_router(footprint_config.router)
app.include_router(context_logs.router)
app.include_router(prompt_templates.router)
app.include_router(admin.router)

# 提供前端静态文件
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    
    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/admin")
    async def serve_admin():
        return FileResponse(os.path.join(frontend_dir, "admin.html"))
else:
    @app.get("/")
    async def root():
        return {"message": "AI聊天系统API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/favicon.ico")
async def favicon():
    """返回空响应，避免404错误"""
    from fastapi.responses import Response
    return Response(content="", media_type="image/x-icon")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "True") == "True"
    )
