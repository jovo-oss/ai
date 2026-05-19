from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.models.database import init_db
from app.plugins.plugin_base import plugin_manager
from app.routes import chat, plugins, models, characters, worldbook
import os

load_dotenv()

# 初始化数据库
init_db()

# 加载插件
# 使用绝对路径，从项目根目录查找plugins文件夹
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
plugins_dir = os.getenv("PLUGINS_DIR", os.path.join(project_root, "plugins"))
scripts_dir = os.getenv("SCRIPTS_DIR", os.path.join(project_root, "scripts"))

# 更新环境变量以便路由可以使用
os.environ["PLUGINS_DIR"] = plugins_dir
os.environ["SCRIPTS_DIR"] = scripts_dir

print(f"插件目录: {plugins_dir}")
print(f"脚本目录: {scripts_dir}")

plugin_manager.load_plugins_from_directory(plugins_dir)

app = FastAPI(
    title="AI聊天系统",
    description="可扩展的AI聊天系统，支持插件和脚本",
    version="1.0.0"
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

# 打印当前模型信息
from app.services.model_registry import model_registry
current = model_registry.get_current_model()
print(f"当前模型: {current.name} ({current.model_name})")
print(f"提供商: {current.provider}")

@app.get("/")
async def root():
    return {"message": "AI聊天系统API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "True") == "True"
    )
