<template>
  <view class="page" :class="cwRootClass">
    <view v-if="list.length" class="top-bar">
      <text class="read-all" @click="readAll">全部标为已读</text>
    </view>
    <view class="notice-list stagger">
      <view
        v-for="item in list" :key="item.id" class="notice-item"
        :class="{ unread: !item.is_read }"
        @click="openItem(item)"
      >
        <view class="notice-icon" :class="kind(item)">{{ iconText(item) }}</view>
        <view class="notice-body">
          <view class="notice-title">{{ item.title }}</view>
          <view class="notice-content">{{ item.content }}</view>
          <view class="notice-time">{{ formatTime(item.created_at) }}</view>
        </view>
        <view v-if="!item.is_read" class="dot"></view>
      </view>
    </view>
    <view v-if="!loading && list.length === 0" class="empty">
      <text class="empty-emoji">🔔</text>
      <text class="empty-text">暂无消息</text>
    </view>
  </view>
</template>
<script setup>
import { ref } from 'vue'
import { onShow, onReachBottom } from '@dcloudio/uni-app'
import { api } from '../../utils/api'
const list = ref([])
const loading = ref(false)
const page = ref(1)
const noMore = ref(false)
const kind = (item) => {
  if (item.type === 'like') return 'like'
  if (item.type === 'comment') return 'comment'
  if (item.type === 'follow') return 'follow'
  const t = item.title || ''
  if (t.includes('通过')) return 'pass'
  if (t.includes('未通过') || t.includes('驳回')) return 'reject'
  if (t.includes('审核') || t.includes('抽中')) return 'review'
  return 'system'
}
const iconText = (item) => ({
  like: '♥', comment: '💬', system: '✉', review: '🛡', pass: '✓', reject: '✕', follow: '＋',
}[kind(item)] || '•')
const formatTime = (t) => {
  const d = new Date(t)
  const now = new Date()
  const diff = (now - d) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前'
  if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前'
  return `${d.getMonth() + 1}-${d.getDate()}`
}
const load = async (reset = false) => {
  if (loading.value) return
  if (reset) { page.value = 1; noMore.value = false; list.value = [] }
  if (noMore.value) return
  loading.value = true
  try {
    const data = await api.getNotifications({ page: page.value, page_size: 20 })
    list.value.push(...data.items)
    if (data.items.length < 20) noMore.value = true
    else page.value++
  } finally {
    loading.value = false
  }
}
const readAll = async () => {
  await api.readAllNotifications()
  list.value.forEach(i => { i.is_read = true })
  uni.showToast({ title: '已全部已读', icon: 'none' })
}
const openItem = (item) => {
  const wasUnread = !item.is_read
  item.is_read = true
  if (wasUnread) api.readNotification(item.id).catch(() => {})
  if (item.type === 'message') {
    uni.switchTab({ url: '/pages/message/inbox' })
  } else if (item.type === 'follow' && item.target_id) {
    uni.navigateTo({ url: `/pages/user/profile?id=${item.target_id}` })
  } else if (item.target_id && !(item.title || '').includes('未通过')) {
    // 被驳回的帖子已下架，不再跳详情；通过/抽中类可跳详情查看
    uni.navigateTo({ url: `/pages/post/detail?id=${item.target_id}` })
  }
}
onShow(() => load(true))
onReachBottom(() => load())
</script>
<style scoped>
.page { min-height: 100vh; background: transparent; }
.top-bar { display: flex; justify-content: flex-end; padding: 20rpx 32rpx 0; }
.read-all { font-size: 25rpx; color: var(--brand); }
.notice-list { padding: 16rpx 24rpx; }
.notice-item {
  display: flex; align-items: flex-start; background: var(--surface);
  border-radius: var(--radius); padding: 28rpx; margin-bottom: 16rpx;
  box-shadow: var(--shadow-sm);
}
.notice-item.unread { background: var(--brand-soft); border: 1rpx solid rgba(255,255,255,.08); }
.notice-icon {
  width: 72rpx; height: 72rpx; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 30rpx; margin-right: 20rpx; background: rgba(255,255,255,.08); color: var(--ink-2);
}
.notice-icon.like { background: rgba(251,113,133,.16); color: var(--danger); }
.notice-icon.comment { background: var(--brand-soft); color: var(--brand); }
.notice-icon.system { background: rgba(52,211,153,.16); color: var(--success); }
.notice-icon.follow { background: rgba(110,231,255,.14); color: var(--brand2); }
.notice-icon.review { background: rgba(251,191,36,.16); color: #fbbf24; }
.notice-icon.pass { background: rgba(52,211,153,.2); color: #34d399; }
.notice-icon.reject { background: rgba(251,113,133,.2); color: #fb7185; }
.notice-body { flex: 1; min-width: 0; }
.notice-title { font-size: 28rpx; font-weight: 600; color: var(--ink); }
.notice-content {
  font-size: 25rpx; color: var(--ink-2); margin-top: 8rpx;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.notice-time { font-size: 21rpx; color: var(--ink-3); margin-top: 10rpx; }
.dot { width: 16rpx; height: 16rpx; border-radius: 50%; background: var(--danger); margin-top: 12rpx; }
.empty { text-align: center; padding-top: 200rpx; }
.empty-emoji { font-size: 80rpx; display: block; opacity: 0.6; }
.empty-text { display: block; margin-top: 20rpx; color: var(--ink-3); font-size: 27rpx; }
</style>
