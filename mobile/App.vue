<script>
import { checkAppUpdate } from './utils/updater'
import { api } from './utils/api.js'
import { applyServerDefault, applyUserPreferences } from './utils/theme.js'
export default {
  onLaunch() {
    this.initPublicSettings()
    setTimeout(() => { checkAppUpdate({ silent: true }) }, 1500)
    if (uni.getStorageSync('token')) {
      this.refreshBadge()
      this.syncUserPreferences()
    }
    uni.$on('badge:refresh', this.refreshBadge)
    this.startBadgePoll()
    // #ifdef H5
    this.initStarfield()
    this.detectClient()
    window.addEventListener('resize', this.detectClient)
    // #endif
  },
  onShow() {
    if (uni.getStorageSync('token')) this.refreshBadge()
    this.startBadgePoll()
  },
  onHide() {
    this.stopBadgePoll()
  },
  methods: {
    // 拉取后台公开配置：默认主题、站点名、功能开关、维护状态
    async initPublicSettings() {
      try {
        const res = await api.getPublicSettings()
        const cfg = res || {}
        if (cfg.site_name) uni.setStorageSync('site_name', cfg.site_name)
        uni.setStorageSync('public_settings', JSON.stringify(cfg))
        applyServerDefault(cfg.default_theme)
        if (cfg.maintenance) {
          // 维护模式由各请求拦截 503 统一提示，这里仅记录
          uni.setStorageSync('maintenance_mode', 1)
        } else {
          uni.removeStorageSync('maintenance_mode')
        }
      } catch (e) { /* 离线时静默 */ }
    },
    // 登录用户：用后端保存的主题/明暗偏好同步本机
    async syncUserPreferences() {
      try {
        const me = await api.getMe()
        applyUserPreferences(me.preferences)
      } catch (e) { /* 静默 */ }
    },
    async refreshBadge() {
      try {
        const [n, m] = await Promise.all([
          api.getUnreadCount().catch(() => ({ count: 0 })),
          api.getMessageUnreadCount().catch(() => ({ count: 0 })),
        ])
        const total = (n?.count || 0) + (m?.count || 0)
        if (total > 0) uni.setTabBarBadge({ index: 1, text: total > 99 ? '99+' : String(total) })
        else uni.removeTabBarBadge({ index: 1 })
      } catch (e) { /* 静默 */ }
    },
    startBadgePoll() {
      this.stopBadgePoll()
      this._badgeTimer = setInterval(() => {
        if (uni.getStorageSync('token')) this.refreshBadge()
      }, 12000)
    },
    stopBadgePoll() {
      if (this._badgeTimer) { clearInterval(this._badgeTimer); this._badgeTimer = null }
    },
    // #ifdef H5
    detectClient() {
      const ua = navigator.userAgent || ''
      const isMobile = /Mobi|Android|iPhone|iPod|Windows Phone/i.test(ua)
      const root = document.documentElement
      root.classList.toggle('cw-mobile', isMobile)
      root.classList.toggle('cw-desktop', !isMobile)
    },
    initStarfield() {
      if (document.getElementById('cw-starfield')) return
      const canvas = document.createElement('canvas')
      canvas.id = 'cw-starfield'
      Object.assign(canvas.style, {
        position: 'fixed', left: '0', top: '0', width: '100%', height: '100%',
        zIndex: '0', pointerEvents: 'none',
      })
      document.body.insertBefore(canvas, document.body.firstChild)
      const ctx = canvas.getContext('2d')
      let w, h, stars = [], shooters = []
      const DPR = Math.min(window.devicePixelRatio || 1, 2)
      const resize = () => {
        w = canvas.width = window.innerWidth * DPR
        h = canvas.height = window.innerHeight * DPR
        canvas.style.width = window.innerWidth + 'px'
        canvas.style.height = window.innerHeight + 'px'
        const count = Math.min(220, Math.floor(window.innerWidth * window.innerHeight / 6500))
        stars = []
        for (let i = 0; i < count; i++) {
          stars.push({
            x: Math.random() * w, y: Math.random() * h,
            r: (Math.random() * 1.3 + 0.3) * DPR,
            tw: Math.random() * Math.PI * 2,
            ts: Math.random() * 0.02 + 0.004,
            depth: Math.random() * 0.8 + 0.2,
            hue: Math.random() > 0.72 ? (Math.random() > 0.5 ? 280 : 200) : 0,
          })
        }
      }
      resize()
      window.addEventListener('resize', resize)
      let mx = 0, my = 0
      window.addEventListener('mousemove', (e) => {
        mx = (e.clientX / window.innerWidth - 0.5)
        my = (e.clientY / window.innerHeight - 0.5)
      })
      const draw = () => {
        ctx.clearRect(0, 0, w, h)
        for (const s of stars) {
          s.tw += s.ts
          const alpha = 0.3 + Math.abs(Math.sin(s.tw)) * 0.65
          const ox = mx * 18 * s.depth * DPR, oy = my * 18 * s.depth * DPR
          ctx.beginPath()
          if (s.hue === 280) ctx.fillStyle = `rgba(196,164,255,${alpha})`
          else if (s.hue === 200) ctx.fillStyle = `rgba(140,210,255,${alpha})`
          else ctx.fillStyle = `rgba(255,255,255,${alpha})`
          ctx.shadowBlur = 6 * DPR
          ctx.shadowColor = ctx.fillStyle
          ctx.arc(s.x + ox, s.y + oy, s.r, 0, Math.PI * 2)
          ctx.fill()
        }
        ctx.shadowBlur = 0
        if (Math.random() < 0.004 && shooters.length < 2) {
          shooters.push({
            x: Math.random() * w * 0.8, y: Math.random() * h * 0.3,
            vx: (4 + Math.random() * 3) * DPR, vy: (2 + Math.random() * 2) * DPR, life: 1,
          })
        }
        shooters = shooters.filter((sh) => sh.life > 0)
        for (const sh of shooters) {
          sh.x += sh.vx; sh.y += sh.vy; sh.life -= 0.012
          const grad = ctx.createLinearGradient(sh.x, sh.y, sh.x - sh.vx * 12, sh.y - sh.vy * 12)
          grad.addColorStop(0, `rgba(255,255,255,${sh.life})`)
          grad.addColorStop(1, 'rgba(160,140,255,0)')
          ctx.strokeStyle = grad
          ctx.lineWidth = 2 * DPR
          ctx.beginPath()
          ctx.moveTo(sh.x, sh.y)
          ctx.lineTo(sh.x - sh.vx * 12, sh.y - sh.vy * 12)
          ctx.stroke()
        }
        requestAnimationFrame(draw)
      }
      draw()
    },
    // #endif
  },
}
</script>

<style >
/* ================= Galaxy 星云设计系统 v2 ================= */
page {
  --bg: #06071a;
  --card: rgba(255, 255, 255, 0.055);
  --card-solid: #141634;
  --text: #eef0ff;
  --text2: #a6aad4;
  --text3: #6f74a8;
  --brand: #8b7cf6;
  --brand2: #6ee7ff;
  --pink: #e879f9;
  --gold: #fbbf24;
  --mint: #34d399;
  --danger: #fb7185;
  --grad: linear-gradient(135deg, #8b7cf6 0%, #6ee7ff 100%);
  --grad-pink: linear-gradient(135deg, #e879f9 0%, #8b7cf6 100%);
  --grad-gold: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  --line: rgba(255, 255, 255, 0.1);
  --shadow: 0 12rpx 40rpx rgba(0, 0, 0, 0.45);
  --glow: 0 0 24rpx rgba(139, 124, 246, 0.45);
  /* 旧版 token 别名，让未逐页重写的页面自动适配暗色星系风 */
  --ink: #eef0ff;
  --ink-2: #a6aad4;
  --ink-3: #6f74a8;
  --surface: rgba(255, 255, 255, 0.06);
  --brand-deep: #7c6cf0;
  --brand-soft: rgba(139, 124, 246, 0.16);
  --accent-deep: #f43f5e;
  --success: #34d399;
  --warning: #fbbf24;
  --radius: 24rpx;
  --radius-lg: 28rpx;
  --radius-sm: 18rpx;
  --shadow-brand: 0 12rpx 34rpx rgba(139, 124, 246, 0.45);
  --shadow-sm: 0 6rpx 20rpx rgba(0, 0, 0, 0.3);
  --grad-warm: linear-gradient(135deg, #fb7185, #f59e0b);
  background: transparent;
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 28rpx;
}
html, body { background: #06071a !important; min-height: 100vh; }
uni-app, uni-layout, uni-page, uni-page-wrapper, uni-page-body, uni-body { background: transparent !important; }
body {
  background:
    radial-gradient(900rpx 600rpx at 12% -6%, rgba(139, 124, 246, 0.28), transparent 60%),
    radial-gradient(800rpx 700rpx at 105% 8%, rgba(110, 231, 255, 0.16), transparent 55%),
    radial-gradient(1000rpx 800rpx at 50% 115%, rgba(232, 121, 249, 0.14), transparent 60%),
    linear-gradient(180deg, #06071a 0%, #0a0c2b 45%, #06071a 100%) !important;
  background-attachment: fixed !important;
  min-height: 100vh;
}
view, text, scroll-view { box-sizing: border-box; }
/* ================= 多主题系统：仅换配色/背景，布局结构不动 ================= */
[class*="cw-t-"] { position: relative; z-index: 1; }
[class*="cw-t-"]::before {
  content: ''; position: fixed; left: 0; top: 0; right: 0; bottom: 0; z-index: -1;
  background: var(--page-bg, transparent); pointer-events: none;
}
/* 默认星云：与原设计一致，背景透明以保留 body 星云与 H5 星空 */
.cw-t-galaxy {
  --brand: #8b7cf6; --brand2: #6ee7ff; --soft: rgba(139,124,246,.16);
  --brand-soft: rgba(139,124,246,.16);
  --grad: linear-gradient(135deg,#8b7cf6,#6ee7ff);
  --glow: 0 0 24rpx rgba(139,124,246,.45);
  --shadow-brand: 0 12rpx 34rpx rgba(139,124,246,.45);
}
.cw-t-ocean {
  --brand: #38bdf8; --brand2: #22d3ee; --soft: rgba(56,189,248,.16);
  --brand-soft: rgba(56,189,248,.16);
  --grad: linear-gradient(135deg,#38bdf8,#22d3ee);
  --glow: 0 0 24rpx rgba(56,189,248,.4); --shadow-brand: 0 12rpx 34rpx rgba(56,189,248,.4);
  --page-bg: radial-gradient(900rpx 620rpx at 10% -6%, rgba(56,189,248,.26), transparent 60%),
             radial-gradient(820rpx 700rpx at 104% 6%, rgba(34,211,238,.15), transparent 55%),
             linear-gradient(180deg,#04101e,#062033 46%,#04101e);
}
.cw-t-forest {
  --brand: #34d399; --brand2: #2dd4bf; --soft: rgba(52,211,153,.16);
  --brand-soft: rgba(52,211,153,.16);
  --grad: linear-gradient(135deg,#34d399,#2dd4bf);
  --glow: 0 0 24rpx rgba(52,211,153,.4); --shadow-brand: 0 12rpx 34rpx rgba(52,211,153,.4);
  --page-bg: radial-gradient(900rpx 620rpx at 10% -6%, rgba(52,211,153,.24), transparent 60%),
             radial-gradient(820rpx 700rpx at 104% 6%, rgba(45,212,191,.14), transparent 55%),
             linear-gradient(180deg,#04140e,#052b20 46%,#04140e);
}
.cw-t-sunset {
  --brand: #fb923c; --brand2: #f472b6; --soft: rgba(251,146,60,.17);
  --brand-soft: rgba(251,146,60,.17);
  --grad: linear-gradient(135deg,#fb923c,#f472b6);
  --glow: 0 0 24rpx rgba(251,146,60,.4); --shadow-brand: 0 12rpx 34rpx rgba(251,146,60,.4);
  --page-bg: radial-gradient(900rpx 620rpx at 10% -6%, rgba(251,146,60,.26), transparent 60%),
             radial-gradient(820rpx 700rpx at 104% 6%, rgba(244,114,182,.16), transparent 55%),
             linear-gradient(180deg,#170a05,#2a120a 46%,#170a05);
}
.cw-t-rose {
  --brand: #f472b6; --brand2: #c084fc; --soft: rgba(244,114,182,.16);
  --brand-soft: rgba(244,114,182,.16);
  --grad: linear-gradient(135deg,#f472b6,#c084fc);
  --glow: 0 0 24rpx rgba(244,114,182,.4); --shadow-brand: 0 12rpx 34rpx rgba(244,114,182,.4);
  --page-bg: radial-gradient(900rpx 620rpx at 10% -6%, rgba(244,114,182,.24), transparent 60%),
             radial-gradient(820rpx 700rpx at 104% 6%, rgba(192,132,252,.15), transparent 55%),
             linear-gradient(180deg,#150811,#2a0f22 46%,#150811);
}
.cw-t-midnight {
  --brand: #818cf8; --brand2: #67e8f9; --soft: rgba(129,140,248,.14);
  --brand-soft: rgba(129,140,248,.14);
  --grad: linear-gradient(135deg,#818cf8,#67e8f9);
  --glow: 0 0 24rpx rgba(129,140,248,.36); --shadow-brand: 0 12rpx 34rpx rgba(129,140,248,.36);
  --page-bg: radial-gradient(900rpx 620rpx at 10% -6%, rgba(129,140,248,.18), transparent 60%),
             radial-gradient(820rpx 700rpx at 104% 6%, rgba(103,232,249,.10), transparent 55%),
             linear-gradient(180deg,#05060d,#0a0b14 46%,#05060d);
}
/* ================= 浅色模式（明暗维度，与配色主题叠加） ================= */
.cw-light {
  --bg: #eef0f9;
  --card: rgba(255, 255, 255, 0.9);
  --card-solid: #ffffff;
  --text: #20233f;
  --text2: #5a5f80;
  --text3: #9398b8;
  --line: rgba(28, 32, 80, 0.09);
  --shadow: 0 12rpx 36rpx rgba(60, 70, 140, 0.1);
  --glow: 0 0 24rpx rgba(139, 124, 246, 0.22);
  --ink: #20233f;
  --ink-2: #5a5f80;
  --ink-3: #9398b8;
  --surface: #ffffff;
  --brand-soft: rgba(124, 108, 240, 0.12);
  --soft: rgba(124, 108, 240, 0.1);
  --shadow-sm: 0 6rpx 20rpx rgba(60, 70, 140, 0.08);
  --shadow-brand: 0 12rpx 30rpx rgba(124, 108, 240, 0.28);
  background:
    radial-gradient(900rpx 600rpx at 12% -6%, rgba(139, 124, 246, 0.12), transparent 60%),
    radial-gradient(800rpx 700rpx at 105% 8%, rgba(110, 231, 255, 0.1), transparent 55%),
    linear-gradient(180deg, #f4f5fc 0%, #eceffa 100%);
  min-height: 100vh;
  color: var(--text);
}
.cw-light.card,
.cw-light .card { background: rgba(255, 255, 255, 0.92); border-color: var(--line); backdrop-filter: blur(18rpx); }
.cw-light .input, .cw-light .uni-input-wrapper, .cw-light .uni-textarea-wrapper {
  background: #f2f3fa !important; border-color: var(--line); color: var(--text);
}
.cw-light input, .cw-light textarea { color: var(--text); }
.cw-light .btn-ghost { background: #ffffff; color: var(--text); border-color: var(--line); }
.cw-light .mode-item { background: #f1f2f9; border-color: transparent; }
.cw-light .seg { background: #e9ebf6 !important; }
/* #ifdef H5 */
html.cw-light body {
  background:
    radial-gradient(900px 600px at 12% -6%, rgba(139, 124, 246, 0.12), transparent 60%),
    radial-gradient(800px 700px at 105% 8%, rgba(110, 231, 255, 0.1), transparent 55%),
    linear-gradient(180deg, #f4f5fc 0%, #eceffa 100%) !important;
}
/* 浅色下隐藏深色星空画布 */
html.cw-light #cw-starfield { display: none !important; }
/* #endif */
.page { padding: 24rpx 24rpx calc(170rpx + env(safe-area-inset-bottom)); position: relative; z-index: 1; }
.card {
  background: var(--card);
  border: 1rpx solid var(--line);
  border-radius: 28rpx; padding: 28rpx; margin-bottom: 24rpx;
  backdrop-filter: blur(18rpx); -webkit-backdrop-filter: blur(18rpx);
  box-shadow: var(--shadow);
}
.muted { color: var(--text2); }
.small { font-size: 24rpx; }
.row { display: flex; align-items: center; }
.between { justify-content: space-between; }
.center { justify-content: center; }
.gap { gap: 16rpx; }
.mt { margin-top: 16rpx; }
.btn {
  display: flex; align-items: center; justify-content: center; gap: 10rpx;
  height: 88rpx; border-radius: 999rpx; font-size: 30rpx; font-weight: 600;
  background: var(--grad); color: #fff; border: none;
  box-shadow: 0 10rpx 30rpx rgba(139, 124, 246, 0.4);
}
.btn::after { border: none; }
button.btn[disabled] { opacity: .5; color: #fff; }
.btn-ghost { background: rgba(255,255,255,.06); color: var(--text); border: 1rpx solid var(--line); box-shadow: none; }
.btn-danger { background: linear-gradient(135deg, #fb7185, #f43f5e); box-shadow: 0 10rpx 30rpx rgba(244,63,94,.35); }
.input, .uni-input-wrapper, .uni-textarea-wrapper {
  background: rgba(255,255,255,.06) !important; border: 1rpx solid var(--line);
  border-radius: 20rpx; color: var(--text);
}
input, textarea { color: var(--text); }
.tag {
  display: inline-flex; align-items: center; padding: 6rpx 18rpx; border-radius: 999rpx;
  font-size: 22rpx; background: rgba(139,124,246,.16); color: #c4b5fd;
  border: 1rpx solid rgba(139,124,246,.3);
}
.tag-gold { background: rgba(251,191,36,.14); color: var(--gold); border-color: rgba(251,191,36,.3); }
.tag-cyan { background: rgba(110,231,255,.12); color: var(--brand2); border-color: rgba(110,231,255,.3); }
.tag-green { background: rgba(52,211,153,.14); color: #34d399; border-color: rgba(52,211,153,.3); }
.tag-red { background: rgba(251,113,133,.14); color: #fb7185; border-color: rgba(251,113,133,.3); }
.tag-gray { background: rgba(255,255,255,.07); color: var(--text2); border-color: var(--line); }
.empty { text-align: center; padding: 90rpx 0; color: var(--text3); font-size: 26rpx; }
@keyframes animUp { from { opacity: 0; transform: translateY(24rpx); } to { opacity: 1; transform: none; } }
@keyframes animPop { 0% { opacity: 0; transform: scale(.92); } 100% { opacity: 1; transform: none; } }
@keyframes floaty { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10rpx); } }
.anim-up { animation: animUp .5s ease both; }
.anim-pop { animation: animPop .4s cubic-bezier(.2,.9,.3,1.3) both; }
.floaty { animation: floaty 4s ease-in-out infinite; }
.stagger > * { animation: animUp .5s ease both; }
.stagger > *:nth-child(1){animation-delay:.04s}.stagger > *:nth-child(2){animation-delay:.08s}
.stagger > *:nth-child(3){animation-delay:.12s}.stagger > *:nth-child(4){animation-delay:.16s}
.stagger > *:nth-child(5){animation-delay:.20s}.stagger > *:nth-child(6){animation-delay:.24s}
.galaxy-text {
  background: linear-gradient(120deg, #c4b5fd, #6ee7ff 55%, #f0abfc);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
/* 桌面浏览器：宽屏自适应布局（首页三栏由 index.vue 内部控制） */
/* #ifdef H5 */
@media (min-width: 1024px) {
  uni-page-wrapper { max-width: 1200px; margin: 0 auto !important; min-height: 100vh; }
  /* 桌面端隐藏原生底部 TabBar，改由首页左侧导航承担 */
  uni-tabbar, .uni-tabbar-bottom { display: none !important; }
  /* 非首页页面保持居中阅读栏，避免宽屏拉散 */
  .page {
    max-width: 760px; margin-left: auto; margin-right: auto;
    padding-bottom: 48px;
  }
  /* 首页自身是三栏 grid，不套用居中窄栏 */
  .page.is-d { max-width: 1200px; }
}
/* #endif */
</style>
