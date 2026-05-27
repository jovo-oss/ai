from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
from typing import Optional
import base64
from app.services.tts_config_service import tts_config_service

load_dotenv()

class TTSService:
    """语音合成服务 - 将文本转换为语音"""
    
    def __init__(self):
        # 先尝试从数据库获取默认配置
        self.config = None
        self.user_id = 1  # 默认用户ID
        
        # 尝试从数据库加载配置
        try:
            config_result = tts_config_service.get_default_config(self.user_id)
            if config_result["success"]:
                self.config = config_result["config"]
                print(f"TTS服务：使用数据库配置 - {self.config['name']}")
        except Exception as e:
            print(f"TTS服务：数据库配置加载失败，使用.env配置 - {str(e)}")
        
        # 如果没有数据库配置，使用.env文件配置
        if not self.config:
            api_key = os.getenv("TTS_API_KEY", os.getenv("OPENAI_API_KEY"))
            if not api_key:
                raise ValueError("未找到TTS_API_KEY或OPENAI_API_KEY环境变量，请先配置API密钥")
            
            # 支持自定义API基础URL（用于国内OpenAI兼容服务）
            base_url = os.getenv("TTS_BASE_URL", os.getenv("OPENAI_BASE_URL"))
            
            client_kwargs = {
                "api_key": api_key,
                "timeout": 30.0
            }
            
            if base_url:
                client_kwargs["base_url"] = base_url
            
            self.client = AsyncOpenAI(**client_kwargs)
            self.model = os.getenv("TTS_MODEL", "tts-1")
            self.voice = os.getenv("TTS_VOICE", "nova")
            print("TTS服务：使用.env文件配置")
        else:
            # 使用数据库配置初始化客户端
            client_kwargs = {
                "api_key": self.config["api_key_full"],
                "timeout": 30.0
            }
            
            if self.config["base_url"]:
                client_kwargs["base_url"] = self.config["base_url"]
            
            self.client = AsyncOpenAI(**client_kwargs)
            self.model = self.config["tts_model"]
            self.voice = self.config["tts_voice"]
    
    async def reload_config(self):
        """重新加载配置（用于切换配置后）"""
        try:
            config_result = tts_config_service.get_default_config(self.user_id)
            if config_result["success"]:
                self.config = config_result["config"]
                
                # 重新初始化客户端
                client_kwargs = {
                    "api_key": self.config["api_key_full"],
                    "timeout": 30.0
                }
                
                if self.config["base_url"]:
                    client_kwargs["base_url"] = self.config["base_url"]
                
                self.client = AsyncOpenAI(**client_kwargs)
                self.model = self.config["tts_model"]
                self.voice = self.config["tts_voice"]
                print(f"TTS服务：配置已重新加载 - {self.config['name']}")
                return True
        except Exception as e:
            print(f"TTS服务：配置重新加载失败 - {str(e)}")
            return False
        return False
    
    async def text_to_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0
    ) -> bytes:
        """
        将文本转换为语音
        :param text: 要转换的文本
        :param voice: 语音类型 (alloy, echo, fable, onyx, nova, shimmer)
        :param speed: 语速 (0.25-4.0)
        :return: 音频数据（字节）
        """
        response = await self.client.audio.speech.create(
            model=self.model,
            voice=voice or self.voice,
            input=text,
            speed=speed
        )
        
        return response.content
    
    async def text_to_speech_base64(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0
    ) -> str:
        """
        将文本转换为base64编码的音频
        :param text: 要转换的文本
        :param voice: 语音类型
        :param speed: 语速
        :return: base64编码的音频字符串
        """
        audio_bytes = await self.text_to_speech(text, voice, speed)
        return base64.b64encode(audio_bytes).decode('utf-8')

tts_service = TTSService()
