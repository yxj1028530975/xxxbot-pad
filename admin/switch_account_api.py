"""
切换账号API模块
提供切换微信账号的API路由和功能
"""

import os
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from loguru import logger

# 创建路由器
router = APIRouter(prefix="/api", tags=["switch_account"])

# 认证检查函数（将在注册路由时设置）
check_auth = None

# 更新机器人状态的函数（将在注册路由时设置）
update_bot_status = None

@router.post("/switch_account", response_class=JSONResponse)
async def api_switch_account(request: Request):
    """删除 robot_stat.json 文件以切换微信账号"""
    # 检查认证状态
    try:
        username = await check_auth(request)
        if not username:
            logger.error("切换账号失败：未认证")
            return JSONResponse(status_code=401, content={"success": False, "error": "未认证"})

        # 获取当前目录
        current_dir = Path(__file__).parent

        # 获取 robot_stat.json 文件路径
        robot_stat_path = current_dir.parent / "resource" / "robot_stat.json"
        
        logger.info(f"尝试删除 robot_stat.json 文件: {robot_stat_path}")

        # 检查文件是否存在
        if robot_stat_path.exists():
            try:
                # 删除文件
                os.remove(robot_stat_path)
                logger.info(f"成功删除 robot_stat.json 文件: {robot_stat_path}")

                # 更新状态文件
                if update_bot_status:
                    update_bot_status("offline", "已切换账号，等待重新登录")
                else:
                    logger.warning("update_bot_status 函数未设置，无法更新机器人状态")

                return JSONResponse(content={
                    "success": True,
                    "message": "成功删除登录信息，请重新登录"
                })
            except Exception as e:
                logger.error(f"删除 robot_stat.json 文件失败: {e}")
                return JSONResponse(content={
                    "success": False,
                    "error": f"删除登录信息失败: {str(e)}"
                })
        else:
            # 文件不存在，也返回成功
            logger.info(f"robot_stat.json 文件不存在: {robot_stat_path}")
            return JSONResponse(content={
                "success": True,
                "message": "登录信息文件不存在，可以直接登录"
            })

    except Exception as e:
        logger.error(f"切换账号失败: {str(e)}")
        return JSONResponse(content={"success": False, "error": str(e)})

def register_switch_account_routes(app, auth_func, status_update_func=None):
    """
    注册切换账号相关路由

    Args:
        app: FastAPI应用实例
        auth_func: 认证检查函数
        status_update_func: 更新机器人状态的函数
    """
    global check_auth, update_bot_status
    check_auth = auth_func
    update_bot_status = status_update_func

    # 注册路由
    app.include_router(router)
    
    logger.info("切换账号API路由注册成功")
