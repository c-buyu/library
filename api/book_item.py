# -*- coding: utf-8 -*-
from flask import Blueprint, request
from db.connection import get_db_conn
from utils.response import success, error

book_item_bp = Blueprint('book_item', __name__)

# 查询单本图书列表（仅管理员使用，按书种筛选）
@book_item_bp.route('/list', methods=['GET'])
def get_book_item_list():
    book_id = request.args.get('book_id')  # 按书种筛选
    status = request.args.get('status')    # 按状态筛选
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        sql = """
            SELECT bi.book_item_id, bi.book_id, b.book_name, 
                   bi.status, bi.shelf_code, bi.create_time
            FROM book_items bi
            LEFT JOIN books b ON bi.book_id = b.book_id
            WHERE 1=1
        """
        params = []
        
        if book_id:
            sql += " AND bi.book_id=%s"
            params.append(book_id)
        if status:
            sql += " AND bi.status=%s"
            params.append(status)
        
        cur.execute(sql, params)
        book_items = cur.fetchall()
        return success(book_items)
    finally:
        cur.close()
        conn.close()

# 新增单本图书（添加复本）
@book_item_bp.route('/add', methods=['POST'])
def add_book_item():
    data = request.json
    book_item_id = data.get('book_item_id')  # 自定义编号，如ISBN-004
    book_id = data.get('book_id')
    status = data.get('status', '在馆')
    
    if not all([book_item_id, book_id]):
        return error("单本图书编号和书种ID不能为空")
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        # 检查编号是否已存在
        cur.execute("SELECT 1 FROM book_items WHERE book_item_id=%s", (book_item_id,))
        if cur.fetchone():
            return error("该单本图书编号已存在")
        
        # 插入单本图书
        cur.execute("""
            INSERT INTO book_items(book_item_id, book_id, status, shelf_code)
            VALUES (%s, %s, %s, %s)
        """, (book_item_id, book_id, status, data.get('shelf_code')))
        
        # 自动更新书种库存
        cur.execute("UPDATE books SET total_stock = total_stock + 1 WHERE book_id=%s", (book_id,))
        if status == '在馆':
            cur.execute("UPDATE books SET available_stock = available_stock + 1 WHERE book_id=%s", (book_id,))
        
        conn.commit()
        return success(msg="单本图书（复本）添加成功")
    except Exception as e:
        conn.rollback()
        return error(f"添加失败：{str(e)}")
    finally:
        cur.close()
        conn.close()

# 修改单本图书状态
@book_item_bp.route('/update', methods=['PUT'])
def update_book_item():
    data = request.json
    book_item_id = data.get('book_item_id')
    status = data.get('status')
    
    if not all([book_item_id, status]):
        return error("单本图书编号和状态不能为空")
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        # 获取原状态和书种ID
        cur.execute("SELECT book_id, status FROM book_items WHERE book_item_id=%s", (book_item_id,))
        item = cur.fetchone()
        if not item:
            return error("单本图书不存在")
        
        # 更新单本状态
        cur.execute("UPDATE book_items SET status=%s WHERE book_item_id=%s", (status, book_item_id))
        
        # 自动同步更新书种可借库存
        book_id = item['book_id']
        old_status = item['status']
        if old_status == '在馆' and status in ['借出', '丢失', '损坏']:
            cur.execute("UPDATE books SET available_stock = available_stock - 1 WHERE book_id=%s", (book_id,))
        elif old_status in ['借出', '丢失', '损坏'] and status == '在馆':
            cur.execute("UPDATE books SET available_stock = available_stock + 1 WHERE book_id=%s", (book_id,))
        
        conn.commit()
        return success(msg="单本图书状态更新成功")
    except Exception as e:
        conn.rollback()
        return error(f"更新失败：{str(e)}")
    finally:
        cur.close()
        conn.close()

# 删除单本图书
@book_item_bp.route('/delete', methods=['DELETE'])
def delete_book_item():
    data = request.json
    book_item_id = data.get('book_item_id')
    
    if not book_item_id:
        return error("单本图书编号不能为空")
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        # 检查是否有未还借阅记录
        cur.execute("SELECT 1 FROM borrows WHERE book_item_id=%s AND status='未还'", (book_item_id,))
        if cur.fetchone():
            return error("该单本图书有未还借阅记录，无法删除")
        
        # 获取书种ID和原状态
        cur.execute("SELECT book_id, status FROM book_items WHERE book_item_id=%s", (book_item_id,))
        item = cur.fetchone()
        if not item:
            return error("单本图书不存在")
        
        # 删除单本图书
        cur.execute("DELETE FROM book_items WHERE book_item_id=%s", (book_item_id,))
        
        # 自动更新书种库存
        book_id = item['book_id']
        cur.execute("UPDATE books SET total_stock = total_stock - 1 WHERE book_id=%s", (book_id,))
        if item['status'] == '在馆':
            cur.execute("UPDATE books SET available_stock = available_stock - 1 WHERE book_id=%s", (book_id,))
        
        conn.commit()
        return success(msg="单本图书删除成功")
    except Exception as e:
        conn.rollback()
        return error(f"删除失败：{str(e)}")
    finally:
        cur.close()
        conn.close()