<template>
  <view class="page" :class="cwRootClass">
    <!-- 顶部切换 -->
    <view class="tabs cw-card">
      <view class="tab" :class="{ on: type === 'following' }" @click="switchType('following')">
        关注<text class="tab-n">{{ followingCount }}</text>
      </view>
      <view class="tab" :class="{ on: type === 'followers' }" @click="switchType('followers')">
        粉丝<text class="tab-n">{{ followersCount }}</text>
      </view>
    </view>
    <!-- 列表 -->
    <view v-if="list.length" class="list stagger">
      <view v-for="u in list" :key="u.id" class="row-item cw-card">
        <cw-avatar :src="u.avatar" :user-id="u.id" :size="88" />
        <view class="ri-main" @click="openUser(u.id)">
          <view class="ri-name-row">
            <text class="ri-name cw-ellipsis">{{ u.nickname }}</text>
            <text v-for="t in staffText(u.perm_tags, u.role)" :key="t" class="ri-tag" :class="tagClass(t)">{{ t }}</text>
          </view>
          <text class="ri-bio cw-ellipsis">{{ u.bio || ('Lv' + (u.level || 1) + ' 校园墙用户') }}</text>
        </view>
        <view
          v-if="u.id !== myId"
          class="ri-btn hover-press" :class="{ on: u.is_following }"
          @click="toggle(u)"
        >{{ u.is_following ? '已关注' : '+ 关注' }}</view>
      </view>
    </view>
    <view v-else-if="!loading" class="empty">
      <text class="empty-emoji">🌌</text>
      <text class="empty-text">{{ type === 'following' ? '还没有关注任何人' : '暂时没有粉丝' }}</text>
    </view>
  </view>
</template>
<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { api } from '../../utils/api'
const userId = ref(0)
const myId = ref(0)
const type = ref('following')
const list = ref([])
const loading = ref(false)
const followingCount = ref(0)
const followersCount = ref(0)
const STAFF_LABELS = { admin: '管理员', content_review: '审核员', report_review: '审查员' }
const staffText = (tags, role) => {
  const list = Array.isArray(tags) ? tags : (role === 'admin' ? ['admin'] : [])
  return list.map((t) => STAFF_LABELS[t]).filter(Boolean)
}
const tagClass = (label) => ({ '管理员': 't-admin', '审核员': 't-review', '审查员': 't-audit' }[label] || '')
const openUser = (id) => uni.navigateTo({ url: `/pages/user/profile?id=${id}` })
const switchType = (t) => { if (type.value !== t) { type.value = t; load() } }
const load = async () => {
  loading.value = true
  try {
    const data = userId.value === myId.value
      ? await api.getMyFollows(type.value)
      : await api.getUserFollows(userId.value, type.value)
    list.value = data.items || []
  } catch (e) {} finally { loading.value = false }
}
const loadCounts = async () => {
  if (!userId.value) return
  try {
    const d = await api.getFollowStatus(userId.value)
    followingCount.value = d.following_count || 0
    followersCount.value = d.followers_count || 0
  } catch (e) {}
}
const toggle = async (u) => {
  try {
    const data = await api.toggleFollow(u.id)
    u.is_following = data.following
    if (type.value === 'followers') followersCount.value = data.followers_count
    uni.showToast({ title: data.following ? '已关注' : '已取消关注', icon: 'none' })
  } catch (e) {}
}
onLoad((q) => {
  try { myId.value = JSON.parse(uni.getStorageSync('userInfo') || 'null')?.id || 0 } catch (e) {}
  userId.value = Number(q.id) || myId.value
  type.value = q.type === 'followers' ? 'followers' : 'following'
  uni.setNavigationBarTitle({ title: userId.value === myId.value ? '我的关注与粉丝' : '关注与粉丝' })
  load()
  loadCounts()
})
</script>
<style scoped>
.page { min-height: 100vh; background: var(--bg); padding: 20rpx 24rpx 60rpx; }
.tabs { display: flex; padding: 10rpx; gap: 10rpx; }
.tab {
  flex: 1; text-align: center; padding: 18rpx 0; font-size: 28rpx; font-weight: 700;
  color: var(--ink-3); border-radius: 16rpx;
}
.tab.on { background: var(--brand-soft); color: #c4b5fd; }
.tab-n { font-size: 23rpx; margin-left: 6rpx; font-weight: 600; }
.list { margin-top: 20rpx; }
.row-item { display: flex; align-items: center; gap: 18rpx; padding: 22rpx 26rpx; margin-bottom: 16rpx; }
.ri-main { flex: 1; min-width: 0; }
.ri-name-row { display: flex; align-items: center; gap: 8rpx; }
.ri-name { font-size: 28rpx; font-weight: 700; color: var(--ink); max-width: 300rpx; }
.ri-tag { font-size: 18rpx; padding: 3rpx 12rpx; border-radius: 999rpx; border: 1rpx solid; font-weight: 700; }
.t-admin { color: #fde68a; background: rgba(251,191,36,.16); border-color: rgba(251,191,36,.4); }
.t-review { color: #a5b4fc; background: rgba(139,124,246,.16); border-color: rgba(139,124,246,.4); }
.t-audit { color: #67e8f9; background: rgba(103,232,249,.12); border-color: rgba(103,232,249,.35); }
.ri-bio { display: block; font-size: 23rpx; color: var(--ink-3); margin-top: 8rpx; }
.ri-btn {
  flex-shrink: 0; font-size: 24rpx; font-weight: 700; color: #fff; background: var(--grad);
  padding: 12rpx 28rpx; border-radius: 999rpx;
}
.ri-btn.on { background: rgba(255,255,255,.08); color: var(--ink-3); border: 1rpx solid var(--line); }
.empty { text-align: center; padding: 140rpx 0; }
.empty-emoji { font-size: 88rpx; }
.empty-text { display: block; margin-top: 20rpx; color: var(--ink-3); font-size: 26rpx; }
</style>
