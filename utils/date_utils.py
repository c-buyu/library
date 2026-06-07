# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from config import SYSTEM_CONFIG

def get_current_date():
    """获取系统当前日期（支持手动调整）"""
    if SYSTEM_CONFIG['MANUAL_DATE']:
        return datetime.strptime(SYSTEM_CONFIG['MANUAL_DATE'], '%Y-%m-%d').date()
    return datetime.now().date()

def add_days(date, days):
    """日期加法（统一使用）"""
    return date + timedelta(days=days)

def diff_days(date1, date2):
    """计算两个日期的天数差（date1 - date2）"""
    return (date1 - date2).days