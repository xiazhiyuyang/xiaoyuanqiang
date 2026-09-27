<template>
  <div class="home">
    <!-- 发帖入口 -->
    <div v-if="auth.isLoggedIn" class="composer-entry card" @click="openCompose()">
      <UserAvatar :src="auth.user?.avatar" :name="auth.user?.nickname" :size="42" />
      <button class="ce-input">{{ auth.user?.nickname }}，分享你的校园新鲜事…</button>
      <span class="ce-btn"><Icon name="image" :size="18" /></span>
    </div>
    <div v-else class="composer-entry card">
      <div class="ce-login">
        <p class="ce-title">登录后发布动态、互动交流</p>
        <RouterLink to="/login" class="btn btn-primary btn-sm">登录 / 注册</RouterLink>
      </div>
    </div>

    <!-- 筛选条 -->
    <div class="filter-bar">
      <div class="chips">
        <button class="chip" :class="{ active: !filters.category_id }" @click="setCat(null)">全部</button>
        <button
          v-for="c in categories" :key="c.id" class="chip"
          :class="{ active: filters.category_id === c.id }"
          @click="setCat(c.id)"
        >{{ c.icon }} {{ c.name }}</button>
      </div>
      <div class="toggles">
        <button v-if="auth.isLoggedIn" class="seg" :class="{ on: filters.feed === 'following' }" @click="toggleFeed">
          <Icon name="users" :size="14" /> 关注
        </button>
        <div class="seg-group">
          <button :class="{ on: filters.sort === 'new' }" @click="setSort('new')">最新</button>
          <button :class="{ on: filters.sort === 'hot' }" @click="setSort('hot')"><Icon name="fire" :size="13" /> 最热</button>
        </div>
      </div>
    </div>

    <!-- 搜索提示 -->
    <div v-if="filters.keyword" class="search-tip">
      <span>“{{ filters.keyword }}”的搜索结果</span>
      <button @click="clearKeyword"><Icon name="x" :size="14" /> 清除</button>
    </div>

    <FeedSkeleton v-if="loading && !posts.length" :count="4" />

    <template v-else>
      <PostCard
        v-for="p in posts" :key="p.id" :post="p"
        @deleted="removePost" @edit="onEdit"
      />
      <EmptyState
        v-if="!posts.length && !loading"
        :icon="filters.feed === 'following' ? 'users' : 'inbox'"
        :title="filters.keyword ? '没有找到相关动态' : (filters.feed === 'following' ? '关注流还是空的' : '还没有人发布动态')"
        :description="filters.feed === 'following' ? '去关注一些同学，TA 们的动态会出现在这里' : '来发布第一条校园动态吧'"
      >
        <button v-if="auth.isLoggedIn" class="btn btn-primary" @click="openCompose()">发布动态</button>
      </EmptyState>

      <div ref="sentinel" class="sentinel" />
      <div v-if="loading && posts.length" class="loading-more"><span class="spinner" /> 加载中…</div>
      <p v-if="!hasMore && posts.length" class="no-more">—— 已经到底啦 ——</p>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import UserAvatar from '../components/UserAvatar.vue'
import PostCard from '../components/PostCard.vue'
import FeedSkeleton from '../components/FeedSkeleton.vue'
import EmptyState from '../components/EmptyState.vue'
import api from '../api'
import { useAuth } from '../stores/auth'
import { useApp } from '../stores/app'

const emit = defineEmits(['compose'])
const route = useRoute()
const router = useRouter()
const auth = useAuth()
const app = useApp()
const openCompose = inject('openCompose', () => {})

const categories = ref([])
const posts = ref([])
const loading = ref(false)
const page = ref(1)
const totalPages = ref(1)
const hasMore = computed(() => page.value < totalPages.value)
const sentinel = ref(null)
let observer = null

const filters = reactive({
  category_id: null,
  sort: 'new',
  feed: 'all',
  keyword: '',
})

async function loadCategories() {
  try { categories.value = await api.getCategories() } catch { /* */ }
}
async function load(reset = false) {
  if (loading.value) return
  if (reset) { page.value = 1; posts.value = []; totalPages.value = 1 }
  loading.value = true
  try {
    const r = await api.getPosts({
      page: page.value, page_size: 10,
      category_id: filters.category_id || undefined,
      sort: filters.sort, feed: filters.feed,
      keyword: filters.keyword || undefined,
    })
    posts.value = reset ? r.items : posts.value.concat(r.items)
    totalPages.value = r.total_pages || 1
  } catch { /* toast handled */ } finally {
    loading.value = false
  }
}
async function more() {
  if (!hasMore.value || loading.value) return
  page.value += 1
  await load(false)
}
function reload() { load(true) }

function setCat(id) { filters.category_id = id; reload() }
function setSort(s) { if (filters.sort === s) return; filters.sort = s; reload() }
function toggleFeed() { filters.feed = filters.feed === 'following' ? 'all' : 'following'; reload() }
function clearKeyword() { router.replace({ query: {} }) }

function removePost(id) { posts.value = posts.value.filter((p) => p.id !== id) }
function onEdit(p) { openCompose(p) }

watch(() => route.query.keyword, (v) => {
  filters.keyword = v || ''
  reload()
})
watch(() => app.feedTick, () => reload())

onMounted(async () => {
  filters.keyword = route.query.keyword || ''
  await loadCategories()
  await load(true)
  observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) more()
  }, { rootMargin: '300px' })
  if (sentinel.value) observer.observe(sentinel.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<style scoped>
.composer-entry {
  display: flex; align-items: center; gap: 12px; padding: 16px 20px; margin-bottom: 16px;
  cursor: pointer; border-radius: var(--r-lg); background: var(--surface);
  border: 1px solid var(--line); box-shadow: var(--shadow-sm);
  transition: box-shadow var(--t-base), border-color var(--t-base), transform var(--t-base);
}
.composer-entry:hover {
  box-shadow: var(--shadow-md); border-color: var(--brand-300);
  transform: translateY(-1px);
}
.ce-input {
  flex: 1; text-align: left; height: 42px; border-radius: 999px; padding: 0 18px;
  background: var(--surface-2); border: 1px solid var(--line); color: var(--ink-4);
  font-size: 14px; font-family: var(--font-serif); transition: border-color var(--t-fast), background var(--t-fast);
}
.composer-entry:hover .ce-input { border-color: var(--brand-400); background: var(--surface); color: var(--ink-3); }
.ce-btn {
  width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; color: var(--surface); background: var(--brand-btn-bg);
  flex: none; transition: background var(--t-fast), transform var(--t-fast);
}
.composer-entry:hover .ce-btn { background: var(--brand-btn-hover); transform: scale(1.05); }
.ce-login { display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 12px; }
.ce-title { color: var(--ink-2); font-size: 14.5px; font-family: var(--font-serif); }

.filter-bar {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; margin-bottom: 16px; flex-wrap: wrap;
  padding-bottom: 12px; border-bottom: 1px solid var(--line);
}
.chips { display: flex; gap: 6px; overflow-x: auto; scrollbar-width: none; padding-bottom: 2px; }
.chips::-webkit-scrollbar { display: none; }
.chip {
  flex: none; padding: 7px 15px; border-radius: 8px; font-size: 13.5px; font-weight: 520;
  color: var(--ink-3); background: transparent; border: 1px solid transparent;
  transition: all var(--t-fast) var(--ease-out); font-family: var(--font-sans);
}
.chip:hover { color: var(--ink); background: var(--surface-3); }
.chip.active {
  background: var(--ink); color: var(--surface); border-color: var(--ink);
  font-weight: 600;
}
.toggles { display: flex; gap: 8px; align-items: center; flex: none; }
.seg, .seg-group button {
  display: inline-flex; align-items: center; gap: 5px; height: 32px; padding: 0 13px;
  border-radius: 8px; font-size: 13px; font-weight: 520; color: var(--ink-3);
  background: var(--surface); border: 1px solid var(--line);
}
.seg-group { display: inline-flex; border-radius: 8px; overflow: hidden; border: 1px solid var(--line); background: var(--surface); }
.seg-group button { border: none; border-radius: 0; background: transparent; }
.seg-group button + button { border-left: 1px solid var(--line); }
.seg.on, .seg-group button.on { color: var(--brand-700); background: var(--brand-50); }
.seg-group button.on { background: var(--brand-50); }

.search-tip { display: flex; align-items: center; justify-content: space-between; font-size: 13.5px; color: var(--ink-3); margin-bottom: 12px; padding: 0 2px; }
.search-tip button { display: inline-flex; align-items: center; gap: 4px; color: var(--ink-4); }
.search-tip button:hover { color: var(--danger-strong); }

.sentinel { height: 10px; }
.loading-more { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 18px; color: var(--ink-4); font-size: 13px; }
.spinner { width: 15px; height: 15px; border: 2px solid var(--line-strong); border-top-color: var(--brand-600); border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.no-more {
  text-align: center; color: var(--ink-4); font-size: 12.5px; padding: 24px;
  font-family: var(--font-serif); letter-spacing: 2px;
}
</style>
