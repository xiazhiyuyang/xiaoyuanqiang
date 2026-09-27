# 校园墙 Campus Wall — 开源校园社区系统 / Open Source Campus Community System

> **免责声明 / Disclaimer**
>
> 本项目仅供学习和研究使用。创作者不对使用本项目造成的任何直接或间接损失承担责任，包括但不限于数据丢失、服务中断、安全漏洞、法律纠纷等。使用者应自行评估风险并承担全部责任。
>
> This project is for learning and research purposes only. The creator shall not be liable for any direct or indirect losses caused by the use of this project, including but not limited to data loss, service interruption, security vulnerabilities, legal disputes, etc. Users shall evaluate risks at their own discretion and assume full responsibility.

---

## 目录 / Table of Contents

- [项目简介 / Introduction](#项目简介--introduction)
- [核心功能 / Core Features](#核心功能--core-features)
- [技术栈 / Tech Stack](#技术栈--tech-stack)
- [系统架构 / Architecture](#系统架构--architecture)
- [快速开始 / Quick Start](#快速开始--quick-start)
- [部署 / Deployment](#部署--deployment)
- [安全特性 / Security](#安全特性--security)
- [数据库说明 / Database](#数据库说明--database)
- [贡献 / Contributing](#贡献--contributing)
- [许可证 / License](#许可证--license)

---

## 项目简介 / Introduction

**中文：**

校园墙（Campus Wall）是一个功能完整的前后端分离校园社区系统，旨在为校园用户提供一个匿名、安全、活跃的交流平台。系统支持发帖、评论、点赞、收藏、关注、私信、通知等完整的社区功能，并内置了AI内容审核、敏感词过滤、设备/IP封禁、UID分配系统等高级特性。

项目采用现代化技术栈，后端基于 Python FastAPI + SQLAlchemy 2.0（异步），前端包含 PC 端（Vue 3 + Vite）、手机 H5 端（uni-app Vue 3）和管理后台（Vue 3 + Element Plus），三端共用同一套后端 API。

**English:**

Campus Wall is a full-featured, frontend-backend separated campus community system designed to provide an anonymous, secure, and active communication platform for campus users. The system supports complete community features including posting, commenting, liking, favoriting, following, private messaging, and notifications, with built-in advanced features such as AI content moderation, sensitive word filtering, device/IP banning, and a UID allocation system.

The project adopts a modern technology stack. The backend is based on Python FastAPI + SQLAlchemy 2.0 (async), and the frontend includes a PC端 (Vue 3 + Vite), mobile H5端 (uni-app Vue 3), and admin dashboard (Vue 3 + Element Plus). All three frontends share the same backend API.

---

## 核心功能 / Core Features

### 社区互动 / Community Interaction

| 功能 / Feature | 中文说明 / Description |
|----------------|----------------------|
| 发帖系统 / Posting | 支持图文混排、分类标签、图片上传 / Supports text-image mixing, categories, tags, image upload |
| 评论系统 / Comments | 多级评论、回复、点赞、举报 / Multi-level comments, replies, likes, reports |
| 互动体系 / Interactions | 点赞、收藏、关注、粉丝 / Likes, favorites, follows, followers |
| 私信聊天 / Messaging | 实时 WebSocket 私信、会话列表、已读状态 / Real-time WebSocket messaging, conversation list, read receipts |
| 通知中心 / Notifications | 互动通知、系统通知、未读计数 / Interaction notifications, system notifications, unread count |
| 个人主页 / Profile | 自定义封面、头像、资料、UID展示 / Custom cover, avatar, profile, UID display |
| 搜索功能 / Search | 帖子搜索、用户搜索 / Post search, user search |
| 等级系统 / Levels | 经验值、等级徽章、活跃度计算 / EXP, level badges, activity calculation |

### 用户系统 / User System

| 功能 / Feature | 中文说明 / Description |
|----------------|----------------------|
| 多种登录 / Multiple Login | 用户名密码、邮箱（带验证）、微信登录 / Username-password, email (with verification), WeChat login |
| 邮箱注册 / Email Registration | 邮箱验证激活、防邮箱枚举 / Email verification activation, anti-enumeration |
| 找回密码 / Password Recovery | 邮箱重置链接、密保问题找回 / Email reset link, security question recovery |
| UID分配系统 / UID System | 普通号段01000起，尊享号段00001-00999，注销后永久封存 / Normal segment from 01000, premium segment 00001-00999, permanently sealed after deletion |
| 账号注销 / Account Deletion | 7天冷静期，期间可撤销 / 7-day cooldown period, revocable during the period |
| 账号安全 / Account Security | 密保问题、修改密码、登录设备管理 / Security question, password change, login device management |

### 内容审核 / Content Moderation

| 功能 / Feature | 中文说明 / Description |
|----------------|----------------------|
| AI智能审核 / AI Moderation | LLM文本审核 + 图片审核，多维度违规分类 / LLM text moderation + image moderation, multi-dimensional violation classification |
| 敏感词过滤 / Sensitive Words | 内置3500+敏感词库，支持自定义 / Built-in 3500+ sensitive word library, customizable |
| 违规打码 / Violation Masking | 仅打码违规部分内容，不影响正常内容阅读 / Only masks violating content, does not affect normal content reading |
| 人工审核 / Manual Review | 审核队列、批量处理、审核记录 / Review queue, batch processing, review records |
| 用户申诉 / Appeals | 对审核结果不服可发起申诉 / Users can appeal against review results |
| 举报系统 / Reports | 用户举报帖子/评论/用户，管理员处理 / Users report posts/comments/users, admins handle them |

### 管理后台 / Admin Dashboard

| 功能 / Feature | 中文说明 / Description |
|----------------|----------------------|
| 数据仪表盘 / Dashboard | 用户数、帖子数、评论数、活跃度趋势 / User count, post count, comment count, activity trends |
| 用户管理 / User Management | 用户详情、封禁/解封、重置密码、修改资料、授予尊享UID / User details, ban/unban, reset password, edit profile, grant premium UID |
| 内容管理 / Content Management | 帖子管理、评论管理、分类管理 / Post management, comment management, category management |
| 审核管理 / Moderation | AI审核配置、敏感词管理、举报处理 / AI review config, sensitive word management, report handling |
| 运营管理 / Operations | 公告管理、Banner管理 / Announcement management, Banner management |
| 系统设置 / Settings | 站点名称、注册开关、审核配置等 / Site name, registration toggle, moderation config, etc. |
| 操作日志 / Audit Logs | 管理员操作记录审计 / Admin operation record auditing |
| 封禁管理 / Ban Management | 账号封禁、设备封禁、IP封禁、IP白名单 / Account ban, device ban, IP ban, IP whitelist |

---

## 技术栈 / Tech Stack

### 后端 / Backend

| 技术 / Technology | 说明 / Description |
|-------------------|-------------------|
| Python 3.10+ | 编程语言 / Programming language |
| FastAPI | 现代异步Web框架 / Modern async web framework |
| SQLAlchemy 2.0 | 异步ORM / Async ORM |
| SQLite / MySQL / PostgreSQL | 数据库 / Database |
| Pydantic v2 | 数据校验 / Data validation |
| bcrypt | 密码哈希 / Password hashing |
| PyJWT | JWT令牌 / JWT tokens |
| WebSocket | 实时通信 / Real-time communication |
| Alembic | 数据库迁移 / Database migrations |

### 前端 / Frontend

| 端 / End | 技术栈 / Tech Stack |
|----------|-------------------|
| PC端 / PC | Vue 3 + Vite + Pinia + Vue Router |
| 手机H5端 / Mobile H5 | uni-app (Vue 3) + Pinia |
| 管理后台 / Admin | Vue 3 + Element Plus + Pinia + Vue Router |

---

## 系统架构 / Architecture

```
┌─────────────────────────────────────────────────────┐
│                    客户端层 / Client Layer            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  PC端    │  │ 手机H5端 │  │   管理后台       │  │
│  │ Vue3+Vite│  │ uni-app  │  │ Vue3+ElementPlus│  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │              │                   │            │
│       └──────────────┼───────────────────┘            │
│                      │ HTTP / WebSocket                │
├──────────────────────┼────────────────────────────────┤
│                后端服务层 / Backend (FastAPI)          │
│  ┌───────────────────┼───────────────────────────┐   │
│  │              API 路由层 / API Routes            │   │
│  │  auth │ posts │ comments │ messages │ admin... │   │
│  └───────────────────┬───────────────────────────┘   │
│                      │                                │
│  ┌───────────────────┼───────────────────────────┐   │
│  │             核心服务层 / Core Services          │   │
│  │  security │ device_mgr │ ai_moderation │ ...  │   │
│  └───────────────────┬───────────────────────────┘   │
│                      │                                │
│  ┌───────────────────┼───────────────────────────┐   │
│  │             数据模型层 / Models (ORM)           │   │
│  │  User │ Post │ Comment │ Message │ Device ...  │   │
│  └───────────────────┬───────────────────────────┘   │
│                      │                                │
├──────────────────────┼────────────────────────────────┤
│                数据存储层 / Data Storage                │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │   SQLite/    │  │    Redis     │  (可选/optional)│
│  │ MySQL/PG     │  │  (缓存/限流) │                 │
│  └──────────────┘  └──────────────┘                 │
└─────────────────────────────────────────────────────┘
```

---

## 快速开始 / Quick Start

### 环境要求 / Requirements

- Python 3.10+
- Node.js 18+
- npm or yarn

### 1. 克隆项目 / Clone

```bash
git clone https://github.com/xiazhiyuyang/xiaoyuanqiang.git
cd xiaoyuanqiang
```

### 2. 启动后端 / Start Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端API文档 / API docs: http://localhost:8000/docs

### 3. 启动PC端 / Start PC

```bash
cd pc
npm install
npm run dev
```

### 4. 启动手机H5端 / Start Mobile H5

```bash
cd mobile
npm install
npm run dev:h5
```

### 5. 启动管理后台 / Start Admin

```bash
cd admin
npm install
npm run dev
```

### 默认账号 / Default Account

- 管理员 / Admin: `admin` / `admin123456`
- 管理后台 / Admin URL: `/admin`

> 首次登录后请立即修改密码 / Please change the password immediately after first login.

---

## 部署 / Deployment

详细部署文档请参考 / For detailed deployment, please refer to:
- [DEPLOYMENT.md](./DEPLOYMENT.md) / 部署文档

### Docker快速部署 / Quick Docker Deployment

```bash
docker-compose up -d
```

### 手动部署 / Manual Deployment

1. 构建前端 / Build frontends:
```bash
cd pc && npm install && npm run build
cd ../mobile && npm install && npm run build:h5
cd ../admin && npm install && npm run build
```

2. 配置Nginx，将 `/` 指向PC端dist，`/h5` 指向手机端dist，`/admin` 指向管理后台dist，`/api` 反向代理到后端。

3. 启动后端服务（推荐使用 systemd 或 supervisor）。

---

## 安全特性 / Security

### 已实现的安全措施 / Implemented Security Measures

- ✅ 无硬编码密钥/密码 / No hardcoded secrets or passwords
- ✅ SQL注入防护（ORM参数化查询）/ SQL injection protection (ORM parameterized queries)
- ✅ XSS防护（前端输出转义）/ XSS protection (frontend output escaping)
- ✅ 密码bcrypt哈希（cost=12）/ Password bcrypt hashing (cost=12)
- ✅ JWT令牌版本控制 / JWT token version control
- ✅ 登录限流与自动封禁 / Login rate limiting and auto-banning
- ✅ 设备/IP封禁系统 / Device/IP banning system
- ✅ 邮箱验证防枚举 / Email verification anti-enumeration
- ✅ 输入校验（Pydantic）/ Input validation (Pydantic)
- ✅ CORS配置 / CORS configuration
- ✅ 文件上传类型/大小限制 / File upload type/size limits

### 设备封禁系统 / Device Banning System

- 自动收集设备码（手机端/PC端/管理后台不同前缀）/ Auto-collect device codes (different prefixes for mobile/PC/admin)
- 支持设备级封禁，封禁后该设备无法注册/登录 / Support device-level banning, banned devices cannot register/login
- 参考 FingerprintJS 浏览器指纹技术 / Reference FingerprintJS browser fingerprinting technology

### IP封禁系统 / IP Banning System

- 支持IP级封禁 / Support IP-level banning
- IP白名单机制 / IP whitelist mechanism
- 参考 fail2ban 自动封禁策略 / Reference fail2ban auto-banning strategy
- 10分钟内连续登录失败10次自动封禁IP / Auto-ban IP after 10 consecutive failed logins within 10 minutes

> **注意 / Note**: 本项目仍可能存在未发现的安全漏洞，使用者应自行进行安全审计并承担相应风险。
>
> This project may still have undiscovered security vulnerabilities. Users should conduct their own security audit and assume corresponding risks.

---

## 数据库说明 / Database

`data/campus_wall.db` 是已脱敏的示例数据库 / is a sanitized sample database:

| 数据 / Data | 数量 / Count |
|-------------|-------------|
| 帖子分类 / Categories | 6 |
| 公告 / Announcements | 3 |
| Banner | 4 |
| 敏感词 / Sensitive Words | 3500+ |
| 系统设置 / Site Settings | 24 |
| 管理员账号 / Admin Account | 1 (admin/admin123456) |
| 示例用户 / Sample Users | 20 (无密码/no password) |

所有用户个人信息、密码哈希、设备码、IP地址、私信内容等均已清理。
All user personal information, password hashes, device codes, IP addresses, private messages, etc. have been cleaned.

如需全新数据库，删除该文件后启动后端会自动创建空数据库。
For a fresh database, delete this file and start the backend to automatically create an empty database.

---

## 贡献 / Contributing

欢迎提交 Issue 和 Pull Request / Issues and Pull Requests are welcome.

### 贡献指南 / Contribution Guidelines

1. Fork 本仓库 / Fork this repository
2. 创建特性分支 / Create a feature branch: `git checkout -b feature/your-feature`
3. 提交更改 / Commit your changes: `git commit -m 'Add some feature'`
4. 推送到分支 / Push to the branch: `git push origin feature/your-feature`
5. 开启Pull Request / Open a Pull Request

---

## 许可证 / License

MIT License

Copyright (c) 2026 Campus Wall

---

**再次声明 / Repeated Statement**: 使用本项目即表示您同意自行承担所有风险，创作者不对任何损失承担责任。
By using this project, you agree to assume all risks at your own discretion, and the creator shall not be liable for any losses.
