# -*- coding: utf-8 -*-
from flask import Blueprint, request
import hashlib
from db.connection import get_db_conn
from utils.response import success, error
from config import BUSINESS_CONFIG

user_bp = Blueprint('user', __name__)

# 登录接口（新增：黑名单校验）
@user_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not all([username, password]):
        return error("账号密码不能为空")
    
    # MD5加密密码
    md5_pwd = hashlib.md5(password.encode()).hexdigest()
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, md5_pwd))
        user = cur.fetchone()
        
        if user:
            # 新增：黑名单校验
            if user['black'] == 1:
                return error("该账号已被禁用，请联系管理员")
            # 移除密码字段，不返回给前端
            user.pop('password')
            return success(user, "登录成功")
        else:
            return error("账号或密码错误")
    finally:
        cur.close()
        conn.close()

# 查询所有用户（新增：black字段）
@user_bp.route('/list', methods=['GET'])
def get_user_list():
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, username, role, name, gender, reader_type, 
                   max_borrow_num, borrow_days, black, create_time 
            FROM users
        """)
        users = cur.fetchall()
        return success(users)
    finally:
        cur.close()
        conn.close()

# 新增用户（新增：black字段默认值）
@user_bp.route('/add', methods=['POST'])
def add_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    name = data.get('name')
    role = data.get('role', '读者')
    black = data.get('black', 0)  # 新增：黑名单字段
    
    if not all([username, password, name]):
        return error("账号、密码、姓名不能为空")
    
    # MD5加密密码
    md5_pwd = hashlib.md5(password.encode()).hexdigest()
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        # 检查用户名是否已存在
        cur.execute("SELECT 1 FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            return error("用户名已存在")
        
        # 插入用户（新增：black字段）
        cur.execute("""
            INSERT INTO users(username, password, name, role, max_borrow_num, borrow_days, black)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (username, md5_pwd, name, role, 
              BUSINESS_CONFIG['DEFAULT_MAX_BORROW_NUM'], 
              BUSINESS_CONFIG['DEFAULT_BORROW_DAYS'],
              black))
        conn.commit()
        return success(msg="用户添加成功")
    except Exception as e:
        conn.rollback()
        return error(f"添加失败：{str(e)}")
    finally:
        cur.close()
        conn.close()

# 修改用户（新增：black字段更新）
@user_bp.route('/update', methods=['PUT'])
def update_user():
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return error("用户ID不能为空")
    
    # 构建更新字段（新增：black）
    update_fields = []
    params = []
    for field in ['name', 'gender', 'reader_type', 'max_borrow_num', 
                  'borrow_days', 'role', 'black']:
        if field in data:
            update_fields.append(f"{field}=%s")
            params.append(data[field])
    
    if not update_fields:
        return error("没有要更新的字段")
    
    params.append(user_id)
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET {','.join(update_fields)} WHERE user_id=%s", params)
        conn.commit()
        return success(msg="用户更新成功")
    except Exception as e:
        conn.rollback()
        return error(f"更新失败：{str(e)}")
    finally:
        cur.close()
        conn.close()

# 删除用户（逻辑不变，外键已改为RESTRICT）
@user_bp.route('/delete', methods=['DELETE'])
def delete_user():
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return error("用户ID不能为空")
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        # 检查用户是否有未还书籍
        cur.execute("SELECT 1 FROM borrows WHERE user_id=%s AND status='未还'", (user_id,))
        if cur.fetchone():
            return error("该用户有未还书籍，无法删除")
        
        cur.execute("DELETE FROM users WHERE user_id=%s", (user_id,))
        conn.commit()
        return success(msg="用户删除成功")
    except Exception as e:
        conn.rollback()
        return error(f"删除失败：{str(e)}")
    finally:
        cur.close()
        conn.close()