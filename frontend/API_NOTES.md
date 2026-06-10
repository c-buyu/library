# 前后端对接说明

这个前端现在按队友的新数据库思路设计：

```text
book：存书种信息，例如 ISBN、书名、作者、分类、价格
book_item：存每一本实体书，例如副本条码、所属书种、馆藏位置、状态
borrow：借阅记录操作具体 book_item
return：还书记录操作具体 borrow
message：借书、还书、到期、续借、超期等通知
```

目前 `app.js` 使用模拟数据，可以直接打开 `index.html` 演示。后端 Flask 写好后，把 `app.js` 顶部的：

```js
const API_BASE = "";
```

改成：

```js
const API_BASE = "http://127.0.0.1:5000";
```

再把模拟数据操作逐步替换成接口请求。

## 建议接口

```text
POST /api/login

GET /api/books
POST /api/books
PUT /api/books/<book_id>
DELETE /api/books/<book_id>

GET /api/book-items
POST /api/book-items
PUT /api/book-items/<item_id>

GET /api/users
POST /api/users
PUT /api/users/<user_id>

GET /api/borrows
POST /api/borrows
POST /api/returns
POST /api/accidents

GET /api/messages
POST /api/messages/generate-due
PUT /api/messages/<msg_id>/read

GET /api/statistics
```

## 推荐返回字段

书种：

```json
{
  "book_id": 1,
  "isbn": "9787111213826",
  "book_name": "Python编程:从入门到实践",
  "author": "埃里克·马瑟斯",
  "category": "计算机",
  "price": 89.00
}
```

实体副本：

```json
{
  "item_id": 101,
  "book_id": 1,
  "barcode": "PY-001",
  "location": "一楼A区",
  "status": "在馆",
  "create_date": "2026-06-08"
}
```

借阅记录建议后端可以直接联表返回书名和读者名，这样前端更省事：

```json
{
  "borrow_id": 1,
  "user_id": 2,
  "reader_name": "张三",
  "item_id": 101,
  "book_name": "Python编程:从入门到实践",
  "barcode": "PY-001",
  "borrow_date": "2026-06-01",
  "return_deadline": "2026-07-01",
  "renew_times": 0,
  "status": "未还"
}
```

## 时间调整功能

前端顶部有“系统日期”，用于演示到期和超期提醒。

后端可以先不做真实时间穿越，只做一个接口：

```text
POST /api/messages/generate-due
```

请求参数：

```json
{
  "current_date": "2026-07-10"
}
```

后端根据这个日期扫描未还记录：

```text
距离应还日期 <= 3 天：生成到期提醒
超过应还日期：生成超期提醒
```
