# 校园墙 Campus Wall

一个功能完整的校园社区系统，包含社区发帖、评论互动、私信聊天、AI内容审核、用户管理、设备/IP封禁、UID系统等功能。前后端分离，支持PC端、手机H5端和管理后台。

> **免责声明**：本项目仅供学习和研究使用。创作者不对使用本项目造成的任何直接或间接损失承担责任。使用者应自行评估风险并承担全部责任。

## 文档 / Documentation

| 文档 | 中文 | English |
|------|------|---------|
| 项目介绍 / Introduction | [PROJECT_INTRODUCTION.zh-CN.md](./PROJECT_INTRODUCTION.zh-CN.md) | [PROJECT_INTRODUCTION.en.md](./PROJECT_INTRODUCTION.en.md) |
| 项目结构 / Structure | [PROJECT_STRUCTURE.zh-CN.md](./PROJECT_STRUCTURE.zh-CN.md) | [PROJECT_STRUCTURE.en.md](./PROJECT_STRUCTURE.en.md) |
| 部署文档 / Deployment | [DEPLOYMENT.zh-CN.md](./DEPLOYMENT.zh-CN.md) | [DEPLOYMENT.en.md](./DEPLOYMENT.en.md) |

## 技术栈

- **后端**: Python 3.10+ / FastAPI / SQLAlchemy 2.0 (async) / SQLite
- **PC端**: Vue 3 + Vite + Pinia
- **手机H5端**: uni-app (Vue 3) + Pinia
- **管理后台**: Vue 3 + Element Plus + Pinia
- **认证**: JWT (bcrypt密码哈希)
- **AI审核**: 支持LLM文本审核 + 图片审核（可配置）

## 功能特性

### 社区功能
- 发帖（支持图文）、分类、标签
- 评论、回复、点赞、收藏、关注
- 私信聊天（实时WebSocket）
- 通知系统（互动通知、系统通知）
- 走马灯公告、Banner轮播
- 个人主页（自定义封面、头像、资料）

### 用户系统
- 用户名密码注册/登录
- 邮箱注册/登录/找回密码（带邮箱验证）
- 微信登录（小程序/公众号H5）
- 第三方登录后信息完善
- UID分配系统（普通号段01000起，尊享号段00001-00999）
- 账号注销（7天冷静期）
- 密保问题找回密码
- 用户等级/经验系统

### 内容审核
- AI智能审核（文本+图片）
- 敏感词过滤（3500+词库）
- 违规内容打码（仅打码违规部分）
- 人工审核队列
- 用户申诉机制
- 举报系统

### 管理后台
- 数据统计仪表盘
- 用户管理（详情、封禁、重置密码、修改资料）
- 帖子/评论管理
- 分类管理
- 敏感词管理
- AI审核配置
- 系统设置
- 操作日志
- 封禁管理（账号/设备/IP）

### 安全特性
- 设备码收集与设备封禁
- IP封禁与白名单
- 登录失败自动封禁（10分钟10次）
- 密码强度校验（最少8位）
- JWT令牌版本控制（修改密码后旧token失效）
- 邮箱验证（防邮箱枚举）
- CORS配置
- 输入校验与SQL注入防护

## 项目结构

```
campus-wall/
├── backend/              # 后端服务
│   ├── app/
│   │   ├── api/          # API路由
│   │   ├── core/         # 核心服务（安全、设备管理、AI审核等）
│   │   ├── models/       # 数据模型
│   │   ├── schemas/      # Pydantic schema
│   │   ├── services/     # 业务服务
│   │   ├── config.py     # 配置
│   │   ├── database.py   # 数据库连接
│   │   └── main.py       # 应用入口
│   ├── requirements.txt
│   └── .env.example
├── pc/                   # PC端前端
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── mobile/               # 手机H5端（uni-app）
│   ├── pages/
│   ├── stores/
│   ├── utils/
│   ├── package.json
│   └── manifest.json
├── admin/                # 管理后台
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── data/                 # 数据库文件
│   └── campus_wall.db    # 已脱敏的示例数据库
├── tools/                # 独立小工具
├── nginx/                # Nginx配置示例
├── docs/                 # 文档
└── docker-compose.yml    # Docker部署配置
```

## 快速开始

### 环境要求
- Python 3.10+
- Node.js 18+
- npm 或 yarn

### 1. 后端启动

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 复制配置文件
cp .env.example .env
# 编辑 .env 配置（SECRET_KEY会自动生成）

# 启动开发服务器
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端API文档: http://localhost:8000/docs

### 2. PC端启动

```bash
cd pc
npm install
npm run dev
```

### 3. 手机H5端启动

```bash
cd mobile
npm install
npm run dev:h5
```

### 4. 管理后台启动

```bash
cd admin
npm install
npm run dev
```

## 默认账号

- **管理员**: admin / admin123456
  - 首次登录后请立即修改密码
  - 管理后台地址: /admin

## 配置说明

复制 `backend/.env.example` 为 `.env`，主要配置项：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `SECRET_KEY` | JWT签名密钥 | 自动生成 |
| `DATABASE_URL` | 数据库连接 | SQLite |
| `ADMIN_USERNAME` | 初始管理员用户名 | admin |
| `ADMIN_PASSWORD` | 初始管理员密码 | 自动生成 |
| `SITE_URL` | 站点URL（用于邮箱验证链接） | http://localhost:8000 |
| `SMTP_HOST` | SMTP服务器 | 空（开发模式） |
| `SMTP_PORT` | SMTP端口 | 465 |
| `SMTP_USER` | SMTP用户名 | 空 |
| `SMTP_PASSWORD` | SMTP密码 | 空 |
| `WECHAT_APP_ID` | 微信小程序AppID | 空 |
| `WECHAT_APP_SECRET` | 微信小程序Secret | 空 |

> 未配置SMTP时，邮箱验证/重置链接会直接在API响应中返回（开发模式），方便测试。

## 部署

### Docker部署

```bash
docker-compose up -d
```

### 手动部署

参考 `docs/` 目录下的部署文档。

## 数据库说明

`data/campus_wall.db` 是已脱敏的示例数据库，包含：
- 6个帖子分类
- 3条公告
- 4个Banner
- 3500+敏感词库
- 24项系统配置
- 1个管理员账号（admin/admin123456）
- 20个示例用户（无密码，无法登录）



## 安全说明

本项目已进行安全审计，包括：
- 无硬编码密钥/密码
- SQL注入防护（ORM参数化查询）
- XSS防护（前端输出转义）
- 密码bcrypt哈希
- JWT令牌版本控制
- 登录限流与自动封禁
- 设备/IP封禁系统
- 邮箱验证防枚举


## 贡献

欢迎提交Issue和Pull Request。

## 许可证

MIT License
