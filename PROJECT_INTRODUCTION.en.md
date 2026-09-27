# Campus Wall — Open Source Campus Community System

> **Disclaimer**: This project is for learning and research purposes only. The creator shall not be liable for any direct or indirect losses caused by the use of this project, including but not limited to data loss, service interruption, security vulnerabilities, legal disputes, etc. Users shall evaluate risks at their own discretion and assume full responsibility. This project is provided "as is" without any warranty, express or implied.

---

## Introduction

Campus Wall is a frontend-backend separated campus community system that provides an anonymous, secure, and active communication platform for campus users. It supports complete community features including posting, commenting, liking, favoriting, following, private messaging, and notifications, with built-in advanced features such as AI content moderation, sensitive word filtering, device/IP banning, and a UID allocation system.

The backend is based on Python FastAPI + SQLAlchemy 2.0 (async), and the frontend includes a PC端 (Vue 3 + Vite), mobile H5端 (uni-app Vue 3), and admin dashboard (Vue 3 + Element Plus). All three frontends share the same backend API.

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
| UID System | Normal users from 01000; premium segment 00001-00999 requires admin grant; UID permanently sealed after deletion |
| Account Deletion | 7-day cooldown period, revocable during the period |
| Account Security | Security question, password change, login device management |

### Content Moderation

| Feature | Description |
|---------|-------------|
| AI Moderation | LLM text moderation + image moderation, multi-dimensional violation classification, risk scoring for auto pass/mask/manual review |
| Sensitive Words | Built-in 3500+ sensitive word library, customizable |
| Violation Masking | Only masks violating content, does not affect normal content reading |
| Manual Review | Review queue, batch processing, review records |
| Appeals | Users can appeal against review results |
| Reports | Users report posts/comments/users, admins handle them |

### Admin Dashboard

| Feature | Description |
|---------|-------------|
| Dashboard | User count, post count, comment count, activity trends |
| User Management | User details (profile/device code/IP/login records), ban/unban, reset password, edit profile, grant premium UID |
| Content Management | Post management, comment management, category management |
| Moderation | AI review config, sensitive word management, report handling |
| Operations | Announcement management, Banner management |
| Settings | Site name, registration toggle, moderation config, etc. |
| Audit Logs | Admin operation record auditing |
| Ban Management | Account ban, device ban, IP ban, IP whitelist |

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

## Architecture

```
Client (PC/H5/Admin)
    │ HTTP/WebSocket
    ▼
API Routes (FastAPI Router)
    │
    ▼
Dependency Injection (deps.py) — auth/permissions/rate limiting
    │
    ▼
Core Services (core/) — business logic
    │
    ▼
Data Models (models/) — SQLAlchemy ORM
    │
    ▼
Database (SQLite/MySQL/PostgreSQL)
```

For detailed directory structure, please refer to [PROJECT_STRUCTURE.en.md](./PROJECT_STRUCTURE.en.md).

## Quick Start

### Requirements

- Python 3.10+
- Node.js 18+
- npm or yarn

### Start Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### Start Frontend

```bash
# PC
cd pc && npm install && npm run dev

# Mobile H5
cd mobile && npm install && npm run dev:h5

# Admin
cd admin && npm install && npm run dev
```

### Default Account

- Admin: `admin` / `admin123456`
- Admin URL: `/admin`

> Please change the password immediately after first login.

## Configuration

Copy `backend/.env.example` to `.env`, key configuration items:

| Config | Description | Default |
|--------|-------------|---------|
| `SECRET_KEY` | JWT signing key | auto-generated |
| `DATABASE_URL` | Database connection | SQLite |
| `ADMIN_USERNAME` | Initial admin username | admin |
| `ADMIN_PASSWORD` | Initial admin password | auto-generated |
| `SITE_URL` | Site URL (for email verification links) | http://localhost:8000 |
| `SMTP_*` | Mail server configuration | empty (dev mode) |
| `WECHAT_*` | WeChat Mini Program configuration | empty |

> When SMTP is not configured, verification/reset links are returned directly in the API response (development mode) for easy testing.

## Deployment

For detailed deployment guide, please refer to [DEPLOYMENT.en.md](./DEPLOYMENT.en.md), including environment requirements, backend deployment, frontend build, Nginx configuration, Docker deployment, Systemd service, database configuration, FAQ, etc.

Quick Docker deployment:
```bash
docker-compose up -d
```

## Database

`data/campus_wall.db` is a sanitized sample database containing 6 post categories, 3 announcements, 4 banners, 3500+ sensitive words, 24 site settings, 1 admin account (admin/admin123456), and 20 sample users (no password).

All user personal information, password hashes, device codes, IP addresses, private messages, etc. have been cleaned. For a fresh database, delete this file and start the backend to automatically create an empty database.

## Security

- Password bcrypt hashing (cost=12), JWT token version control
- Login rate limiting: auto-ban IP after 10 consecutive failures within 10 minutes
- Device banning: auto-collect device codes, support device-level ban
- IP banning: support IP-level ban and IP whitelist
- Email security: login after verification, anti-enumeration for password recovery
- Input security: Pydantic validation, ORM parameterized queries, CORS configuration, file upload type/size limits

> This project may still have undiscovered security vulnerabilities. Users should conduct their own security audit and assume corresponding risks.

## Contributing

Issues and Pull Requests are welcome.

## License

MIT License

---

**Repeated Statement**: By using this project, you agree to assume all risks at your own discretion, and the creator shall not be liable for any losses.
