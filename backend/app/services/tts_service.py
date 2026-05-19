from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
from typing import Optional
import base64

load_dotenv()

class TTSService:
    """语音合成服务 - 将文本转换为语音"""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("TTS_API_KEY", os.getenv("OPENAI_API_KEY"))
        )
        self.model = os.getenv("TTS_MODEL", "tts-1")
        self.voice = os.getenv("TTS_VOICE", "nova")
    
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
