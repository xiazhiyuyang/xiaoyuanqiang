<template>
  <div class="review">
    <header class="rv-head">
      <h1>审查中心</h1>
      <div class="rv-counts">
        <span v-if="auth.canContentReview" class="rv-count"><strong class="tabular">{{ overview.pending_posts ?? '—' }}</strong> 待审帖子</span>
        <span v-if="auth.canReportReview" class="rv-count"><strong class="tabular">{{ overview.pending_reports ?? '—' }}</strong> 待处理举报</span>
      </div>
    </header>

    <div class="rv-tabs">
      <button v-if="auth.canContentReview" :class="{ on: tab === 'posts' }" @click="tab = 'posts'">内容审查</button>
      <button v-if="auth.canReportReview" :class="{ on: tab === 'reports' }" @click="tab = 'reports'">举报处理</button>
    </div>

    <!-- 内容审查 -->
    <template v-if="tab === 'posts'">
      <div class="rv-filters">
        <button v-for="s in postStatuses" :key="s.v" :class="{ on: postStatus === s.v }" @click="setPostStatus(s.v)">{{ s.label }}</button>
      </div>
      <template v-if="loading">
        <div v-for="i in 3" :key="i" class="card" style="padding:18px;margin-bottom:12px">
          <div class="skeleton" style="width:40%;height:15px;margin-bottom:10px"></div>
          <div class="skeleton" style="width:90%;height:12px;margin-bottom:7px"></div>
          <div class="skeleton" style="width:70%;height:12px"></div>
        </div>
      </template>
      <template v-else>
        <div v-for="p in posts" :key="p.id" class="rv-post card">
          <div class="rv-post-head">
            <span class="rv-author">{{ p.is_anonymous ? '匿名用户' : p.author_name }}</span>
            <span v-if="p.category_name" class="faint">· {{ p.category_name }}</span>
            <span class="faint">· {{ timeAgo(p.created_at) }}</span>
            <span class="status-tag" :class="p.status">{{ statusLabel(p.status) }}</span>
          </div>
          <h3 v-if="p.title">{{ p.title }}</h3>
          <p class="rv-content clamp-2">{{ p.content }}</p>
          <ImageGrid v-if="p.images && p.images.length" :images="p.images" />
          <div class="rv-actions">
            <RouterLink :to="`/post/${p.id}`" class="btn btn-ghost btn-sm">查看</RouterLink>
            <template v-if="p.status === 'pending'">
              <button class="btn btn-soft btn-sm" :disabled="acting === p.id" @click="act(p, 'approve')">通过</button>
              <button class="btn btn-danger-ghost btn-sm" :disabled="acting === p.id" @click="act(p, 'remove')">驳回删除</button>
            </template>
          </div>
        </div>
        <EmptyState v-if="!posts.length" icon="shield" title="当前没有需要审查的内容" />
        <button v-if="postPage < postPages" class="btn btn-ghost btn-block" style="margin-top:10px" @click="loadPosts(false)">加载更多</button>
      </template>
    </template>

    <!-- 举报处理 -->
    <template v-else>
      <div class="rv-filters">
        <button v-for="s in reportStatuses" :key="s.v" :class="{ on: reportStatus === s.v }" @click="setReportStatus(s.v)">{{ s.label }}</button>
      </div>
      <template v-if="loading">
        <div v-for="i in 3" :key="i" class="card" style="padding:18px;margin-bottom:12px">
          <div class="skeleton" style="width:50%;height:14px;margin-bottom:10px"></div>
          <div class="skeleton" style="width:80%;height:12px"></div>
        </div>
      </template>
      <template v-else>
        <div v-for="r in reports" :key="r.id" class="rv-report card">
          <div class="rv-report-head">
            <span class="report-reason">{{ r.reason_text }}</span>
            <span class="faint">· {{ targetLabel(r.target_type) }} #{{ r.target_id }}</span>
            <span class="status-tag" :class="r.status">{{ reportStatusLabel(r.status) }}</span>
          </div>
          <p class="rv-meta faint">举报人：{{ r.reporter_name || '未知' }}<span v-if="r.target_user_name"> · 被举报人：{{ r.target_user_name }}</span> · {{ timeAgo(r.created_at) }}</p>
          <p v-if="r.detail" class="rv-detail">补充说明：{{ r.detail }}</p>
          <div v-if="r.snapshot" class="rv-snapshot clamp-2">{{ r.snapshot }}</div>
          <p v-if="r.handle_remark" class="faint rv-remark">处理备注：{{ r.handle_remark }}</p>
          <div v-if="r.status === 'pending'" class="rv-actions">
            <RouterLink :to="targetLink(r)" class="btn btn-ghost btn-sm">查看内容</RouterLink>
            <button class="btn btn-soft btn-sm" :disabled="acting === r.id" @click="handle(r, 'rejected')">驳回举报</button>
            <button class="btn btn-danger-ghost btn-sm" :disabled="acting === r.id" @click="handle(r, 'approved')">成立并处理</button>
          </div>
        </div>
        <EmptyState v-if="!reports.length" icon="flag" title="当前没有需要处理的举报" />
        <button v-if="reportPage < reportPages" class="btn btn-ghost btn-block" style="margin-top:10px" @click="loadReports(false)">加载更多</button>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import EmptyState from '../components/EmptyState.vue'
import api from '../api'
import { useAuth } from '../stores/auth'
import { timeAgo } from '../utils/format'
import { toast } from '../utils/toast'

const auth = useAuth()
const tab = ref(auth.canContentReview ? 'posts' : 'reports')
const overview = reactive({ pending_posts: 0, pending_reports: 0 })

const postStatuses = [{ v: 'pending', label: '待审核' }, { v: 'published', label: '已发布' }, { v: 'deleted', label: '已删除' }]
const reportStatuses = [{ v: 'pending', label: '待处理' }, { v: 'approved', label: '已成立' }, { v: 'rejected', label: '已驳回' }]
const postStatus = ref('pending')
const reportStatus = ref('pending')
const posts = ref([]); const reports = ref([])
const postPage = ref(1); const postPages = ref(1)
const reportPage = ref(1); const reportPages = ref(1)
const loading = ref(false)
const acting = ref(null)

function statusLabel(s) { return { pending: '待审核', published: '已发布', deleted: '已删除' }[s] || s }
function reportStatusLabel(s) { return { pending: '待处理', approved: '已成立', rejected: '已驳回' }[s] || s }
function targetLabel(t) { return { post: '帖子', comment: '评论', user: '用户', message: '私信' }[t] || t }
function targetLink(r) { return r.target_type === 'post' ? `/post/${r.target_id}` : r.target_type === 'user' ? `/u/${r.target_id}` : '/' }

async function loadOverview() { try { Object.assign(overview, await api.getReviewOverview()) } catch { /* */ } }
async function loadPosts(reset = false) {
  if (reset) { postPage.value = 1; posts.value = [] }
  loading.value = true
  try {
    const r = await api.getReviewPosts({ page: postPage.value, page_size: 15, status: postStatus.value })
    posts.value = reset ? r.items : posts.value.concat(r.items); postPages.value = r.total_pages || 1
  } catch { /* */ } finally { loading.value = false }
}
async function loadReports(reset = false) {
  if (reset) { reportPage.value = 1; reports.value = [] }
  loading.value = true
  try {
    const r = await api.getReviewReports({ page: reportPage.value, page_size: 15, status: reportStatus.value })
    reports.value = reset ? r.items : reports.value.concat(r.items); reportPages.value = r.total_pages || 1
  } catch { /* */ } finally { loading.value = false }
}
function setPostStatus(s) { postStatus.value = s; loadPosts(true) }
function setReportStatus(s) { reportStatus.value = s; loadReports(true) }

async function act(p, action) {
  let reason = ''
  if (action === 'remove') {
    reason = window.prompt('驳回原因（选填，将通知作者）') || ''
  }
  acting.value = p.id
  try {
    await api.reviewPostAction(p.id, { action, reason })
    toast.success(action === 'approve' ? '已通过' : '已驳回删除')
    posts.value = posts.value.filter((x) => x.id !== p.id)
    loadOverview()
  } catch { /* */ } finally { acting.value = null }
}
async function handle(r, status) {
  let remark = window.prompt(status === 'approved' ? '处理备注（选填）' : '驳回理由（选填）') || ''
  const ban_user = status === 'approved' && r.target_type === 'user'
    ? window.confirm('是否同时封禁被举报用户？确定=封禁，取消=不封禁')
    : false
  acting.value = r.id
  try {
    const res = await api.handleReport(r.id, { status, ban_user, remark })
    toast.success(res?.actions?.length ? res.actions.join('、') : '处理完成')
    reports.value = reports.value.filter((x) => x.id !== r.id)
    loadOverview()
  } catch { /* */ } finally { acting.value = null }
}

onMounted(async () => {
  loadOverview()
  if (auth.canContentReview) loadPosts(true); else loadReports(true)
})
</script>

<style scoped>
.rv-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 16px; }
.rv-head h1 { font-size: 22px; }
.rv-counts { display: flex; gap: 18px; font-size: 13px; color: var(--ink-3); }
.rv-count strong { font-size: 18px; color: var(--danger-strong); margin-right: 4px; }
.rv-tabs, .rv-filters { display: flex; gap: 6px; margin-bottom: 14px; }
.rv-tabs button, .rv-filters button { padding: 7px 16px; border-radius: 999px; font-size: 13.5px; font-weight: 520; color: var(--ink-3); background: var(--surface); border: 1px solid var(--line); }
.rv-tabs button.on, .rv-filters button.on { background: var(--ink); color: var(--surface); border-color: var(--ink); }
.rv-post, .rv-report { padding: 16px 18px; margin-bottom: 12px; }
.rv-post-head, .rv-report-head { display: flex; align-items: center; gap: 6px; font-size: 12.5px; margin-bottom: 8px; flex-wrap: wrap; }
.rv-author, .report-reason { font-weight: 650; color: var(--ink); font-size: 13.5px; }
.report-reason { color: var(--danger-strong); }
.rv-post h3 { font-size: 15.5px; margin-bottom: 6px; }
.rv-content { font-size: 14px; color: var(--ink-2); line-height: 1.7; white-space: pre-wrap; }
.rv-meta { font-size: 12.5px; margin-bottom: 6px; }
.rv-detail { font-size: 13.5px; color: var(--ink-2); margin-bottom: 6px; }
.rv-snapshot { font-size: 13px; color: var(--ink-3); background: var(--surface-2); border-radius: var(--r-sm); padding: 9px 12px; margin-bottom: 8px; border-left: 3px solid var(--line-strong); }
.rv-remark { font-size: 12.5px; }
.rv-actions { display: flex; gap: 8px; margin-top: 12px; justify-content: flex-end; }
.status-tag { margin-left: auto; font-size: 11.5px; font-weight: 600; padding: 2px 9px; border-radius: 999px; }
.status-tag.pending { background: var(--warning-bg); color: var(--warning); }
.status-tag.published, .status-tag.approved { background: var(--success-bg); color: var(--success); }
.status-tag.deleted, .status-tag.rejected { background: var(--surface-3); color: var(--ink-4); }
</style>
