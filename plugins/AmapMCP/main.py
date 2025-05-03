import json
import os
import tomllib
import aiohttp
import asyncio
import uuid
from loguru import logger
import sseclient

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase

class AmapMCPPlugin(PluginBase):
    description = "高德地图MCP服务插件"
    author = "Claude"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        # 获取配置文件路径
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        
        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
                
            # 读取基本配置
            basic_config = config.get("basic", {})
            self.enable = basic_config.get("enable", False)
            
            # 读取高德地图配置
            amap_config = config.get("amap", {})
            self.api_key = amap_config.get("api_key", "")
            self.sse_url = amap_config.get("sse_url", "https://mcp.amap.com/sse")
            self.timeout = amap_config.get("timeout", 10)
            self.debug = amap_config.get("debug", False)

            if not self.api_key:
                logger.warning("高德地图API密钥未配置，AmapMCP插件将无法正常工作")
                self.enable = False

        except Exception as e:
            logger.error(f"加载AmapMCP配置文件失败: {str(e)}")
            self.enable = False
        
        # 初始化SSE客户端会话
        self.session = None
        self.current_requests = {}

    async def async_init(self):
        if self.enable:
            self.session = aiohttp.ClientSession()
            logger.info("AmapMCP插件初始化完成")

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def send_sse_request(self, function_call, arguments):
        """发送SSE请求并获取响应"""
        if not self.enable or not self.session:
            return {"error": "插件未启用或会话未初始化"}

        request_id = str(uuid.uuid4())
        url = f"{self.sse_url}?key={self.api_key}"
        
        if self.debug:
            logger.debug(f"SSE请求 {request_id}: {function_call} - {arguments}")

        payload = {
            "request_id": request_id,
            "function_call": function_call,
            "arguments": arguments
        }

        result_future = asyncio.Future()
        self.current_requests[request_id] = result_future

        try:
            async with self.session.post(url, json=payload, timeout=self.timeout) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"SSE请求失败: {response.status} - {error_text}")
                    return {"error": f"请求失败: {response.status}", "details": error_text}
                
                # 处理SSE响应
                client = sseclient.SSEClient(response.content)
                async for event in client.events():
                    if event.event == "function_response":
                        data = json.loads(event.data)
                        if data.get("request_id") == request_id:
                            if self.debug:
                                logger.debug(f"SSE响应 {request_id}: {data}")
                            return data.get("response", {})
        except asyncio.TimeoutError:
            logger.error(f"SSE请求超时: {request_id}")
            return {"error": "请求超时"}
        except Exception as e:
            logger.error(f"SSE请求异常: {str(e)}")
            return {"error": f"请求异常: {str(e)}"}
        finally:
            if request_id in self.current_requests:
                del self.current_requests[request_id]

    # 接口封装 - 地理编码
    async def geocode(self, address, city=None):
        """将地址转换为经纬度坐标"""
        arguments = {"address": address}
        if city:
            arguments["city"] = city
        return await self.send_sse_request("geocode", arguments)

    # 接口封装 - 逆地理编码
    async def regeocode(self, location):
        """将经纬度坐标转换为地址"""
        return await self.send_sse_request("regeocode", {"location": location})

    # 接口封装 - IP定位
    async def ip_location(self, ip):
        """根据IP地址获取位置信息"""
        return await self.send_sse_request("ip", {"ip": ip})

    # 接口封装 - 天气查询
    async def weather(self, city):
        """查询指定城市的天气情况"""
        return await self.send_sse_request("weather", {"city": city})

    # 接口封装 - 骑行路径规划
    async def riding(self, origin, destination):
        """规划骑行路线"""
        return await self.send_sse_request("riding", {
            "origin": origin,
            "destination": destination
        })

    # 接口封装 - 步行路径规划
    async def walking(self, origin, destination):
        """规划步行路线"""
        return await self.send_sse_request("walking", {
            "origin": origin,
            "destination": destination
        })

    # 接口封装 - 驾车路径规划
    async def driving(self, origin, destination):
        """规划驾车路线"""
        return await self.send_sse_request("driving", {
            "origin": origin,
            "destination": destination
        })

    # 接口封装 - 公交路径规划
    async def transit(self, origin, destination, city=None, cityd=None):
        """规划公交路线"""
        arguments = {
            "origin": origin,
            "destination": destination
        }
        if city:
            arguments["city"] = city
        if cityd:
            arguments["cityd"] = cityd
        return await self.send_sse_request("transit", arguments)

    # 接口封装 - 距离测量
    async def distance(self, origin, destination):
        """计算两点之间的距离"""
        return await self.send_sse_request("distance", {
            "origin": origin,
            "destination": destination
        })

    # 接口封装 - 关键词搜索
    async def search(self, keywords, city=None):
        """搜索兴趣点"""
        arguments = {"keywords": keywords}
        if city:
            arguments["city"] = city
        return await self.send_sse_request("search", arguments)

    # 接口封装 - 周边搜索
    async def around(self, keywords, location, radius=None):
        """搜索周边兴趣点"""
        arguments = {
            "keywords": keywords,
            "location": location
        }
        if radius:
            arguments["radius"] = radius
        return await self.send_sse_request("around", arguments)

    # 接口封装 - 详情搜索
    async def detail(self, id):
        """获取兴趣点详情"""
        return await self.send_sse_request("detail", {"id": id})

    @on_text_message(priority=80)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        """处理文本消息中的地图查询指令"""
        if not self.enable:
            return

        text = message.get("text", "").strip()
        sender = message.get("sender", {}).get("wxid", "")
        room_id = message.get("room_wxid", "")

        # 示例指令: 天气 北京
        if text.startswith("天气 "):
            city = text[3:].strip()
            if city:
                result = await self.weather(city)
                if "error" in result:
                    await bot.send_text(room_id or sender, f"获取天气信息失败: {result['error']}")
                else:
                    forecasts = result.get("forecasts", [])
                    if forecasts:
                        weather_info = forecasts[0]
                        response = f"{city}天气:\n"
                        response += f"日期: {weather_info.get('date', '未知')}\n"
                        response += f"白天: {weather_info.get('dayweather', '未知')}, {weather_info.get('daytemp', '未知')}°C\n"
                        response += f"夜间: {weather_info.get('nightweather', '未知')}, {weather_info.get('nighttemp', '未知')}°C\n"
                        response += f"风向: {weather_info.get('daywind', '未知')}\n"
                        response += f"风力: {weather_info.get('daypower', '未知')}"
                        await bot.send_text(room_id or sender, response)
                    else:
                        await bot.send_text(room_id or sender, f"未找到{city}的天气信息")

        # 示例指令: 搜索 餐厅 北京
        elif text.startswith("搜索 "):
            parts = text[3:].strip().split(" ", 1)
            if len(parts) == 2:
                keywords, city = parts
                result = await self.search(keywords, city)
                if "error" in result:
                    await bot.send_text(room_id or sender, f"搜索失败: {result['error']}")
                else:
                    pois = result.get("pois", [])
                    if pois:
                        response = f"在{city}搜索\"{keywords}\"的结果:\n"
                        for i, poi in enumerate(pois[:5], 1):
                            response += f"{i}. {poi.get('name', '未知')}\n"
                            response += f"   地址: {poi.get('address', '未知')}\n"
                        await bot.send_text(room_id or sender, response)
                    else:
                        await bot.send_text(room_id or sender, f"未找到与\"{keywords}\"相关的地点")
            else:
                await bot.send_text(room_id or sender, "搜索格式错误，请使用'搜索 关键词 城市'的格式")

        # 添加更多指令处理...

    # 在插件销毁时关闭会话
    def __del__(self):
        if self.session and not self.session.closed:
            asyncio.create_task(self.close()) 