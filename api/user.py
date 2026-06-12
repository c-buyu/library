# -*- coding: utf-8 -*-
import hashlib

from flask import Blueprint, request

from config import BUSINESS_CONFIG
from db.connection import get_db_conn
from utils.response import error, success

user_bp = Blueprint('user', __name__)


def _md5(password):
    return hashlib.md5(password.encode()).hexdigest()


def _is_admin(data):
    return data.get('operator_role') == '管理员' or request.args.get('operator_role') == '管理员'


def _change_password(user_id, old_password, new_password):
    if not all([user_id, old_password, new_password]):
        return error("用户ID、原密码、新密码不能为空")
    if len(new_password) < 6:
        return error("新密码长度不能少于6位")

    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE user_id=%s", (user_id,))
        user = cur.fetchone()
        if not user:
            return error("用户不存在")
        if user['password'] != _md5(old_password):
            return error("原密码错误")

        cur.execute("UPDATE users SET password=%s WHERE user_id=%s", (_md5(new_password), user_id))
        conn.commit()
        return success(msg="密码修改成功")
    except Exception as e:
        conn.rollback()
        return error(f"修改失败：{str(e)}")
    finally:
        cur.close()
        conn.close()


@user_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')

    if not all([username, password]):
        return error("账号密码不能为空")

    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, _md5(password))
        )
        user = cur.fetchone()

        if not user:
            return error("账号或密码错误")
        if user['black'] == 1:
            return error("该账号已被禁用，请联系管理员")

        user.pop('password')
        return success(user, "登录成功")
    finally:
        cur.close()
        conn.close()


@user_bp.route('/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    name = data.get('name')

    if not all([username, password, name]):
        return error("账号、密码、姓名不能为空")
    if len(password) < 6:
        return error("密码长度不能少于6位")

    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            return error("用户名已存在")

        cur.execute(
            """
            INSERT INTO users(username, password, name, role, gender, reader_type,
                              max_borrow_num, borrow_days, black)
            VALUES (%s, %s, %s, '读者', %s, %s, %s, %s, 0)
            """,
            (
                username, _md5(password), name, data.get('gender'), data.get('reader_type'),
                BUSINESS_CONFIG['DEFAULT_MAX_BORROW_NUM'],
                BUSINESS_CONFIG['DEFAULT_BORROW_DAYS']
            )
        )
        conn.commit()
        return success(msg="注册成功")
    except Exception as e:
        conn.rollback()
        return error(f"注册失败：{str(e)}")
    finally:
        cur.close()
        conn.close()


@user_bp.route('/list', methods=['GET'])
def get_user_list():
    operator_role = request.args.get('operator_role')
    operator_user_id = request.args.get('operator_user_id')

    conn = get_db_conn()
    try:
        cur = conn.cursor()
        if operator_role == '管理员':
            cur.execute(
                """
                SELECT user_id, username, role, name, gender, reader_type,
                       max_borrow_num, borrow_days, black, create_time
                FROM users
                """
            )
        else:
            if not operator_user_id:
                return error("缺少当前用户信息", code=403)
            cur.execute(
                """
                SELECT user_id, username, role, name, gender, reader_type,
                       max_borrow_num, borrow_days, black, create_time
                FROM users WHERE user_id=%s
                """,
                (operator_user_id,)
            )
        return success(cur.fetchall())
    finally:
        cur.close()
        conn.close()


@user_bp.route('/add', methods=['POST'])
def add_user():
    data = request.json or {}
    if not _is_admin(data):
        return error("只有管理员可以新增后台用户", code=403)

    username = data.get('username')
    password = data.get('password')
    name = data.get('name')
    role = data.get('role', '读者')
    black = data.get('black', 0)

    if not all([username, password, name]):
        return error("账号、密码、姓名不能为空")

    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            return error("用户名已存在")

        cur.execute(
            """
            INSERT INTO users(username, password, name, role, max_borrow_num, borrow_days, black)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                username, _md5(password), name, role,
                BUSINESS_CONFIG['DEFAULT_MAX_BORROW_NUM'],
                BUSINESS_CONFIG['DEFAULT_BORROW_DAYS'],
                black
            )
        )
        conn.commit()
        return success(msg="用户添加成功")
    except Exception as e:
        conn.rollback()
        return error(f"添加失败：{str(e)}")
    finally:
        cur.close()
        conn.close()


@user_bp.route('/update', methods=['PUT'])
def update_user():
    data = request.json or {}
    if not _is_admin(data):
        return error("只有管理员可以修改用户信息", code=403)

    user_id = data.get('user_id')
    if not user_id:
        return error("用户ID不能为空")

    update_fields = []
    params = []
    for field in ['name', 'gender', 'reader_type', 'max_borrow_num', 'borrow_days', 'role', 'black']:
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


@user_bp.route('/delete', methods=['DELETE'])
def delete_user():
    data = request.json or {}
    if not _is_admin(data):
        return error("只有管理员可以删除用户", code=403)

    user_id = data.get('user_id')
    if not user_id:
        return error("用户ID不能为空")

    conn = get_db_conn()
    try:
        cur = conn.cursor()
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


@user_bp.route('/change_password', methods=['PUT'])
def change_password():
    data = request.json or {}
    return _change_password(data.get('user_id'), data.get('old_password'), data.get('new_password'))


@user_bp.route('/change_pwd', methods=['PUT'])
def change_pwd():
    data = request.json or {}
    return _change_password(data.get('user_id'), data.get('old_pwd'), data.get('new_pwd'))
