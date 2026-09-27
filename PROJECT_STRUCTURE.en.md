# Project Structure

```
campus-wall/
├── backend/                          # Backend service (Python FastAPI)
│   ├── app/
│   │   ├── api/                      # API routes
│   │   │   ├── admin/                # Admin API
│   │   │   │   ├── bans.py           #   Ban management (account/device/IP)
│   │   │   │   ├── categories.py     #   Category management
│   │   │   │   ├── comments.py       #   Comment management
│   │   │   │   ├── dashboard.py      #   Dashboard statistics
│   │   │   │   ├── logs.py           #   Operation logs
│   │   │   │   ├── posts.py          #   Post management
│   │   │   │   ├── promotions.py     #   Announcement/Banner management
│   │   │   │   ├── reports.py        #   Report management
│   │   │   │   ├── sensitive.py      #   Sensitive word management
│   │   │   │   ├── settings.py       #   System settings
│   │   │   │   ├── users.py          #   User management (details/ban/reset password)
│   │   │   │   └── _utils.py         #   Admin utility functions
│   │   │   ├── ai_guard.py           # AI content guard (pre-publish interception)
│   │   │   ├── ai_review.py          # AI review config and records
│   │   │   ├── app_update.py         # APP version update check
│   │   │   ├── auth.py               # Auth (register/login/email/wechat/recovery/deletion)
│   │   │   ├── comments.py           # Comment API (CRUD/likes)
│   │   │   ├── deps.py               # Dependency injection (current user/permission check)
│   │   │   ├── messages.py           # Private message API (conversations/messages/read)
│   │   │   ├── notifications.py      # Notification API (list/read/unread count)
│   │   │   ├── posts.py              # Post API (CRUD/likes/favorites/follows)
│   │   │   ├── promotions.py         # Announcement/Banner API
│   │   │   ├── reports.py            # Report API
│   │   │   ├── review.py             # Manual review API
│   │   │   ├── settings_api.py       # Site settings API
│   │   │   ├── stats.py              # Statistics API
│   │   │   ├── tools.py              # Toolbox API
│   │   │   ├── upload.py             # File upload API
│   │   │   ├── users.py              # User API (profile/edit/follows/followers)
│   │   │   └── ws.py                 # WebSocket (real-time notifications/messages)
│   │   ├── core/                     # Core services
│   │   │   ├── ai_moderation/        # AI moderation engine
│   │   │   │   ├── categories.py     #   Violation category definitions
│   │   │   │   ├── config.py         #   Moderation config
│   │   │   │   ├── decision.py       #   Moderation decision logic
│   │   │   │   ├── domains.py        #   Violation domain definitions
│   │   │   │   ├── image.py          #   Image moderation
│   │   │   │   ├── lexicon_import.py #   Sensitive word library import
│   │   │   │   ├── llm.py            #   LLM text moderation
│   │   │   │   ├── normalize.py      #   Text normalization
│   │   │   │   ├── pipeline.py       #   Moderation pipeline
│   │   │   │   ├── rules.py          #   Rule engine
│   │   │   │   └── scoring.py        #   Risk scoring
│   │   │   ├── activity.py           # Activity calculation
│   │   │   ├── device_mgr.py         # Device management (device code generation/records/ban)
│   │   │   ├── email_service.py      # Email service (SMTP/verification token/reset)
│   │   │   ├── hotness.py            # Post hotness algorithm
│   │   │   ├── levels.py             # User level/EXP system
│   │   │   ├── moderation.py         # Content moderation service
│   │   │   ├── ratelimit.py          # Rate limiting (login failure/IP ban)
│   │   │   ├── redis_client.py       # Redis client
│   │   │   ├── security.py           # Security (JWT/bcrypt/password validation)
│   │   │   ├── uid_allocator.py      # UID allocation system (normal/premium segment)
│   │   │   └── ws_manager.py         # WebSocket connection management
│   │   ├── models/                   # Data models (SQLAlchemy ORM)
│   │   │   ├── ai_review.py          # AI review records/config/appeals
│   │   │   ├── comment.py            # Comments
│   │   │   ├── device.py             # Devices/device bans/IP bans/login failures
│   │   │   ├── email_verification.py # Email verification/password reset tokens
│   │   │   ├── interaction.py        # Likes/favorites/follows
│   │   │   ├── message.py            # Private message conversations/messages
│   │   │   ├── moderation.py         # Moderation records/appeals
│   │   │   ├── notification.py       # Notifications
│   │   │   ├── operation_log.py      # Operation logs
│   │   │   ├── post.py               # Posts/post images
│   │   │   ├── promotion.py          # Announcements/Banners
│   │   │   ├── report.py             # Reports
│   │   │   ├── sensitive_word.py     # Sensitive words
│   │   │   ├── site_setting.py       # Site settings
│   │   │   ├── tool.py               # Toolbox categories/tools
│   │   │   ├── uid.py                # UID allocation records
│   │   │   └── user.py               # Users
│   │   ├── schemas/                  # Pydantic Schemas (request/response validation)
│   │   │   ├── admin.py              # Admin schemas
│   │   │   ├── comment.py            # Comment schemas
│   │   │   ├── common.py             # Common schemas (pagination/unified response)
│   │   │   ├── message.py            # Message schemas
│   │   │   ├── post.py               # Post schemas
│   │   │   ├── report.py             # Report schemas
│   │   │   └── user.py               # User schemas (register/login/email/profile completion)
│   │   ├── services/                 # Business services
│   │   │   ├── auth_service.py       # Auth service
│   │   │   └── user_service.py       # User service
│   │   ├── app-update.json           # APP version update config
│   │   ├── config.py                 # Config management (environment variables/auto key generation)
│   │   ├── database.py               # Database connection (async SQLAlchemy)
│   │   └── main.py                   # Application entry (FastAPI app/middleware/migration)
│   ├── alembic/                      # Database migrations
│   ├── scripts/                      # Scripts
│   ├── tests/                        # Tests
│   ├── Dockerfile                    # Docker image
│   ├── requirements.txt              # Python dependencies
│   └── .env.example                  # Environment variable example
│
├── pc/                               # PC frontend (Vue 3 + Vite)
│   ├── src/
│   │   ├── api/                      # API wrapper
│   │   │   ├── client.js             #   Axios instance (interceptors/error handling)
│   │   │   └── index.js              #   API method collection
│   │   ├── components/               # Common components
│   │   │   ├── AnnouncementsCard.vue #   Marquee announcements
│   │   │   ├── CommentItem.vue       #   Comment item
│   │   │   ├── EmptyState.vue        #   Empty state
│   │   │   ├── FeedSkeleton.vue      #   Skeleton loader
│   │   │   ├── FollowButton.vue      #   Follow button
│   │   │   ├── Icon.vue              #   SVG icon
│   │   │   ├── ImageGrid.vue         #   Image grid
│   │   │   ├── LevelBadge.vue        #   Level badge
│   │   │   ├── Modal.vue             #   Modal
│   │   │   ├── PostCard.vue          #   Post card
│   │   │   ├── PostComposer.vue      #   Post composer
│   │   │   ├── ReportDialog.vue      #   Report dialog
│   │   │   ├── SuggestCard.vue       #   Suggested users
│   │   │   ├── ToastHost.vue         #   Toast
│   │   │   └── UserAvatar.vue        #   User avatar
│   │   ├── layouts/
│   │   │   └── MainLayout.vue        # Main layout (navigation/sidebar)
│   │   ├── pages/                    # Pages
│   │   │   ├── Home.vue              #   Home (feed)
│   │   │   ├── Login.vue             #   Login/register/recovery (username/email)
│   │   │   ├── PostDetail.vue        #   Post detail
│   │   │   ├── Profile.vue           #   User profile
│   │   │   ├── Messages.vue          #   Messages
│   │   │   ├── Notifications.vue     #   Notifications
│   │   │   ├── Follows.vue           #   Follows/followers
│   │   │   ├── Settings.vue          #   Settings
│   │   │   ├── Review.vue            #   Review center
│   │   │   ├── Tools.vue             #   Toolbox
│   │   │   ├── ToolDetail.vue        #   Tool detail
│   │   │   ├── Levels.vue            #   Level info
│   │   │   ├── NotFound.vue          #   404
│   │   │   └── MeRedirect.vue        #   My profile redirect
│   │   ├── router/
│   │   │   └── index.js              # Router config
│   │   ├── stores/                    # Pinia state management
│   │   │   ├── app.js                #   App state (settings/theme)
│   │   │   └── auth.js               #   Auth state (user/token)
│   │   ├── styles/                    # Styles
│   │   │   ├── base.css              #   Base styles
│   │   │   ├── tokens.css            #   Design tokens
│   │   │   └── variables.css         #   CSS variables
│   │   ├── utils/                     # Utility functions
│   │   │   ├── device-fingerprint.js #   Device fingerprint
│   │   │   ├── format.js             #   Format (time/number)
│   │   │   └── toast.js              #   Toast
│   │   ├── App.vue                   # Root component
│   │   └── main.js                   # Entry
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── mobile/                           # Mobile H5 (uni-app Vue 3)
│   ├── pages/                        # Pages
│   │   ├── index/index.vue           #   Home (feed)
│   │   ├── login/login.vue           #   Login/register (username/email)
│   │   ├── account/                  #   Account
│   │   │   ├── forgot.vue            #     Password recovery
│   │   │   ├── password.vue          #     Change password
│   │   │   └── security.vue          #     Account security
│   │   ├── agreement/privacy.vue     #   Privacy policy
│   │   ├── level/level.vue           #   Level info
│   │   ├── message/                  #   Messages
│   │   │   ├── inbox.vue             #     Conversation list
│   │   │   └── chat.vue              #     Chat
│   │   ├── notifications/list.vue    #   Notification list
│   │   ├── post/                     #   Posts
│   │   │   ├── create.vue            #     Create post
│   │   │   ├── detail.vue            #     Post detail
│   │   │   └── edit.vue              #     Edit post
│   │   ├── profile/                  #   Profile
│   │   │   ├── mine.vue              #     Mine
│   │   │   ├── profile.vue           #     User profile
│   │   │   ├── edit.vue              #     Edit profile
│   │   │   └── privacy.vue           #     Privacy settings
│   │   ├── review/                   #   Review
│   │   │   ├── center.vue            #     Review center
│   │   │   ├── posts.vue             #     Post review
│   │   │   └── reports.vue           #     Report review
│   │   ├── search/search.vue         #   Search
│   │   ├── settings/settings.vue     #   Settings
│   │   ├── splash/splash.vue         #   Splash screen
│   │   └── user/follows.vue          #   Follows/followers
│   ├── components/                    # Components
│   ├── stores/                        # Pinia state
│   │   └── user.js                   #   User state
│   ├── utils/                         # Utilities
│   │   ├── api.js                    #   API wrapper
│   │   ├── link.js                   #   Page navigation
│   │   ├── theme.js                  #   Theme
│   │   ├── updater.js                #   APP update
│   │   └── ws.js                     #   WebSocket
│   ├── static/                        # Static assets (icons/Logo)
│   ├── App.vue                       # Root component
│   ├── main.js                       # Entry
│   ├── pages.json                    # Page route config
│   ├── manifest.json                 # uni-app config
│   ├── package.json
│   └── vite.config.js
│
├── admin/                            # Admin dashboard (Vue 3 + Element Plus)
│   ├── src/
│   │   ├── api/index.js              # API wrapper
│   │   ├── layouts/
│   │   │   └── AdminLayout.vue       # Admin layout (sidebar/topbar)
│   │   ├── views/                     # Pages
│   │   │   ├── Login.vue             #   Login
│   │   │   ├── Dashboard.vue         #   Dashboard
│   │   │   ├── Users.vue             #   User management (details/ban/reset password)
│   │   │   ├── Posts.vue             #   Post management
│   │   │   ├── Comments.vue          #   Comment management
│   │   │   ├── Categories.vue        #   Category management
│   │   │   ├── SensitiveWords.vue    #   Sensitive word management
│   │   │   ├── AiReview.vue          #   AI review config
│   │   │   ├── Reports.vue           #   Report management
│   │   │   ├── Promotions.vue        #   Announcement/Banner management
│   │   │   ├── Settings.vue          #   System settings
│   │   │   └── Logs.vue              #   Operation logs
│   │   ├── router/index.js           # Router
│   │   ├── stores/auth.js            # Auth state
│   │   ├── styles/theme.css          # Theme styles
│   │   ├── App.vue
│   │   └── main.js
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── data/                             # Database
│   └── campus_wall.db                # SQLite database (sanitized)
│
├── tools/                            # Standalone tools (pure HTML)
│   ├── base64.html                   # Base64 encode/decode
│   ├── color-picker.html             # Color picker
│   ├── json-formatter.html           # JSON formatter
│   ├── regex-tester.html             # Regex tester
│   └── timestamp.html                # Timestamp converter
│
├── docs/                             # Documentation
├── nginx/                            # Nginx config example
│   └── nginx.conf
├── docker-compose.yml                # Docker Compose config
├── .env.example                      # Environment variable example
├── LICENSE                           # MIT License
└── README.md                         # Project description
```

## Technical Architecture

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
│  │   SQLite/    │  │    Redis     │  (optional)     │
│  │ MySQL/PG     │  │  (cache/rate)│                 │
│  └──────────────┘  └──────────────┘                 │
└─────────────────────────────────────────────────────┘
```

## Database Tables

| Table | Description |
|-------|-------------|
| users | Users |
| posts | Posts |
| post_images | Post images |
| comments | Comments |
| conversations | Private message conversations |
| messages | Private messages |
| notifications | Notifications |
| like_records | Like records |
| favorites | Favorites |
| follows | Follow relationships |
| reports | Reports |
| categories | Categories |
| sensitive_words | Sensitive words |
| announcements | Announcements |
| banners | Banners |
| site_settings | Site settings |
| operation_logs | Operation logs |
| devices | Device records |
| device_bans | Device bans |
| ip_bans | IP bans |
| ip_whitelist | IP whitelist |
| login_failures | Login failure records |
| email_verifications | Email verification/reset tokens |
| uid_allocations | UID allocation records |
| moderation_records | Moderation records |
| moderation_appeals | Moderation appeals |
| ai_review_records | AI review records |
| ai_review_config | AI review config |
| ai_review_appeals | AI review appeals |
| tool_categories | Tool categories |
| tools | Tools |
