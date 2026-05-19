from abc import ABC, abstractmethod
from typing import Any, Dict
import subprocess
import asyncio

class BaseScript(ABC):
    """脚本基类 - 用于执行一次性或定时任务"""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.description = ""
    
    @abstractmethod
    async def run(self, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行脚本
        :param args: 脚本参数
        :return: 执行结果
        """
        pass

class ScriptRunner:
    """脚本运行器"""
    
    @staticmethod
    async def run_python_script(script_path: str, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行Python脚本文件"""
        try:
            cmd = ["python", script_path]
            if args:
                for key, value in args.items():
                    cmd.extend([f"--{key}", str(value)])
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "returncode": process.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def run_external_script(script_path: str, interpreter: str = None) -> Dict[str, Any]:
        """运行外部脚本（bash、powershell等）"""
        try:
            if interpreter:
                cmd = [interpreter, script_path]
            else:
                cmd = ["python", script_path]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode(),
                "stderr": stderr.decode()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
