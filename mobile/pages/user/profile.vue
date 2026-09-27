<template>
  <view class="page" :class="cwRootClass">
    <!-- 封面 -->
    <view class="cover">
      <view class="cover-mask"></view>
      <view class="cover-head">
        <view class="back hover-press" @click="back">‹</view>
        <text class="cover-title">个人主页</text>
        <view class="back" style="opacity:0">‹</view>
      </view>
    </view>

    <view v-if="user" class="content">
      <!-- 头像 + 名字 -->
      <view class="id-card cw-card anim-up">
        <view class="id-top">
          <cw-avatar :src="user.avatar" :size="140" ring />
          <view class="id-info">
            <view class="id-name-row">
              <text class="id-name cw-ellipsis">{{ user.nickname }}</text>
              <text v-if="genderIcon" class="id-gender">{{ genderIcon }}</text>
              <text
                v-for="t in staffLabels" :key="t"
                class="id-badge" :class="badgeClass(t)"
              >{{ t }}</text>
            </view>
            <text class="id-bio cw-ellipsis-2">{{ user.bio || '这个人很神秘，什么都没写~' }}</text>
            <text class="id-since">加入于 {{ joinText }}</text>
          </view>
        </view>

        <!-- 资料 chips（后端已按可见范围过滤，缺省即不可见） -->
        <view class="chips">
          <view v-if="user.grade" class="chip">🎓 {{ user.grade }}</view>
          <view v-if="user.college" class="chip">🏫 {{ user.college }}</view>
          <view v-if="user.major" class="chip">📚 {{ user.major }}</view>
          <view v-if="user.location" class="chip">📍 {{ user.location }}</view>
          <view v-if="user.birthday" class="chip">🎂 {{ user.birthday }}</view>
          <view v-if="!hasAnyInfo" class="chip chip-muted">TA 的资料未公开</view>
        </view>

        <!-- 数据 -->
        <view class="stats">
          <view class="stat"><text class="num">{{ user.post_count || 0 }}</text><text class="lab">动态</text></view>
          <view class="stat" @click="openFollows('following')"><text class="num">{{ user.following_count || 0 }}</text><text class="lab">关注</text></view>
          <view class="stat" @click="openFollows('followers')"><text class="num">{{ user.followers_count || 0 }}</text><text class="lab">粉丝</text></view>
          <view class="stat"><text class="num">{{ user.like_count || 0 }}</text><text class="lab">获赞</text></view>
          <view class="stat"><text class="num">{{ user.favorite_count || 0 }}</text><text class="lab">收藏</text></view>
        </view>

        <!-- 操作 -->
        <view class="actions">
          <view v-if="user.is_self" class="btn primary hover-press" @click="edit">编辑资料</view>
          <template v-else>
            <view
              class="btn hover-press" :class="user.is_following ? 'ghost' : 'primary'"
              @click="toggleFollow"
            >{{ user.is_following ? '✓ 已关注' : '+ 关注' }}</view>
            <view class="btn primary hover-press" @click="chat">💬 私信</view>
          </template>
        </view>
      </view>

      <!-- TA 的动态 -->
      <view class="section-title anim-up delay-1">
        <text class="bar"></text>{{ user.is_self ? '我的动态' : 'TA 的动态' }}
      </view>
      <view class="stagger">
        <cw-post-card v-for="p in posts" :key="p.id" :post="p" />
      </view>
      <view v-if="!loading && posts.length===0" class="empty">
        <text class="empty-emoji">🫧</text>
        <text class="empty-text">还没有发布动态</text>
      </view>
      <view v-if="noMore && posts.length>0" class="end">— 已经到底啦 —</view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onLoad, onReachBottom, onUnload } from '@dcloudio/uni-app'
import { api } from '../../utils/api'
const userId = ref(0)
const user = ref(null)
const posts = ref([])
const page = ref(1)
const loading = ref(false)
const noMore = ref(false)

const genderIcon = computed(() => ({ male: '♂️', female: '♀️' }[user.value?.gender] || ''))
const joinText = computed(() => String(user.value?.created_at || '').slice(0, 10) || '—')
const hasAnyInfo = computed(() => {
  const u = user.value || {}
  return !!(u.grade || u.college || u.major || u.location || u.birthday)
})
const STAFF_MAP = { admin: '管理员', content_review: '审核员', report_review: '审查员' }
const staffLabels = computed(() => {
  const u = user.value
  if (!u) return []
  const tags = Array.isArray(u.perm_tags) ? u.perm_tags : (u.role === 'admin' ? ['admin'] : [])
  return tags.map((t) => STAFF_MAP[t]).filter(Boolean)
})
const badgeClass = (label) => ({
  '管理员': 'badge-admin', '审核员': 'badge-review', '审查员': 'badge-audit',
}[label] || '')
const back = () => uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/index/index' }) })
const edit = () => uni.navigateTo({ url: '/pages/profile/edit' })
const openFollows = (type) => uni.navigateTo({ url: `/pages/user/follows?id=${userId.value}&type=${type}` })
const toggleFollow = async () => {
  if (!uni.getStorageSync('token')) { uni.showToast({ title: '请先登录', icon: 'none' }); return }
  try {
    const data = await api.toggleFollow(userId.value)
    user.value.is_following = data.following
    user.value.followers_count = data.followers_count
    user.value.following_count = data.following_count
    uni.showToast({ title: data.following ? '已关注' : '已取消关注', icon: 'none' })
  } catch (e) {}
}

const loadProfile = async () => {
  try { user.value = await api.getUserProfile(userId.value) }
  catch (e) { setTimeout(back, 800) }
}
const loadPosts = async (reset = false) => {
  if (loading.value) return
  if (reset) { page.value = 1; posts.value = []; noMore.value = false }
  if (noMore.value) return
  loading.value = true
  try {
    const data = await api.getUserPosts(userId.value, { page: page.value, page_size: 10 })
    posts.value.push(...data.items)
    if (data.items.length < 10) noMore.value = true
    else page.value++
  } catch (e) {} finally { loading.value = false }
}
const chat = async () => {
  if (!uni.getStorageSync('token')) { uni.showToast({ title: '请先登录', icon: 'none' }); return }
  uni.showLoading({ title: '加载中', mask: true })
  try {
    const conv = await api.createConversation(userId.value)
    uni.navigateTo({ url: `/pages/message/chat?id=${conv.id}&name=${encodeURIComponent(user.value.nickname)}` })
  } catch (e) {} finally { uni.hideLoading() }
}
const onPostDeleted = (id) => { posts.value = posts.value.filter((p) => p.id !== id) }
onLoad((q) => {
  uni.$on('campus:post-deleted', onPostDeleted)
  userId.value = Number(q.id)
  if (!userId.value) { uni.showToast({ title: '用户不存在', icon: 'none' }); return setTimeout(back, 800) }
  loadProfile(); loadPosts(true)
})
onReachBottom(() => loadPosts())
onUnload(() => uni.$off('campus:post-deleted', onPostDeleted))
</script>

<style scoped>
.page { min-height: 100vh; background: var(--bg); padding-bottom: 60rpx; }
.cover { height: 300rpx; background: var(--grad); position: relative; overflow: hidden; }
.cover-mask { position: absolute; inset: 0; background: radial-gradient(circle at 80% 10%, rgba(255,255,255,.25), transparent 60%); }
.cover-head { position: relative; display: flex; align-items: center; justify-content: space-between; height: 88rpx; padding: 0 24rpx; padding-top: var(--status-bar-height, 0px); }
.back { width: 64rpx; height: 64rpx; border-radius: 50%; background: rgba(255,255,255,.25); color: #fff; font-size: 44rpx; display: flex; align-items: center; justify-content: center; line-height: 1; }
.cover-title { color: #fff; font-size: 32rpx; font-weight: 700; }
.content { padding: 0 24rpx; margin-top: -70rpx; position: relative; }
.id-card { padding: 30rpx; }
.id-top { display: flex; align-items: center; }
.id-info { flex: 1; margin-left: 24rpx; min-width: 0; }
.id-name-row { display: flex; align-items: center; flex-wrap: wrap; gap: 10rpx; }
.id-name { font-size: 38rpx; font-weight: 800; color: var(--ink); max-width: 320rpx; }
.id-gender { font-size: 30rpx; margin-left: 10rpx; }
.id-badge { font-size: 19rpx; color: #fff; background: var(--grad); padding: 3rpx 14rpx; border-radius: 999rpx; margin-left: 12rpx; }
.id-badge.badge-admin { color: #fff; background: #d97706; border: 1rpx solid rgba(255,255,255,.35); }
.id-badge.badge-review { color: #fff; background: #6366f1; border: 1rpx solid rgba(255,255,255,.35); }
.id-badge.badge-audit { color: #fff; background: #0891b2; border: 1rpx solid rgba(255,255,255,.35); }
.id-bio { color: var(--ink-2); font-size: 25rpx; line-height: 1.5; margin-top: 10rpx; }
.id-since { color: var(--ink-3); font-size: 21rpx; margin-top: 10rpx; display: block; }
.chips { display: flex; flex-wrap: wrap; gap: 12rpx; margin-top: 22rpx; }
.chip { font-size: 23rpx; color: var(--ink-2); background: rgba(255,255,255,.06); border: 1rpx solid var(--line); padding: 10rpx 22rpx; border-radius: 999rpx; }
.chip-muted { color: var(--ink-3); }
.stats { display: flex; margin-top: 26rpx; padding: 24rpx 0; border-top: 1rpx solid var(--line); border-bottom: 1rpx solid var(--line); }
.stat { flex: 1; display: flex; flex-direction: column; align-items: center; }
.num { font-size: 38rpx; font-weight: 800; color: var(--ink); }
.lab { font-size: 22rpx; color: var(--ink-3); margin-top: 6rpx; }
.actions { display: flex; gap: 20rpx; margin-top: 26rpx; }
.btn { flex: 1; height: 80rpx; border-radius: 999rpx; display: flex; align-items: center; justify-content: center; font-size: 28rpx; font-weight: 700; }
.btn.primary { background: var(--grad); color: #fff; box-shadow: var(--shadow-brand); }
.btn.ghost { background: rgba(255,255,255,.08); color: var(--ink-2); border: 1rpx solid var(--line); }
.section-title { display: flex; align-items: center; font-size: 30rpx; font-weight: 800; color: var(--ink); margin: 30rpx 8rpx 20rpx; }
.bar { width: 8rpx; height: 30rpx; border-radius: 99rpx; background: var(--grad); margin-right: 14rpx; }
.empty { text-align: center; padding: 80rpx 0; }
.empty-emoji { font-size: 80rpx; }
.empty-text { display: block; color: var(--ink-3); margin-top: 20rpx; font-size: 26rpx; }
.end { text-align: center; color: var(--ink-3); font-size: 23rpx; padding: 30rpx; }
</style>
