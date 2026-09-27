<template>
  <view class="page" :class="cwRootClass">
    <view class="header">
      <text class="title">消息</text>
    </view>

    <!-- 互动消息入口 -->
    <view class="entries cw-card anim-up">
      <view class="entry hover-press" @click="openNotifications">
        <view class="entry-ico bell">🔔</view>
        <view class="entry-body">
          <text class="entry-name">互动消息</text>
          <text class="entry-sub">点赞、评论、系统通知</text>
        </view>
        <text v-if="noticeUnread" class="dot">{{ noticeUnread > 99 ? '99+' : noticeUnread }}</text>
        <text class="chevron">›</text>
      </view>
    </view>

    <view class="section">
      <text class="section-name">私信</text>
    </view>

    <!-- 私信会话 -->
    <view v-if="conversations.length" class="conv-list stagger">
      <view v-for="item in conversations" :key="item.id" class="conv-item cw-card hover-press" @click="openChat(item)">
        <cw-avatar :src="item.peer_avatar" :user-id="item.peer_id" :size="92" :badge="0" />
        <view class="conv-body">
          <view class="conv-top">
            <text class="nickname cw-ellipsis">{{ item.peer_nickname }}</text>
            <text class="time">{{ formatTime(item.last_message_at) }}</text>
          </view>
          <view class="conv-bottom">
            <text class="last-msg">{{ item.last_sender_id === myId ? '我：' : '' }}{{ item.last_content || '开始聊天吧' }}</text>
            <text v-if="item.unread_count > 0" class="unread">{{ item.unread_count > 99 ? '99+' : item.unread_count }}</text>
          </view>
        </view>
      </view>
    </view>

    <view v-else-if="!loading" class="empty anim-fade">
      <text class="empty-emoji">✉️</text>
      <text class="empty-text">还没有私信</text>
      <text class="empty-sub">在帖子详情或别人主页可以发起私信</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow, onHide, onUnload, onPullDownRefresh } from '@dcloudio/uni-app'
import { api } from '../../utils/api'
import { realtime } from '../../utils/ws'
const conversations = ref([])
const noticeUnread = ref(0)
const loading = ref(false)
const myId = ref(0)
let pollTimer = null
let offWs = []
// WS 在线时不轮询；断开时 15 秒兜底（改造前是固定 3 秒）
const FALLBACK_POLL = 15000

const formatTime = (t) => {
  const d = new Date(String(t || '').replace(/-/g, '/'))
  const now = new Date()
  const diff = (now - d) / 1000
  if (isNaN(diff)) return ''
  if (diff < 60) return '刚刚'
  if (diff < 3600) return Math.floor(diff / 60) + '分钟前'
  if (diff < 86400) return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  if (diff < 86400 * 7) return Math.floor(diff / 86400) + '天前'
  return String(t).slice(5, 10)
}
const loadData = async () => {
  if (!uni.getStorageSync('token')) { conversations.value = []; return }
  loading.value = true
  try {
    const info = uni.getStorageSync('userInfo')
    myId.value = info ? JSON.parse(info).id : 0
    const [convs, unread] = await Promise.all([
      api.getConversations().catch(() => []),
      api.getUnreadCount().catch(() => ({ count: 0 })),
    ])
    conversations.value = convs || []
    noticeUnread.value = unread?.count || 0
  } catch (e) {} finally { loading.value = false }
}
const openNotifications = () => uni.navigateTo({ url: '/pages/notifications/list' })
const openChat = (item) => {
  item.unread_count = 0
  uni.$emit('badge:refresh')
  uni.navigateTo({ url: `/pages/message/chat?id=${item.id}&peerId=${item.peer_id}&peerName=${encodeURIComponent(item.peer_nickname)}` })
}
const adjustPolling = () => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (!realtime.isConnected()) pollTimer = setInterval(loadData, FALLBACK_POLL)
}
// 服务端推送的未读数直接采用，省掉一次 /unread-count 请求
const onWsUnread = (frame) => {
  if (frame && typeof frame.message === 'number') noticeUnread.value = frame.message
  uni.$emit('badge:refresh')
}
// 新私信到达：刷新会话列表（顺序与最后一条预览都变了）
const onWsMessage = () => { loadData() }
const onWsState = () => adjustPolling()
onShow(() => {
  loadData()
  realtime.connect()
  offWs.forEach((off) => { try { off() } catch (e) {} })
  offWs = [
    realtime.on('message', onWsMessage),
    realtime.on('unread', onWsUnread),
    realtime.on('open', onWsState),
    realtime.on('close', onWsState),
  ]
  // WS 在线时不再轮询；断开时自动启用兜底轮询
  adjustPolling()
})
onHide(() => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  offWs.forEach((off) => { try { off() } catch (e) {} })
  offWs = []
})
onUnload(() => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  offWs.forEach((off) => { try { off() } catch (e) {} })
  offWs = []
})
onPullDownRefresh(async () => { await loadData(); uni.stopPullDownRefresh() })
</script>

<style scoped>
.page { min-height: 100vh; background: var(--bg); padding: 0 24rpx 40rpx; }
.header { padding: 30rpx 8rpx 20rpx; }
.title { font-size: 46rpx; font-weight: 800; color: var(--ink); }
.entries { border-radius: var(--radius-lg); overflow: hidden; }
.entry { display: flex; align-items: center; padding: 28rpx; }
.entry-ico { width: 84rpx; height: 84rpx; border-radius: 26rpx; display: flex; align-items: center; justify-content: center; font-size: 42rpx; margin-right: 22rpx; }
.entry-ico.bell { background: linear-gradient(135deg,#fde68a,#fb923c); }
.entry-body { flex: 1; min-width: 0; }
.entry-name { font-size: 30rpx; font-weight: 700; color: var(--ink); display: block; }
.entry-sub { font-size: 23rpx; color: var(--ink-3); margin-top: 6rpx; display: block; }
.dot { background: var(--accent-deep); color: #fff; font-size: 20rpx; min-width: 34rpx; height: 34rpx; line-height: 34rpx; text-align: center; border-radius: 999rpx; padding: 0 10rpx; margin-right: 12rpx; }
.chevron { color: var(--ink-3); font-size: 40rpx; }
.section { padding: 30rpx 8rpx 16rpx; }
.section-name { font-size: 26rpx; color: var(--ink-3); font-weight: 600; }
.conv-item { display: flex; align-items: center; padding: 24rpx 26rpx; margin-bottom: 16rpx; }
.conv-body { flex: 1; min-width: 0; margin-left: 20rpx; }
.conv-top { display: flex; justify-content: space-between; align-items: center; }
.nickname { font-size: 29rpx; color: var(--ink); font-weight: 600; max-width: 380rpx; }
.time { font-size: 22rpx; color: var(--ink-3); flex-shrink: 0; margin-left: 16rpx; }
.conv-bottom { display: flex; justify-content: space-between; align-items: center; margin-top: 12rpx; }
.last-msg { font-size: 25rpx; color: var(--ink-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; margin-right: 16rpx; }
.unread { background: var(--accent-deep); color: #fff; font-size: 20rpx; min-width: 34rpx; height: 34rpx; line-height: 34rpx; text-align: center; border-radius: 999rpx; padding: 0 10rpx; }
.empty { text-align: center; padding-top: 140rpx; }
.empty-emoji { font-size: 88rpx; }
.empty-text { display: block; margin-top: 24rpx; font-size: 30rpx; color: var(--ink-2); font-weight: 600; }
.empty-sub { display: block; margin-top: 12rpx; font-size: 24rpx; color: var(--ink-3); }
</style>
