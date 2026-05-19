from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from app.plugins.plugin_base import plugin_manager
from app.scripts.script_base import ScriptRunner
import os

router = APIRouter(prefix="/api", tags=["插件和脚本"])

class PluginResponse(BaseModel):
    success: bool
    plugins: Dict[str, Any]

class ScriptRequest(BaseModel):
    script_name: str
    args: Dict[str, Any] = {}

@router.get("/plugins", response_model=PluginResponse)
async def list_plugins():
    """列出所有已加载的插件"""
    plugins_info = {
        name: {
            "version": plugin.metadata.version,
            "description": plugin.metadata.description,
            "enabled": plugin.metadata.enabled
        }
        for name, plugin in plugin_manager.plugins.items()
    }
    
    return PluginResponse(
        success=True,
        plugins=plugins_info
    )

@router.post("/scripts/run")
async def run_script(request: ScriptRequest):
    """运行脚本"""
    scripts_dir = os.getenv("SCRIPTS_DIR", "./scripts")
    script_path = os.path.join(scripts_dir, f"{request.script_name}.py")
    
    if not os.path.exists(script_path):
        return {
            "success": False,
            "error": f"脚本不存在: {script_path}"
        }
    
    result = await ScriptRunner.run_python_script(script_path, request.args)
    return result
