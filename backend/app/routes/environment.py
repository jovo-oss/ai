from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.services.time_awareness_service import time_awareness_service
from app.services.weather_awareness_service import weather_awareness_service
from app.models.database import SessionLocal, User

router = APIRouter(prefix="/api/environment", tags=["环境感知"])


class CityUpdate(BaseModel):
    """城市更新请求"""
    user_id: int
    city: str


@router.get("/time")
async def get_time_info():
    """获取当前时间信息"""
    return time_awareness_service.get_current_time_info()


@router.get("/greeting")
async def get_greeting(character_name: Optional[str] = None):
    """获取当前时段的问候语"""
    greeting = time_awareness_service.get_greeting(character_name)
    care_tip = time_awareness_service.get_care_tip()
    
    return {
        "greeting": greeting,
        "care_tip": care_tip,
        "is_sleep_time": time_awareness_service.is_sleep_time(),
        "meal_time": time_awareness_service.is_meal_time()
    }


@router.get("/weather")
async def get_weather(city: str = "北京"):
    """获取指定城市的天气信息"""
    return await weather_awareness_service.get_weather(city)


@router.get("/user-weather")
async def get_user_weather(user_id: int):
    """获取用户所在城市的天气"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "message": "用户不存在",
                "weather": None
            }
        
        # 获取用户设置的城市
        preferences = user.preferences or {}
        city = preferences.get("city", "北京")
        
        # 获取天气
        return await weather_awareness_service.get_weather(city)
    finally:
        db.close()


@router.post("/update-city")
async def update_city(data: CityUpdate):
    """更新用户所在城市"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == data.user_id).first()
        if not user:
            return {
                "success": False,
                "message": "用户不存在"
            }
        
        # 更新用户偏好
        preferences = user.preferences or {}
        preferences["city"] = data.city
        user.preferences = preferences
        
        db.commit()
        
        return {
            "success": True,
            "message": "城市设置已更新",
            "city": data.city
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"更新失败：{str(e)}"
        }
    finally:
        db.close()


@router.get("/user-city")
async def get_user_city(user_id: int):
    """获取用户所在城市"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "message": "用户不存在",
                "city": "北京"
            }
        
        preferences = user.preferences or {}
        city = preferences.get("city", "北京")
        
        return {
            "success": True,
            "city": city
        }
    finally:
        db.close()


@router.get("/full-info")
async def get_full_environment_info(user_id: int):
    """获取完整的环境信息（时间+天气+问候）"""
    db = SessionLocal()
    try:
        # 获取时间信息
        time_info = time_awareness_service.get_current_time_info()
        greeting_info = time_awareness_service.get_greeting()
        care_tip = time_awareness_service.get_care_tip()
        
        # 获取用户城市
        user = db.query(User).filter(User.id == user_id).first()
        city = "北京"
        if user:
            preferences = user.preferences or {}
            city = preferences.get("city", "北京")
        
        # 获取天气
        weather_result = await weather_awareness_service.get_weather(city)
        weather_info = weather_result.get("weather") if weather_result.get("success") else None
        
        # 生成天气问候
        weather_greeting = ""
        if weather_info:
            weather_greeting = weather_awareness_service.get_weather_greeting(weather_info)
        
        return {
            "success": True,
            "time": time_info,
            "greeting": greeting_info,
            "care_tip": care_tip,
            "weather": weather_info,
            "weather_greeting": weather_greeting,
            "city": city
        }
    finally:
        db.close()
