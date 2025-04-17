"""
数据库模块
包含所有与数据库相关的功能
"""
from loguru import logger

# 导出联系人数据库模块
from .contacts_db import (
    get_contacts_from_db,
    save_contacts_to_db,
    update_contact_in_db,
    get_contact_from_db,
    get_contacts_count,
    delete_contact_from_db,
    init_db as init_contacts_db
)

def init_database():
    """初始化所有数据库"""
    logger.info("初始化数据库...")
    
    # 初始化联系人数据库
    init_contacts_db()
    
    # 未来可以在这里添加其他数据库的初始化
    
    logger.success("数据库初始化完成")

# 当模块被导入时自动初始化所有数据库
init_database()
