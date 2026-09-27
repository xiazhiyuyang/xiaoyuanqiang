<template>
  <div class="notifications">
    <header class="n-head card">
      <h2>通知</h2>
      <button class="btn btn-ghost btn-sm" :disabled="!hasUnread" @click="readAll">
        <Icon name="check-double" :size="15" /> 全部已读
      </button>
    </header>

    <div v-if="loading" class="card" style="padding:8px 18px">
      <div v-for="i in 6" :key="i" class="sk-n">
        <div class="skeleton" style="width:42px;height:42px;border-radius:50%"></div>
        <div class="grow"><div class="skeleton" style="width:60%;height:13px;margin-bottom:8px"></div><div class="skeleton" style="width:120px;height:11px"></div></div>
      </div>
    </div>

    <template v-else>
      <div class="n-list card">
        <div
          v-for="n in items" :key="n.id"
          class="n-item" :class="{ unread: !n.is_read }"
        >
          <button class="n-main" @click="openDetail(n)">
            <span class="n-icon" :style="{ background: meta(n.type).bg, color: meta(n.type).color }">
              <Icon :name="meta(n.type).icon" :size="18" />
            </span>
            <span class="grow">
              <span class="n-title">{{ n.title }}</span>
              <span class="n-content faint ellipsis">{{ n.content }}</span>
            </span>
            <span class="n-time faint">{{ timeAgo(n.created_at) }}</span>
            <span v-if="!n.is_read" class="n-dot" />
          </button>
          <button v-if="canAppeal(n)" class="appeal-btn" @click.stop="openAppeal(n)">申诉</button>
        </div>
        <EmptyState v-if="!items.length" icon="bell" title="暂无通知" description="互动和系统消息会出现在这里" />
      </div>
      <button v-if="page < pages" class="btn btn-ghost btn-block" style="margin-top:12px" @click="load(false)">加载更多</button>
    </template>

    <!-- 通知详情弹窗 -->
    <Transition name="fade">
      <div v-if="detailOpen" class="modal-mask" @click.self="detailOpen = false">
        <div class="modal-card">
          <div class="modal-head">
            <span class="modal-icon" :style="{ background: meta(detail?.type).bg, color: meta(detail?.type).color }">
              <Icon :name="meta(detail?.type).icon" :size="20" />
            </span>
            <div class="grow">
              <h3>{{ detail?.title }}</h3>
              <span class="modal-time faint">{{ timeAgo(detail?.created_at) }}</span>
            </div>
            <button class="icon-only close-btn" @click="detailOpen = false"><Icon name="x" :size="18" /></button>
          </div>
          <div class="modal-body">
            <p class="detail-content">{{ detail?.content }}</p>
            <div v-if="detail?.extra" class="detail-extra">
              <div v-for="(v, k) in detail.extra" :key="k" class="extra-row">
                <span class="extra-key">{{ k }}</span>
                <span class="extra-val">{{ v }}</span>
              </div>
            </div>
          </div>
          <div class="modal-foot">
            <button v-if="canAppeal(detail)" class="btn btn-ghost" @click="openAppeal(detail); detailOpen = false">申诉</button>
            <button v-if="hasTarget(detail)" class="btn btn-primary" @click="goTarget(detail)">查看详情</button>
            <button v-else class="btn btn-ghost" @click="detailOpen = false">关闭</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 申诉弹窗 -->
    <Transition name="fade">
      <div v-if="appealOpen" class="modal-mask" @click.self="appealOpen = false">
        <div class="modal-card appeal-card">
          <div class="modal-head">
            <h3>内容申诉</h3>
            <button class="icon-only close-btn" @click="appealOpen = false"><Icon name="x" :size="18" /></button>
          </div>
          <div class="modal-body">
            <p class="appeal-hint">请说明你认为内容合规的理由，审核团队将重新评估。</p>
            <textarea v-model="appealReason" class="appeal-textarea" placeholder="至少5个字，描述申诉理由…" rows="4" :disabled="appealing" />
            <p v-if="appealError" class="appeal-error">{{ appealError }}</p>
          </div>
          <div class="modal-foot">
            <button class="btn btn-ghost" @click="appealOpen = false" :disabled="appealing">取消</button>
            <button class="btn btn-primary" @click="submitAppeal" :disabled="appealing || appealReason.trim().length < 5">
              {{ appealing ? '提交中…' : '提交申诉' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import EmptyState from '../components/EmptyState.vue'
import api from '../api'
import { useApp } from '../stores/app'
import { timeAgo } from '../utils/format'

const router = useRouter()
const app = useApp()
const items = ref([])
const loading = ref(true)
const page = ref(1)
const pages = ref(1)
const hasUnread = computed(() => items.value.some((n) => !n.is_read))

// 详情弹窗
const detailOpen = ref(false)
const detail = ref(null)

// 申诉弹窗
const appealOpen = ref(false)
const appealTarget = ref(null)
const appealReason = ref('')
const appealing = ref(false)
const appealError = ref('')

const METAS = {
  like: { icon: 'heart', color: '#cf5046', bg: '#fdeceb' },
  comment: { icon: 'comment', color: '#14806f', bg: '#ecf8f5' },
  follow: { icon: 'user-plus', color: '#3f7fd4', bg: '#eaf1fc' },
  system: { icon: 'bell', color: '#bd7b1f', bg: '#faf2e2' },
}
function meta(t) { return METAS[t] || METAS.system }

function canAppeal(n) {
  if (!n?.target_id) return false
  const t = (n.title || '') + (n.content || '')
  return /未通过|打码|驳回|拦截|屏蔽|审核/.test(t)
}

function hasTarget(n) {
  return n?.target_id && (n.type === 'follow' || n.type === 'like' || n.type === 'comment' || n.type === 'system')
}

async function load(reset = false) {
  if (reset) { page.value = 1; items.value = [] }
  loading.value = true
  try {
    const r = await api.getNotifications({ page: page.value, page_size: 20 })
    items.value = reset ? r.items : items.value.concat(r.items)
    pages.value = r.total_pages || 1
  } catch { /* */ } finally { loading.value = false }
}

async function markRead(n) {
  if (!n.is_read) {
    n.is_read = true
    await api.readNotification(n.id).catch(() => {})
    app.refreshUnread()
  }
}

async function openDetail(n) {
  await markRead(n)
  detail.value = n
  detailOpen.value = true
}

function goTarget(n) {
  detailOpen.value = false
  if (n.type === 'follow') router.push(`/u/${n.target_id}`)
  else if (n.target_id) router.push(`/post/${n.target_id}`)
}

function openAppeal(n) {
  appealTarget.value = n
  appealReason.value = ''
  appealError.value = ''
  appealOpen.value = true
}

async function submitAppeal() {
  if (appealReason.value.trim().length < 5) return
  appealing.value = true
  appealError.value = ''
  try {
    await api.submitAppeal({
      target_type: 'post',
      target_id: appealTarget.value.target_id,
      reason: appealReason.value.trim(),
    })
    appealOpen.value = false
  } catch (e) {
    appealError.value = e?.msg || '提交失败，请重试'
  } finally {
    appealing.value = false
  }
}

async function readAll() {
  items.value.forEach((n) => (n.is_read = true))
  await api.readAllNotifications().catch(() => {})
  app.refreshUnread()
}

onMounted(() => load(true))
</script>

<style scoped>
.n-head { display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; margin-bottom: 14px; }
.n-head h2 { font-size: 17px; }
.n-list { padding: 6px 8px; }
.n-item { display: flex; align-items: center; gap: 8px; border-radius: var(--r-md); position: relative; }
.n-item:hover { background: var(--surface-2); }
.n-item.unread { background: var(--brand-50); }
.n-item.unread:hover { background: var(--brand-50); }
.n-main { display: flex; align-items: center; gap: 13px; flex: 1; text-align: left; padding: 13px 12px; border: none; background: none; cursor: pointer; min-width: 0; }
.n-icon { width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex: none; }
.n-title { font-size: 14.5px; font-weight: 600; color: var(--ink); display: block; margin-bottom: 2px; }
.n-content { font-size: 13px; display: block; }
.n-time { font-size: 12px; flex: none; align-self: flex-start; }
.n-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--danger); flex: none; }
.appeal-btn {
  flex: none; padding: 5px 14px; font-size: 12px; border-radius: 8px;
  border: 1px solid var(--brand); color: var(--brand); background: transparent;
  cursor: pointer; margin-right: 10px; transition: all .2s;
}
.appeal-btn:hover { background: var(--brand); color: #fff; }
.sk-n { display: flex; gap: 12px; align-items: center; padding: 13px 0; }

/* 弹窗 */
.modal-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 1000;
  display: flex; align-items: center; justify-content: center; padding: 20px;
}
.modal-card {
  background: var(--surface); border-radius: 16px; width: 100%; max-width: 480px;
  box-shadow: 0 20px 60px rgba(0,0,0,.2); overflow: hidden;
}
.modal-head {
  display: flex; align-items: center; gap: 12px; padding: 18px 20px 14px;
  border-bottom: 1px solid var(--line);
}
.modal-head h3 { font-size: 16px; font-weight: 700; margin: 0; }
.modal-icon { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex: none; }
.modal-time { font-size: 12px; }
.close-btn { flex: none; color: var(--ink-3); }
.close-btn:hover { color: var(--ink); }
.modal-body { padding: 20px; }
.detail-content { font-size: 14px; line-height: 1.7; color: var(--ink-2); margin: 0; white-space: pre-wrap; word-break: break-word; }
.detail-extra { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--line); }
.extra-row { display: flex; gap: 12px; font-size: 13px; margin-bottom: 6px; }
.extra-key { color: var(--ink-3); flex: none; min-width: 60px; }
.extra-val { color: var(--ink-2); flex: 1; }
.modal-foot { display: flex; gap: 10px; justify-content: flex-end; padding: 14px 20px; border-top: 1px solid var(--line); }

/* 申诉 */
.appeal-card { max-width: 440px; }
.appeal-hint { font-size: 13px; color: var(--ink-3); margin: 0 0 12px; line-height: 1.6; }
.appeal-textarea {
  width: 100%; padding: 12px 14px; border: 1px solid var(--line); border-radius: 10px;
  font-size: 14px; font-family: inherit; resize: vertical; background: var(--bg);
  color: var(--ink); box-sizing: border-box;
}
.appeal-textarea:focus { outline: none; border-color: var(--brand); }
.appeal-textarea:disabled { opacity: .5; }
.appeal-error { color: var(--danger); font-size: 12px; margin: 8px 0 0; }

.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
