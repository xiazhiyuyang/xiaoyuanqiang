# Deployment Guide

This document provides detailed instructions for deploying the Campus Wall project to a production environment.

## Table of Contents

- [Requirements](#requirements)
- [Project Structure](#project-structure)
- [Backend Deployment](#backend-deployment)
- [Frontend Build](#frontend-build)
- [Nginx Configuration](#nginx-configuration)
- [Docker Deployment](#docker-deployment)
- [Systemd Service](#systemd-service)
- [Database](#database)
- [Configuration](#configuration)
- [FAQ](#faq)

---

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.10 | 3.11+ |
| Node.js | 18 | 20 LTS |
| npm | 8 | 10+ |
| Nginx | 1.18 | 1.24+ |
| OS | - | Ubuntu 22.04 / Debian 12 / CentOS 8+ |

Optional:
- Redis (for caching and rate limiting; in-memory limiting is used when not configured)
- MySQL 8.0+ / PostgreSQL 14+ (alternative to SQLite)

---

## Project Structure

```
campus-wall/
├── backend/          # Backend service (Python FastAPI)
├── pc/               # PC frontend (Vue 3)
├── mobile/           # Mobile H5 (uni-app)
├── admin/            # Admin dashboard (Vue 3 + Element Plus)
├── data/             # Database files
├── nginx/            # Nginx config examples
├── tools/            # Standalone tools
├── docker-compose.yml
└── .env.example
```

Static file structure after deployment (Nginx):
```
/var/www/campus-wall/
├── index.html        # PC entry (or redirect to /pc)
├── pc/               # PC build output
├── h5/               # Mobile H5 build output
├── admin/            # Admin build output
├── tools/            # Standalone tools
└── uploads/          # User uploads
```

---

## Backend Deployment

### 1. Install Python Dependencies

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# For MySQL support
pip install aiomysql cryptography

# For PostgreSQL support
pip install asyncpg
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Key configuration:

```env
# Application
APP_NAME=Campus Wall
DEBUG=false
HOST=127.0.0.1
PORT=8000

# Security (auto-generated on first run, or set manually)
SECRET_KEY=your-random-secret-key-at-least-32-chars

# Database (SQLite by default)
DATABASE_URL=sqlite+aiosqlite:///./data/campus_wall.db
# MySQL example:
# DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/campus_wall?charset=utf8mb4
# PostgreSQL example:
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/campus_wall

# Initial admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-strong-admin-password

# Site URL (for email verification links)
SITE_URL=https://your-domain.com

# CORS (allowed frontend domains)
CORS_ORIGINS=["https://your-domain.com","http://localhost:5173"]

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Upload
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=10485760
```

### 3. Initialize Database

```bash
# Auto-creates tables and initial data on first start
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Or use Alembic migrations
alembic upgrade head
```

### 4. Test Backend

```bash
# Health check
curl http://127.0.0.1:8000/api/health

# API docs
# Open http://127.0.0.1:8000/docs in browser
```

---

## Frontend Build

### 1. PC Build

```bash
cd pc
npm install
npm run build
# Output in dist/
```

### 2. Mobile H5 Build

```bash
cd mobile
npm install
npm run build:h5
# Output in dist/build/h5/
```

### 3. Admin Build

```bash
cd admin
npm install
npm run build
# Output in dist/
```

### 4. Deploy Static Files

```bash
# Create deployment directories
mkdir -p /var/www/campus-wall/{pc,h5,admin,tools,uploads}

# Copy build outputs
cp -r pc/dist/* /var/www/campus-wall/pc/
cp -r mobile/dist/build/h5/* /var/www/campus-wall/h5/
cp -r admin/dist/* /var/www/campus-wall/admin/
cp -r tools/* /var/www/campus-wall/tools/

# Set permissions
chown -R www-data:www-data /var/www/campus-wall
chmod -R 755 /var/www/campus-wall
```

---

## Nginx Configuration

### Complete Configuration Example

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL
    ssl_certificate /etc/nginx/ssl/your-domain.com.crt;
    ssl_certificate_key /etc/nginx/ssl/your-domain.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Logs
    access_log /var/log/nginx/campus-wall-access.log;
    error_log /var/log/nginx/campus-wall-error.log;

    # Root
    root /var/www/campus-wall;
    index index.html;

    # Upload size limit
    client_max_body_size 20m;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;
    gzip_min_length 1024;

    # PC (root path)
    location / {
        alias /var/www/campus-wall/pc/;
        try_files $uri $uri/ /index.html;
    }

    # Mobile H5
    location /h5/ {
        alias /var/www/campus-wall/h5/;
        try_files $uri $uri/ /h5/index.html;
    }

    # Admin
    location /admin/ {
        alias /var/www/campus-wall/admin/;
        try_files $uri $uri/ /admin/index.html;
    }

    # Tools
    location /tools/ {
        alias /var/www/campus-wall/tools/;
    }

    # API reverse proxy
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

    # User uploads
    location /uploads/ {
        alias /var/www/campus-wall/uploads/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Static asset caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

### Enable Configuration

```bash
# Test configuration
nginx -t

# Reload
systemctl reload nginx
```

---

## Docker Deployment

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

### Start

```bash
# Build frontends
cd pc && npm install && npm run build && cd ..
cd mobile && npm install && npm run build:h5 && cd ..
cd admin && npm install && npm run build && cd ..

# Set environment variables
export SECRET_KEY=$(openssl rand -hex 32)
export ADMIN_PASSWORD=your-strong-password

# Start
docker-compose up -d

# View logs
docker-compose logs -f backend
```

---

## Systemd Service

### Create Service File

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

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/www/campus-wall/data /var/www/campus-wall/uploads

[Install]
WantedBy=multi-user.target
```

### Enable Service

```bash
systemctl daemon-reload
systemctl enable campus-wall
systemctl start campus-wall
systemctl status campus-wall
```

### Logs

```bash
journalctl -u campus-wall -f
journalctl -u campus-wall --since "1 hour ago"
```

---

## Database

### Default Database

The project uses SQLite by default. The database file is located at `backend/data/campus_wall.db`.

The backend automatically creates database tables and initial data (categories, sensitive words, admin account, etc.) on first start.

### Switch to MySQL

1. Install dependencies:
```bash
pip install aiomysql cryptography
```

2. Create database:
```sql
CREATE DATABASE campus_wall CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'campus_wall'@'localhost' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON campus_wall.* TO 'campus_wall'@'localhost';
FLUSH PRIVILEGES;
```

3. Update `.env`:
```env
DATABASE_URL=mysql+aiomysql://campus_wall:your-password@localhost:3306/campus_wall?charset=utf8mb4
```

4. Start backend to auto-create tables.

### Backup

```bash
# SQLite backup
sqlite3 data/campus_wall.db ".backup" backup_$(date +%Y%m%d).db

# MySQL backup
mysqldump -u campus_wall -p campus_wall > backup_$(date +%Y%m%d).sql
```

### Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Configuration

### Complete Configuration List

| Config | Env Variable | Default | Description |
|--------|-------------|---------|-------------|
| App Name | APP_NAME | Campus Wall | Site name |
| Debug | DEBUG | false | Set true for development |
| Host | HOST | 127.0.0.1 | Backend listen address |
| Port | PORT | 8000 | Backend listen port |
| Secret Key | SECRET_KEY | auto-generated | JWT signing key, must set manually in production |
| Database | DATABASE_URL | sqlite | Database connection URL |
| Admin Username | ADMIN_USERNAME | admin | Initial admin username |
| Admin Password | ADMIN_PASSWORD | auto-generated | Initial admin password |
| Site URL | SITE_URL | http://localhost:8000 | For email verification links |
| CORS Origins | CORS_ORIGINS | ["*"] | Allowed frontend domains |
| Redis URL | REDIS_URL | empty | Redis connection URL, in-memory limiting when empty |
| Upload Dir | UPLOAD_DIR | ./uploads | User upload directory |
| Max Upload Size | MAX_UPLOAD_SIZE | 10485760 | Max file size 10MB |
| SMTP Host | SMTP_HOST | empty | Mail server address |
| SMTP Port | SMTP_PORT | 465 | Mail server port |
| SMTP User | SMTP_USER | empty | Mail account |
| SMTP Password | SMTP_PASSWORD | empty | Mail password |
| SMTP SSL | SMTP_USE_SSL | true | Use SSL |
| From Name | SMTP_FROM_NAME | Campus Wall | Email sender name |
| WeChat AppID | WECHAT_APP_ID | empty | WeChat Mini Program AppID |
| WeChat AppSecret | WECHAT_APP_SECRET | empty | WeChat Mini Program AppSecret |
| WeChat Open AppID | WECHAT_OPEN_APP_ID | empty | WeChat Open Platform AppID |
| WeChat Open AppSecret | WECHAT_OPEN_APP_SECRET | empty | WeChat Open Platform AppSecret |

### Email Configuration Example (QQ Mail)

```env
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your-email@qq.com
SMTP_PASSWORD=your-qq-mail-authorization-code
SMTP_USE_SSL=true
SMTP_FROM_NAME=Campus Wall
```

### Email Configuration Example (Alibaba Cloud Direct Mail)

```env
SMTP_HOST=smtpdm.aliyun.com
SMTP_PORT=465
SMTP_USER=noreply@your-domain.com
SMTP_PASSWORD=your-smtp-password
SMTP_USE_SSL=true
SMTP_FROM_NAME=Campus Wall
```

---

## FAQ

### 1. Backend startup error: ModuleNotFoundError

Ensure the virtual environment is activated and all dependencies are installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Frontend page is blank

Check browser console for errors, verify:
- Nginx configuration is correct, static file paths are correct
- API proxy configuration is correct, backend service is running
- Frontend build base path matches deployment path

### 3. Image upload fails

Check:
- `uploads` directory exists and has write permission
- `MAX_UPLOAD_SIZE` is large enough
- Nginx `client_max_body_size` is large enough
- Backend `UPLOAD_DIR` path is correct

### 4. Email verification not received

Check:
- SMTP configuration is correct (HOST/PORT/USER/PASSWORD)
- Email account has SMTP service enabled
- Some email providers require an authorization code instead of login password
- Check spam folder
- When SMTP is not configured, verification links are returned in API response (development mode)

### 5. WeChat login fails

Check:
- WeChat Mini Program AppID and AppSecret are correct
- Mini Program has configured legal domains (request legal domain, uploadFile legal domain)
- WeChat Open Platform account is verified

### 6. Database is locked (SQLite)

SQLite may experience database lock errors under high concurrency. For production, use MySQL or PostgreSQL:
```env
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/campus_wall?charset=utf8mb4
```

### 7. How to change admin password

Method 1: Reset password in Admin Dashboard → User Management.
Method 2: Directly modify the database:
```bash
python3 -c "
import bcrypt
print(bcrypt.hashpw(b'new-password', bcrypt.gensalt()).decode())
"
# Then update database with the generated hash
sqlite3 data/campus_wall.db "UPDATE users SET password_hash='generated-hash' WHERE username='admin';"
```

### 8. How to enable/disable registration

In Admin Dashboard → System Settings, modify `allow_register`, or directly modify the database:
```bash
sqlite3 data/campus_wall.db "UPDATE site_settings SET value='false' WHERE key='allow_register';"
```

### 9. Log locations

- Backend logs: `backend/logs/` directory, or `journalctl -u campus-wall`
- Nginx logs: `/var/log/nginx/campus-wall-*.log`
- Access logs: database `operation_logs` table

### 10. Performance optimization tips

- Use MySQL/PostgreSQL instead of SQLite
- Enable Redis caching
- Start backend with multiple workers: `uvicorn app.main:app --workers 4`
- Configure Nginx Gzip compression and static asset caching
- Use CDN for static assets
- Regularly clean old operation logs and notifications

---

## Update Deployment

```bash
# 1. Pull latest code
git pull

# 2. Install new dependencies (if any)
cd backend && source venv/bin/activate && pip install -r requirements.txt && cd ..

# 3. Database migration (if any)
cd backend && alembic upgrade head && cd ..

# 4. Rebuild frontends
cd pc && npm install && npm run build && cd ..
cd mobile && npm install && npm run build:h5 && cd ..
cd admin && npm install && npm run build && cd ..

# 5. Deploy static files
cp -r pc/dist/* /var/www/campus-wall/pc/
cp -r mobile/dist/build/h5/* /var/www/campus-wall/h5/
cp -r admin/dist/* /var/www/campus-wall/admin/

# 6. Restart backend
systemctl restart campus-wall

# 7. Reload Nginx
nginx -t && systemctl reload nginx
```
