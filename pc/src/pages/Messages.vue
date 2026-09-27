<template>
  <div class="messages card-flush">
    <!-- 会话列表 -->
    <aside class="conv-list" :class="{ hidden: current }">
      <header class="ml-head"><h2>私信</h2></header>
      <div v-if="loadingConv" class="p-4">
        <div v-for="i in 6" :key="i" class="sk-conv">
          <div class="skeleton" style="width:46px;height:46px;border-radius:50%"></div>
          <div class="grow"><div class="skeleton" style="width:120px;height:13px;margin-bottom:8px"></div><div class="skeleton" style="width:180px;height:11px"></div></div>
        </div>
      </div>
      <template v-else>
        <button
          v-for="c in conversations" :key="c.id"
          class="conv" :class="{ active: Number(route.params.cid) === c.id }"
          @click="open(c.id)"
        >
          <UserAvatar :src="c.peer_avatar" :name="c.peer_nickname" :size="46" />
          <span class="conv-meta">
            <span class="conv-top">
              <strong class="ellipsis">{{ c.peer_nickname }}</strong>
              <time class="faint">{{ timeAgo(c.last_message_at) }}</time>
            </span>
            <span class="conv-bottom">
              <span class="conv-last ellipsis" :class="{ unread: c.unread_count }">
                {{ c.last_sender_id === auth.user?.id ? '我：' : '' }}{{ c.last_content || '开始聊天吧' }}
              </span>
              <em v-if="c.unread_count" class="unread-badge">{{ c.unread_count > 99 ? '99+' : c.unread_count }}</em>
            </span>
          </span>
        </button>
        <EmptyState v-if="!conversations.length" icon="message" title="还没有私信" description="在同学的主页点击「私信」开始交流" />
      </template>
    </aside>

    <!-- 聊天窗 -->
    <section class="chat" :class="{ hidden: !current }">
      <template v-if="current">
        <header class="chat-head">
          <button class="back-mobile" @click="goList"><Icon name="arrow-left" :size="19" /></button>
          <RouterLink :to="`/u/${current.peer_id}`" class="chat-user">
            <UserAvatar :src="current.peer_avatar" :name="current.peer_nickname" :size="38" />
            <strong>{{ current.peer_nickname }}</strong>
          </RouterLink>
        </header>

        <div ref="scroller" class="chat-scroll" @scroll="onScroll">
          <button v-if="msgPage < msgPages" class="btn btn-ghost btn-sm btn-block" @click="loadOlder">加载更早消息</button>
          <div v-if="loadingMsg" class="chat-loading faint">加载中…</div>
          <div v-for="(m, i) in msgs" :key="m.id" class="msg-row" :class="{ mine: m.sender_id === auth.user?.id }">
            <div class="bubble">
              <p>{{ m.content }}</p>
              <span class="bubble-time">{{ formatTime(m.created_at) }}</span>
            </div>
          </div>
          <EmptyState v-if="!msgs.length && !loadingMsg" icon="message" title="还没有消息" description="发送第一条消息打个招呼吧" />
        </div>

        <div class="chat-input">
          <textarea
            v-model="draft" rows="1" placeholder="输入消息，Enter 发送，Shift+Enter 换行"
            @keydown.enter.exact.prevent="send"
          />
          <button class="btn btn-primary" :disabled="!draft.trim() || sending" @click="send">
            <Icon name="send" :size="17" />
          </button>
        </div>
      </template>
      <div v-else class="chat-empty">
        <EmptyState icon="message" title="选择一个会话" description="从左侧选择私信，或前往同学主页发起对话" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import UserAvatar from '../components/UserAvatar.vue'
import EmptyState from '../components/EmptyState.vue'
import Icon from '../components/Icon.vue'
import api from '../api'
import { useAuth } from '../stores/auth'
import { useApp } from '../stores/app'
import { timeAgo } from '../utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const app = useApp()

const conversations = ref([])
const loadingConv = ref(true)
const current = ref(null)
const msgs = ref([])
const loadingMsg = ref(false)
const msgPage = ref(1)
const msgPages = ref(1)
const draft = ref('')
const sending = ref(false)
const scroller = ref(null)
let poll = null

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function loadConversations(silent = false) {
  if (!silent) loadingConv.value = true
  try { conversations.value = await api.getConversations() } catch { /* */ } finally { loadingConv.value = false }
}
async function open(cid) {
  router.replace(`/messages/${cid}`)
}
async function enterConversation(cid) {
  current.value = conversations.value.find((c) => c.id === Number(cid)) || null
  msgs.value = []; msgPage.value = 1; msgPages.value = 1
  if (!current.value) {
    // 直接通过路由进入（如新建会话），先拉会话列表补齐
    await loadConversations(true)
    current.value = conversations.value.find((c) => c.id === Number(cid)) || null
    if (!current.value) return
  }
  await loadMessages(true)
  api.markConversationRead(cid).catch(() => {})
  current.value.unread_count = 0
  app.refreshUnread()
}
async function loadMessages(reset = false) {
  if (!current.value) return
  loadingMsg.value = true
  try {
    const cid = route.params.cid
    const r = await api.getMessages(cid, { page: msgPage.value, page_size: 30 })
    const incoming = r.items.slice().reverse()
    if (reset) { msgs.value = incoming; await nextTick(); scrollBottom() }
    else {
      const el = scroller.value; const prevH = el?.scrollHeight || 0
      msgs.value = incoming.concat(msgs.value)
      msgPages.value = r.total_pages || 1
      await nextTick()
      if (el) el.scrollTop += el.scrollHeight - prevH
    }
    msgPages.value = r.total_pages || 1
  } catch { /* */ } finally { loadingMsg.value = false }
}
async function loadOlder() { msgPage.value += 1; await loadMessages(false) }
function onScroll() {
  // 预留：触顶加载已用按钮，保持简单
}
function scrollBottom() { const el = scroller.value; if (el) el.scrollTop = el.scrollHeight }
async function send() {
  const text = draft.value.trim()
  if (!text || !current.value || sending.value) return
  sending.value = true
  try {
    const m = await api.sendMessage(route.params.cid, { content: text })
    msgs.value.push(m)
    draft.value = ''
    await nextTick(); scrollBottom()
    loadConversations(true)
  } catch { /* */ } finally { sending.value = false }
}
function goList() { router.push('/messages') }

async function pollTick() {
  await loadConversations(true)
  if (route.params.cid) {
    const before = msgs.value.length
    const r = await api.getMessages(route.params.cid, { page: 1, page_size: 30 })
    const incoming = r.items.slice().reverse()
    if (incoming.length !== msgs.value.length || (incoming.length && incoming[incoming.length - 1].id !== msgs.value[msgs.value.length - 1]?.id)) {
      const wasBottom = scroller.value && (scroller.value.scrollHeight - scroller.value.scrollTop - scroller.value.clientHeight < 80)
      msgs.value = incoming; msgPages.value = r.total_pages || 1
      if (wasBottom) await nextTick().then(scrollBottom)
      api.markConversationRead(route.params.cid).catch(() => {})
      const c = conversations.value.find((x) => x.id === Number(route.params.cid)); if (c) c.unread_count = 0
      app.refreshUnread()
    }
  }
}

watch(() => route.params.cid, (cid) => {
  if (cid) enterConversation(cid)
  else { current.value = null; msgs.value = [] }
}, { immediate: false })

onMounted(async () => {
  await loadConversations()
  if (route.params.cid) await enterConversation(route.params.cid)
  poll = setInterval(pollTick, 8000)
})
onBeforeUnmount(() => clearInterval(poll))
</script>

<style scoped>
.messages {
  display: grid; grid-template-columns: 320px 1fr; height: calc(100dvh - var(--nav-h) - 48px);
  min-height: 520px; background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--r-lg); box-shadow: var(--shadow-sm); overflow: hidden;
}
.conv-list { border-right: 1px solid var(--line); display: flex; flex-direction: column; overflow-y: auto; }
.ml-head { padding: 18px 18px 10px; }
.conv { display: flex; gap: 12px; padding: 12px 16px; text-align: left; width: 100%; transition: background var(--t-fast); }
.conv:hover { background: var(--surface-2); }
.conv.active { background: var(--brand-50); }
.conv-meta { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 4px; }
.conv-top { display: flex; justify-content: space-between; gap: 8px; }
.conv-top strong { font-size: 14.5px; color: var(--ink); font-weight: 620; }
.conv-top time { font-size: 11.5px; flex: none; }
.conv-bottom { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.conv-last { font-size: 13px; color: var(--ink-4); }
.conv-last.unread { color: var(--ink); font-weight: 560; }
.unread-badge { background: var(--danger); color: #fff; font-size: 11px; font-weight: 700; min-width: 18px; height: 18px; border-radius: 999px; padding: 0 5px; display: flex; align-items: center; justify-content: center; flex: none; font-style: normal; }
.sk-conv { display: flex; gap: 12px; align-items: center; padding: 11px 0; }

.chat { display: flex; flex-direction: column; min-width: 0; }
.chat-head { display: flex; align-items: center; gap: 10px; padding: 12px 18px; border-bottom: 1px solid var(--line); }
.back-mobile { display: none; color: var(--ink-3); }
.chat-user { display: flex; align-items: center; gap: 10px; color: var(--ink); }
.chat-user strong { font-size: 15px; }
.chat-scroll { flex: 1; overflow-y: auto; padding: 18px; display: flex; flex-direction: column; gap: 12px; background: var(--surface-2); }
.chat-loading { text-align: center; font-size: 13px; padding: 8px; }
.msg-row { display: flex; }
.msg-row.mine { justify-content: flex-end; }
.bubble { max-width: min(70%, 460px); background: var(--surface); border: 1px solid var(--line); border-radius: 4px 16px 16px 16px; padding: 9px 14px; box-shadow: var(--shadow-xs); }
.msg-row.mine .bubble { background: var(--brand-btn-bg); border-color: var(--brand-btn-bg); color: var(--brand-btn-fg); border-radius: 16px 4px 16px 16px; }
.bubble p { font-size: 14.5px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
.bubble-time { display: block; font-size: 10.5px; opacity: .65; margin-top: 3px; text-align: right; }
.chat-input { display: flex; gap: 10px; padding: 14px 16px; border-top: 1px solid var(--line); align-items: flex-end; }
.chat-input textarea { flex: 1; resize: none; max-height: 140px; border-radius: var(--r-md); }
.chat-empty { flex: 1; display: flex; align-items: center; justify-content: center; }

@media (max-width: 768px) {
  .messages { grid-template-columns: 1fr; height: calc(100dvh - var(--nav-h) - 24px); min-height: 420px; }
  .conv-list.hidden { display: none; }
  .chat.hidden { display: none; }
  .back-mobile { display: flex; }
}
</style>
