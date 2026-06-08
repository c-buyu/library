# -*- coding: utf-8 -*-
from datetime import datetime

from flask import Blueprint, request

from config import BUSINESS_CONFIG
from db.connection import get_db_conn
from utils.date_utils import get_current_date
from utils.response import error, success

message_bp = Blueprint('message', __name__)


def _parse_date(date_str):
    if not date_str:
        return get_current_date()
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


def _insert_message(cur, user_id, msg_type, title, content):
    cur.execute(
        """
        SELECT 1 FROM messages
        WHERE user_id=%s AND msg_type=%s AND content=%s
        LIMIT 1
        """,
        (user_id, msg_type, content)
    )
    if cur.fetchone():
        return False

    cur.execute(
        """
        INSERT INTO messages(user_id, msg_type, title, content)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, msg_type, title, content)
    )
    return True


@message_bp.route('/list', methods=['GET'])
def get_message_list():
    user_id = request.args.get('user_id')
    is_read = request.args.get('is_read')

    conn = get_db_conn()
    try:
        cur = conn.cursor()
        sql = """
            SELECT msg_id, user_id, msg_type, title, content, is_read, create_time
            FROM messages
            WHERE 1=1
        """
        params = []

        if user_id:
            sql += " AND user_id=%s"
            params.append(user_id)
        if is_read is not None:
            sql += " AND is_read=%s"
            params.append(is_read)

        sql += " ORDER BY create_time DESC, msg_id DESC"
        cur.execute(sql, params)
        return success(cur.fetchall())
    finally:
        cur.close()
        conn.close()


@message_bp.route('/read', methods=['PUT'])
def mark_message_read():
    data = request.json or {}
    msg_id = data.get('msg_id')

    if not msg_id:
        return error("消息ID不能为空")

    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE messages SET is_read=1 WHERE msg_id=%s", (msg_id,))
        conn.commit()
        return success(msg="消息已标记为已读")
    except Exception as e:
        conn.rollback()
        return error(f"标记失败：{str(e)}")
    finally:
        cur.close()
        conn.close()


@message_bp.route('/generate_due', methods=['POST'])
def generate_due_messages():
    data = request.json or {}
    current_date = _parse_date(data.get('current_date'))
    if current_date is None:
        return error("日期格式错误，请使用YYYY-MM-DD格式")

    remind_days = BUSINESS_CONFIG['REMIND_DAYS_BEFORE_DUE']
    generated_count = 0

    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT br.borrow_id, br.user_id, br.return_deadline,
                   bo.book_name, br.book_item_id
            FROM borrows br
            LEFT JOIN books bo ON br.book_id = bo.book_id
            WHERE br.status='未还'
            """
        )
        rows = cur.fetchall()

        for row in rows:
            left_days = (row['return_deadline'] - current_date).days
            if left_days < 0:
                content = (
                    f"《{row['book_name']}》（{row['book_item_id']}）已超期"
                    f"{abs(left_days)}天，请尽快归还。"
                )
                if _insert_message(cur, row['user_id'], '超期', '图书已超期', content):
                    generated_count += 1
            elif left_days <= remind_days:
                content = (
                    f"《{row['book_name']}》（{row['book_item_id']}）还有"
                    f"{left_days}天到期，请留意还书时间。"
                )
                if _insert_message(cur, row['user_id'], '到期', '图书即将到期', content):
                    generated_count += 1

        conn.commit()
        return success({"generated_count": generated_count}, "到期提醒生成完成")
    except Exception as e:
        conn.rollback()
        return error(f"生成提醒失败：{str(e)}")
    finally:
        cur.close()
        conn.close()
