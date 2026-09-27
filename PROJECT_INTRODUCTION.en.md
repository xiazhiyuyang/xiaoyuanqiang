# Campus Wall — Open Source Campus Community System

> **Disclaimer**
>
> This project is for learning and research purposes only. The creator shall not be liable for any direct or indirect losses caused by the use of this project, including but not limited to data loss, service interruption, security vulnerabilities, legal disputes, etc. Users shall evaluate risks at their own discretion and assume full responsibility. This project is provided "as is" without any warranty, express or implied.

---

## Table of Contents

- [Introduction](#introduction)
- [Core Features](#core-features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [Security](#security)
- [Database](#database)
- [Contributing](#contributing)
- [License](#license)

---

## Introduction

Campus Wall is a full-featured, frontend-backend separated campus community system designed to provide an anonymous, secure, and active communication platform for campus users. The system supports complete community features including posting, commenting, liking, favoriting, following, private messaging, and notifications, with built-in advanced features such as AI content moderation, sensitive word filtering, device/IP banning, and a UID allocation system.

The project adopts a modern technology stack. The backend is based on Python FastAPI + SQLAlchemy 2.0 (async), and the frontend includes a PC端 (Vue 3 + Vite), mobile H5端 (uni-app Vue 3), and admin dashboard (Vue 3 + Element Plus). All three frontends share the same backend API.

---

## Core Features

### Community Interaction

| Feature | Description |
|---------|-------------|
| Posting | Text-image mixing, categories, tags, image upload |
| Comments | Multi-level comments, replies, likes, reports |
| Interactions | Likes, favorites, follows, followers |
| Messaging | Real-time WebSocket messaging, conversation list, read receipts |
| Notifications | Interaction notifications, system notifications, unread count |
| Profile | Custom cover, avatar, profile, UID display |
| Search | Post search, user search |
| Levels | EXP, level badges, activity calculation |

### User System

| Feature | Description |
|---------|-------------|
| Multiple Login | Username-password, email (with verification), WeChat login |
| Email Registration | Email verification activation, anti-enumeration |
| Password Recovery | Email reset link, security question recovery |
| Third-party Login | Profile completion modal after WeChat login |
| UID System | Normal segment from 01000, premium segment 00001-00999, permanently sealed after deletion |
| Account Deletion | 7-day cooldown period, revocable during the period |
| Account Security | Security question, password change, login device management |

### Content Moderation

| Feature | Description |
|---------|-------------|
| AI Moderation | LLM text moderation + image moderation, multi-dimensional violation classification |
| Sensitive Words | Built-in 3500+ sensitive word library, customizable |
| Violation Masking | Only masks violating content, does not affect normal content reading |
| Manual Review | Review queue, batch processing, review records |
| Appeals | Users can appeal against review results |
| Reports | Users report posts/comments/users, admins handle them |

### Admin Dashboard

| Feature | Description |
|---------|-------------|
| Dashboard | User count, post count, comment count, activity trends |
| User Management | User details, ban/unban, reset password, edit profile, grant premium UID |
| Content Management | Post management, comment management, category management |
| Moderation | AI review config, sensitive word management, report handling |
| Operations | Announcement management, Banner management |
| Settings | Site name, registration toggle, moderation config, etc. |
| Audit Logs | Admin operation record auditing |
| Ban Management | Account ban, device ban, IP ban, IP whitelist |

---

## Tech Stack

### Backend

| Technology | Description |
|------------|-------------|
| Python 3.10+ | Programming language |
| FastAPI | Modern async web framework |
| SQLAlchemy 2.0 | Async ORM |
| SQLite / MySQL / PostgreSQL | Database |
| Pydantic v2 | Data validation |
| bcrypt | Password hashing |
| PyJWT | JWT tokens |
| WebSocket | Real-time communication |
| Alembic | Database migrations |

### Frontend

| End | Tech Stack |
|-----|-----------|
| PC | Vue 3 + Vite + Pinia + Vue Router |
| Mobile H5 | uni-app (Vue 3) + Pinia |
| Admin | Vue 3 + Element Plus + Pinia + Vue Router |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Client Layer                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │    PC    │  │ Mobile H5│  │   Admin Dashboard│  │
│  │ Vue3+Vite│  │ uni-app  │  │ Vue3+ElementPlus│  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │              │                   │            │
│       └──────────────┼───────────────────┘            │
│                      │ HTTP / WebSocket                │
├──────────────────────┼────────────────────────────────┤
│                Backend Layer (FastAPI)                 │
│  ┌───────────────────┼───────────────────────────┐   │
│  │              API Routes                         │   │
│  │  auth │ posts │ comments │ messages │ admin... │   │
│  └───────────────────┬───────────────────────────┘   │
│                      │                                │
│  ┌───────────────────┼───────────────────────────┐   │
│  │             Core Services                       │   │
│  │  security │ device_mgr │ ai_moderation │ ...  │   │
│  └───────────────────┬───────────────────────────┘   │
│                      │                                │
│  ┌───────────────────┼───────────────────────────┐   │
│  │             Models (ORM)                        │   │
│  │  User │ Post │ Comment │ Message │ Device ...  │   │
│  └───────────────────┬───────────────────────────┘   │
│                      │                                │
├──────────────────────┼────────────────────────────────┤
│                Data Storage                            │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │ SQLite/MySQL/│  │    Redis     │  (optional)     │
│  │ PostgreSQL   │  │  (cache/rate)│                 │
│  └──────────────┘  └──────────────┘                 │
└─────────────────────────────────────────────────────┘
```

---

## Quick Start

### Requirements

- Python 3.10+
- Node.js 18+
- npm or yarn

### 1. Clone

```bash
git clone https://github.com/xiazhiyuyang/xiaoyuanqiang.git
cd xiaoyuanqiang
```

### 2. Start Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### 3. Start PC

```bash
cd pc
npm install
npm run dev
```

### 4. Start Mobile H5

```bash
cd mobile
npm install
npm run dev:h5
```

### 5. Start Admin

```bash
cd admin
npm install
npm run dev
```

### Default Account

- Admin: `admin` / `admin123456`
- Admin URL: `/admin`

> Please change the password immediately after first login.

---

## Deployment

For detailed deployment, please refer to:
- [DEPLOYMENT.en.md](./DEPLOYMENT.en.md) / Deployment Guide

### Quick Docker Deployment

```bash
docker-compose up -d
```

### Manual Deployment

1. Build frontends:
```bash
cd pc && npm install && npm run build
cd ../mobile && npm install && npm run build:h5
cd ../admin && npm install && npm run build
```

2. Configure Nginx: map `/` to PC dist, `/h5` to mobile dist, `/admin` to admin dist, `/api` reverse proxy to backend.

3. Start backend service (recommend systemd or supervisor).

---

## Security

### Implemented Security Measures

- ✅ No hardcoded secrets or passwords
- ✅ SQL injection protection (ORM parameterized queries)
- ✅ XSS protection (frontend output escaping)
- ✅ Password bcrypt hashing (cost=12)
- ✅ JWT token version control
- ✅ Login rate limiting and auto-banning
- ✅ Device/IP banning system
- ✅ Email verification anti-enumeration
- ✅ Input validation (Pydantic)
- ✅ CORS configuration
- ✅ File upload type/size limits

### Device Banning System

- Auto-collect device codes (different prefixes for mobile/PC/admin)
- Support device-level banning, banned devices cannot register/login
- Reference FingerprintJS browser fingerprinting technology

### IP Banning System

- Support IP-level banning
- IP whitelist mechanism
- Reference fail2ban auto-banning strategy
- Auto-ban IP after 10 consecutive failed logins within 10 minutes

> **Note**: This project may still have undiscovered security vulnerabilities. Users should conduct their own security audit and assume corresponding risks.

---

## Database

`data/campus_wall.db` is a sanitized sample database:

| Data | Count |
|------|-------|
| Categories | 6 |
| Announcements | 3 |
| Banners | 4 |
| Sensitive Words | 3500+ |
| Site Settings | 24 |
| Admin Account | 1 (admin/admin123456) |
| Sample Users | 20 (no password) |

All user personal information, password hashes, device codes, IP addresses, private messages, etc. have been cleaned.

For a fresh database, delete this file and start the backend to automatically create an empty database.

---

## Contributing

Issues and Pull Requests are welcome.

### Contribution Guidelines

1. Fork this repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## License

MIT License

Copyright (c) 2026 Campus Wall

---

**Repeated Statement**: By using this project, you agree to assume all risks at your own discretion, and the creator shall not be liable for any losses.
