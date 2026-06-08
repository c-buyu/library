# -*- coding: utf-8 -*-
from flask import Flask, jsonify
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
app = Flask(__name__)
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

# 根路由测试
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "code": 200,
        "msg": "图书管理系统后端服务启动成功！",
        "data": {
            "version": "1.0.0",
            "status": "running"
        }
    })

# 全局异常处理
@app.errorhandler(Exception)
def global_exception_handler(e):
    """全局异常捕获，返回统一格式的错误响应"""
    app.logger.error(f"全局异常：{str(e)}")
    return error(f"服务器内部错误：{str(e)}", code=500)

# 启动应用
if __name__ == "__main__":
    # 启动服务，监听所有网卡，端口5000
    app.run(host="0.0.0.0", port=5000, debug=FLASK_CONFIG["DEBUG"])
