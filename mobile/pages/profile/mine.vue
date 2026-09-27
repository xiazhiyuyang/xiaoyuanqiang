<template>
  <view class="page" :class="cwRootClass">
    <!-- 顶部双 Tab -->
    <view class="tabs card">
      <view class="tab" :class="{ on: tab === 'posts' }" @click="switchTab('posts')">
        我的发布<text class="tab-n">{{ counts.posts }}</text>
      </view>
      <view class="tab" :class="{ on: tab === 'favs' }" @click="switchTab('favs')">
        我的收藏<text class="tab-n">{{ counts.favs }}</text>
      </view>
    </view>
    <!-- 我的发布：状态筛选 -->
    <scroll-view v-if="tab === 'posts'" class="sub-filter" scroll-x :show-scrollbar="false">
      <view class="chip" :class="{ on: postStatus === 'all' }" @click="switchStatus('all')">全部</view>
      <view class="chip" :class="{ on: postStatus === 'published' }" @click="switchStatus('published')">已发布</view>
      <view class="chip" :class="{ on: postStatus === 'pending' }" @click="switchStatus('pending')">审核中</view>
    </scroll-view>
    <!-- 列表 -->
    <view class="post-list stagger">
      <view v-for="post in list" :key="post.id">
        <view v-if="tab === 'posts' && post.status === 'pending'" class="pending-row">
          <text class="pending-tag">⏳ 审核中，仅你可见</text>
        </view>
        <cw-post-card
          :post="post" :cat-map="catMap"
          @like="onLike" @follow="onFollow"
        />
      </view>
      <view v-if="!loading && list.length === 0" class="empty">
        <text class="empty-emoji">{{ tab === 'posts' ? '📝' : '⭐' }}</text>
        <text class="empty-text">{{ tab === 'posts' ? '还没有发布过动态' : '还没有收藏内容' }}</text>
        <text class="empty-sub">{{ tab === 'posts' ? '点首页「发布」写下第一条吧' : '看到喜欢的动态，点☆收藏后会出现在这里' }}</text>
        <button v-if="tab === 'posts'" class="btn go-btn" @click="goCreate">去发布</button>
      </view>
      <view v-if="loading" class="loading-text">加载中…</view>
      <view v-if="!loading && noMore && list.length > 0" class="loading-text">— 已经到底啦 —</view>
    </view>
  </view>
</template>
<script setup>
import { ref } from 'vue'
import { onLoad, onShow, onReachBottom, onPullDownRefresh } from '@dcloudio/uni-app'
import { api } from '../../utils/api'
const tab = ref('posts')           // posts / favs
onLoad((options) => {
  if (options && options.tab === 'favs') tab.value = 'favs'
})
const postStatus = ref('all')      // all / published / pending
const list = ref([])
const page = ref(1)
const loading = ref(false)
const noMore = ref(false)
const counts = ref({ posts: 0, favs: 0 })
const catMap = ref({})
const loadCats = async () => {
  try {
    const cats = await api.getCategories()
    const m = {};
    (cats || []).forEach((c) => { m[c.id] = c.name })
    catMap.value = m
  } catch (e) {}
}
const loadCounts = async () => {
  try {
    const d = await api.getMyOverview()
    counts.value.favs = d.stats.favorite_count || 0
    const mine = await api.getMyPosts({ page: 1, page_size: 1, status: 'all' })
    counts.value.posts = mine.total || 0
  } catch (e) {}
}
const load = async (reset = false) => {
  if (loading.value) return
  if (reset) { page.value = 1; noMore.value = false; list.value = [] }
  if (noMore.value) return
  loading.value = true
  try {
    const params = { page: page.value, page_size: 10 }
    const data = tab.value === 'posts'
      ? await api.getMyPosts({ ...params, status: postStatus.value })
      : await api.getMyFavorites(params)
    if (reset) list.value = data.items
    else list.value.push(...data.items)
    if (data.items.length < 10) noMore.value = true
    else page.value++
  } catch (e) {
    noMore.value = true
  } finally {
    loading.value = false
  }
}
const switchTab = (t) => {
  if (tab.value === t) return
  tab.value = t
  load(true)
}
const switchStatus = (s) => {
  if (postStatus.value === s) return
  postStatus.value = s
  load(true)
}
const goCreate = () => uni.navigateTo({ url: '/pages/post/create' })
const onLike = async (post) => {
  try {
    const data = await api.likePost(post.id)
    post.is_liked = data.liked
    post.like_count = data.like_count
  } catch (e) {}
}
const onFollow = async (post) => {
  const uid = post.author?.id || post.user_id
  if (!uid) return
  try {
    const data = await api.toggleFollow(uid)
    if (post.author) post.author.is_following = data.following
  } catch (e) {}
}
const onDeleted = (id) => {
  list.value = list.value.filter((p) => p.id !== id)
  counts.value.posts = Math.max(0, counts.value.posts - 1)
}
uni.$on('campus:post-deleted', onDeleted)
onShow(() => {
  loadCats()
  loadCounts()
  load(true)
})
onReachBottom(() => load())
onPullDownRefresh(async () => {
  await Promise.all([load(true), loadCounts()])
  uni.stopPullDownRefresh()
})
</script>
<style scoped>
.tabs {
  display: flex; padding: 8rpx; gap: 8rpx; margin: 24rpx 24rpx 16rpx;
}
.tab {
  flex: 1; text-align: center; padding: 20rpx 0; border-radius: 999rpx;
  font-size: 28rpx; color: var(--text2); font-weight: 600;
}
.tab.on { background: var(--grad); color: #fff; font-weight: 700; box-shadow: var(--shadow-brand); }
.tab-n { font-size: 22rpx; margin-left: 8rpx; opacity: .85; }
.sub-filter { white-space: nowrap; padding: 4rpx 24rpx 12rpx; }
.chip {
  display: inline-block; padding: 12rpx 28rpx; margin-right: 14rpx;
  border-radius: 999rpx; font-size: 25rpx; color: var(--text2);
  background: var(--surface); border: 1rpx solid var(--line);
}
.chip.on { background: var(--brand-soft); color: var(--brand); border-color: transparent; font-weight: 700; }
.post-list { padding: 0 24rpx; }
.pending-row { padding: 4rpx 8rpx 10rpx; }
.pending-tag {
  font-size: 22rpx; color: var(--gold, #fbbf24);
  background: rgba(251, 191, 36, 0.14); border: 1rpx solid rgba(251, 191, 36, 0.3);
  padding: 6rpx 18rpx; border-radius: 999rpx;
}
.empty { text-align: center; padding: 110rpx 0; }
.empty-emoji { font-size: 92rpx; display: block; }
.empty-text { display: block; margin-top: 24rpx; font-size: 30rpx; font-weight: 700; color: var(--text); }
.empty-sub { display: block; margin-top: 12rpx; font-size: 24rpx; color: var(--text3); line-height: 1.6; }
.go-btn { margin: 32rpx 80rpx 0; }
.loading-text { text-align: center; padding: 36rpx; color: var(--text3); font-size: 24rpx; }
</style>
