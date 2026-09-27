# 校园墙 · AI 智能审查机制 交付说明

> 部署时间：2026-09-23 ｜ 目标服务器：your-server（Ubuntu 22.04）
> 项目路径：`/www/wwwroot/campus-wall` ｜ 服务：`campus-wall.service`（FastAPI + Uvicorn，127.0.0.1:8000）
> 站点域名：`cy.ihyuan.cn`

---

## 一、交付了什么

在原「敏感词 DFA 引擎」之上，新增了一整套**分级、可解释、可回滚**的 AI 智能审查机制：

| 能力 | 说明 |
|---|---|
| 五层审查流水线 | 归一化 → 词库 DFA → 规则正则 → 特征打分 → 大模型语义（可选）→ 图片审查（可选） |
| 14 类违规分类 | 政治敏感 / 暴恐极端 / 违法犯罪 / 色情低俗 / 涉未成年人 / 诈骗赌博 / 隐私侵害 / 学术不端 / 暴力威胁 / 轻生倾向 / 广告引流 / 辱骂攻击 / 刷屏灌水 / 其他 |
| 4 级处置动作 | 通过 / 打码 / 转人工复核 / 直接拦截（后台可逐分类配置） |
| 全场景接入 | 帖子标题正文、评论回复、私信、用户昵称与简介、帖子图片 |
| 人工复核队列 | 中风险内容自动落库、对外不可见，后台一键通过或驳回 |
| 可解释证据链 | 每条记录都保留「命中了哪些词、哪些规则、各加了多少分、AI 怎么说的」 |
| 用户申诉通道 | 用户可对自己的审查记录提交申诉，后台受理并可一键恢复内容 |
| 开源词库 | 3,533 条清洗后词条 + 14,584 条违规域名黑名单（MIT 许可） |
| 大模型语义审查 | 可选接入智谱 GLM-4-Flash（官方免费）/ DeepSeek / 通义 / 硅基流动等 OpenAI 兼容接口 |
| 图片审查 | 可选 Sightengine / 自定义 HTTP 接口 / 本地轻量启发式 |
| 观察模式 | 只记录不处置，用于上线前评估误报率 |

**当前线上状态**：AI 审查已开启，本地引擎生效，大模型未配置 Key（自动降级，功能不中断）。

---

## 二、架构：级联分层，省钱又不漏

```
用户投稿（帖子/评论/私信/昵称）
        │
   ┌────▼─────────────────────────────────────────────┐
   │ L0 归一化   全角→半角 / 去零宽字符 / 去干扰符号      │
   │             繁简与异体字映射 / 重复字折叠           │
   │             识破「加 微 信」「傻\u200b逼」「傻傻傻逼逼逼」│
   ├──────────────────────────────────────────────────┤
   │ L1 词库 DFA  3,533 条词条，分类 + 危险等级 + 动作   │
   │             支持 mask / review / block / 白名单    │
   ├──────────────────────────────────────────────────┤
   │ L2 规则正则  27 条规则，抓住「有结构的信息」：       │
   │             联系方式、二维码、外链、刷单话术、        │
   │             代写代考、赌博、涉枪涉爆、涉毒、          │
   │             人肉开盒、身份证/银行卡、轻生倾向         │
   ├──────────────────────────────────────────────────┤
   │ L2b 域名黑名单 14,584 条涉黄涉赌涉诈域名            │
   ├──────────────────────────────────────────────────┤
   │ L3 特征打分  联系方式密度、符号灌水、字符构成异常、    │
   │             短文本引流、与违规样例的字符二元组相似度   │
   ├──────────────────────────────────────────────────┤
   │ L4 大模型语义（可选，默认只对本地可疑内容调用）        │
   │             超时/失败/超配额一律静默降级，不阻塞发布   │
   ├──────────────────────────────────────────────────┤
   │ L5 图片审查（可选）                                │
   └────┬─────────────────────────────────────────────┘
        │
   ┌────▼──────────────────────────────────────────────┐
   │ 裁决：分类策略表（权威） + 分数有限升级 + 法定硬红线   │
   │  → pass / mask / review / block                  │
   └───────────────────────────────────────────────────┘
```

**关键设计取舍**（都是为了「不误杀、不阻塞、可回滚」）：

1. **分类策略是权威，分数只能升级一级。**
   后台把「辱骂攻击」设成打码，就不会因为分数高而被直接删帖 —— 行为可预期。
2. **法定违法信息（政治/暴恐/违法/色情/涉未成年人/诈骗赌博）无条件拦截**，
   不受分数与人工设置影响（后台把分类改成「放行」也拦不住，只有停用词条才行）。
3. **轻生倾向是受保护分类，永不自动拦截**，最高只能转人工并保留原文 ——
   把求助信号删掉是危险的，必须留给人工关怀介入。
4. **大模型全程可降级**：没配 Key、网络不通、连续失败熔断、超出每日配额，
   一律回退到本地判定，用户发布永远不被阻塞。
5. **请求协程内不做重 CPU 计算**：图片启发式走线程池，大模型走纯异步 httpx。

---

## 三、处置策略表（当前线上取值）

| 分类 | 危险等级 | 法定 | 当前动作 | 说明 |
|---|---|---|---|---|
| 政治敏感 politics | 5 | ✅ | **转人工复核** | 见下方「关于政治类的重要说明」 |
| 暴恐极端 terror | 5 | ✅ | 直接拦截 | |
| 违法犯罪 illegal | 5 | ✅ | 直接拦截 | 枪支弹药、毒品、假证 |
| 色情低俗 porn | 5 | ✅ | 直接拦截 | |
| 涉未成年人 minor | 5 | ✅ | 直接拦截 | 零容忍 |
| 诈骗赌博 fraud | 5 | ✅ | 直接拦截 | 刷单、校园贷、赌博、跑分 |
| 学术不端 academic | 5 | — | 直接拦截 | 代写代考、出售答案 |
| 隐私侵害 privacy | 4 | — | 转人工复核 | 手机号单独规则会打码 |
| 暴力威胁 violence | 4 | — | 转人工复核 | |
| 轻生倾向 self_harm | 4 | — | 转人工复核 | **受保护，永不拦截** |
| 广告引流 ad | 3 | — | 转人工复核 | |
| 辱骂攻击 abuse | 2 | — | 打码后发布 | 分数很高时升级为复核 |
| 刷屏灌水 spam | 2 | — | 打码后发布 | |
| 其他违规 other | 2 | — | 转人工复核 | |

分数门槛：**≥75 拦截 / ≥40 转人工 / ≥20 打码**。

### ⚠️ 关于政治类的重要说明

政治类两个词库（政治类型 + 反动词库）共 **842 条 `block` 级词条**，
是全部词库里误报风险最高的一类（例如正常引用领导人讲话也会命中）。

因此**首次部署我没有用「直接拦截」，而是设为「转人工复核」**：

- 内容同样**不会公开**，法律风险与拦截完全一致；
- 但不会给用户弹「你的内容违规被拦截」，避免误伤正常讨论引发的投诉；
- 如果你们希望改成硬拦截：后台 →「AI 审查」→「审查配置」→「分类处置策略」→
  把「政治敏感」改成「直接拦截」→ 保存，**立即生效**。

### 另一处行为变更（需要你确认）

线上原本是「按 55% 比例随机送人工审核」。AI 审查上线后这套粗放随机已经没有意义
（一半正常帖子会卡在待审里），我已把它关闭，改由 AI 精准判定谁需要人工复核。

- 如需恢复：后台 →「系统设置」→「发帖先审核」/ 或调用 `/api/admin/settings` 设 `review_mode`。

---

## 四、文件清单

### 新增（后端）

| 文件 | 作用 |
|---|---|
| `backend/app/core/ai_moderation/__init__.py` | 对外统一入口 |
| `backend/app/core/ai_moderation/config.py` | 配置模型、服务商预设、默认值、校验 |
| `backend/app/core/ai_moderation/categories.py` | 14 类违规分类体系与默认策略 |
| `backend/app/core/ai_moderation/normalize.py` | 深度归一化（对抗谐音/拆字/跳字绕过） |
| `backend/app/core/ai_moderation/rules.py` | 27 条正则规则 |
| `backend/app/core/ai_moderation/scoring.py` | 特征打分 + 违规样例相似度 |
| `backend/app/core/ai_moderation/decision.py` | 裁决引擎（分类策略 + 分数升级 + 红线） |
| `backend/app/core/ai_moderation/pipeline.py` | 流水线编排、配置读写、落库、风险画像 |
| `backend/app/core/ai_moderation/llm.py` | 大模型适配（OpenAI 兼容、缓存、熔断、配额） |
| `backend/app/core/ai_moderation/image.py` | 图片审查（Sightengine / 通用 HTTP / 本地启发式） |
| `backend/app/core/ai_moderation/lexicon_import.py` | 开源词库下载、清洗、导入 |
| `backend/app/core/ai_moderation/domains.py` | 违规域名黑名单加载与匹配 |
| `backend/app/api/ai_review.py` | AI 审查全部接口（管理端 + 用户申诉） |
| `backend/app/api/ai_guard.py` | 业务接口层的统一接线与处置 |
| `backend/app/models/moderation.py` | `ModerationRecord` / `ModerationAppeal` |
| `backend/scripts/import_lexicon.py` | 词库导入 CLI |
| `backend/data/blocked_domains.txt` | 14,584 条违规域名（生成物） |
| `backend/app/core/ai_moderation/data/char_map.json` | 81 条繁简/异体字符映射（生成物） |
| `admin/src/views/AiReview.vue` | 管理后台「AI 智能审查」页面 |

### 修改（后端）

| 文件 | 改动 |
|---|---|
| `app/core/moderation.py` | 动作扩展 mask/review/block；词条带分类与等级；白名单；零宽字符与繁简归一；新增 `scan_hits` / `mask_text` / `ensure_loaded` |
| `app/models/sensitive_word.py` | 新增 `severity` / `source` / `note` 列 |
| `app/models/comment.py` | 新增 `status` 列（支撑评论的人工复核队列） |
| `app/models/user.py` | 新增 `ai_review` 权限项 |
| `app/api/posts.py` | 发帖/改帖接入 AI 审查；AI 判定的人工复核优先于随机抽样 |
| `app/api/comments.py` | 评论接入 AI 审查；待复核评论对外不可见且不产生通知 |
| `app/api/messages.py` | 私信接入 AI 审查（涉黄/诈骗引流高发场景） |
| `app/api/users.py` | 昵称 / 简介接入 AI 审查 |
| `app/api/admin.py` | 敏感词管理支持等级、备注、review/allow 动作与按动作筛选 |
| `app/schemas/admin.py` | 敏感词模型支持新字段与新动作 |
| `app/core/activity.py` | 新增 `ai_review_config` 配置键与 5 个操作日志标签 |
| `app/main.py` | 注册 AI 审查路由；启动迁移补齐新表新列 |
| `backend/requirements.txt` | 新增 `httpx`、`zhconv` |

### 修改（前端）

| 文件 | 改动 |
|---|---|
| `admin/src/router/index.js` | 新增 `/ai-review` 路由 |
| `admin/src/layouts/AdminLayout.vue` | 新增「AI 智能审查」菜单 |
| `admin/src/views/SensitiveWords.vue` | 支持危险等级、备注、转人工复核、白名单 |

---

## 五、后台使用指南

访问 `https://cy.ihyuan.cn/admin/` → 左侧「**AI 智能审查**」。

| 标签页 | 用途 |
|---|---|
| **复核队列** | 待人工复核的内容。点任意一行看 AI 判定依据（命中的词、规则、加分项、证据链、作者近 30 天违规画像），再决定「通过 / 通过（保留打码）/ 驳回 / 驳回并封禁」。 |
| **审查记录** | 全量流水，可按状态、动作、场景、风险等级、违规分类、关键词筛选。被拦截的帖子也会在这里留证。 |
| **在线试审** | 粘贴任意文本立刻看判定结果，**不落库、不影响线上**。页面内置正常/广告/辱骂/代写四个样本，方便调参。 |
| **审查配置** | 总开关、观察模式、审查范围、大模型、图片审查、处置门槛、逐分类策略。 |
| **词库与规则** | 词库条数、域名黑名单、导入来源映射表、27 条内置规则明细，以及「一键导入/更新开源词库」。 |
| **申诉** | 用户申诉队列，接受后会恢复内容并通知用户。 |

### 建议的调参流程

1. **先开「观察模式」跑 3–7 天**（配置页一个开关）。
   AI 只记录不处置，你在「审查记录」里看误报率。
2. 误报多的分类，把它的处置动作降到「转人工复核」。
   某个词误报，去「敏感词管理」把它停用，或在「AI 审查配置 → 词库白名单」里加白。
3. 误报可接受后关掉观察模式。
4. 想接大模型语义审查（能抓「阴阳怪气」「隐晦软广」这类词库抓不到的内容）：
   注册智谱开放平台（GLM-4-Flash 官方免费）→ 拿 API Key →
   配置页「服务商」选「智谱 GLM-4-Flash」→ 填 Key → 点「测试大模型连通性」→ 保存。
   默认只对本地判定可疑的内容调用（`llm_trigger=suspect`），有每日上限和熔断保护。

---

## 六、运维

```bash
# 服务状态 / 日志
systemctl status campus-wall
journalctl -u campus-wall -n 100 --no-pager
tail -f /www/wwwroot/campus-wall/backend/logs/app.log

# 词库统计
sqlite3 /www/wwwroot/campus-wall/data/campus_wall.db \
  "select category,action,count(*) from sensitive_words group by category,action;"

# 重新导入/更新开源词库（联网）
cd /www/wwwroot/campus-wall/backend
venv/bin/python scripts/import_lexicon.py            # 全量
venv/bin/python scripts/import_lexicon.py --dry-run  # 只看会导入多少

# 重新构建管理后台
bash /root/build_admin.sh
```

### 资源占用

| 项 | 占用 |
|---|---|
| 词库 DFA（3533 条） | 约 5–10 MB 常驻 |
| 域名黑名单（14,584 条） | 约 2 MB |
| 单次审查耗时（纯本地） | 0–5 ms |
| 单次审查耗时（含大模型） | 通常 1–3 s，异步不阻塞其他请求 |

部署前可用内存约 1.0 GB，实测审查链路未造成内存压力；大模型走外部 API，不占本地算力。

---

## 七、开源引用与许可

| 项目 | 用途 | 许可 |
|---|---|---|
| [Konsheng/Sensitive-lexicon](https://github.com/Konsheng/Sensitive-lexicon) | 中文敏感词库（清洗后导入 3,533 条 + 14,584 条域名） | **MIT** |
| 智谱 GLM-4-Flash | 可选的大模型语义审查（官方免费） | 服务条款 |
| Sightengine | 可选的图片 NSFW 审查（有免费额度） | 服务条款 |

> 说明：调研中评估过的 [notAI-tech/NudeNet](https://github.com/notAI-tech/NudeNet)
> 虽然只有 11.6 MB 且很适合 2G 内存，但其仓库 LICENSE 为 **AGPL-3.0**
> （PyPI 元数据却写 MIT，存在冲突），为避免传染性许可风险**未采用**。
> 同样排除的还有 opennsfw2 / GantMan/nsfw_model（依赖 TensorFlow，RSS 500MB+，
> 2G 内存下不可行）与任何 7B 级本地大模型。

---

## 八、回滚方案

```bash
bash /root/rollback_ai_review.sh
```

该脚本会：
1. 停止服务；
2. 用 `pre-ai-review-20260923-143202` 的代码备份覆盖回 `backend/app`；
3. 恢复 `admin/dist` 到构建前版本；
4. 重启服务并做健康检查。

**注意**：回滚代码**不会**删除 `moderation_records` / `moderation_appeals` 两张新表，
也**不会**回退 `sensitive_words` 的 3,533 条词（旧代码读不了这两个新列但不会报错）。
如需彻底回退数据库，用：

```bash
sqlite3 /www/wwwroot/campus-wall/data/campus_wall.db \
  "DELETE FROM sensitive_words WHERE source='lexicon';"
```

---

## 九、已知限制与后续建议

1. **本地图片启发式（肤色占比）误报率天生偏高**，因此设计上**永不参与自动拦截**，
   最高只转人工复核。要真正可用的图片审核，建议接入 Sightengine（有免费额度）
   或自建接口（配置页已留好「自定义 HTTP 接口」的位置）。
2. **大模型语义审查默认未开启**（没有 API Key）。启用后能显著提升对
   「阴阳怪气、隐晦软广、反串嘲讽」的识别率，建议尽快配上免费的 GLM-4-Flash。
3. **视频内容未做审查**（只有文本与图片）。当前站点的视频是外链 URL，未做进一步处理。
4. **昵称/简介审查没有「待审」中间态**：拦截即拒绝提交，打码/复核则先放行并落库记录。
5. **高风险处置结果目前通过站内通知告知用户**，App 端还没有专门的「我的审查记录 / 申诉」
   页面（后端接口 `/api/ai-review/my-records` 与 `POST /api/ai-review/appeals` 已就绪），
   需要移动端配合加页面。
6. **数据库里存在历史遗留的孤儿外键行**（`posts.user_id=9`、`comments.post_id=16` 等，
   指向早已删除的账号/帖子）。这是本次改造之前就存在的状态，不是本次引入，
   恢复前后完全一致。如需清理请单独评估。

---

## 十、本次部署过程中的一次数据事件（如实说明）

清理端到端测试账号时，发生了**计划外的级联删除**：

- 历史遗留数据里有 `posts.user_id = 9`，但 `users` 表里**并没有** id=9 的账号
  （该账号在更早的时候已被删除，当时外键约束未生效，所以帖子残留了下来）。
- SQLite 的自增主键会复用被删除的最大 id，我的自动化测试注册的第一个账号**恰好拿到了 id=9**。
- 清理测试账号时 SQLAlchemy 打开了外键强制，`ON DELETE CASCADE` 于是把那条
  **指向 id=9 的历史帖子（已是 `deleted` 状态）连同 1 条评论、1 张图片、3 条通知、
  1 条点赞、1 条收藏**一并删除了。

**影响评估**：丢失的全部是 2026-08-30/31 的一次性测试数据，且帖子本就是软删除状态、
对任何用户不可见；**真实用户的任何内容都没有受到影响**。

**处置**：已按 id 从部署前备份中**逐行精确补回**，恢复后各表行数与备份完全一致
（posts 21、comments 2、post_images 14、notifications 39、like_records 2、favorites 1、users 7）。
恢复前的库另存为 `/root/campus-deploy-backups/campus_wall.pre-restore-20260923-144715.db`。

---

## 附：备份清单

| 路径 | 内容 |
|---|---|
| `/root/campus-deploy-backups/pre-ai-review-20260923-143202/` | 改造前的完整代码 tar、数据库、.env、service 单元、nginx 配置 |
| `/root/campus-deploy-backups/apply-20260923-1441xx/` | 每次应用补丁前的 `backend/app` 快照 |
| `/root/campus-deploy-backups/campus_wall.pre-restore-20260923-144715.db` | 数据恢复前的库 |
| `/root/campus_releases/admin_dist.bak-ai-review-*.tar.gz` | 构建前的管理后台 dist |
