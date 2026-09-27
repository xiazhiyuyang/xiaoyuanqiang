<template>
  <div class="detail">
    <button class="back" @click="goBack"><Icon name="arrow-left" :size="17" /> 返回</button>

    <div v-if="loading" class="card sk-article">
      <div class="sk-head">
        <div class="skeleton" style="width:46px;height:46px;border-radius:50%"></div>
        <div class="grow"><div class="skeleton" style="width:140px;height:13px;margin-bottom:9px"></div><div class="skeleton" style="width:90px;height:11px"></div></div>
      </div>
      <div class="skeleton" style="width:80%;height:22px;margin:18px 0 12px"></div>
      <div class="skeleton" style="width:100%;height:13px;margin-bottom:8px"></div>
      <div class="skeleton" style="width:96%;height:13px;margin-bottom:8px"></div>
      <div class="skeleton" style="width:60%;height:13px"></div>
    </div>

    <template v-else-if="post">
      <article class="article card">
        <header class="a-head">
          <RouterLink :to="profileUrl" class="a-user">
            <UserAvatar :src="post.author?.avatar" :name="displayName" :anonymous="post.is_anonymous" :seed="post.user_id" :size="46" />
            <span class="a-user-meta">
              <span class="a-name-row">
                <strong>{{ displayName }}</strong>
                <LevelBadge v-if="post.level_badge" :badge="post.level_badge" />
                <span v-for="t in staffTags" :key="t" class="staff-tag">{{ staffLabel(t) }}</span>
              </span>
              <span class="a-sub faint">
                <span class="tabular">{{ formatDateTime(post.created_at) }}</span>
                <span v-if="post.category"> · {{ post.category.name }}</span>
                <span v-if="post.visibility === 'private'"> · 仅自己可见</span>
              </span>
            </span>
          </RouterLink>
          <FollowButton v-if="showFollow" :user-id="post.author.id" :model-value="post.author.is_following" size="lg"
            @update:model-value="(v) => post.author.is_following = v" />
        </header>

        <h1 v-if="post.title" class="a-title">{{ post.title }}</h1>
        <div v-if="post.content" class="a-content">{{ post.content }}</div>

        <ImageGrid v-if="post.images && post.images.length" :images="post.images" />
        <video v-if="post.video_url" class="a-video" :src="mediaUrl(post.video_url)" controls preload="metadata" />

        <div class="a-stats faint">
          <span class="tabular"><Icon name="eye" :size="14" /> {{ post.view_count || 0 }} 浏览</span>
          <span class="tabular">{{ post.comment_count || 0 }} 评论</span>
        </div>

        <div class="a-actions">
          <button class="aa" :class="{ on: liked }" @click="toggleLike">
            <Icon name="heart" :size="20" :filled="liked" /><span class="tabular">{{ post.like_count || 0 }}</span><span>赞</span>
          </button>
          <a class="aa" href="#comments"><Icon name="comment" :size="20" /><span class="tabular">{{ post.comment_count || 0 }}</span><span>评论</span></a>
          <button class="aa" :class="{ on: favorited }" @click="toggleFavorite">
            <Icon name="bookmark" :size="20" :filled="favorited" /><span>{{ favorited ? '已收藏' : '收藏' }}</span>
          </button>
          <span class="grow" />
          <button class="aa icon-only" title="复制链接" @click="copyLink"><Icon name="link" :size="18" /></button>
          <button v-if="canManage" class="aa icon-only" title="编辑" @click="openCompose(post)"><Icon name="edit" :size="18" /></button>
          <button v-if="canManage" class="aa icon-only danger" title="删除" @click="onDelete"><Icon name="trash" :size="18" /></button>
          <button v-if="!isOwner" class="aa icon-only danger" title="举报" @click="reportOpen = true"><Icon name="flag" :size="18" /></button>
        </div>
      </article>

      <section id="comments" class="comments card">
        <h3 class="cm-title">评论 <span class="faint tabular">{{ total }}</span></h3>

        <div v-if="auth.isLoggedIn" class="cm-composer">
          <UserAvatar :src="auth.user?.avatar" :name="auth.user?.nickname" :size="38" />
          <div class="grow">
            <textarea v-model="draft" class="textarea" rows="3" maxlength="2000" placeholder="友善发言，说点什么…" />
            <div class="cm-send">
              <span class="faint tabular">{{ draft.length }}/2000</span>
              <button class="btn btn-primary btn-sm" :disabled="submitting || !draft.trim()" @click="submitComment">
                {{ submitting ? '发送中…' : '发表评论' }}
              </button>
            </div>
          </div>
        </div>
        <div v-else class="cm-login">
          <p class="muted">登录后参与评论</p>
          <RouterLink to="/login" class="btn btn-soft btn-sm">登录 / 注册</RouterLink>
        </div>

        <div v-if="commentsLoading && !comments.length" class="cm-list">
          <div v-for="i in 3" :key="i" class="sk-comment">
            <div class="skeleton" style="width:40px;height:40px;border-radius:50%"></div>
            <div class="grow"><div class="skeleton" style="width:200px;height:12px;margin-bottom:8px"></div><div class="skeleton" style="width:80%;height:12px"></div></div>
          </div>
        </div>

        <template v-else>
          <div class="cm-list">
            <CommentItem
              v-for="c in comments" :key="c.id"
              :comment="c" :post-id="postId" :root-id="c.id" :depth="0" :name-map="nameMap"
              @changed="reloadComments"
            />
          </div>
          <EmptyState v-if="!comments.length" icon="comment" title="还没有评论" description="来抢沙发，写下第一条评论吧" />
          <button v-if="commentPage < commentPages" class="btn btn-ghost btn-block load-more" @click="loadComments(false)">
            加载更多评论
          </button>
        </template>
      </section>
    </template>

    <NotFound v-else-if="notFound" />

    <ReportDialog v-model="reportOpen" target-type="post" :target-id="postId" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import UserAvatar from '../components/UserAvatar.vue'
import LevelBadge from '../components/LevelBadge.vue'
import ImageGrid from '../components/ImageGrid.vue'
import FollowButton from '../components/FollowButton.vue'
import ReportDialog from '../components/ReportDialog.vue'
import CommentItem from '../components/CommentItem.vue'
import EmptyState from '../components/EmptyState.vue'
import NotFound from './NotFound.vue'
import api from '../api'
import { useAuth } from '../stores/auth'
import { useApp } from '../stores/app'
import { mediaUrl, formatDateTime } from '../utils/format'
import { toast } from '../utils/toast'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const app = useApp()
const openCompose = inject('openCompose', () => {})

const postId = computed(() => route.params.id)
const post = ref(null)
const loading = ref(true)
const notFound = ref(false)
const liked = ref(false)
const favorited = ref(false)
const reportOpen = ref(false)

const comments = ref([])
const commentsLoading = ref(false)
const commentPage = ref(1)
const commentPages = ref(1)
const total = ref(0)
const draft = ref('')
const submitting = ref(false)

const isOwner = computed(() => post.value?.author && auth.user && post.value.author.id === auth.user.id)
const canManage = computed(() => isOwner.value || post.value?.can_edit || auth.isAdmin)
const displayName = computed(() => post.value?.is_anonymous ? (post.value.author_name || '匿名同学') : (post.value?.author?.nickname || '未知用户'))
const staffTags = computed(() => post.value?.is_anonymous ? [] : post.value?.author?.staff_tags || [])
const profileUrl = computed(() => post.value?.author ? `/u/${post.value.author.id}` : '#')
const showFollow = computed(() => post.value?.author && auth.isLoggedIn && !isOwner.value && post.value.author.is_following === false)

const nameMap = computed(() => {
  const m = {}
  const walk = (list) => list.forEach((c) => {
    if (c.author) m[c.author.id] = c.author.nickname
    if (c.replies?.length) walk(c.replies)
  })
  walk(comments.value)
  return m
})

async function loadPost() {
  loading.value = true; notFound.value = false
  try {
    const p = await api.getPost(postId.value)
    post.value = p
    liked.value = !!p.is_liked
    favorited.value = !!p.is_favorited
    document.title = p.title ? `${p.title} · ${app.siteName}` : app.siteName
    await loadComments(true)
  } catch (e) {
    if (e.response?.status === 404) notFound.value = true
  } finally { loading.value = false }
}
async function loadComments(reset = false) {
  if (reset) { commentPage.value = 1; comments.value = [] }
  commentsLoading.value = true
  try {
    const r = await api.getComments(postId.value, { page: commentPage.value, page_size: 20 })
    comments.value = reset ? r.items : comments.value.concat(r.items)
    commentPages.value = r.total_pages || 1
    total.value = r.total || 0
  } catch { /* */ } finally { commentsLoading.value = false }
}
function reloadComments() {
  loadComments(true).then(() => { if (post.value) post.value.comment_count = total.value })
}
async function submitComment() {
  const text = draft.value.trim()
  if (!text) return
  submitting.value = true
  try {
    const res = await api.createComment(postId.value, { content: text })
    draft.value = ''
    const msg = res?._msg || ''
    if (msg && /审核|复核|打码|等待/.test(msg)) {
      toast.info(msg)
    } else {
      toast.success('评论成功')
    }
    await loadComments(true)
    if (post.value) post.value.comment_count = total.value
  } catch { /* */ } finally { submitting.value = false }
}
async function toggleLike() {
  if (!auth.isLoggedIn) return router.push('/login')
  liked.value = !liked.value
  post.value.like_count += liked.value ? 1 : -1
  try { const r = await api.likePost(postId.value); liked.value = r.liked; post.value.like_count = r.like_count }
  catch { liked.value = !liked.value; post.value.like_count += liked.value ? 1 : -1 }
}
async function toggleFavorite() {
  if (!auth.isLoggedIn) return router.push('/login')
  favorited.value = !favorited.value
  try { const r = await api.favoritePost(postId.value); favorited.value = r.favorited; toast.success(r.favorited ? '已收藏' : '已取消收藏') }
  catch { favorited.value = !favorited.value }
}
function copyLink() {
  const url = location.origin + '/pc/post/' + postId.value
  navigator.clipboard?.writeText(url).then(() => toast.success('链接已复制')).catch(() => toast.info(url))
}
async function onDelete() {
  if (!window.confirm('确定删除这条动态吗？')) return
  try { await api.deletePost(postId.value); toast.success('已删除'); app.bumpFeed(); router.push('/') } catch { /* */ }
}
function goBack() { if (window.history.length > 1) router.back(); else router.push('/') }
function staffLabel(t) { return { admin: '管理员', content_review: '审核员', report_review: '审查员' }[t] || t }

watch(() => route.params.id, () => { loadPost(); window.scrollTo({ top: 0 }) })
onMounted(loadPost)
</script>

<style scoped>
.back { display: inline-flex; align-items: center; gap: 6px; color: var(--ink-3); font-size: 14px; margin-bottom: 14px; padding: 6px 10px; border-radius: var(--r-pill); }
.back:hover { background: var(--surface-3); color: var(--ink); }
.sk-article { padding: 22px; }
.sk-head { display: flex; gap: 12px; align-items: center; }

.article { padding: 24px 26px; margin-bottom: 16px; }
.a-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.a-user { display: flex; align-items: center; gap: 12px; color: inherit; }
.a-user-meta { display: flex; flex-direction: column; gap: 4px; }
.a-name-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.a-name-row strong { font-size: 15.5px; color: var(--ink); }
.staff-tag { font-size: 11px; font-weight: 600; color: var(--brand-700); background: var(--brand-50); border-radius: 6px; padding: 1px 6px; }
.a-sub { font-size: 12.5px; display: flex; gap: 4px; }
.a-title { font-size: 24px; line-height: 1.4; letter-spacing: -0.01em; margin: 20px 0 12px; }
.a-content { font-size: 15.5px; line-height: 1.9; color: var(--ink-2); white-space: pre-wrap; word-break: break-word; }
.a-video { width: 100%; border-radius: var(--r-md); margin-top: 14px; background: #000; max-height: 520px; }
.a-stats { display: flex; gap: 18px; font-size: 13px; margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--line); }
.a-stats span { display: inline-flex; align-items: center; gap: 5px; }
.a-actions { display: flex; align-items: center; gap: 8px; margin-top: 12px; }
.aa { display: inline-flex; align-items: center; gap: 7px; padding: 9px 16px; border-radius: var(--r-pill); color: var(--ink-2); font-size: 14px; transition: background var(--t-fast), color var(--t-fast), transform var(--t-fast); }
.aa:hover { background: var(--surface-3); color: var(--ink); }
.aa:active { transform: scale(.96); }
.aa.on { color: var(--danger-strong); }
.aa.icon-only { padding: 9px; }
.aa.danger:hover { color: var(--danger-strong); }

.comments { padding: 20px 22px; }
.cm-title { font-size: 16px; margin-bottom: 16px; }
.cm-composer { display: flex; gap: 12px; margin-bottom: 8px; }
.cm-send { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }
.cm-login { display: flex; align-items: center; justify-content: space-between; padding: 14px; background: var(--surface-2); border-radius: var(--r-md); margin-bottom: 10px; }
.cm-list { border-top: 1px solid var(--line); }
.sk-comment { display: flex; gap: 12px; padding: 16px 0; }
.load-more { margin-top: 12px; }
</style>
