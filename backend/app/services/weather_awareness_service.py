import os
import httpx
from typing import Dict, Any, Optional
from datetime import datetime


class WeatherAwarenessService:
    """天气感知服务 - 让角色知道天气情况并给出关怀建议"""
    
    # 天气代码映射（WMO Weather interpretation codes）
    WEATHER_CODES = {
        0: {"desc": "晴朗", "icon": "☀️", "care": "天气真好，心情也会变好呢~"},
        1: {"desc": " mostly clear", "icon": "🌤️", "care": "天气不错，适合出去走走~"},
        2: {"desc": "多云", "icon": "⛅", "care": "多云的天气，不冷不热刚刚好~"},
        3: {"desc": "阴天", "icon": "☁️", "care": "阴天也没关系，有我在呢~"},
        45: {"desc": "雾", "icon": "🌫️", "care": "今天有雾，出门要注意安全哦~"},
        48: {"desc": "雾凇", "icon": "🌫️", "care": "雾天路滑，小心慢行~"},
        51: {"desc": "小毛毛雨", "icon": "🌦️", "care": "下小雨了，记得带伞哦~"},
        53: {"desc": "中毛毛雨", "icon": "️", "care": "雨不大，但还是带把伞吧~"},
        55: {"desc": "大毛毛雨", "icon": "🌧️", "care": "雨有点大，出门一定要带伞！"},
        61: {"desc": "小雨", "icon": "🌧️", "care": "下雨了，记得带伞，路上小心~"},
        63: {"desc": "中雨", "icon": "🌧️", "care": "雨不小呢，出门记得带伞，注意安全~"},
        65: {"desc": "大雨", "icon": "🌧️", "care": "雨很大！尽量不要出门，如果必须出门一定要注意安全~"},
        71: {"desc": "小雪", "icon": "🌨️", "care": "下雪了，好浪漫呀~ 不过要注意保暖哦~"},
        73: {"desc": "中雪", "icon": "🌨️", "care": "雪不小呢，出门要注意防滑~"},
        75: {"desc": "大雪", "icon": "❄️", "care": "大雪纷飞，尽量别出门，在家暖暖和和的~"},
        77: {"desc": "雪粒", "icon": "❄️", "care": "下雪了，记得多穿点衣服~"},
        80: {"desc": "小阵雨", "icon": "️", "care": "阵雨天气，带把伞以防万一~"},
        81: {"desc": "中阵雨", "icon": "🌧️", "care": "有阵雨，出门记得带伞~"},
        82: {"desc": "大阵雨", "icon": "⛈️", "care": "阵雨很大，注意安全~"},
        85: {"desc": "小阵雪", "icon": "🌨️", "care": "阵雪天气，注意保暖~"},
        86: {"desc": "大阵雪", "icon": "❄️", "care": "雪很大，尽量待在室内~"},
        95: {"desc": "雷暴", "icon": "️", "care": "有雷暴！尽量待在室内，注意安全~"},
        96: {"desc": "雷暴伴冰雹", "icon": "⛈️", "care": "雷暴天气，千万不要出门！"},
        99: {"desc": "强雷暴伴冰雹", "icon": "⛈️", "care": "恶劣天气！一定要待在安全的地方~"}
    }
    
    # 关怀提示模板
    CARE_TEMPLATES = {
        "hot": "今天好热呀，记得多喝水，注意防暑降温~",
        "cold": "今天好冷，多穿点衣服，别感冒了~",
        "rain": "下雨了，出门记得带伞，路上小心~",
        "snow": "下雪了，注意保暖，路上小心滑~",
        "windy": "今天风好大，出门要注意安全~",
        "fog": "有雾呢，出门要注意交通安全~",
        "nice": "天气真好，心情也会变好呢~"
    }
    
    def __init__(self):
        # 使用免费的Open-Meteo API（不需要API密钥）
        self.api_url = "https://api.open-meteo.com/v1/forecast"
    
    async def get_weather(self, city: str = "北京") -> Dict[str, Any]:
        """获取指定城市的天气信息"""
        try:
            # 首先获取城市的经纬度
            coords = await self._get_city_coordinates(city)
            if not coords:
                return {
                    "success": False,
                    "message": f"无法找到城市：{city}",
                    "weather": None
                }
            
            # 获取天气数据
            weather_data = await self._fetch_weather_data(coords["latitude"], coords["longitude"])
            
            if not weather_data:
                return {
                    "success": False,
                    "message": "获取天气数据失败",
                    "weather": None
                }
            
            # 解析天气数据
            current = weather_data.get("current", {})
            daily = weather_data.get("daily", {})
            
            weather_code = current.get("weather_code", 0)
            weather_info = self.WEATHER_CODES.get(weather_code, self.WEATHER_CODES[0])
            
            temperature = current.get("temperature_2m", 0)
            feels_like = current.get("apparent_temperature", temperature)
            humidity = current.get("relative_humidity_2m", 50)
            wind_speed = current.get("wind_speed_10m", 0)
            
            # 获取今日最高最低温度
            temp_max = daily.get("temperature_2m_max", [temperature])[0] if daily.get("temperature_2m_max") else temperature
            temp_min = daily.get("temperature_2m_min", [temperature])[0] if daily.get("temperature_2m_min") else temperature
            
            # 生成关怀提示
            care_tip = self._generate_care_tip(weather_code, temperature, wind_speed)
            
            return {
                "success": True,
                "weather": {
                    "city": city,
                    "temperature": temperature,
                    "feels_like": feels_like,
                    "temp_max": temp_max,
                    "temp_min": temp_min,
                    "humidity": humidity,
                    "wind_speed": wind_speed,
                    "weather_code": weather_code,
                    "weather_desc": weather_info["desc"],
                    "weather_icon": weather_info["icon"],
                    "care_tip": care_tip,
                    "update_time": datetime.now().strftime("%H:%M")
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"获取天气失败：{str(e)}",
                "weather": None
            }
    
    async def _get_city_coordinates(self, city: str) -> Optional[Dict[str, float]]:
        """获取城市经纬度"""
        # 常用城市坐标（可以扩展）
        city_coords = {
            "北京": {"latitude": 39.9042, "longitude": 116.4074},
            "上海": {"latitude": 31.2304, "longitude": 121.4737},
            "广州": {"latitude": 23.1291, "longitude": 113.2644},
            "深圳": {"latitude": 22.5431, "longitude": 114.0579},
            "杭州": {"latitude": 30.2741, "longitude": 120.1551},
            "成都": {"latitude": 30.5728, "longitude": 104.0668},
            "武汉": {"latitude": 30.5928, "longitude": 114.3055},
            "南京": {"latitude": 32.0603, "longitude": 118.7969},
            "重庆": {"latitude": 29.5630, "longitude": 106.5516},
            "西安": {"latitude": 34.3416, "longitude": 108.9398},
            "天津": {"latitude": 39.3434, "longitude": 117.3616},
            "苏州": {"latitude": 31.2989, "longitude": 120.5853},
            "长沙": {"latitude": 28.2282, "longitude": 112.9388},
            "郑州": {"latitude": 34.7466, "longitude": 113.6253},
            "青岛": {"latitude": 36.0671, "longitude": 120.3826},
            "大连": {"latitude": 38.9140, "longitude": 121.6147},
            "厦门": {"latitude": 24.4798, "longitude": 118.0894},
            "昆明": {"latitude": 25.0389, "longitude": 102.7183},
        }
        
        # 先查找本地缓存
        if city in city_coords:
            return city_coords[city]
        
        # 如果本地没有，尝试通过API获取
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": city, "count": 1, "language": "zh"}
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("results"):
                        result = data["results"][0]
                        return {
                            "latitude": result["latitude"],
                            "longitude": result["longitude"]
                        }
        except Exception:
            pass
        
        return None
    
    async def _fetch_weather_data(self, latitude: float, longitude: float) -> Optional[Dict]:
        """获取天气数据"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.api_url,
                    params={
                        "latitude": latitude,
                        "longitude": longitude,
                        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                        "daily": "temperature_2m_max,temperature_2m_min",
                        "timezone": "auto",
                        "forecast_days": 1
                    }
                )
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass
        
        return None
    
    def _generate_care_tip(self, weather_code: int, temperature: float, wind_speed: float) -> str:
        """根据天气生成关怀提示"""
        # 温度关怀
        if temperature >= 35:
            return self.CARE_TEMPLATES["hot"]
        elif temperature <= 5:
            return self.CARE_TEMPLATES["cold"]
        
        # 天气关怀
        if weather_code in [61, 63, 65, 80, 81, 82]:  # 雨天
            return self.CARE_TEMPLATES["rain"]
        elif weather_code in [71, 73, 75, 77, 85, 86]:  # 雪天
            return self.CARE_TEMPLATES["snow"]
        elif wind_speed > 20:  # 大风
            return self.CARE_TEMPLATES["windy"]
        elif weather_code in [45, 48]:  # 雾天
            return self.CARE_TEMPLATES["fog"]
        
        # 默认关怀
        return self.CARE_TEMPLATES["nice"]
    
    def get_weather_greeting(self, weather_info: Dict) -> str:
        """根据天气生成问候语"""
        if not weather_info:
            return ""
        
        weather_desc = weather_info.get("weather_desc", "")
        care_tip = weather_info.get("care_tip", "")
        temperature = weather_info.get("temperature", 0)
        
        greetings = []
        
        # 根据天气添加问候
        if weather_desc in ["晴朗", " mostly clear"]:
            greetings.append("今天天气真好呀~")
        elif "雨" in weather_desc:
            greetings.append("今天下雨了呢~")
        elif "雪" in weather_desc:
            greetings.append("今天下雪了~")
        elif "多云" in weather_desc or "阴" in weather_desc:
            greetings.append("今天是多云天气~")
        
        # 添加温度提示
        if temperature >= 30:
            greetings.append(f"气温有{temperature}度，好热呀~")
        elif temperature <= 10:
            greetings.append(f"气温只有{temperature}度，好冷呀~")
        
        # 添加关怀
        if care_tip:
            greetings.append(care_tip)
        
        return " ".join(greetings) if greetings else ""


# 全局天气感知服务实例
weather_awareness_service = WeatherAwarenessService()
