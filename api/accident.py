# -*- coding: utf-8 -*-
from flask import Blueprint, request
from db.connection import get_db_conn
from utils.response import success, error
from datetime import datetime
from config import BUSINESS_CONFIG
from utils.date_utils import get_current_date, add_days

accident_bp = Blueprint('accident', __name__)

# 意外处理记录（修改：关联单本图书）
@accident_bp.route('/add', methods=['POST'])
def add_accident():
    data = request.json
    borrow_id = data.get('borrow_id')
    handle_type = data.get('handle_type')
    amount = data.get('amount', 0.00)
    
    if not all([borrow_id, handle_type]):
        return error("借阅记录ID和处理类型不能为空")
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        # 获取借阅信息（包含单本图书编号）
        cur.execute("""
            SELECT user_id, book_id, book_item_id 
            FROM borrows WHERE borrow_id=%s
        """, (borrow_id,))
        borrow = cur.fetchone()
        if not borrow:
            return error("借阅记录不存在")
        
        current_date = get_current_date()
        user_id = borrow['user_id']
        book_id = borrow['book_id']
        book_item_id = borrow['book_item_id']
        
        # 插入意外处理记录（关联单本图书）
        cur.execute("""
            INSERT INTO accidents(borrow_id, user_id, book_id, book_item_id, handle_type, amount, handle_date, remark)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (borrow_id, user_id, book_id, book_item_id, 
              handle_type, amount, current_date, data.get('remark')))
        
        # 如果是丢失赔偿，更新单本图书状态为丢失
        if handle_type == '丢失赔偿':
            cur.execute("UPDATE book_items SET status='丢失' WHERE book_item_id=%s", (book_item_id,))
            cur.execute("UPDATE borrows SET status='已还' WHERE borrow_id=%s", (borrow_id,))
        
        # 如果是损坏赔偿，更新单本图书状态为损坏
        if handle_type == '损坏赔偿':
            cur.execute("UPDATE book_items SET status='损坏' WHERE book_item_id=%s", (book_item_id,))
            cur.execute("UPDATE borrows SET status='已还' WHERE borrow_id=%s", (borrow_id,))
        
        conn.commit()
        return success(msg="处理记录添加成功")
    except Exception as e:
        conn.rollback()
        return error(f"添加失败：{str(e)}")
    finally:
        cur.close()
        conn.close()

# 查询意外处理记录（新增单本图书编号字段）
@accident_bp.route('/list', methods=['GET'])
def get_accident_list():
    user_id = request.args.get('user_id')
    handle_type = request.args.get('handle_type')
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        sql = """
            SELECT a.accident_id, a.borrow_id, a.user_id, u.name as user_name,
                   a.book_id, bo.book_name, a.book_item_id,
                   bo.price, bi.status as book_item_status, bo.available_stock,
                   a.handle_type, a.amount, a.handle_date, a.remark
            FROM accidents a
            LEFT JOIN users u ON a.user_id = u.user_id
            LEFT JOIN books bo ON a.book_id = bo.book_id
            LEFT JOIN book_items bi ON a.book_item_id = bi.book_item_id
            WHERE 1=1
        """
        params = []
        
        if user_id:
            sql += " AND a.user_id=%s"
            params.append(user_id)
        if handle_type:
            sql += " AND a.handle_type=%s"
            params.append(handle_type)
        
        sql += " ORDER BY a.handle_date DESC"
        cur.execute(sql, params)
        accidents = cur.fetchall()
        return success(accidents)
    finally:
        cur.close()
        conn.close()

# 计算超期罚款（无修改）
@accident_bp.route('/calculate_overdue', methods=['GET'])
def calculate_overdue():
    borrow_id = request.args.get('borrow_id')
    
    if not borrow_id:
        return error("借阅记录ID不能为空")
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT return_deadline
            FROM borrows WHERE borrow_id=%s AND status='未还'
        """, (borrow_id,))
        result = cur.fetchone()
        
        if not result:
            return error("借阅记录不存在或已归还")
        
        overdue_days = max(0, (get_current_date() - result['return_deadline']).days)
        amount = overdue_days * BUSINESS_CONFIG['OVERDUE_FEE_PER_DAY']
        
        return success({
            "overdue_days": overdue_days,
            "amount": round(amount, 2)
        })
    finally:
        cur.close()
        conn.close()
