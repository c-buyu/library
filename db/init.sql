-- ==============================================
-- 图书管理系统数据库初始化脚本（新增单本图书编号）
-- 编码：UTF-8mb4
-- 优化：书种+单本图书双维度管理
-- ==============================================

-- 创建UTF-8编码数据库
CREATE DATABASE IF NOT EXISTS library 
DEFAULT CHARACTER SET utf8mb4 
DEFAULT COLLATE utf8mb4_unicode_ci;

USE library;

-- 关闭外键检查（防止建表顺序报错）
SET FOREIGN_KEY_CHECKS = 0;

-- ==============================================
-- 1. 用户表
-- ==============================================
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(20) NOT NULL UNIQUE COMMENT '登录账号',
    password VARCHAR(32) NOT NULL COMMENT 'MD5加密密码',
    role VARCHAR(10) NOT NULL DEFAULT '读者' COMMENT '角色：管理员/读者',
    name VARCHAR(10) NOT NULL COMMENT '真实姓名',
    gender CHAR(1) COMMENT '性别：男/女',
    reader_type VARCHAR(20) COMMENT '读者类型：学生/教师/其他',
    max_borrow_num INT NOT NULL DEFAULT 5 COMMENT '最大借书数量',
    borrow_days INT NOT NULL DEFAULT 30 COMMENT '借书期限（天）',
    black TINYINT NOT NULL DEFAULT 0 COMMENT '黑名单:0正常/1禁用',
    remark VARCHAR(200) COMMENT '备注',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- ==============================================
-- 2. 图书表（书种表）
-- ==============================================
DROP TABLE IF EXISTS books;
CREATE TABLE books (
    book_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '图书ID（书种）',
    isbn VARCHAR(20) UNIQUE NOT NULL COMMENT 'ISBN编号',
    book_name VARCHAR(100) NOT NULL COMMENT '书名',
    author VARCHAR(50) COMMENT '作者',
    category VARCHAR(20) COMMENT '分类：计算机/文学/历史等',
    keywords VARCHAR(100) COMMENT '关键词',
    price DECIMAL(10,2) DEFAULT 0.00 COMMENT '图书价格（用于赔偿计算）',
    total_stock INT NOT NULL DEFAULT 1 COMMENT '总库存（书种维度）',
    available_stock INT NOT NULL DEFAULT 1 COMMENT '可借库存（书种维度）',
    remark VARCHAR(200) COMMENT '备注',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='图书表（书种）';

-- ==============================================
-- 图书实例表（单本图书，唯一编号）
-- ==============================================
DROP TABLE IF EXISTS book_items;
CREATE TABLE book_items (
    book_item_id VARCHAR(30) PRIMARY KEY COMMENT '单本图书编号（自定义规则，如ISBN+序号）',
    book_id INT NOT NULL COMMENT '关联书种ID',
    status VARCHAR(10) NOT NULL DEFAULT '在馆' COMMENT '单本状态：在馆/借出/丢失/损坏',
    shelf_code VARCHAR(20) COMMENT '书架编码（可选）',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='图书实例表（单本图书）';

-- ==============================================
-- 3. 借书记录表
-- ==============================================
DROP TABLE IF EXISTS borrows;
CREATE TABLE borrows (
    borrow_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '借阅ID',
    user_id INT NOT NULL COMMENT '用户ID',
    book_id INT NOT NULL COMMENT '图书ID（书种，冗余字段）',
    book_item_id VARCHAR(30) NOT NULL COMMENT '单本图书编号',
    borrow_date DATE NOT NULL COMMENT '借书日期',
    return_deadline DATE NOT NULL COMMENT '应还日期',
    renew_times INT NOT NULL DEFAULT 0 COMMENT '已续借次数',
    remark VARCHAR(200) COMMENT '备注',
    status VARCHAR(10) NOT NULL DEFAULT '未还' COMMENT '状态：未还/已还',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE RESTRICT,
    FOREIGN KEY (book_item_id) REFERENCES book_items(book_item_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='借书记录表';

-- ==============================================
-- 4. 还书记录表
-- ==============================================
DROP TABLE IF EXISTS return_records;
CREATE TABLE return_records (
    return_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '还书ID',
    borrow_id INT NOT NULL UNIQUE COMMENT '借阅ID',
    user_id INT NOT NULL COMMENT '用户ID',
    book_id INT NOT NULL COMMENT '图书ID（书种）',
    book_item_id VARCHAR(30) NOT NULL COMMENT '单本图书编号',
    return_date DATE NOT NULL COMMENT '还书日期',
    overdue_days INT NOT NULL DEFAULT 0 COMMENT '超期天数',
    overdue_fee DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '超期罚款',
    remark VARCHAR(200) COMMENT '备注',
    FOREIGN KEY (borrow_id) REFERENCES borrows(borrow_id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE RESTRICT,
    FOREIGN KEY (book_item_id) REFERENCES book_items(book_item_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='还书记录表';

-- ==============================================
-- 5. 意外处理表
-- ==============================================
DROP TABLE IF EXISTS accidents;
CREATE TABLE accidents (
    accident_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '处理ID',
    borrow_id INT NOT NULL COMMENT '借阅ID',
    user_id INT NOT NULL COMMENT '用户ID',
    book_id INT NOT NULL COMMENT '图书ID（书种）',
    book_item_id VARCHAR(30) NOT NULL COMMENT '单本图书编号',
    handle_type VARCHAR(20) NOT NULL COMMENT '处理类型：续借/超期赔偿/丢失赔偿/损坏赔偿',
    amount DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '赔偿金额',
    handle_date DATE NOT NULL COMMENT '处理日期',
    remark VARCHAR(200) COMMENT '备注',
    FOREIGN KEY (borrow_id) REFERENCES borrows(borrow_id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE RESTRICT,
    FOREIGN KEY (book_item_id) REFERENCES book_items(book_item_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='意外处理表';

-- ==============================================
-- 6. 消息表
-- ==============================================
DROP TABLE IF EXISTS messages;
CREATE TABLE messages (
    msg_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '消息ID',
    user_id INT NOT NULL COMMENT '接收用户ID',
    title VARCHAR(50) NOT NULL COMMENT '消息标题',
    content VARCHAR(200) NOT NULL COMMENT '消息内容',
    is_read TINYINT NOT NULL DEFAULT 0 COMMENT '是否已读:0未读/1已读',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息表';

-- 开启外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- ==============================================
-- 初始化数据
-- ==============================================

-- 1. 默认管理员账号
INSERT INTO users(username, password, role, name, max_borrow_num, borrow_days)
VALUES ('admin', 'e10adc3949ba59abbe56e057f20f883e', '管理员', '系统管理员', 10, 60)
ON DUPLICATE KEY UPDATE password='e10adc3949ba59abbe56e057f20f883e';

-- 2. 测试读者账号
INSERT INTO users(username, password, role, name, reader_type, max_borrow_num, borrow_days)
VALUES ('student1', 'e10adc3949ba59abbe56e057f20f883e', '读者', '张三', '学生', 5, 30)
ON DUPLICATE KEY UPDATE password='e10adc3949ba59abbe56e057f20f883e';

-- 3. 测试图书数据（书种）
INSERT INTO books(isbn, book_name, author, category, price, total_stock, available_stock) VALUES
('9787111213826', 'Python编程:从入门到实践', '埃里克·马瑟斯', '计算机', 89.00, 3, 3),
('9787115546081', '深度学习', '伊恩·古德费洛', '计算机', 168.00, 2, 2),
('9787020002207', '红楼梦', '曹雪芹', '文学', 59.70, 5, 5),
('9787100017565', '史记', '司马迁', '历史', 198.00, 2, 2),
('9787544270878', '解忧杂货店', '东野圭吾', '文学', 39.50, 4, 4)
ON DUPLICATE KEY UPDATE isbn=isbn;

-- 4. 初始化单本图书实例（按书种生成唯一编号，规则：ISBN-序号）
-- Python编程:从入门到实践（3本）
INSERT INTO book_items(book_item_id, book_id, status) VALUES
('9787111213826-001', 1, '在馆'),
('9787111213826-002', 1, '在馆'),
('9787111213826-003', 1, '在馆');

-- 深度学习（2本）
INSERT INTO book_items(book_item_id, book_id, status) VALUES
('9787115546081-001', 2, '在馆'),
('9787115546081-002', 2, '在馆');

-- 红楼梦（5本）
INSERT INTO book_items(book_item_id, book_id, status) VALUES
('9787020002207-001', 3, '在馆'),
('9787020002207-002', 3, '在馆'),
('9787020002207-003', 3, '在馆'),
('9787020002207-004', 3, '在馆'),
('9787020002207-005', 3, '在馆');

-- 史记（2本）
INSERT INTO book_items(book_item_id, book_id, status) VALUES
('9787100017565-001', 4, '在馆'),
('9787100017565-002', 4, '在馆');

-- 解忧杂货店（4本）
INSERT INTO book_items(book_item_id, book_id, status) VALUES
('9787544270878-001', 5, '在馆'),
('9787544270878-002', 5, '在馆'),
('9787544270878-003', 5, '在馆'),
('9787544270878-004', 5, '在馆');

-- ==============================================
-- 创建索引
-- ==============================================
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_books_isbn ON books(isbn);
CREATE INDEX idx_books_name ON books(book_name);
CREATE INDEX idx_books_category ON books(category);
CREATE INDEX idx_book_items_book_id ON book_items(book_id);
CREATE INDEX idx_book_items_status ON book_items(status);
CREATE INDEX idx_borrows_user_id ON borrows(user_id);
CREATE INDEX idx_borrows_book_id ON borrows(book_id);
CREATE INDEX idx_borrows_book_item_id ON borrows(book_item_id);
CREATE INDEX idx_borrows_status ON borrows(status);
CREATE INDEX idx_return_records_borrow_id ON return_records(borrow_id);
CREATE INDEX idx_return_records_book_item_id ON return_records(book_item_id);
CREATE INDEX idx_accidents_borrow_id ON accidents(borrow_id);
CREATE INDEX idx_accidents_book_item_id ON accidents(book_item_id);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_is_read ON messages(is_read);

-- ==============================================
-- 验证脚本
-- ==============================================
SELECT '数据库优化完成' AS result;
SELECT '表数量：' AS info, COUNT(*) AS count FROM information_schema.TABLES WHERE TABLE_SCHEMA='library';
SELECT '管理员账号：' AS info, username, name, role FROM users WHERE role='管理员';
SELECT '测试图书（书种）数量：' AS info, COUNT(*) AS count FROM books;
SELECT '测试图书（单本）数量：' AS info, COUNT(*) AS count FROM book_items;