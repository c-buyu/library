# -*- coding: utf-8 -*-
import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from config import FLASK_CONFIG

# 导入各个接口蓝图
from api.user import user_bp
from api.reader import reader_bp
from api.book import book_bp
from api.borrow import borrow_bp
from api.accident import accident_bp
from api.book_item import book_item_bp
from api.system import system_bp
from api.message import message_bp

# 导入统一响应工具
from utils.response import error

# 初始化Flask应用
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.config.update(FLASK_CONFIG)

# 配置跨域
# 允许所有域名跨域访问，开发环境使用；生产环境可指定具体域名
CORS(app, supports_credentials=True)

# 注册所有接口蓝图
# 蓝图前缀统一为/api/xxx
app.register_blueprint(user_bp, url_prefix="/api/user")
app.register_blueprint(reader_bp, url_prefix="/api/reader")
app.register_blueprint(book_bp, url_prefix="/api/book")
app.register_blueprint(borrow_bp, url_prefix="/api/borrow")
app.register_blueprint(accident_bp, url_prefix="/api/accident")
app.register_blueprint(book_item_bp, url_prefix='/api/book_item')
app.register_blueprint(system_bp, url_prefix="/api/system")
app.register_blueprint(message_bp, url_prefix="/api/message")

@app.route("/", methods=["GET"])
def index():
    if os.path.exists(os.path.join(FRONTEND_DIR, "index.html")):
        return send_from_directory(FRONTEND_DIR, "index.html")
    return jsonify({
        "code": 200,
        "msg": "图书管理系统后端服务启动成功！",
        "data": {
            "version": "1.0.0",
            "status": "running"
        }
    })


@app.route("/<path:filename>", methods=["GET"])
def frontend_assets(filename):
    if os.path.exists(os.path.join(FRONTEND_DIR, filename)):
        return send_from_directory(FRONTEND_DIR, filename)
    return error("资源不存在", code=404)

# 全局异常处理
@app.errorhandler(Exception)
def global_exception_handler(e):
    """全局异常捕获，返回统一格式的错误响应"""
    app.logger.error(f"全局异常：{str(e)}")
    return error(f"服务器内部错误：{str(e)}", code=500)

# 启动应用
if __name__ == "__main__":
    # 启动时执行一次到期提醒检查（覆盖自然日期推进的场景）
    from api.message import run_due_reminder_check
    try:
        run_due_reminder_check()
        app.logger.info("启动时到期提醒检查完成")
    except Exception:
        app.logger.exception("启动时到期提醒检查失败")
    app.run(host="0.0.0.0", port=5000, debug=FLASK_CONFIG["DEBUG"])
