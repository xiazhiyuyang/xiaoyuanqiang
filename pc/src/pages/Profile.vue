<template>
  <div class="profile">
    <div v-if="loading" class="profile-head card-flush">
      <div class="skeleton" style="height:150px;border-radius:0"></div>
      <div class="head-body">
        <div class="skeleton" style="width:92px;height:92px;border-radius:50%"></div>
        <div class="grow"><div class="skeleton" style="width:160px;height:22px"></div></div>
        <div class="skeleton" style="width:104px;height:38px;border-radius:999px"></div>
      </div>
      <div class="head-sub">
        <div class="skeleton" style="width:55%;height:13px;margin-bottom:10px"></div>
        <div class="skeleton" style="width:38%;height:12px"></div>
      </div>
      <div class="head-stats">
        <div v-for="n in 4" :key="n" class="stat"><div class="skeleton" style="width:26px;height:19px;margin-bottom:5px"></div><div class="skeleton" style="width:28px;height:11px"></div></div>
      </div>
    </div>

    <template v-else-if="u">
      <div class="profile-head card-flush">
        <div class="cover" :style="{ background: coverBg }" />
        <div class="head-body">
          <UserAvatar :src="u.avatar" :name="u.nickname" :size="92" class="head-avatar" />
          <div class="head-main">
            <div class="head-name-row">
              <div class="name-uid-group">
                <h1>{{ u.nickname }}</h1>
                <span v-if="u.uid" class="uid-card" :class="{ premium: isPremiumUid(u.uid) }">
                  <span class="uid-label">UID</span>
                  <span class="uid-num">{{ u.uid }}</span>
                  <span v-if="isPremiumUid(u.uid)" class="uid-crown">👑</span>
                </span>
              </div>
              <span v-for="t in u.perm_tags" :key="t" class="staff-tag">{{ tagLabel(t) }}</span>
            </div>
          </div>
          <div class="head-actions">
            <template v-if="u.is_self">
              <RouterLink to="/settings" class="btn btn-soft"><Icon name="edit" :size="16" /> 编辑资料</RouterLink>
            </template>
            <template v-else>
              <FollowButton :user-id="u.id" :model-value="u.is_following" size="lg" @update:model-value="onFollowChange" />
              <button class="btn btn-soft" @click="message"><Icon name="message" :size="16" /> 私信</button>
            </template>
          </div>
        </div>
        <div class="head-sub">
          <p class="head-bio" :class="{ faint: !u.bio }">{{ u.bio || '这位同学还没有填写简介' }}</p>
          <div class="head-meta faint">
            <span v-if="u.college"><Icon name="school" :size="14" /> {{ [u.college, u.major].filter(Boolean).join(' · ') }}</span>
            <span v-if="u.grade"><Icon name="book" :size="14" /> {{ u.grade }}</span>
            <span v-if="u.location"><Icon name="pin" :size="14" /> {{ u.location }}</span>
            <span><Icon name="calendar" :size="14" /> {{ joinYear }} 年加入</span>
          </div>
        </div>
        <div class="head-stats">
          <RouterLink :to="`/u/${u.id}/follows?type=following`" class="stat"><strong class="tabular">{{ u.post_count || 0 }}</strong><span>动态</span></RouterLink>
          <span class="stat"><strong class="tabular">{{ u.like_count || 0 }}</strong><span>获赞</span></span>
          <RouterLink :to="`/u/${u.id}/follows?type=followers`" class="stat"><strong class="tabular">{{ u.followers_count || 0 }}</strong><span>粉丝</span></RouterLink>
          <RouterLink :to="`/u/${u.id}/follows?type=following`" class="stat"><strong class="tabular">{{ u.following_count || 0 }}</strong><span>关注</span></RouterLink>
        </div>
      </div>

      <!-- 本人多一个状态切换 -->
      <div v-if="u.is_self" class="pt-tabs">
        <button :class="{ on: tab === 'published' }" @click="switchTab('published')">已发布</button>
        <button :class="{ on: tab === 'pending' }" @click="switchTab('pending')">待审核</button>
        <button :class="{ on: tab === 'fav' }" @click="switchTab('fav')">我的收藏</button>
      </div>

      <FeedSkeleton v-if="listLoading && !posts.length" :count="3" />
      <template v-else>
        <PostCard v-for="p in posts" :key="p.id" :post="p" @deleted="removePost" @edit="(p) => openCompose(p)" />
        <EmptyState
          v-if="!posts.length"
          :icon="tab === 'fav' ? 'bookmark' : tab === 'pending' ? 'clock' : 'inbox'"
          :title="emptyTitle"
        />
        <div ref="sentinel" />
        <p v-if="!hasMore && posts.length" class="no-more">—— 已经到底啦 ——</p>
      </template>
    </template>

    <NotFound v-else />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import UserAvatar from '../components/UserAvatar.vue'
import FollowButton from '../components/FollowButton.vue'
import PostCard from '../components/PostCard.vue'
import FeedSkeleton from '../components/FeedSkeleton.vue'
import EmptyState from '../components/EmptyState.vue'
import NotFound from './NotFound.vue'
import api from '../api'
import { useAuth } from '../stores/auth'
import { useApp } from '../stores/app'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const app = useApp()
const openCompose = inject('openCompose', () => {})

const u = ref(null)
const loading = ref(true)
const posts = ref([])
const listLoading = ref(false)
const page = ref(1)
const totalPages = ref(1)
const tab = ref('published')
const sentinel = ref(null)
let observer = null

const hasMore = computed(() => page.value < totalPages.value)
const joinYear = computed(() => (u.value?.created_at ? new Date(u.value.created_at).getFullYear() : '——'))
const coverBg = computed(() => {
  if (u.value?.cover_image) {
    return `url(${u.value.cover_image}) center/cover no-repeat`
  }
  const colors = ['linear-gradient(120deg,#14806f,#0f554c)', 'linear-gradient(120deg,#3f7fd4,#2c5fa8)', 'linear-gradient(120deg,#bd7b1f,#9a5f12)', 'linear-gradient(120deg,#7c6bc4,#5a4aa0)']
  let h = 0; const k = String(u.value?.id || 0); for (let i = 0; i < k.length; i++) h = (h * 31 + k.charCodeAt(i)) >>> 0
  return colors[h % colors.length]
})
const emptyTitle = computed(() => ({ fav: '还没有收藏内容', pending: '没有待审核的动态', published: '还没有发布动态' }[tab.value]))

function tagLabel(t) { return { admin: '管理员', content_review: '审核员', report_review: '审查员' }[t] || t }
const isPremiumUid = (uid) => uid && parseInt(uid) < 1000

async function loadProfile() {
  loading.value = true; u.value = null
  try {
    u.value = await api.getUser(route.params.id)
    tab.value = 'published'
    await loadList(true)
  } catch { u.value = null } finally { loading.value = false }
}
async function loadList(reset = false) {
  if (listLoading.value) return
  if (reset) { page.value = 1; posts.value = []; totalPages.value = 1 }
  listLoading.value = true
  try {
    let r
    if (tab.value === 'fav') r = await api.getMyFavorites({ page: page.value, page_size: 10 })
    else if (u.value.is_self) r = await api.getMyPosts({ page: page.value, page_size: 10, status: tab.value })
    else r = await api.getUserPosts(route.params.id, { page: page.value, page_size: 10 })
    posts.value = reset ? r.items : posts.value.concat(r.items)
    totalPages.value = r.total_pages || 1
  } catch { /* */ } finally { listLoading.value = false }
}
async function more() { if (!hasMore.value || listLoading.value) return; page.value += 1; await loadList(false) }
function switchTab(t) { if (tab.value === t) return; tab.value = t; loadList(true) }
function removePost(id) { posts.value = posts.value.filter((p) => p.id !== id) }
function onFollowChange(r) {
  if (u.value) u.value.is_following = r.following
}
async function message() {
  if (!auth.isLoggedIn) return router.push('/login')
  try {
    const c = await api.createConversation({ target_user_id: Number(route.params.id) })
    router.push(`/messages/${c.id}`)
  } catch { /* */ }
}

watch(() => route.params.id, loadProfile, { immediate: true })
watch(() => app.feedTick, () => { if (u.value?.is_self) loadList(true) })

onMounted(() => {
  observer = new IntersectionObserver((es) => { if (es[0].isIntersecting) more() }, { rootMargin: '300px' })
  if (sentinel.value) observer.observe(sentinel.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<style scoped>
.profile-head { background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-lg); box-shadow: var(--shadow-sm); overflow: hidden; margin-bottom: 18px; }
.cover { height: 150px; }
.head-body { display: flex; gap: 16px; align-items: center; padding: 0 24px; margin-top: -24px; flex-wrap: wrap; }
.head-avatar { box-shadow: 0 0 0 4px var(--surface); border-radius: 50%; flex: none; position: relative; z-index: 1; }
.head-main { flex: 1 1 300px; min-width: 0; }
.head-name-row { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; }
.name-uid-group { display: flex; align-items: center; gap: 9px; flex-wrap: nowrap; flex-shrink: 0; }
.name-uid-group h1 { flex-shrink: 0; white-space: nowrap; }
.head-name-row h1 { font-size: 22px; line-height: 1.2; }
.staff-tag { font-size: 11px; font-weight: 600; color: var(--brand-700); background: var(--brand-50); border-radius: 6px; padding: 2px 7px; }
.uid-card {
  display: inline-flex; align-items: center; gap: 8px;
  flex-shrink: 0; flex-wrap: nowrap;
  background: linear-gradient(135deg, #1e293b, #0f172a);
  border: 1px solid rgba(148,163,184,.25);
  border-radius: 10px; padding: 5px 14px 5px 10px;
  position: relative; overflow: hidden;
  box-shadow: 0 2px 8px rgba(15,23,42,.15);
}
.uid-card::before {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: linear-gradient(180deg, #3b82f6, #60a5fa);
}
.uid-card .uid-label {
  font-size: 9px; font-weight: 800; letter-spacing: 1.5px;
  color: rgba(148,163,184,.7); text-transform: uppercase;
  background: rgba(148,163,184,.1); border-radius: 4px; padding: 2px 5px;
}
.uid-card .uid-num {
  font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
  font-size: 16px; font-weight: 700; letter-spacing: 2px;
  color: #e2e8f0; line-height: 1;
}
.uid-card.premium {
  background: linear-gradient(135deg, #451a03, #78350f);
  border-color: rgba(252,211,77,.35);
  box-shadow: 0 2px 12px rgba(217,119,6,.25);
}
.uid-card.premium::before {
  background: linear-gradient(180deg, #fbbf24, #f59e0b);
}
.uid-card.premium .uid-label {
  color: rgba(252,211,77,.8); background: rgba(252,211,77,.12);
}
.uid-card.premium .uid-num {
  color: #fef3c7;
}
.uid-card .uid-crown { font-size: 14px; }
.head-actions { display: flex; gap: 9px; flex: none; }
.head-sub { padding: 14px 24px 0; }
.head-bio { color: var(--ink-2); font-size: 14px; line-height: 1.6; }
.head-meta { display: flex; flex-wrap: wrap; gap: 14px; font-size: 12.5px; margin-top: 8px; }
.head-meta span { display: inline-flex; align-items: center; gap: 5px; }
.head-stats { display: flex; gap: 4px; padding: 14px 24px; margin-top: 16px; border-top: 1px solid var(--line); }
.stat { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 4px 22px; color: inherit; position: relative; }
.stat + .stat::before { content: ''; position: absolute; left: 0; top: 50%; transform: translateY(-50%); width: 1px; height: 26px; background: var(--line); }
.stat strong { font-size: 19px; font-weight: 700; color: var(--ink); }
.stat span { font-size: 12.5px; color: var(--ink-4); }
.stat:hover strong { color: var(--brand-700); }

.pt-tabs { display: flex; gap: 4px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-pill); padding: 4px; margin-bottom: 16px; width: max-content; }
.pt-tabs button { padding: 7px 18px; border-radius: var(--r-pill); font-size: 13.5px; font-weight: 540; color: var(--ink-3); }
.pt-tabs button.on { background: var(--ink); color: var(--surface); }
.no-more { text-align: center; color: var(--ink-4); font-size: 12.5px; padding: 18px; }
</style>
