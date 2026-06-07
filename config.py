# -*- coding: utf-8 -*-
import pymysql.cursors

# 数据库配置
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",  
    "database": "library",
    "charset": "utf8mb4",  
    "cursorclass": pymysql.cursors.DictCursor,  # 返回字典格式结果
    "autocommit": False  # 手动控制事务，保证数据一致性
}

# Flask 核心配置
FLASK_CONFIG = {
    "DEBUG": True,  # 开发模式开启debug，生产环境改为False
    "JSON_AS_ASCII": False,  # 强制JSON响应使用UTF-8
    "SECRET_KEY": "library_management_system_2024",  # 用于session加密，随便写一串字符串
    "JSON_SORT_KEYS": False  # 保持JSON响应字段顺序，不自动排序
}

# 全局业务常量
BUSINESS_CONFIG = {
    "DEFAULT_MAX_BORROW_NUM": 5,  # 默认最大借书数量
    "DEFAULT_BORROW_DAYS": 30,  # 默认借书期限（天）
    "OVERDUE_FEE_PER_DAY": 0.1,  # 超期每日罚款（元）
    "MAX_RENEW_TIMES": 1,  # 单本书最大续借次数
    "RENEW_DAYS": 30,  # 每次续借天数
    "REMIND_DAYS_BEFORE_DUE": 1  # 到期前1天提醒
}

# 系统配置
SYSTEM_CONFIG = {
    "MANUAL_DATE": None,  # 手动设置日期，格式：'YYYY-MM-DD'，None=使用系统真实日期
    "ENABLE_MANUAL_DATE": True,  # 生产环境改为False禁用此功能
    "ENABLE_AUTO_REMIND": True  # 开启自动到期提醒
}