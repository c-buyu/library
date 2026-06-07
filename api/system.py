# -*- coding: utf-8 -*-
from flask import Blueprint, request
from utils.response import success, error
from config import SYSTEM_CONFIG
from datetime import datetime

system_bp = Blueprint('system', __name__)

# 设置系统日期（仅管理员可用）
@system_bp.route('/set_date', methods=['POST'])
def set_system_date():
    if not SYSTEM_CONFIG['ENABLE_MANUAL_DATE']:
        return error("手动调整日期功能已禁用")
    
    data = request.json
    date_str = data.get('date')
    
    if not date_str:
        return error("日期不能为空")
    
    try:
        # 验证日期格式
        datetime.strptime(date_str, '%Y-%m-%d')
        SYSTEM_CONFIG['MANUAL_DATE'] = date_str
        return success(msg=f"系统日期已设置为：{date_str}")
    except ValueError:
        return error("日期格式错误，请使用YYYY-MM-DD格式")

# 重置为系统真实日期
@system_bp.route('/reset_date', methods=['POST'])
def reset_system_date():
    SYSTEM_CONFIG['MANUAL_DATE'] = None
    return success(msg="系统日期已重置为真实日期")

# 获取当前系统日期
@system_bp.route('/current_date', methods=['GET'])
def get_system_date():
    from utils.date_utils import get_current_date
    current_date = get_current_date()
    return success({
        "current_date": current_date.strftime('%Y-%m-%d'),
        "is_manual": SYSTEM_CONFIG['MANUAL_DATE'] is not None
    })