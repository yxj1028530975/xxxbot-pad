"""
插件管理相关的API路由
"""
import os
import sys
import logging
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse

# 设置日志
logger = logging.getLogger("plugin_routes")

# 创建路由器
router = APIRouter()

def register_plugin_routes(app, check_auth_func):
    """
    注册插件管理相关的路由
    
    Args:
        app: FastAPI应用实例
        check_auth_func: 认证检查函数
    """
    # 导入DOW插件辅助模块
    try:
        from admin.dow_plugins import get_dow_plugins
        logger.info("成功导入DOW插件辅助模块")
    except ImportError:
        logger.error("导入DOW插件辅助模块失败")
        get_dow_plugins = lambda: []
    
    # 获取DOW框架插件列表
    @app.get("/api/dow_plugins", response_class=JSONResponse)
    async def api_dow_plugins_list(request: Request):
        # 检查认证状态
        username = await check_auth_func(request)
        if not username:
            return JSONResponse(status_code=401, content={"success": False, "error": "未认证"})

        try:
            # 获取插件列表
            plugins_info = get_dow_plugins()
            
            return {
                "success": True,
                "data": {
                    "plugins": plugins_info
                }
            }
        except Exception as e:
            logger.error(f"获取DOW插件信息失败: {str(e)}")
            return {"success": False, "error": f"获取DOW插件信息失败: {str(e)}"}
            
    # 获取所有框架的插件列表（合并原始框架和DOW框架的插件）
    @app.get("/api/all_plugins", response_class=JSONResponse)
    async def api_all_plugins_list(request: Request):
        # 检查认证状态
        username = await check_auth_func(request)
        if not username:
            return JSONResponse(status_code=401, content={"success": False, "error": "未认证"})
            
        try:
            # 获取原始框架插件
            from utils.plugin_manager import plugin_manager
            original_plugins = plugin_manager.get_plugin_info()
            
            # 确保返回的数据是可序列化的
            if not isinstance(original_plugins, list):
                original_plugins = []
                logger.error("plugin_manager.get_plugin_info()返回了非列表类型")
            
            # 添加框架标记
            for plugin in original_plugins:
                plugin["framework"] = "original"
                    
            # 获取DOW框架插件
            dow_plugins = get_dow_plugins()
            
            # 合并插件列表
            all_plugins = original_plugins + dow_plugins
            
            return {
                "success": True,
                "data": {
                    "plugins": all_plugins
                }
            }
        except Exception as e:
            logger.error(f"获取所有插件信息失败: {str(e)}")
            return {"success": False, "error": f"获取所有插件信息失败: {str(e)}"}
            
    logger.info("插件管理API路由注册成功")