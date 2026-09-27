<template>
  <view class="page" :class="cwRootClass">
    <!-- 搜索栏 -->
    <view class="search-bar">
      <view class="search-box">
        <text class="search-ico">🔍</text>
        <input
          ref="searchInput" class="search-input" v-model="keyword"
          placeholder="搜索帖子或同学" placeholder-class="ph" confirm-type="search"
          focus
          @confirm="doSearch"
        />
        <text v-if="keyword" class="search-clear" @click="clearKeyword">✕</text>
      </view>
      <text class="cancel" @click="goBack">取消</text>
    </view>
    <!-- 未搜索：历史记录 -->
    <view v-if="!searched" class="history-wrap">
      <view class="card" v-if="history.length">
        <view class="hist-head">
          <text class="hist-title">搜索历史</text>
          <text class="hist-clear" @click="clearHistory">清空</text>
        </view>
        <view class="hist-tags">
          <text v-for="(h, i) in history" :key="i" class="hist-tag" @click="tapHistory(h)">{{ h }}</text>
        </view>
      </view>
      <view class="card tips-card">
        <view class="hist-title">小提示</view>
        <view class="tip-line">· 帖子：按标题和正文关键词匹配</view>
        <view class="tip-line">· 用户：按昵称或登录名匹配</view>
      </view>
    </view>
    <!-- 搜索结果 -->
    <block v-else>
      <view class="result-tabs">
        <view class="r-tab" :class="{ on: resultTab === 'posts' }" @click="switchResult('posts')">
          帖子<text v-if="postsTotal" class="r-n">{{ postsTotal }}</text>
        </view>
        <view class="r-tab" :class="{ on: resultTab === 'users' }" @click="switchResult('users')">
          用户<text v-if="usersTotal" class="r-n">{{ usersTotal }}</text>
        </view>
      </view>
      <!-- 帖子结果 -->
      <view v-if="resultTab === 'posts'" class="result-list">
        <cw-post-card
          v-for="post in posts" :key="post.id" :post="post" :cat-map="{}"
          @like="onLike" @follow="onFollow"
        />
        <view v-if="!loading && posts.length === 0" class="empty">
          <text class="empty-emoji">🔍</text>
          <text class="empty-text">没有找到相关帖子</text>
          <text class="empty-sub">换个关键词试试吧</text>
        </view>
        <view v-if="loading" class="loading-text">搜索中…</view>
        <view v-if="!loading && noMorePosts && posts.length > 0" class="loading-text">— 已经到底啦 —</view>
      </view>
      <!-- 用户结果 -->
      <view v-else class="result-list">
        <view v-for="u in users" :key="u.id" class="user-row card" @click="openUser(u.id)">
          <cw-avatar :src="u.avatar" :user-id="u.id" :size="88" />
          <view class="u-main">
            <view class="u-name-row">
              <text class="u-name">{{ u.nickname }}</text>
              <text v-if="u.role === 'admin'" class="u-tag admin">管理员</text>
            </view>
            <text class="u-bio">{{ u.bio || ('Lv' + (u.level || 1) + ' · ' + (u.post_count || 0) + ' 条动态') }}</text>
          </view>
          <view v-if="u.is_self" class="u-btn self-btn">我</view>
          <view
            v-else
            class="u-btn" :class="{ on: u.is_following }"
            @click.stop="toggleFollow(u)"
          >{{ u.is_following ? '已关注' : '+ 关注' }}</view>
        </view>
        <view v-if="!loading && users.length === 0" class="empty">
          <text class="empty-emoji">🫧</text>
          <text class="empty-text">没有找到相关同学</text>
          <text class="empty-sub">试试 TA 的昵称或登录名</text>
        </view>
        <view v-if="loading" class="loading-text">搜索中…</view>
      </view>
    </block>
  </view>
</template>
<script setup>
import { ref } from 'vue'
import { onReachBottom } from '@dcloudio/uni-app'
import { api } from '../../utils/api'
const HISTORY_KEY = 'cw_search_history'
const keyword = ref('')
const searched = ref(false)
const resultTab = ref('posts')
const posts = ref([])
const users = ref([])
const postsTotal = ref(0)
const usersTotal = ref(0)
const postPage = ref(1)
const noMorePosts = ref(false)
const loading = ref(false)
const history = ref(uni.getStorageSync(HISTORY_KEY) || [])
const pushHistory = (kw) => {
  const list = history.value.filter((x) => x !== kw)
  list.unshift(kw)
  history.value = list.slice(0, 15)
  uni.setStorageSync(HISTORY_KEY, history.value)
}
const doSearch = () => {
  const kw = keyword.value.trim()
  if (!kw) {
    uni.showToast({ title: '请输入关键词', icon: 'none' })
    return
  }
  keyword.value = kw
  searched.value = true
  resultTab.value = 'posts'
  pushHistory(kw)
  loadPosts(true)
  loadUsers(true)
}
const tapHistory = (h) => { keyword.value = h; doSearch() }
const clearKeyword = () => {
  keyword.value = ''
  searched.value = false
  posts.value = []; users.value = []
}
const clearHistory = () => {
  history.value = []
  uni.removeStorageSync(HISTORY_KEY)
}
const switchResult = (t) => { resultTab.value = t }
const loadPosts = async (reset = false) => {
  if (loading.value) return
  if (reset) { postPage.value = 1; noMorePosts.value = false; posts.value = [] }
  if (noMorePosts.value) return
  loading.value = true
  try {
    const data = await api.getPosts({ page: postPage.value, page_size: 10, keyword: keyword.value, sort: 'new' })
    postsTotal.value = data.total || 0
    if (reset) posts.value = data.items
    else posts.value.push(...data.items)
    if (data.items.length < 10) noMorePosts.value = true
    else postPage.value++
  } catch (e) { noMorePosts.value = true } finally { loading.value = false }
}
const loadUsers = async () => {
  try {
    const data = await api.searchUsers({ keyword: keyword.value, page: 1, page_size: 30 })
    usersTotal.value = data.total || 0
    users.value = data.items
  } catch (e) { users.value = []; usersTotal.value = 0 }
}
const onLike = async (post) => {
  if (!uni.getStorageSync('token')) { uni.showToast({ title: '请先登录', icon: 'none' }); return }
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
const toggleFollow = async (u) => {
  if (!uni.getStorageSync('token')) { uni.showToast({ title: '请先登录', icon: 'none' }); return }
  try {
    const data = await api.toggleFollow(u.id)
    u.is_following = data.following
    uni.showToast({ title: data.following ? '已关注' : '已取消关注', icon: 'none' })
  } catch (e) {}
}
const openUser = (id) => uni.navigateTo({ url: `/pages/user/profile?id=${id}` })
const goBack = () => uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/index/index' }) })
onReachBottom(() => { if (searched.value && resultTab.value === 'posts') loadPosts() })
</script>
<style scoped>
.page { min-height: 100vh; }
.search-bar { display: flex; align-items: center; gap: 18rpx; padding: 16rpx 24rpx; }
.search-box {
  flex: 1; display: flex; align-items: center; height: 76rpx; padding: 0 24rpx;
  background: var(--surface); border: 1rpx solid var(--line); border-radius: 999rpx;
}
.search-ico { font-size: 28rpx; margin-right: 12rpx; }
.search-input { flex: 1; font-size: 27rpx; color: var(--text); height: 76rpx; }
.ph { color: var(--text3); font-size: 27rpx; }
.search-clear { color: var(--text3); font-size: 24rpx; padding: 8rpx; }
.cancel { font-size: 28rpx; color: var(--brand); }
.history-wrap { padding: 12rpx 24rpx; }
.hist-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18rpx; }
.hist-title { font-size: 28rpx; font-weight: 700; color: var(--text); }
.hist-clear { font-size: 24rpx; color: var(--text3); }
.hist-tags { display: flex; flex-wrap: wrap; gap: 16rpx; }
.hist-tag {
  font-size: 25rpx; color: var(--text2); padding: 12rpx 26rpx;
  background: var(--brand-soft); border-radius: 999rpx;
}
.tips-card { margin-top: 20rpx; }
.tip-line { font-size: 24rpx; color: var(--text3); line-height: 2; }
.result-tabs { display: flex; gap: 40rpx; padding: 12rpx 36rpx 20rpx; }
.r-tab { font-size: 29rpx; color: var(--text3); font-weight: 600; position: relative; padding-bottom: 10rpx; }
.r-tab.on { color: var(--text); font-size: 33rpx; font-weight: 800; }
.r-tab.on::after {
  content: ''; position: absolute; left: 50%; bottom: 0; transform: translateX(-50%);
  width: 40rpx; height: 8rpx; border-radius: 999rpx; background: var(--grad);
}
.r-n { font-size: 22rpx; margin-left: 6rpx; opacity: .8; }
.result-list { padding: 0 24rpx; }
.user-row { display: flex; align-items: center; gap: 20rpx; padding: 24rpx; margin-bottom: 18rpx; }
.u-main { flex: 1; min-width: 0; }
.u-name-row { display: flex; align-items: center; gap: 10rpx; }
.u-name { font-size: 29rpx; font-weight: 700; color: var(--text); }
.u-tag { font-size: 19rpx; padding: 3rpx 12rpx; border-radius: 999rpx; font-weight: 700; }
.u-tag.admin { color: #fde68a; background: rgba(251, 191, 36, .16); border: 1rpx solid rgba(251, 191, 36, .35); }
.u-bio {
  display: block; margin-top: 8rpx; font-size: 24rpx; color: var(--text3);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.u-btn {
  flex-shrink: 0; font-size: 24rpx; font-weight: 700; color: #fff;
  background: var(--grad); padding: 12rpx 28rpx; border-radius: 999rpx;
}
.u-btn.on { background: transparent; color: var(--text3); border: 1rpx solid var(--line); }
.u-btn.self-btn { background: var(--brand-soft); color: var(--brand); }
.empty { text-align: center; padding: 110rpx 0; }
.empty-emoji { font-size: 90rpx; display: block; }
.empty-text { display: block; margin-top: 22rpx; font-size: 30rpx; font-weight: 700; color: var(--text); }
.empty-sub { display: block; margin-top: 12rpx; font-size: 24rpx; color: var(--text3); }
.loading-text { text-align: center; padding: 36rpx; color: var(--text3); font-size: 24rpx; }
</style>
