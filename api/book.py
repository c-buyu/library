# -*- coding: utf-8 -*-
from flask import Blueprint, request
from db.connection import get_db_conn
from utils.response import success, error

book_bp = Blueprint('book', __name__)

# 查询所有图书（仅返回书种信息）
@book_bp.route('/list', methods=['GET'])
def get_book_list():
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT book_id, isbn, book_name, author, category, keywords, 
                   price, total_stock, available_stock, remark, create_time 
            FROM books
        """)
        books = cur.fetchall()
        return success(books)
    finally:
        cur.close()
        conn.close()

# 新增图书（书种+自动生成单本）
@book_bp.route('/add', methods=['POST'])
def add_book():
    data = request.json
    isbn = data.get('isbn')
    book_name = data.get('book_name')
    price = data.get('price', 0.00)
    total_stock = data.get('total_stock', 1)  # 传入总册数，自动生成对应单本
    
    if not all([isbn, book_name]):
        return error("ISBN和书名不能为空")
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        # ISBN查重
        cur.execute("SELECT 1 FROM books WHERE isbn=%s", (isbn,))
        if cur.fetchone():
            return error("该ISBN图书已存在")
        
        # 插入书种（available_stock自动等于total_stock）
        cur.execute("""
            INSERT INTO books(isbn, book_name, author, category, keywords, 
                             price, total_stock, available_stock, remark)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (isbn, book_name, data.get('author'), data.get('category'),
              data.get('keywords'), price, total_stock, total_stock,
              data.get('remark')))
        # 获取新增书种ID
        cur.execute("SELECT book_id FROM books WHERE isbn=%s", (isbn,))
        book_id = cur.fetchone()['book_id']
        
        # 自动生成单本图书（规则：ISBN-001、ISBN-002...）
        for i in range(1, total_stock + 1):
            book_item_id = f"{isbn}-{str(i).zfill(3)}"
            cur.execute("""
                INSERT INTO book_items(book_item_id, book_id, status)
                VALUES (%s, %s, '在馆')
            """, (book_item_id, book_id))
        
        conn.commit()
        return success(msg=f"图书添加成功，共生成{total_stock}本单本图书")
    except Exception as e:
        conn.rollback()
        return error(f"添加失败：{str(e)}")
    finally:
        cur.close()
        conn.close()

# 修改图书（仅允许修改书种基本信息，禁止修改库存）
@book_bp.route('/update', methods=['PUT'])
def update_book():
    data = request.json
    book_id = data.get('book_id')
    
    if not book_id:
        return error("图书ID不能为空")
    
    update_fields = []
    params = []
    # 移除total_stock和available_stock，禁止手动修改库存
    for field in ['isbn', 'book_name', 'author', 'category', 'keywords', 
                  'price', 'remark']:
        if field in data:
            update_fields.append(f"{field}=%s")
            params.append(data[field])
    
    if not update_fields:
        return error("没有要更新的字段")
    
    params.append(book_id)
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(f"UPDATE books SET {','.join(update_fields)} WHERE book_id=%s", params)
        conn.commit()
        return success(msg="图书信息更新成功")
    except Exception as e:
        conn.rollback()
        return error(f"更新失败：{str(e)}")
    finally:
        cur.close()
        conn.close()

# 删除图书（书种+级联删除所有单本）
@book_bp.route('/delete', methods=['DELETE'])
def delete_book():
    data = request.json
    book_id = data.get('book_id')
    
    if not book_id:
        return error("图书ID不能为空")
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        # 检查该图书所有单本是否有未还借阅记录
        cur.execute("SELECT 1 FROM borrows WHERE book_id=%s AND status='未还'", (book_id,))
        if cur.fetchone():
            return error("该图书有未还借阅记录，无法删除")
        
        # 先删除所有关联单本
        cur.execute("DELETE FROM book_items WHERE book_id=%s", (book_id,))
        # 再删除书种
        cur.execute("DELETE FROM books WHERE book_id=%s", (book_id,))
        
        conn.commit()
        return success(msg="图书（含所有单本）删除成功")
    except Exception as e:
        conn.rollback()
        return error(f"删除失败：{str(e)}")
    finally:
        cur.close()
        conn.close()

# 删除单本图书
@book_bp.route('/delete_item', methods=['DELETE'])
def delete_book_item():
    data = request.json
    book_item_id = data.get('book_item_id')
    
    if not book_item_id:
        return error("单本图书编号不能为空")
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        # 1. 检查该单本是否有未还借阅记录
        cur.execute("SELECT 1 FROM borrows WHERE book_item_id=%s AND status='未还'", (book_item_id,))
        if cur.fetchone():
            return error("该单本图书有未还借阅记录，无法删除")
        
        # 2. 获取单本信息（书种ID、原状态）
        cur.execute("SELECT book_id, status FROM book_items WHERE book_item_id=%s", (book_item_id,))
        item = cur.fetchone()
        if not item:
            return error("单本图书不存在")
        
        book_id = item['book_id']
        old_status = item['status']
        
        # 3. 删除单本图书
        cur.execute("DELETE FROM book_items WHERE book_item_id=%s", (book_item_id,))
        
        # 4. 自动更新书种库存
        cur.execute("UPDATE books SET total_stock = total_stock - 1 WHERE book_id=%s", (book_id,))
        # 只有原状态是"在馆"时，才减少可借库存
        if old_status == '在馆':
            cur.execute("UPDATE books SET available_stock = available_stock - 1 WHERE book_id=%s", (book_id,))
        
        conn.commit()
        return success(msg="单本图书删除成功")
    except Exception as e:
        conn.rollback()
        return error(f"删除失败：{str(e)}")
    finally:
        cur.close()
        conn.close()

# 多条件查询图书（仅返回书种信息）
@book_bp.route('/search', methods=['GET'])
def search_book():
    isbn = request.args.get('isbn', '')
    book_name = request.args.get('book_name', '')
    author = request.args.get('author', '')
    category = request.args.get('category', '')
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        sql = """
            SELECT book_id, isbn, book_name, author, category, keywords, 
                   price, total_stock, available_stock, remark, create_time 
            FROM books WHERE 1=1
        """
        params = []
        
        if isbn:
            sql += " AND isbn LIKE %s"
            params.append(f"%{isbn}%")
        if book_name:
            sql += " AND book_name LIKE %s"
            params.append(f"%{book_name}%")
        if author:
            sql += " AND author LIKE %s"
            params.append(f"%{author}%")
        if category:
            sql += " AND category=%s"
            params.append(category)
        
        cur.execute(sql, params)
        books = cur.fetchall()
        return success(books)
    finally:
        cur.close()
        conn.close()