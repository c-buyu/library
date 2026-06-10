# -*- coding: utf-8 -*-
from flask import Blueprint, request
from db.connection import get_db_conn
from utils.response import success, error
from config import BUSINESS_CONFIG
import hashlib

reader_bp = Blueprint('reader', __name__)

# 查询所有读者（新增：black字段）
@reader_bp.route('/list', methods=['GET'])
def get_reader_list():
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, username, name, gender, reader_type, 
                   max_borrow_num, borrow_days, black, create_time 
            FROM users WHERE role='读者'
        """)
        readers = cur.fetchall()
        return success(readers)
    finally:
        cur.close()
        conn.close()

# 新增读者（新增：black字段）
@reader_bp.route('/add', methods=['POST'])
def add_reader():
    data = request.json
    username = data.get('username')
    password = data.get('password', '123456')  # 默认密码123456
    name = data.get('name')
    black = data.get('black', 0)  # 新增：黑名单字段
    gender = data.get('gender')
    reader_type = data.get('reader_type')
    max_borrow_num = data.get('max_borrow_num', BUSINESS_CONFIG['DEFAULT_MAX_BORROW_NUM'])
    borrow_days = data.get('borrow_days', BUSINESS_CONFIG['DEFAULT_BORROW_DAYS'])
    
    if not all([username, name]):
        return error("账号、姓名不能为空")
    
    md5_pwd = hashlib.md5(password.encode()).hexdigest()
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            return error("读者账号已存在")
        
        cur.execute("""
            INSERT INTO users(username, password, name, role, gender, reader_type,
                              max_borrow_num, borrow_days, black)
            VALUES (%s, %s, %s, '读者', %s, %s, %s, %s, %s)
        """, (username, md5_pwd, name, gender, reader_type,
              max_borrow_num, borrow_days, black))
        conn.commit()
        return success(msg="读者添加成功")
    except Exception as e:
        conn.rollback()
        return error(f"添加失败：{str(e)}")
    finally:
        cur.close()
        conn.close()

# 修改读者信息（新增：black字段）
@reader_bp.route('/update', methods=['PUT'])
def update_reader():
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return error("读者ID不能为空")
    
    update_fields = []
    params = []
    # 新增：black字段
    for field in ['name', 'gender', 'reader_type', 'max_borrow_num', 'borrow_days', 'black']:
        if field in data:
            update_fields.append(f"{field}=%s")
            params.append(data[field])
    
    if not update_fields:
        return error("没有要更新的字段")
    
    params.append(user_id)
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET {','.join(update_fields)} WHERE user_id=%s AND role='读者'", params)
        conn.commit()
        return success(msg="读者信息更新成功")
    except Exception as e:
        conn.rollback()
        return error(f"更新失败：{str(e)}")
    finally:
        cur.close()
        conn.close()

# 删除读者（逻辑不变）
@reader_bp.route('/delete', methods=['DELETE'])
def delete_reader():
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return error("读者ID不能为空")
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM borrows WHERE user_id=%s AND status='未还'", (user_id,))
        if cur.fetchone():
            return error("该读者有未还书籍，无法删除")
        
        cur.execute("DELETE FROM users WHERE user_id=%s AND role='读者'", (user_id,))
        conn.commit()
        return success(msg="读者删除成功")
    except Exception as e:
        conn.rollback()
        return error(f"删除失败：{str(e)}")
    finally:
        cur.close()
        conn.close()

# 多条件查询读者（新增：black字段）
@reader_bp.route('/search', methods=['GET'])
def search_reader():
    name = request.args.get('name', '')
    reader_type = request.args.get('reader_type', '')
    black = request.args.get('black')  # 新增：黑名单筛选
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        sql = "SELECT user_id, username, name, gender, reader_type, black FROM users WHERE role='读者'"
        params = []
        
        if name:
            sql += " AND name LIKE %s"
            params.append(f"%{name}%")
        if reader_type:
            sql += " AND reader_type=%s"
            params.append(reader_type)
        if black is not None:
            sql += " AND black=%s"
            params.append(black)
        
        cur.execute(sql, params)
        readers = cur.fetchall()
        return success(readers)
    finally:
        cur.close()
        conn.close()
