# 项目结构说明

```
campus-wall/
├── backend/                          # 后端服务（Python FastAPI）
│   ├── app/
│   │   ├── api/                      # API 路由层
│   │   │   ├── admin/                # 管理后台 API
│   │   │   │   ├── bans.py           #   封禁管理（账号/设备/IP）
│   │   │   │   ├── categories.py     #   分类管理
│   │   │   │   ├── comments.py       #   评论管理
│   │   │   │   ├── dashboard.py      #   数据仪表盘统计
│   │   │   │   ├── logs.py           #   操作日志
│   │   │   │   ├── posts.py          #   帖子管理
│   │   │   │   ├── promotions.py     #   公告/Banner管理
│   │   │   │   ├── reports.py        #   举报管理
│   │   │   │   ├── sensitive.py      #   敏感词管理
│   │   │   │   ├── settings.py       #   系统设置
│   │   │   │   ├── users.py          #   用户管理（详情/封禁/重置密码）
│   │   │   │   └── _utils.py         #   管理后台工具函数
│   │   │   ├── ai_guard.py           # AI内容守卫（发布前拦截）
│   │   │   ├── ai_review.py          # AI审核配置与记录
│   │   │   ├── app_update.py         # APP版本更新检查
│   │   │   ├── auth.py               # 认证（注册/登录/邮箱/微信/找回/注销）
│   │   │   ├── comments.py           # 评论API（增删改查/点赞）
│   │   │   ├── deps.py               # 依赖注入（当前用户/权限校验）
│   │   │   ├── messages.py           # 私信API（会话/消息/已读）
│   │   │   ├── notifications.py      # 通知API（列表/已读/未读数）
│   │   │   ├── posts.py              # 帖子API（增删改查/点赞/收藏/关注）
│   │   │   ├── promotions.py         # 公告/Banner API
│   │   │   ├── reports.py            # 举报API
│   │   │   ├── review.py             # 人工审核API
│   │   │   ├── settings_api.py       # 站点设置API
│   │   │   ├── stats.py              # 统计API
│   │   │   ├── tools.py              # 工具箱API
│   │   │   ├── upload.py             # 文件上传API
│   │   │   ├── users.py              # 用户API（资料/修改/关注/粉丝）
│   │   │   └── ws.py                 # WebSocket（实时通知/私信）
│   │   ├── core/                     # 核心服务层
│   │   │   ├── ai_moderation/        # AI审核引擎
│   │   │   │   ├── categories.py     #   违规分类定义
│   │   │   │   ├── config.py         #   审核配置
│   │   │   │   ├── decision.py       #   审核决策逻辑
│   │   │   │   ├── domains.py        #   违规领域定义
│   │   │   │   ├── image.py          #   图片审核
│   │   │   │   ├── lexicon_import.py #   敏感词库导入
│   │   │   │   ├── llm.py            #   LLM文本审核
│   │   │   │   ├── normalize.py      #   文本归一化
│   │   │   │   ├── pipeline.py       #   审核流水线
│   │   │   │   ├── rules.py          #   规则引擎
│   │   │   │   └── scoring.py        #   风险评分
│   │   │   ├── activity.py           # 活跃度计算
│   │   │   ├── device_mgr.py         # 设备管理（设备码生成/记录/封禁）
│   │   │   ├── email_service.py      # 邮件服务（SMTP/验证token/重置）
│   │   │   ├── hotness.py            # 帖子热度算法
│   │   │   ├── levels.py             # 用户等级/经验系统
│   │   │   ├── moderation.py         # 内容审核服务
│   │   │   ├── ratelimit.py          # 限流（登录失败/IP封禁）
│   │   │   ├── redis_client.py       # Redis客户端
│   │   │   ├── security.py           # 安全（JWT/bcrypt/密码校验）
│   │   │   ├── uid_allocator.py      # UID分配系统（普通/尊享号段）
│   │   │   └── ws_manager.py         # WebSocket连接管理
│   │   ├── models/                   # 数据模型（SQLAlchemy ORM）
│   │   │   ├── ai_review.py          # AI审核记录/配置/申诉
│   │   │   ├── comment.py            # 评论
│   │   │   ├── device.py             # 设备/设备封禁/IP封禁/登录失败
│   │   │   ├── email_verification.py # 邮箱验证/密码重置token
│   │   │   ├── interaction.py        # 点赞/收藏/关注
│   │   │   ├── message.py            # 私信会话/消息
│   │   │   ├── moderation.py         # 审核记录/申诉
│   │   │   ├── notification.py       # 通知
│   │   │   ├── operation_log.py      # 操作日志
│   │   │   ├── post.py               # 帖子/帖子图片
│   │   │   ├── promotion.py          # 公告/Banner
│   │   │   ├── report.py             # 举报
│   │   │   ├── sensitive_word.py     # 敏感词
│   │   │   ├── site_setting.py       # 站点设置
│   │   │   ├── tool.py               # 工具箱分类/工具
│   │   │   ├── uid.py                # UID分配记录
│   │   │   └── user.py               # 用户
│   │   ├── schemas/                  # Pydantic Schema（请求/响应校验）
│   │   │   ├── admin.py              # 管理后台Schema
│   │   │   ├── comment.py            # 评论Schema
│   │   │   ├── common.py             # 通用Schema（分页/统一响应）
│   │   │   ├── message.py            # 私信Schema
│   │   │   ├── post.py               # 帖子Schema
│   │   │   ├── report.py             # 举报Schema
│   │   │   └── user.py               # 用户Schema（注册/登录/邮箱/完善资料）
│   │   ├── services/                 # 业务服务层
│   │   │   ├── auth_service.py       # 认证服务
│   │   │   └── user_service.py       # 用户服务
│   │   ├── app-update.json           # APP版本更新配置
│   │   ├── config.py                 # 配置管理（环境变量/自动生成密钥）
│   │   ├── database.py               # 数据库连接（async SQLAlchemy）
│   │   └── main.py                   # 应用入口（FastAPI app/中间件/迁移）
│   ├── alembic/                      # 数据库迁移
│   ├── scripts/                      # 脚本
│   ├── tests/                        # 测试
│   ├── Dockerfile                    # Docker镜像
│   ├── requirements.txt              # Python依赖
│   └── .env.example                  # 环境变量示例
│
├── pc/                               # PC端前端（Vue 3 + Vite）
│   ├── src/
│   │   ├── api/                      # API封装
│   │   │   ├── client.js             #   Axios实例（拦截器/错误处理）
│   │   │   └── index.js              #   API方法集合
│   │   ├── components/               # 通用组件
│   │   │   ├── AnnouncementsCard.vue #   走马灯公告
│   │   │   ├── CommentItem.vue       #   评论项
│   │   │   ├── EmptyState.vue        #   空状态
│   │   │   ├── FeedSkeleton.vue      #   骨架屏
│   │   │   ├── FollowButton.vue      #   关注按钮
│   │   │   ├── Icon.vue              #   SVG图标
│   │   │   ├── ImageGrid.vue         #   图片网格
│   │   │   ├── LevelBadge.vue        #   等级徽章
│   │   │   ├── Modal.vue             #   弹窗
│   │   │   ├── PostCard.vue          #   帖子卡片
│   │   │   ├── PostComposer.vue      #   发帖编辑器
│   │   │   ├── ReportDialog.vue      #   举报弹窗
│   │   │   ├── SuggestCard.vue       #   推荐用户
│   │   │   ├── ToastHost.vue         #   Toast提示
│   │   │   └── UserAvatar.vue        #   用户头像
│   │   ├── layouts/
│   │   │   └── MainLayout.vue        # 主布局（导航/侧边栏）
│   │   ├── pages/                    # 页面
│   │   │   ├── Home.vue              #   首页（信息流）
│   │   │   ├── Login.vue             #   登录/注册/找回（账号密码/邮箱）
│   │   │   ├── PostDetail.vue        #   帖子详情
│   │   │   ├── Profile.vue           #   个人主页
│   │   │   ├── Messages.vue          #   私信
│   │   │   ├── Notifications.vue     #   通知
│   │   │   ├── Follows.vue           #   关注/粉丝
│   │   │   ├── Settings.vue          #   设置
│   │   │   ├── Review.vue            #   审核中心
│   │   │   ├── Tools.vue             #   工具箱
│   │   │   ├── ToolDetail.vue        #   工具详情
│   │   │   ├── Levels.vue            #   等级说明
│   │   │   ├── NotFound.vue          #   404
│   │   │   └── MeRedirect.vue        #   我的主页重定向
│   │   ├── router/
│   │   │   └── index.js              # 路由配置
│   │   ├── stores/                    # Pinia状态管理
│   │   │   ├── app.js                #   应用状态（设置/主题）
│   │   │   └── auth.js               #   认证状态（用户/token）
│   │   ├── styles/                    # 样式
│   │   │   ├── base.css              #   基础样式
│   │   │   ├── tokens.css            #   设计令牌
│   │   │   └── variables.css         #   CSS变量
│   │   ├── utils/                     # 工具函数
│   │   │   ├── device-fingerprint.js #   设备指纹
│   │   │   ├── format.js             #   格式化（时间/数字）
│   │   │   └── toast.js              #   Toast
│   │   ├── App.vue                   # 根组件
│   │   └── main.js                   # 入口
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── mobile/                           # 手机H5端（uni-app Vue 3）
│   ├── pages/                        # 页面
│   │   ├── index/index.vue           #   首页（信息流）
│   │   ├── login/login.vue           #   登录/注册（账号密码/邮箱）
│   │   ├── account/                  #   账号
│   │   │   ├── forgot.vue            #     找回密码
│   │   │   ├── password.vue          #     修改密码
│   │   │   └── security.vue          #     账号安全
│   │   ├── agreement/privacy.vue     #   隐私协议
│   │   ├── level/level.vue           #   等级说明
│   │   ├── message/                  #   私信
│   │   │   ├── inbox.vue             #     会话列表
│   │   │   └── chat.vue              #     聊天
│   │   ├── notifications/list.vue    #   通知列表
│   │   ├── post/                     #   帖子
│   │   │   ├── create.vue            #     发帖
│   │   │   ├── detail.vue            #     帖子详情
│   │   │   └── edit.vue              #     编辑帖子
│   │   ├── profile/                  #   个人
│   │   │   ├── mine.vue              #     我的
│   │   │   ├── profile.vue           #     个人主页
│   │   │   ├── edit.vue              #     编辑资料
│   │   │   └── privacy.vue           #     隐私设置
│   │   ├── review/                   #   审核
│   │   │   ├── center.vue            #     审核中心
│   │   │   ├── posts.vue             #     帖子审核
│   │   │   └── reports.vue           #     举报审核
│   │   ├── search/search.vue         #   搜索
│   │   ├── settings/settings.vue     #   设置
│   │   ├── splash/splash.vue         #   启动页
│   │   └── user/follows.vue          #   关注/粉丝
│   ├── components/                    # 组件
│   ├── stores/                        # Pinia状态
│   │   └── user.js                   #   用户状态
│   ├── utils/                         # 工具
│   │   ├── api.js                    #   API封装
│   │   ├── link.js                   #   页面跳转
│   │   ├── theme.js                  #   主题
│   │   ├── updater.js                #   APP更新
│   │   └── ws.js                     #   WebSocket
│   ├── static/                        # 静态资源（图标/Logo）
│   ├── App.vue                       # 根组件
│   ├── main.js                       # 入口
│   ├── pages.json                    # 页面路由配置
│   ├── manifest.json                 # uni-app配置
│   ├── package.json
│   └── vite.config.js
│
├── admin/                            # 管理后台（Vue 3 + Element Plus）
│   ├── src/
│   │   ├── api/index.js              # API封装
│   │   ├── layouts/
│   │   │   └── AdminLayout.vue       # 后台布局（侧边栏/顶栏）
│   │   ├── views/                     # 页面
│   │   │   ├── Login.vue             #   登录
│   │   │   ├── Dashboard.vue         #   数据仪表盘
│   │   │   ├── Users.vue             #   用户管理（详情/封禁/重置密码）
│   │   │   ├── Posts.vue             #   帖子管理
│   │   │   ├── Comments.vue          #   评论管理
│   │   │   ├── Categories.vue        #   分类管理
│   │   │   ├── SensitiveWords.vue    #   敏感词管理
│   │   │   ├── AiReview.vue          #   AI审核配置
│   │   │   ├── Reports.vue           #   举报管理
│   │   │   ├── Promotions.vue        #   公告/Banner管理
│   │   │   ├── Settings.vue          #   系统设置
│   │   │   └── Logs.vue              #   操作日志
│   │   ├── router/index.js           # 路由
│   │   ├── stores/auth.js            # 认证状态
│   │   ├── styles/theme.css          # 主题样式
│   │   ├── App.vue
│   │   └── main.js
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── data/                             # 数据库
│   └── campus_wall.db                # SQLite数据库（已脱敏）
│
├── tools/                            # 独立小工具（纯HTML）
│   ├── base64.html                   # Base64编解码
│   ├── color-picker.html             # 颜色选择器
│   ├── json-formatter.html           # JSON格式化
│   ├── regex-tester.html             # 正则测试
│   └── timestamp.html                # 时间戳转换
│
├── docs/                             # 文档
├── nginx/                            # Nginx配置示例
│   └── nginx.conf
├── docker-compose.yml                # Docker Compose配置
├── .env.example                      # 环境变量示例
├── LICENSE                           # MIT许可证
└── README.md                         # 项目说明
```

## 技术架构

```
┌─────────────────────────────────────────────────────┐
│                    客户端层                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  PC端    │  │ 手机H5端 │  │   管理后台       │  │
│  │ Vue3+Vite│  │ uni-app  │  │ Vue3+ElementPlus│  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │              │                   │            │
│       └──────────────┼───────────────────┘            │
│                      │ HTTP / WebSocket                │
├──────────────────────┼────────────────────────────────┤
│                后端服务层 (FastAPI)                    │
│  ┌───────────────────┼───────────────────────────┐   │
│  │              API 路由层                          │   │
│  │  auth │ posts │ comments │ messages │ admin... │   │
│  └───────────────────┬───────────────────────────┘   │
│                      │                                │
│  ┌───────────────────┼───────────────────────────┐   │
│  │             核心服务层                           │   │
│  │  security │ device_mgr │ ai_moderation │ ...  │   │
│  └───────────────────┬───────────────────────────┘   │
│                      │                                │
│  ┌───────────────────┼───────────────────────────┐   │
│  │             数据模型层 (SQLAlchemy)             │   │
│  │  User │ Post │ Comment │ Message │ Device ...  │   │
│  └───────────────────┬───────────────────────────┘   │
│                      │                                │
├──────────────────────┼────────────────────────────────┤
│                数据存储层                              │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │   SQLite     │  │    Redis     │  (可选)         │
│  │  (主数据库)   │  │  (缓存/限流) │                 │
│  └──────────────┘  └──────────────┘                 │
└─────────────────────────────────────────────────────┘
```

## 数据库表清单

| 表名 | 说明 |
|------|------|
| users | 用户表 |
| posts | 帖子表 |
| post_images | 帖子图片表 |
| comments | 评论表 |
| conversations | 私信会话表 |
| messages | 私信消息表 |
| notifications | 通知表 |
| like_records | 点赞记录表 |
| favorites | 收藏表 |
| follows | 关注关系表 |
| reports | 举报表 |
| categories | 分类表 |
| sensitive_words | 敏感词表 |
| announcements | 公告表 |
| banners | Banner表 |
| site_settings | 站点设置表 |
| operation_logs | 操作日志表 |
| devices | 设备记录表 |
| device_bans | 设备封禁表 |
| ip_bans | IP封禁表 |
| ip_whitelist | IP白名单表 |
| login_failures | 登录失败记录表 |
| email_verifications | 邮箱验证/重置token表 |
| uid_allocations | UID分配记录表 |
| moderation_records | 审核记录表 |
| moderation_appeals | 审核申诉表 |
| ai_review_records | AI审核记录表 |
| ai_review_config | AI审核配置表 |
| ai_review_appeals | AI审核申诉表 |
| tool_categories | 工具分类表 |
| tools | 工具表 |
