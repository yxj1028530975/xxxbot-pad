"""
处理DOW框架插件的模块
"""
import os
import sys
import logging
import json
from pathlib import Path

# 设置日志
logger = logging.getLogger("dow_plugins")

def get_dow_plugins():
    """获取DOW框架的插件列表"""
    # 启用调试模式
    debug_mode = os.environ.get("DEBUG_DOW_PLUGINS", "False").lower() in ("true", "1", "yes")
    
    try:
        logger.info("开始获取DOW框架插件...")
        
        # 获取当前脚本目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # DOW框架路径
        dow_path = os.path.join(os.path.dirname(script_dir), "dow")
        dow_abs_path = os.path.abspath(dow_path)
        
        logger.info(f"DOW框架路径: {dow_abs_path}")
        
        # 检查DOW框架是否存在
        if not os.path.exists(dow_abs_path):
            logger.warning(f"DOW框架目录不存在: {dow_abs_path}")
            return generate_mock_plugins() if debug_mode else []
        
        # 插件目录路径 - 改为 dow/plugins 目录
        plugins_dir = os.path.join(dow_path, "plugins")
        
        logger.info(f"DOW插件目录路径: {plugins_dir}")
        
        # 检查插件目录是否存在
        if not os.path.exists(plugins_dir):
            logger.warning(f"DOW插件目录不存在: {plugins_dir}")
            return generate_mock_plugins() if debug_mode else []
        
        # 尝试获取插件管理器实例（用于找正在使用的插件）
        plugin_manager = None
        try:
            if dow_abs_path not in sys.path:
                sys.path.insert(0, dow_abs_path)
                logger.info(f"已将DOW框架路径添加到sys.path: {dow_abs_path}")
            
            from dow.plugins.plugin_manager import PluginManager
            plugin_manager = PluginManager()
            logger.info("成功获取DOW框架插件管理器实例")
        except Exception as e:
            logger.warning(f"获取DOW插件管理器实例失败: {e}")
            plugin_manager = None
        
        # 直接扫描插件目录获取插件
        plugins_info = []
        plugin_id = 0
        
        for item_name in os.listdir(plugins_dir):
            item_path = os.path.join(plugins_dir, item_name)
            
            # 只处理目录或Python文件
            if os.path.isfile(item_path) and not item_path.endswith('.py'):
                continue
                
            # 如果是Python文件，判断它是否是插件文件
            if os.path.isfile(item_path) and item_path.endswith('.py'):
                if item_name == '__init__.py' or item_name == 'plugin_manager.py' or item_name == 'event.py':
                    continue
                    
                # 尝试从Python文件中提取插件信息
                plugin_info = {
                    "id": f"dow_plugin_{plugin_id}",
                    "name": os.path.splitext(item_name)[0],
                    "enabled": True,  # 默认设为启用
                    "description": "DOW框架插件",
                    "author": "DOW",
                    "version": "1.0.0",
                    "path": item_path,
                    "framework": "dow"
                }
                plugin_id += 1
                plugins_info.append(plugin_info)
                continue
            
            # 目录处理
            if not os.path.isdir(item_path):
                continue
                
            # 跳过非插件目录
            if item_name.startswith('__') or item_name == 'config':
                continue
            
            # 检查是否是插件目录（包含__init__.py文件或任何.py文件）
            init_file = os.path.join(item_path, "__init__.py")
            has_py_files = any(f.endswith('.py') for f in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, f)))
            config_file = os.path.join(item_path, "config.json")
            
            is_plugin = os.path.isfile(init_file) or has_py_files
            
            if not is_plugin:
                continue
            
            # 尝试从config.json获取插件信息
            plugin_info = {
                "id": f"dow_plugin_{plugin_id}",
                "name": item_name,
                "enabled": True,  # 默认设为启用，因为在DOW/plugins中的插件通常是启用的
                "description": "DOW框架插件",
                "author": "DOW",
                "version": "1.0.0",
                "path": item_path,
                "framework": "dow"
            }
            plugin_id += 1
            
            # 如果存在config.json，从中获取更多信息
            if os.path.isfile(config_file):
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        config_data = json.load(f)
                        
                    # 更新插件信息
                    if "name" in config_data:
                        plugin_info["name"] = config_data["name"]
                    if "description" in config_data:
                        plugin_info["description"] = config_data["description"]
                    if "author" in config_data:
                        plugin_info["author"] = config_data["author"]
                    if "version" in config_data:
                        plugin_info["version"] = config_data["version"]
                except Exception as e:
                    logger.warning(f"解析插件 {item_name} 的config.json文件失败: {e}")
            
            # 从插件管理器检查插件是否已启用
            if plugin_manager and hasattr(plugin_manager, "plugins"):
                # 检查是否在已加载的插件中
                for name, plugin in plugin_manager.plugins.items():
                    if getattr(plugin, 'name', '').lower() == item_name.lower():
                        plugin_info["enabled"] = getattr(plugin, 'enabled', True)
                        # 使用DOW插件管理器中的其他信息
                        plugin_info["description"] = getattr(plugin, 'desc', plugin_info["description"])
                        plugin_info["author"] = getattr(plugin, 'author', plugin_info["author"])
                        plugin_info["version"] = getattr(plugin, 'version', plugin_info["version"])
                        break
            
            plugins_info.append(plugin_info)
        
        logger.info(f"成功扫描到 {len(plugins_info)} 个DOW框架插件")
        
        # 如果没有找到插件但启用了调试模式，返回模拟数据
        if not plugins_info and debug_mode:
            logger.info("没有找到DOW框架插件，使用模拟数据")
            return generate_mock_plugins()
        
        return plugins_info
            
    except Exception as e:
        logger.error(f"获取DOW插件信息失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return generate_mock_plugins() if debug_mode else []

def generate_mock_plugins():
    """生成模拟的DOW框架插件数据（用于调试）"""
    logger.info("生成模拟的DOW框架插件数据")
    
    # 检查是否存在缓存的模拟数据
    mock_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_dow_plugins.json")
    
    if os.path.exists(mock_file):
        try:
            with open(mock_file, "r", encoding="utf-8") as f:
                mock_plugins = json.load(f)
                logger.info(f"从缓存加载了{len(mock_plugins)}个模拟DOW插件")
                return mock_plugins
        except Exception as e:
            logger.error(f"加载模拟插件数据失败: {e}")
    
    # 创建默认的模拟插件数据
    mock_plugins = [
        {
            "id": "DOWChatBot",
            "name": "DOW聊天机器人",
            "enabled": True,
            "description": "DOW框架下的聊天机器人插件",
            "author": "DOW团队",
            "version": "1.0.0",
            "path": "dow/plugins/chat_bot",
            "framework": "dow"
        },
        {
            "id": "DOWEventHandler",
            "name": "DOW事件处理器",
            "enabled": True,
            "description": "处理DOW框架的各种事件",
            "author": "DOW团队",
            "version": "1.1.0",
            "path": "dow/plugins/event_handler",
            "framework": "dow"
        },
        {
            "id": "DOWDataSync",
            "name": "DOW数据同步",
            "enabled": False,
            "description": "同步DOW框架的数据到云端",
            "author": "DOW团队",
            "version": "0.9.0",
            "path": "dow/plugins/data_sync",
            "framework": "dow"
        }
    ]
    
    # 保存模拟数据到缓存
    try:
        with open(mock_file, "w", encoding="utf-8") as f:
            json.dump(mock_plugins, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存{len(mock_plugins)}个模拟DOW插件到缓存")
    except Exception as e:
        logger.error(f"保存模拟插件数据失败: {e}")
    
    return mock_plugins

# 设置环境变量以启用调试模式（默认启用）
os.environ["DEBUG_DOW_PLUGINS"] = "True" 