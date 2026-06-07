# -*- coding: utf-8 -*-
import pymysql
from config import DB_CONFIG

def get_db_conn():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)