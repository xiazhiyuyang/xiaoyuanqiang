<template>
  <div class="shell">
    <header class="topbar">
      <div class="container topbar-inner">
        <RouterLink to="/" class="brand">
          <span class="brand-mark">
            <img v-if="app.settings?.site_logo" :src="app.settings.site_logo" class="brand-logo" alt="logo" />
            <Icon v-else name="compass" :size="20" />
          </span>
          <span class="brand-text">{{ app.siteName }}</span>
        </RouterLink>

        <div class="search" @click.outside="suggest = []">
          <Icon name="search" :size="17" class="search-ico" />
          <input
            v-model="kw" type="text" placeholder="搜索用户、帖子…"
            @keyup.enter="doSearch" @focus="onSearchFocus" @input="onSearchInput"
          />
          <div v-if="suggest.length || searching" class="suggest pop">
            <div v-if="searching" class="sg-loading faint">搜索中…</div>
            <RouterLink v-for="u in suggest" :key="u.id" :to="`/u/${u.id}`" class="sg-item" @click="suggest=[]">
              <UserAvatar :src="u.avatar" :name="u.nickname" :size="32" />
              <span class="grow">
                <span class="sg-name">{{ u.nickname }} <span class="faint">@{{ u.username }}</span></span>
                <span class="sg-meta faint">{{ u.post_count || 0 }} 条动态</span>
              </span>
              <Icon name="chevron-right" :size="15" class="faint" />
            </RouterLink>
            <button v-if="kw.trim()" class="sg-more" @click="doSearch">搜索含“{{ kw }}”的帖子</button>
          </div>
        </div>

        <nav class="top-actions">
          <button class="icon-btn" :class="{ active: isDark }" title="切换主题" @click="cycleTheme">
            <Icon :name="themeIcon" :size="19" />
          </button>

          <template v-if="auth.isLoggedIn">
            <RouterLink class="icon-btn" to="/messages" title="私信">
              <Icon name="message" :size="19" />
              <span v-if="app.unreadMessage" class="dot">{{ app.unreadMessage > 99 ? '99+' : app.unreadMessage }}</span>
            </RouterLink>
            <RouterLink class="icon-btn" to="/notifications" title="通知">
              <Icon name="bell" :size="19" />
              <span v-if="app.unreadNotify" class="dot">{{ app.unreadNotify > 99 ? '99+' : app.unreadNotify }}</span>
            </RouterLink>
            <button class="btn btn-primary compose" @click="composer = true">
              <Icon name="edit" :size="16" /><span>发帖</span>
            </button>

            <div class="user-menu" @click.stop>
              <button class="um-btn" @click="menu = !menu">
                <UserAvatar :src="auth.user?.avatar" :name="auth.user?.nickname" :size="34" />
                <Icon name="chevron-down" :size="14" class="faint" />
              </button>
              <Transition name="menu">
                <div v-if="menu" class="um-panel pop" @click="menu = false">
                  <div class="um-head">
                    <UserAvatar :src="auth.user?.avatar" :name="auth.user?.nickname" :size="42" />
                    <div class="grow ellipsis">
                      <div class="um-name">{{ auth.user?.nickname }}</div>
                      <div class="faint um-id">@{{ auth.user?.username }}</div>
                    </div>
                  </div>
                  <RouterLink to="/me" class="um-item"><Icon name="user" :size="16" /> 我的主页</RouterLink>
                  <RouterLink to="/me/follows" class="um-item"><Icon name="users" :size="16" /> 关注 / 粉丝</RouterLink>
                  <RouterLink to="/levels" class="um-item"><Icon name="medal" :size="16" /> 等级中心</RouterLink>
                  <RouterLink v-if="auth.canAnyReview" to="/review" class="um-item"><Icon name="shield" :size="16" /> 审查中心</RouterLink>
                  <RouterLink to="/settings" class="um-item"><Icon name="settings" :size="16" /> 设置</RouterLink>
                  <RouterLink v-if="auth.isAdmin" to="/admin/" class="um-item"><Icon name="lock" :size="16" /> 管理后台</RouterLink>
                  <div class="um-sep" />
                  <button class="um-item danger" @click="logout"><Icon name="logout" :size="16" /> 退出登录</button>
                </div>
              </Transition>
            </div>
          </template>
          <template v-else>
            <RouterLink to="/login" class="btn btn-ghost"><Icon name="login" :size="16" /> 登录</RouterLink>
          </template>
        </nav>
      </div>
    </header>

    <main class="container layout" :class="{ wide: wide }">
      <aside class="rail rail-left">
        <nav class="side-nav">
          <RouterLink to="/" class="sn" :class="{ active: route.name === 'home' }"><Icon name="home" :size="20" /><span>首页</span></RouterLink>
          <RouterLink v-if="auth.isLoggedIn" to="/messages" class="sn" :class="{ active: route.path.startsWith('/messages') }">
            <Icon name="message" :size="20" /><span>私信</span>
            <em v-if="app.unreadMessage" class="sn-dot">{{ app.unreadMessage }}</em>
          </RouterLink>
          <RouterLink v-if="auth.isLoggedIn" to="/notifications" class="sn" :class="{ active: route.name === 'notifications' }">
            <Icon name="bell" :size="20" /><span>通知</span>
            <em v-if="app.unreadNotify" class="sn-dot">{{ app.unreadNotify }}</em>
          </RouterLink>
          <RouterLink to="/levels" class="sn" :class="{ active: route.name === 'levels' }"><Icon name="medal" :size="20" /><span>等级中心</span></RouterLink>
          <RouterLink to="/tools" class="sn" :class="{ active: route.name === 'tools' || route.name === 'tool-detail' }"><Icon name="tool" :size="20" /><span>工具箱</span></RouterLink>
          <RouterLink v-if="auth.isLoggedIn" to="/me" class="sn" :class="{ active: route.name === 'me' }"><Icon name="user" :size="20" /><span>我的主页</span></RouterLink>
          <RouterLink v-if="auth.canAnyReview" to="/review" class="sn" :class="{ active: route.name === 'review' }"><Icon name="shield" :size="20" /><span>审查中心</span></RouterLink>
          <RouterLink v-if="auth.isLoggedIn" to="/settings" class="sn" :class="{ active: route.name === 'settings' }"><Icon name="settings" :size="20" /><span>设置</span></RouterLink>
        </nav>
        <button v-if="auth.isLoggedIn" class="btn btn-primary btn-block side-post" @click="composer = true">
          <Icon name="edit" :size="17" /> 发布动态
        </button>
        <div class="rail-foot faint">
          <p>{{ app.slogan }}</p>
        </div>
      </aside>

      <section class="content">
        <RouterView v-slot="{ Component }">
          <Transition name="view" mode="out-in">
            <component :is="Component" @compose="composer = true" />
          </Transition>
        </RouterView>
      </section>

      <aside v-if="!wide" class="rail rail-right">
        <AnnouncementsCard />
        <SuggestCard />
        <footer class="legal">
          <p class="faint">{{ app.settings?.footer_note || '请遵守校园社区公约，文明交流' }}</p>
          <p class="faint">
            <a v-if="app.settings?.icp_number" :href="app.settings.icp_link || '#'" target="_blank" rel="noopener">{{ app.settings.icp_number }}</a>
          </p>
        </footer>
      </aside>
    </main>

    <PostComposer v-model="composer" :categories="categories" :post="editingPost" @created="onCreated" @updated="onUpdated" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import UserAvatar from '../components/UserAvatar.vue'
import PostComposer from '../components/PostComposer.vue'
import AnnouncementsCard from '../components/AnnouncementsCard.vue'
import SuggestCard from '../components/SuggestCard.vue'
import api from '../api'
import { useAuth } from '../stores/auth'
import { useApp } from '../stores/app'
import { toast } from '../utils/toast'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const app = useApp()

const composer = ref(false)
const editingPost = ref(null)
const categories = ref([])
const menu = ref(false)

function openCompose(post = null) {
  editingPost.value = post
  composer.value = true
}
provide('openCompose', openCompose)

const wide = computed(() => ['messages', 'conversation', 'review', 'settings', 'tools'].includes(route.name))

const themeIcon = computed(() => ({ light: 'sun', dark: 'moon', system: 'monitor' }[app.theme]))
const isDark = computed(() => document.documentElement.getAttribute('data-mode') === 'dark')
function cycleTheme() {
  const order = ['light', 'dark', 'system']
  app.setTheme(order[(order.indexOf(app.theme) + 1) % order.length])
}

/* 搜索 */
const kw = ref(route.query.keyword || '')
const suggest = ref([])
const searching = ref(false)
let timer = null
function onSearchFocus() { if (kw.value.trim()) onSearchInput() }
function onSearchInput() {
  clearTimeout(timer)
  const q = kw.value.trim()
  if (!q) { suggest.value = []; return }
  timer = setTimeout(async () => {
    searching.value = true
    try { const r = await api.searchUsers({ keyword: q, page_size: 6 }); suggest.value = r.items } catch { suggest.value = [] }
    searching.value = false
  }, 260)
}
function doSearch() {
  suggest.value = []
  const q = kw.value.trim()
  if (!q) return
  router.push({ name: 'home', query: { keyword: q } })
}

function onCreated() {
  app.bumpFeed()
  if (route.name !== 'home') router.push({ name: 'home' })
}
function onUpdated() { app.bumpFeed() }
function logout() {
  auth.logout()
  toast.info('已退出登录')
  router.push('/')
}
function onDocClick(e) {
  if (!e.target.closest('.user-menu')) menu.value = false
}
onMounted(() => {
  document.addEventListener('click', onDocClick)
  api.getCategories().then((r) => (categories.value = r)).catch(() => {})
  app.loadSettings()
})
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
watch(() => route.query.keyword, (v) => { kw.value = v || '' })
</script>

<style scoped>
.shell { min-height: 100dvh; }

.topbar {
  position: sticky; top: 0; z-index: var(--z-nav);
  background: color-mix(in srgb, var(--surface) 82%, transparent);
  backdrop-filter: saturate(180%) blur(14px); -webkit-backdrop-filter: saturate(180%) blur(14px);
  border-bottom: 1px solid var(--line);
}
.topbar-inner { display: flex; align-items: center; gap: 22px; height: var(--nav-h); }
.brand { display: flex; align-items: center; gap: 10px; color: var(--ink); flex: none; }
.brand-mark {
  width: 36px; height: 36px; border-radius: 11px; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(150deg, #1f9685, #0f554c); color: #fff;
  box-shadow: 0 6px 14px -6px rgba(15, 85, 76, 0.6);
}
.brand-text { font-size: 18px; font-weight: 700; letter-spacing: -0.02em; }
.brand-logo { width: 24px; height: 24px; border-radius: 6px; object-fit: cover; display: block; }

.search { position: relative; flex: 1; max-width: 460px; }
.search-ico { position: absolute; left: 13px; top: 50%; transform: translateY(-50%); color: var(--ink-4); pointer-events: none; }
.search input {
  width: 100%; height: 40px; padding: 0 14px 0 38px;
  border-radius: 999px; border: 1px solid var(--line-strong);
  background: var(--surface-2); font-size: 14px; transition: all var(--t-base) var(--ease-out);
}
.search input:focus { outline: none; border-color: var(--brand-500); background: var(--surface); box-shadow: 0 0 0 3px color-mix(in srgb, var(--brand-500) 16%, transparent); }
.suggest {
  position: absolute; top: calc(100% + 8px); left: 0; right: 0; z-index: var(--z-dropdown);
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-md);
  box-shadow: var(--shadow-pop); padding: 6px; max-height: 380px; overflow-y: auto;
}
.sg-item { display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: var(--r-xs); color: inherit; }
.sg-item:hover { background: var(--surface-3); }
.sg-name { font-size: 14px; font-weight: 560; color: var(--ink); display: block; }
.sg-meta { font-size: 12px; }
.sg-loading { padding: 10px; font-size: 13px; }
.sg-more { width: 100%; text-align: center; padding: 10px; font-size: 13px; color: var(--brand-700); border-top: 1px solid var(--line); margin-top: 4px; }

.top-actions { display: flex; align-items: center; gap: 8px; margin-left: auto; flex: none; }
.icon-btn {
  position: relative; width: 40px; height: 40px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; color: var(--ink-2);
  transition: background var(--t-fast), color var(--t-fast);
}
.icon-btn:hover { background: var(--surface-3); color: var(--ink); }
.icon-btn .dot, .sn-dot {
  position: absolute; top: 3px; right: 3px; min-width: 16px; height: 16px; padding: 0 4px;
  background: var(--danger); color: #fff; border-radius: 999px; font-size: 10.5px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; border: 2px solid var(--surface);
}
.compose .icon-btn { display: none; }

.user-menu { position: relative; }
.um-btn { display: flex; align-items: center; gap: 5px; padding: 3px 6px 3px 3px; border-radius: 999px; }
.um-btn:hover { background: var(--surface-3); }
.um-panel {
  position: absolute; right: 0; top: calc(100% + 10px); width: 240px;
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-md);
  box-shadow: var(--shadow-pop); padding: 8px; z-index: var(--z-dropdown);
}
.um-head { display: flex; align-items: center; gap: 10px; padding: 8px 8px 12px; border-bottom: 1px solid var(--line); margin-bottom: 6px; }
.um-name { font-weight: 650; color: var(--ink); font-size: 14.5px; }
.um-id { font-size: 12px; }
.um-item { display: flex; align-items: center; gap: 10px; padding: 9px 10px; border-radius: var(--r-xs); font-size: 14px; color: var(--ink-2); width: 100%; text-align: left; }
.um-item:hover { background: var(--surface-3); color: var(--ink); }
.um-item.danger { color: var(--danger-strong); }
.um-sep { height: 1px; background: var(--line); margin: 4px 2px; }

.layout { display: grid; grid-template-columns: 232px minmax(0, 1fr) 300px; gap: 28px; padding-top: 26px; padding-bottom: 60px; align-items: start; }
.layout.wide { grid-template-columns: 232px minmax(0, 1fr); }
.rail { position: sticky; top: calc(var(--nav-h) + 22px); }
.rail-left { display: flex; flex-direction: column; gap: 14px; }
.side-nav { display: flex; flex-direction: column; gap: 2px; }
.sn {
  display: flex; align-items: center; gap: 13px; padding: 11px 16px; border-radius: 10px;
  color: var(--ink-2); font-size: 15px; font-weight: 520; position: relative;
  transition: background var(--t-fast), color var(--t-fast), transform var(--t-fast);
  overflow: hidden;
}
.sn::before {
  content: ""; position: absolute; left: 0; top: 50%; transform: translateY(-50%) scaleY(0);
  width: 3px; height: 60%; border-radius: 0 3px 3px 0; background: var(--brand-500);
  transition: transform var(--t-fast) var(--ease-out);
}
.sn:hover { background: var(--surface-3); color: var(--ink); transform: translateX(2px); }
.sn.active {
  background: var(--brand-50); color: var(--brand-700); font-weight: 650;
}
.sn.active::before { transform: translateY(-50%) scaleY(1); }
.sn .sn-dot { position: static; margin-left: auto; border: none; }
.side-post {
  margin-top: 6px; height: 44px; border-radius: 12px;
  font-weight: 600; letter-spacing: .5px;
  box-shadow: 0 4px 14px -6px color-mix(in srgb, var(--brand-btn-bg) 60%, transparent);
  transition: transform var(--t-fast), box-shadow var(--t-fast);
}
.side-post:hover { transform: translateY(-1px); box-shadow: 0 8px 20px -6px color-mix(in srgb, var(--brand-btn-bg) 50%, transparent); }
.rail-foot { padding: 12px 14px; font-size: 12px; line-height: 1.6; font-family: var(--font-serif); color: var(--ink-4); }

.content { min-width: 0; max-width: 680px; width: 100%; margin: 0 auto; }
.layout.wide .content { max-width: 920px; }
.rail-right { display: flex; flex-direction: column; gap: 16px; }
.legal { font-size: 12px; line-height: 1.7; padding: 0 6px; }
.legal a { color: var(--ink-4); }

.menu-enter-active, .menu-leave-active { transition: all var(--t-fast) var(--ease-out); }
.menu-enter-from, .menu-leave-to { opacity: 0; transform: translateY(-6px); }
.view-enter-active { transition: opacity var(--t-base) var(--ease-out); }
.view-enter-from { opacity: 0; }

/* ---- 响应式断点 ----
   >1200px：三栏（左导航 + 信息流 + 右推荐）
   768–1200px：两栏（隐藏右侧推荐栏）
   <768px：单栏（隐藏左侧导航，仅顶部栏） */
@media (max-width: 1200px) {
  .layout { grid-template-columns: 208px minmax(0, 1fr); gap: 22px; }
  .layout.wide { grid-template-columns: 208px minmax(0, 1fr); }
  .rail-right { display: none; }
  .content { max-width: 760px; }
  .layout.wide .content { max-width: 960px; }
}
@media (max-width: 768px) {
  .layout, .layout.wide { grid-template-columns: 1fr; padding-top: 18px; }
  .rail-left { display: none; }
  .content, .layout.wide .content { max-width: 100%; }
  .brand-text, .compose span { display: none; }
  .search { display: none; }
}
</style>
