# 图书馆管理系统

基于 Flask + MySQL + 原生 HTML/CSS/JavaScript 的 B/S 图书馆管理系统。

## 功能

- 登录与权限基础校验
- 图书书种管理
- 馆藏副本管理
- 读者管理与黑名单
- 借书、还书、续借
- 丢失、损坏、超期赔偿记录
- 手动调整系统日期
- 借书、还书、续借、到期、超期消息通知

## 初始化数据库

先确认 `config.py` 中的 MySQL 账号密码正确：

```python
DB_CONFIG = {
    "user": "root",
    "password": "123456",
    "database": "library"
}
```

然后在 MySQL 中执行：

```text
db/init.sql
```

默认账号：

```text
管理员：admin / 123456
读者：student1 / 123456
```

## 启动项目

安装依赖：

```bash
pip install -r requirements.txt
```

启动后端：

```bash
python app.py
```

浏览器访问：

```text
http://127.0.0.1:5000
```

进入后就是前端页面，前端会直接调用同一个 Flask 服务下的 `/api/...` 接口。

## 常用接口

```text
POST /api/user/login
GET  /api/book/list
GET  /api/book_item/list
GET  /api/reader/list
GET  /api/borrow/list
POST /api/borrow/add
POST /api/borrow/return
POST /api/borrow/renew
GET  /api/message/list
POST /api/message/generate_due
POST /api/system/set_date
```

## 到期提醒测试

1. 登录系统。
2. 借出一本馆藏副本。
3. 在页面右上角调整“系统日期”，改到应还日期前后。
4. 进入“消息通知”，点击“生成到期提醒”。
5. 系统会根据当前设置日期生成到期或超期消息。
