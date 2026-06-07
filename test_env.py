# -*- coding: utf-8 -*-

""" 环境测试脚本,用于检查Flask环境和MySQL连接是否正常 """
from flask import Flask
import pymysql

app = Flask(__name__)

# 测试MySQL连接
def test_mysql():
    try:
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="123456",  
            database="mysql",
            charset="utf8mb4"
        )
        print("MySQL连接成功!")
        conn.close()
    except Exception as e:
        print("MySQL连接失败:", e)

# 测试路由
@app.route('/')
def hello():
    return "Flask环境正常!"

if __name__ == '__main__':
    test_mysql()
    app.run(debug=True)