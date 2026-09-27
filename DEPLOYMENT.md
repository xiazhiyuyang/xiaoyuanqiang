# 部署文档 Deployment Guide

本文档详细说明如何将校园墙项目部署到生产环境。

## 目录

- [环境要求](#环境要求)
- [项目结构](#项目结构)
- [后端部署](#后端部署)
- [前端构建](#前端构建)
- [Nginx配置](#nginx配置)
- [Docker部署](#docker部署)
- [Systemd服务配置](#systemd服务配置)
- [数据库说明](#数据库说明)
- [配置项说明](#配置项说明)
- [常见问题](#常见问题)

---

## 环境要求

| 组件 | 最低版本 | 推荐版本 |
|------|---------|---------|
| Python | 3.10 | 3.11+ |
| Node.js | 18 | 20 LTS |
| npm | 8 | 10+ |
| Nginx | 1.18 | 1.24+ |
| 操作系统 | - | Ubuntu 22.04 / Debian 12 / CentOS 8+ |

可选组件：
- Redis（用于缓存和限流，不配置时使用内存限流）
- MySQL 8.0+ / PostgreSQL 14+（替代SQLite）

---

## 项目结构

```
campus-wall/
├── backend/          # 后端服务（Python FastAPI）
├── pc/               # PC端前端（Vue 3）
├── mobile/           # 手机H5端（uni-app）
├── admin/            # 管理后台（Vue 3 + Element Plus）
├── data/             # 数据库文件目录
├── nginx/            # Nginx配置示例
├── tools/            # 独立小工具
├── docker-compose.yml
└── .env.example
```

部署后静态文件目录结构（Nginx）：
```
/var/www/campus-wall/
├── index.html        # PC端入口（或重定向到/pc）
├── pc/               # PC端构建产物
├── h5/               # 手机H5端构建产物
├── admin/            # 管理后台构建产物
├── tools/            # 独立小工具
└── uploads/          # 用户上传文件
```

---

## 后端部署

### 1. 安装Python依赖

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 如需MySQL支持，额外安装
pip install aiomysql cryptography

# 如需PostgreSQL支持
pip install asyncpg
```

### 2. 配置环境变量

```bash
cp .env.example .env
nano .env
```

关键配置项：

```env
# 应用配置
APP_NAME=校园墙
DEBUG=false
HOST=127.0.0.1
PORT=8000

# 安全配置（首次启动自动生成，也可手动设置）
SECRET_KEY=your-random-secret-key-at-least-32-chars

# 数据库配置（默认SQLite）
DATABASE_URL=sqlite+aiosqlite:///./data/campus_wall.db
# MySQL示例：
# DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/campus_wall?charset=utf8mb4
# PostgreSQL示例：
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/campus_wall

# 初始管理员
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-strong-admin-password

# 站点URL（用于邮箱验证链接）
SITE_URL=https://your-domain.com

# CORS（允许的前端域名）
CORS_ORIGINS=["https://your-domain.com","http://localhost:5173"]

# Redis（可选）
REDIS_URL=redis://localhost:6379/0

# 上传配置
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=10485760
```

### 3. 初始化数据库

```bash
# 首次启动会自动创建数据库表和初始数据
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 或使用Alembic迁移
alembic upgrade head
```

### 4. 测试后端

```bash
# 健康检查
curl http://127.0.0.1:8000/api/health

# API文档
# 浏览器打开 http://127.0.0.1:8000/docs
```

---

## 前端构建

### 1. PC端构建

```bash
cd pc
npm install
npm run build
# 产物在 dist/ 目录
```

### 2. 手机H5端构建

```bash
cd mobile
npm install
npm run build:h5
# 产物在 dist/build/h5/ 目录
```

### 3. 管理后台构建

```bash
cd admin
npm install
npm run build
# 产物在 dist/ 目录
```

### 4. 部署静态文件

```bash
# 创建部署目录
mkdir -p /var/www/campus-wall/{pc,h5,admin,tools,uploads}

# 复制构建产物
cp -r pc/dist/* /var/www/campus-wall/pc/
cp -r mobile/dist/build/h5/* /var/www/campus-wall/h5/
cp -r admin/dist/* /var/www/campus-wall/admin/
cp -r tools/* /var/www/campus-wall/tools/

# 设置权限
chown -R www-data:www-data /var/www/campus-wall
chmod -R 755 /var/www/campus-wall
```

---

## Nginx配置

### 完整配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL证书配置
    ssl_certificate /etc/nginx/ssl/your-domain.com.crt;
    ssl_certificate_key /etc/nginx/ssl/your-domain.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 日志
    access_log /var/log/nginx/campus-wall-access.log;
    error_log /var/log/nginx/campus-wall-error.log;

    # 根目录
    root /var/www/campus-wall;
    index index.html;

    # 客户端上传大小限制
    client_max_body_size 20m;

    # Gzip压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;
    gzip_min_length 1024;

    # PC端（根路径）
    location / {
        alias /var/www/campus-wall/pc/;
        try_files $uri $uri/ /index.html;
    }

    # 手机H5端
    location /h5/ {
        alias /var/www/campus-wall/h5/;
        try_files $uri $uri/ /h5/index.html;
    }

    # 管理后台
    location /admin/ {
        alias /var/www/campus-wall/admin/;
        try_files $uri $uri/ /admin/index.html;
    }

    # 独立小工具
    location /tools/ {
        alias /var/www/campus-wall/tools/;
    }

    # API反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }

    # 用户上传文件
    location /uploads/ {
        alias /var/www/campus-wall/uploads/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

### 启用配置

```bash
# 测试配置
nginx -t

# 重载配置
systemctl reload nginx
```

---

## Docker部署

### docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: campus-wall-backend
    restart: always
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      - DEBUG=false
      - HOST=0.0.0.0
      - PORT=8000
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=sqlite+aiosqlite:////app/data/campus_wall.db
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - SITE_URL=https://your-domain.com
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
    networks:
      - campus-wall

  redis:
    image: redis:7-alpine
    container_name: campus-wall-redis
    restart: always
    networks:
      - campus-wall

  nginx:
    image: nginx:1.25-alpine
    container_name: campus-wall-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf
      - ./pc/dist:/var/www/campus-wall/pc
      - ./mobile/dist/build/h5:/var/www/campus-wall/h5
      - ./admin/dist:/var/www/campus-wall/admin
      - ./tools:/var/www/campus-wall/tools
      - ./uploads:/var/www/campus-wall/uploads
    depends_on:
      - backend
    networks:
      - campus-wall

networks:
  campus-wall:
    driver: bridge
```

### 启动

```bash
# 构建前端
cd pc && npm install && npm run build && cd ..
cd mobile && npm install && npm run build:h5 && cd ..
cd admin && npm install && npm run build && cd ..

# 设置环境变量
export SECRET_KEY=$(openssl rand -hex 32)
export ADMIN_PASSWORD=your-strong-password

# 启动
docker-compose up -d

# 查看日志
docker-compose logs -f backend
```

---

## Systemd服务配置

### 创建服务文件

```bash
nano /etc/systemd/system/campus-wall.service
```

```ini
[Unit]
Description=Campus Wall Backend Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/campus-wall/backend
Environment="PATH=/var/www/campus-wall/backend/venv/bin"
ExecStart=/var/www/campus-wall/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

# 安全限制
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/www/campus-wall/data /var/www/campus-wall/uploads

[Install]
WantedBy=multi-user.target
```

### 启用服务

```bash
systemctl daemon-reload
systemctl enable campus-wall
systemctl start campus-wall
systemctl status campus-wall
```

### 日志查看

```bash
journalctl -u campus-wall -f
journalctl -u campus-wall --since "1 hour ago"
```

---

## 数据库说明

### 默认数据库

项目默认使用SQLite，数据库文件位于 `backend/data/campus_wall.db`。

首次启动后端会自动创建数据库表和初始数据（分类、敏感词、管理员账号等）。

### 切换到MySQL

1. 安装依赖：
```bash
pip install aiomysql cryptography
```

2. 创建数据库：
```sql
CREATE DATABASE campus_wall CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'campus_wall'@'localhost' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON campus_wall.* TO 'campus_wall'@'localhost';
FLUSH PRIVILEGES;
```

3. 修改 `.env`：
```env
DATABASE_URL=mysql+aiomysql://campus_wall:your-password@localhost:3306/campus_wall?charset=utf8mb4
```

4. 启动后端自动建表。

### 数据库备份

```bash
# SQLite备份
sqlite3 data/campus_wall.db ".backup" backup_$(date +%Y%m%d).db

# MySQL备份
mysqldump -u campus_wall -p campus_wall > backup_$(date +%Y%m%d).sql
```

### 数据库迁移

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

---

## 配置项说明

### 完整配置列表

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|---------|--------|------|
| 应用名称 | APP_NAME | 校园墙 | 站点名称 |
| 调试模式 | DEBUG | false | 开发时设为true |
| 监听地址 | HOST | 127.0.0.1 | 后端监听地址 |
| 监听端口 | PORT | 8000 | 后端监听端口 |
| 密钥 | SECRET_KEY | 自动生成 | JWT签名密钥，生产环境务必手动设置 |
| 数据库 | DATABASE_URL | sqlite | 数据库连接URL |
| 管理员用户名 | ADMIN_USERNAME | admin | 初始管理员用户名 |
| 管理员密码 | ADMIN_PASSWORD | 自动生成 | 初始管理员密码 |
| 站点URL | SITE_URL | http://localhost:8000 | 用于邮箱验证链接 |
| CORS域名 | CORS_ORIGINS | ["*"] | 允许的前端域名 |
| Redis地址 | REDIS_URL | 空 | Redis连接URL，不配置使用内存限流 |
| 上传目录 | UPLOAD_DIR | ./uploads | 用户上传文件目录 |
| 最大上传大小 | MAX_UPLOAD_SIZE | 10485760 | 单文件最大10MB |
| SMTP服务器 | SMTP_HOST | 空 | 邮件服务器地址 |
| SMTP端口 | SMTP_PORT | 465 | 邮件服务器端口 |
| SMTP用户名 | SMTP_USER | 空 | 邮件账号 |
| SMTP密码 | SMTP_PASSWORD | 空 | 邮件密码 |
| SMTP启用SSL | SMTP_USE_SSL | true | 是否使用SSL |
| 发件人名称 | SMTP_FROM_NAME | 校园墙 | 邮件发件人名称 |
| 微信AppID | WECHAT_APP_ID | 空 | 微信小程序AppID |
| 微信AppSecret | WECHAT_APP_SECRET | 空 | 微信小程序AppSecret |
| 微信开放平台AppID | WECHAT_OPEN_APP_ID | 空 | 微信开放平台AppID |
| 微信开放平台AppSecret | WECHAT_OPEN_APP_SECRET | 空 | 微信开放平台AppSecret |

### 邮箱配置示例（QQ邮箱）

```env
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your-email@qq.com
SMTP_PASSWORD=your-qq-mail-authorization-code
SMTP_USE_SSL=true
SMTP_FROM_NAME=校园墙
```

### 邮箱配置示例（阿里云邮件推送）

```env
SMTP_HOST=smtpdm.aliyun.com
SMTP_PORT=465
SMTP_USER=noreply@your-domain.com
SMTP_PASSWORD=your-smtp-password
SMTP_USE_SSL=true
SMTP_FROM_NAME=校园墙
```

---

## 常见问题

### 1. 后端启动报错：ModuleNotFoundError

确保已激活虚拟环境并安装了所有依赖：
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 前端页面空白

检查浏览器控制台是否有报错，确认：
- Nginx配置正确，静态文件路径正确
- API代理配置正确，后端服务正常运行
- 前端构建时的base路径与部署路径一致

### 3. 图片上传失败

检查：
- `uploads` 目录存在且有写入权限
- `MAX_UPLOAD_SIZE` 配置足够大
- Nginx `client_max_body_size` 配置足够大
- 后端 `UPLOAD_DIR` 路径正确

### 4. 邮箱验证收不到邮件

检查：
- SMTP配置正确（HOST/PORT/USER/PASSWORD）
- 邮箱账号已开启SMTP服务
- 部分邮箱需要使用授权码而非登录密码
- 检查垃圾邮件文件夹
- 未配置SMTP时，验证链接会在API响应中返回（开发模式）

### 5. 微信登录失败

检查：
- 微信小程序AppID和AppSecret配置正确
- 小程序已配置合法域名（request合法域名、uploadFile合法域名）
- 微信开放平台账号已认证

### 6. 数据库锁定（SQLite）

SQLite在高并发下可能出现数据库锁定错误。生产环境建议使用MySQL或PostgreSQL：
```env
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/campus_wall?charset=utf8mb4
```

### 7. 如何修改管理员密码

方式一：在管理后台「用户管理」中重置密码。
方式二：直接修改数据库：
```bash
python3 -c "
import bcrypt
print(bcrypt.hashpw(b'new-password', bcrypt.gensalt()).decode())
"
# 然后用生成的哈希更新数据库
sqlite3 data/campus_wall.db "UPDATE users SET password_hash='generated-hash' WHERE username='admin';"
```

### 8. 如何开启/关闭注册

在管理后台「系统设置」中修改 `allow_register` 配置，或直接修改数据库：
```bash
sqlite3 data/campus_wall.db "UPDATE site_settings SET value='false' WHERE key='allow_register';"
```

### 9. 日志位置

- 后端日志：`backend/logs/` 目录，或使用 `journalctl -u campus-wall`
- Nginx日志：`/var/log/nginx/campus-wall-*.log`
- 访问日志：数据库 `operation_logs` 表

### 10. 性能优化建议

- 使用MySQL/PostgreSQL替代SQLite
- 启用Redis缓存
- 后端使用多worker启动：`uvicorn app.main:app --workers 4`
- 配置Nginx Gzip压缩和静态资源缓存
- 使用CDN加速静态资源
- 定期清理旧的操作日志和通知

---

## 更新部署

```bash
# 1. 拉取最新代码
git pull

# 2. 安装新依赖（如有）
cd backend && source venv/bin/activate && pip install -r requirements.txt && cd ..

# 3. 数据库迁移（如有）
cd backend && alembic upgrade head && cd ..

# 4. 重新构建前端
cd pc && npm install && npm run build && cd ..
cd mobile && npm install && npm run build:h5 && cd ..
cd admin && npm install && npm run build && cd ..

# 5. 部署静态文件
cp -r pc/dist/* /var/www/campus-wall/pc/
cp -r mobile/dist/build/h5/* /var/www/campus-wall/h5/
cp -r admin/dist/* /var/www/campus-wall/admin/

# 6. 重启后端
systemctl restart campus-wall

# 7. 重载Nginx
nginx -t && systemctl reload nginx
```
