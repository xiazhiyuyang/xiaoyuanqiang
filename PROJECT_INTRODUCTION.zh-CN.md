# 校园墙 Campus Wall — 开源校园社区系统

> **免责声明**：本项目仅供学习和研究使用。创作者不对使用本项目造成的任何直接或间接损失承担责任，包括但不限于数据丢失、服务中断、安全漏洞、法律纠纷等。使用者应自行评估风险并承担全部责任。本项目不附带任何明示或暗示的担保。

---

## 项目简介

校园墙（Campus Wall）是一个前后端分离的校园社区系统，为校园用户提供匿名、安全、活跃的交流平台。支持发帖、评论、点赞、收藏、关注、私信、通知等完整社区功能，内置AI内容审核、敏感词过滤、设备/IP封禁、UID分配系统等高级特性。

后端基于 Python FastAPI + SQLAlchemy 2.0（异步），前端包含 PC 端（Vue 3 + Vite）、手机 H5 端（uni-app Vue 3）和管理后台（Vue 3 + Element Plus），三端共用同一套后端 API。

## 核心功能

### 社区互动

| 功能 | 说明 |
|------|------|
| 发帖系统 | 图文混排、分类标签、图片上传 |
| 评论系统 | 多级评论、回复、点赞、举报 |
| 互动体系 | 点赞、收藏、关注、粉丝 |
| 私信聊天 | 实时 WebSocket 私信、会话列表、已读状态 |
| 通知中心 | 互动通知、系统通知、未读计数 |
| 个人主页 | 自定义封面、头像、资料、UID展示 |
| 搜索功能 | 帖子搜索、用户搜索 |
| 等级系统 | 经验值、等级徽章、活跃度计算 |

### 用户系统

| 功能 | 说明 |
|------|------|
| 多种登录 | 用户名密码、邮箱（带验证）、微信登录 |
| 邮箱注册 | 邮箱验证激活、防邮箱枚举 |
| 找回密码 | 邮箱重置链接、密保问题找回 |
| 第三方登录 | 微信登录后弹出信息完善窗口 |
| UID分配 | 普通用户从01000开始；尊享号段00001-00999需管理员授予；注销后UID永久封存 |
| 账号注销 | 7天冷静期，期间可撤销 |
| 账号安全 | 密保问题、修改密码、登录设备管理 |

### 内容审核

| 功能 | 说明 |
|------|------|
| AI智能审核 | LLM文本审核 + 图片审核，多维度违规分类，风险评分自动判定通过/打码/人工复审 |
| 敏感词过滤 | 内置3500+敏感词库，支持自定义 |
| 违规打码 | 仅打码违规部分内容，不影响正常内容阅读 |
| 人工审核 | 审核队列、批量处理、审核记录 |
| 用户申诉 | 对审核结果不服可发起申诉 |
| 举报系统 | 用户举报帖子/评论/用户，管理员处理 |

### 管理后台

| 功能 | 说明 |
|------|------|
| 数据仪表盘 | 用户数、帖子数、评论数、活跃度趋势 |
| 用户管理 | 用户详情（资料/设备码/IP/登录记录）、封禁/解封、重置密码、修改资料、授予尊享UID |
| 内容管理 | 帖子管理、评论管理、分类管理 |
| 审核管理 | AI审核配置、敏感词管理、举报处理 |
| 运营管理 | 公告管理、Banner管理 |
| 系统设置 | 站点名称、注册开关、审核配置等 |
| 操作日志 | 管理员操作记录审计 |
| 封禁管理 | 账号封禁、设备封禁、IP封禁、IP白名单 |

## 技术栈

### 后端

| 技术 | 说明 |
|------|------|
| Python 3.10+ | 编程语言 |
| FastAPI | 现代异步Web框架 |
| SQLAlchemy 2.0 | 异步ORM |
| SQLite / MySQL / PostgreSQL | 数据库 |
| Pydantic v2 | 数据校验 |
| bcrypt | 密码哈希 |
| PyJWT | JWT令牌 |
| WebSocket | 实时通信 |
| Alembic | 数据库迁移 |

### 前端

| 端 | 技术栈 |
|----|--------|
| PC端 | Vue 3 + Vite + Pinia + Vue Router |
| 手机H5端 | uni-app (Vue 3) + Pinia |
| 管理后台 | Vue 3 + Element Plus + Pinia + Vue Router |

## 项目架构

```
客户端 (PC/H5/Admin)
    │ HTTP/WebSocket
    ▼
API 路由层 (FastAPI Router)
    │
    ▼
依赖注入层 (deps.py) — 认证/权限/限流
    │
    ▼
核心服务层 (core/) — 业务逻辑
    │
    ▼
数据模型层 (models/) — SQLAlchemy ORM
    │
    ▼
数据库 (SQLite/MySQL/PostgreSQL)
```

详细目录结构请参考 [PROJECT_STRUCTURE.zh-CN.md](./PROJECT_STRUCTURE.zh-CN.md)。

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- npm 或 yarn

### 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API文档：http://localhost:8000/docs

### 启动前端

```bash
# PC端
cd pc && npm install && npm run dev

# 手机H5端
cd mobile && npm install && npm run dev:h5

# 管理后台
cd admin && npm install && npm run dev
```

### 默认账号

- 管理员：`admin` / `admin123456`
- 管理后台地址：`/admin`

> 首次登录后请立即修改管理员密码。

## 配置说明

复制 `backend/.env.example` 为 `.env`，主要配置项：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `SECRET_KEY` | JWT签名密钥 | 自动生成 |
| `DATABASE_URL` | 数据库连接 | SQLite |
| `ADMIN_USERNAME` | 初始管理员用户名 | admin |
| `ADMIN_PASSWORD` | 初始管理员密码 | 自动生成 |
| `SITE_URL` | 站点URL（用于邮件验证链接） | http://localhost:8000 |
| `SMTP_*` | 邮件服务器配置 | 空（开发模式） |
| `WECHAT_*` | 微信小程序配置 | 空 |

> 未配置SMTP时，邮箱验证/重置链接会直接在API响应中返回（开发模式），方便测试。

## 部署

详细部署指南请参考 [DEPLOYMENT.zh-CN.md](./DEPLOYMENT.zh-CN.md)，包含环境要求、后端部署、前端构建、Nginx配置、Docker部署、Systemd服务、数据库配置、常见问题等。

快速Docker部署：
```bash
docker-compose up -d
```

## 数据库说明

`data/campus_wall.db` 是已脱敏的示例数据库，包含6个帖子分类、3条公告、4个Banner、3500+敏感词库、24项系统配置、1个管理员账号（admin/admin123456）、20个示例用户（无密码）。

所有用户个人信息、密码哈希、设备码、IP地址、私信内容等均已清理。如需全新数据库，删除该文件后启动后端会自动创建空数据库。

## 安全特性

- 密码bcrypt哈希（cost=12），JWT令牌版本控制
- 登录限流：10分钟内连续失败10次自动封禁IP
- 设备封禁：自动收集设备码，支持设备级封禁
- IP封禁：支持IP级封禁和IP白名单
- 邮箱安全：验证后才能登录，找回密码防枚举
- 输入安全：Pydantic校验、ORM参数化查询、CORS配置、上传文件类型/大小限制

> 本项目仍可能存在未发现的安全漏洞，使用者应自行进行安全审计并承担相应风险。

## 贡献

欢迎提交 Issue 和 Pull Request。

## 许可证

MIT License

---

**再次声明：使用本项目即表示您同意自行承担所有风险，创作者不对任何损失承担责任。**
