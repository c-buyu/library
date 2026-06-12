# -*- coding: utf-8 -*-
from flask import Blueprint, request
from db.connection import get_db_conn
from utils.response import success, error
from config import BUSINESS_CONFIG
from utils.date_utils import add_days, get_current_date

borrow_bp = Blueprint('borrow', __name__)

# 借书接口（指定单本图书编号）
@borrow_bp.route('/add', methods=['POST'])
def add_borrow():
    data = request.json
    user_id = data.get('user_id')
    book_item_id = data.get('book_item_id')  # 仅此处需要传入单本编号
    operator_user_id = data.get('operator_user_id')
    operator_role = data.get('operator_role')
    
    if not all([user_id, book_item_id]):
        return error("读者ID和单本图书编号不能为空")
    if operator_role != '管理员' and str(operator_user_id) != str(user_id):
        return error("读者只能为自己借书", code=403)
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        # 1. 校验读者状态
        cur.execute("SELECT black FROM users WHERE user_id=%s", (user_id,))
        user_black = cur.fetchone()
        if not user_black or user_black['black'] == 1:
            return error("该用户已被禁用，无法借书")
        
        # 2. 校验借书数量
        cur.execute("SELECT COUNT(*) as cnt FROM borrows WHERE user_id=%s AND status='未还'", (user_id,))
        count = cur.fetchone()['cnt']
        cur.execute("SELECT max_borrow_num, borrow_days FROM users WHERE user_id=%s", (user_id,))
        user_rule = cur.fetchone()
        max_num = user_rule['max_borrow_num']
        if count >= max_num:
            return error(f"借书数量超限，最多可借{max_num}本")
        
        # 3. 校验单本图书状态
        cur.execute("SELECT book_id, status FROM book_items WHERE book_item_id=%s", (book_item_id,))
        item_info = cur.fetchone()
        if not item_info or item_info['status'] != '在馆':
            return error("该图书不可借")
        
        book_id = item_info['book_id']
        borrow_date = get_current_date()
        return_deadline = add_days(borrow_date, user_rule['borrow_days'])
        
        # 4. 插入借阅记录
        cur.execute("""
            INSERT INTO borrows(user_id, book_id, book_item_id, borrow_date, return_deadline, renew_times)
            VALUES (%s, %s, %s, %s, %s, 0)
        """, (user_id, book_id, book_item_id, borrow_date, return_deadline))
        
        # 5. 更新单本状态和书种库存
        cur.execute("UPDATE book_items SET status='借出' WHERE book_item_id=%s", (book_item_id,))
        cur.execute("UPDATE books SET available_stock = available_stock - 1 WHERE book_id=%s", (book_id,))
        cur.execute("""
            SELECT book_name FROM books WHERE book_id=%s
        """, (book_id,))
        book = cur.fetchone()
        cur.execute("""
            INSERT INTO messages(user_id, msg_type, title, content)
            VALUES (%s, '借书', '借书成功', %s)
        """, (user_id, f"你已借阅《{book['book_name']}》（{book_item_id}），应还日期为{return_deadline}。"))
        
        conn.commit()
        return success(msg="借书成功")
    except Exception as e:
        conn.rollback()
        return error(f"借书失败：{str(e)}")
    finally:
        cur.close()
        conn.close()

# 还书接口（自动关联单本图书）
@borrow_bp.route('/return', methods=['POST'])
def return_book():
    data = request.json
    borrow_id = data.get('borrow_id')
    operator_user_id = data.get('operator_user_id')
    operator_role = data.get('operator_role')
    
    if not borrow_id:
        return error("借阅记录ID不能为空")
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        # 1. 获取借阅信息（含单本编号）
        cur.execute("""
            SELECT b.*, u.borrow_days 
            FROM borrows b 
            LEFT JOIN users u ON b.user_id = u.user_id
            WHERE b.borrow_id=%s AND b.status='未还'
        """, (borrow_id,))
        borrow = cur.fetchone()
        if not borrow:
            return error("借阅记录不存在或已归还")
        if operator_role != '管理员' and str(operator_user_id) != str(borrow['user_id']):
            return error("读者只能归还自己的借阅记录", code=403)
        
        book_id = borrow['book_id']
        book_item_id = borrow['book_item_id']
        current_date = get_current_date()
        
        # 2. 计算超期罚款
        overdue_days = max(0, (current_date - borrow['return_deadline']).days)
        overdue_fee = round(overdue_days * BUSINESS_CONFIG['OVERDUE_FEE_PER_DAY'], 2)
        
        # 3. 插入还书记录
        cur.execute("""
            INSERT INTO return_records(borrow_id, user_id, book_id, book_item_id, return_date, overdue_days, overdue_fee)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (borrow_id, borrow['user_id'], book_id, book_item_id, current_date, overdue_days, overdue_fee))
        
        # 4. 更新状态和库存
        cur.execute("UPDATE borrows SET status='已还' WHERE borrow_id=%s", (borrow_id,))
        cur.execute("UPDATE book_items SET status='在馆' WHERE book_item_id=%s", (book_item_id,))
        cur.execute("UPDATE books SET available_stock = available_stock + 1 WHERE book_id=%s", (book_id,))
        
        # 5. 记录超期罚款
        if overdue_fee > 0:
            cur.execute("""
                INSERT INTO accidents(borrow_id, user_id, book_id, book_item_id, handle_type, amount, handle_date, remark)
                VALUES (%s, %s, %s, %s, '超期赔偿', %s, %s, %s)
            """, (borrow_id, borrow['user_id'], book_id, book_item_id, overdue_fee, current_date, f"超期{overdue_days}天"))
        cur.execute("""
            SELECT book_name FROM books WHERE book_id=%s
        """, (book_id,))
        book = cur.fetchone()
        cur.execute("""
            INSERT INTO messages(user_id, msg_type, title, content)
            VALUES (%s, '还书', '还书成功', %s)
        """, (borrow['user_id'], f"你已归还《{book['book_name']}》（{book_item_id}）。"))
        
        conn.commit()
        return success({
            "msg": "还书成功",
            "overdue_days": overdue_days,
            "overdue_fee": overdue_fee
        })
    except Exception as e:
        conn.rollback()
        return error(f"还书失败：{str(e)}")
    finally:
        cur.close()
        conn.close()

# 查询借阅记录
@borrow_bp.route('/list', methods=['GET'])
def get_borrow_list():
    user_id = request.args.get('user_id')
    status = request.args.get('status')
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        sql = """
            SELECT b.borrow_id, b.user_id, u.name as user_name, 
                   b.book_id, bo.book_name, b.book_item_id,
                   b.borrow_date, b.return_deadline, b.renew_times, b.status
            FROM borrows b
            LEFT JOIN users u ON b.user_id = u.user_id
            LEFT JOIN books bo ON b.book_id = bo.book_id
            WHERE 1=1
        """
        params = []
        
        if user_id:
            sql += " AND b.user_id=%s"
            params.append(user_id)
        if status:
            sql += " AND b.status=%s"
            params.append(status)
        
        sql += " ORDER BY b.borrow_date DESC"
        cur.execute(sql, params)
        borrows = cur.fetchall()
        return success(borrows)
    finally:
        cur.close()
        conn.close()

# 续借接口
@borrow_bp.route('/renew', methods=['POST'])
def renew_book():
    data = request.json
    borrow_id = data.get('borrow_id')
    operator_user_id = data.get('operator_user_id')
    operator_role = data.get('operator_role')
    
    if not borrow_id:
        return error("借阅记录ID不能为空")
    
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM borrows WHERE borrow_id=%s AND status='未还'", (borrow_id,))
        borrow = cur.fetchone()
        if not borrow:
            return error("借阅记录不存在或已归还")
        if operator_role != '管理员' and str(operator_user_id) != str(borrow['user_id']):
            return error("读者只能续借自己的借阅记录", code=403)
        
        if borrow['renew_times'] >= BUSINESS_CONFIG['MAX_RENEW_TIMES']:
            return error(f"已续借{borrow['renew_times']}次，无法再次续借")
        
        new_deadline = add_days(borrow['return_deadline'], BUSINESS_CONFIG['RENEW_DAYS'])
        current_date = get_current_date()
        cur.execute("""
            UPDATE borrows 
            SET return_deadline = %s,
                renew_times = renew_times + 1
            WHERE borrow_id=%s
        """, (new_deadline, borrow_id))
        
        cur.execute("""
            INSERT INTO accidents(borrow_id, user_id, book_id, book_item_id, handle_type, handle_date)
            VALUES (%s, %s, %s, %s, '续借', %s)
        """, (borrow_id, borrow['user_id'], borrow['book_id'], borrow['book_item_id'], current_date))
        cur.execute("""
            SELECT book_name FROM books WHERE book_id=%s
        """, (borrow['book_id'],))
        book = cur.fetchone()
        cur.execute("""
            INSERT INTO messages(user_id, msg_type, title, content)
            VALUES (%s, '续借', '续借成功', %s)
        """, (borrow['user_id'], f"《{book['book_name']}》（{borrow['book_item_id']}）已续借，新应还日期为{new_deadline}。"))
        
        conn.commit()
        return success(msg="续借成功")
    except Exception as e:
        conn.rollback()
        return error(f"续借失败：{str(e)}")
    finally:
        cur.close()
        conn.close()
