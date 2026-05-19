"""
示例脚本 - 数据清理
演示如何创建脚本
"""
from app.scripts.script_base import BaseScript
from typing import Any, Dict

class CleanOldDataScript(BaseScript):
    """清理旧数据脚本"""
    
    def __init__(self):
        super().__init__()
        self.name = "CleanOldDataScript"
        self.description = "清理30天前的聊天数据"
    
    async def run(self, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行清理任务"""
        try:
            # 这里可以添加实际的数据库清理逻辑
            return {
                "success": True,
                "message": "数据清理完成",
                "cleaned_records": 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

if __name__ == "__main__":
    import asyncio
    script = CleanOldDataScript()
    result = asyncio.run(script.run())
    print(result)
