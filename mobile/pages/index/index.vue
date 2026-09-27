<template>
  <view class="page" :class="[cwRootClass, { 'is-d': isDesktop }]">
    <!-- ========== 桌面端左侧导航（仅 H5 桌面布局显示，移动端不渲染） ========== -->
    <!-- #ifdef H5 -->
    <view class="d-left">
      <view class="d-brand" @click="scrollTop">
        <text class="d-brand-logo">🌌</text>
        <view>
          <text class="d-brand-name">{{ siteName }}</text>
          <text class="d-brand-sub">分享校园生活每一刻</text>
        </view>
      </view>
      <view class="d-nav">
        <view class="d-nav-item on"><text class="d-ni-ico">🏠</text><text>首页</text></view>
        <view class="d-nav-item" @click="goSearch"><text class="d-ni-ico">🔍</text><text>搜索</text></view>
        <view class="d-nav-item" @click="goTab('/pages/message/inbox')">
          <text class="d-ni-ico">💬</text><text>消息</text>
          <text v-if="unreadTotal" class="d-nav-badge">{{ unreadTotal > 99 ? '99+' : unreadTotal }}</text>
        </view>
        <view class="d-nav-item" @click="goTab('/pages/profile/profile')"><text class="d-ni-ico">👤</text><text>我的</text></view>
      </view>
      <view class="d-pub btn hover-press" @click="goCreate"><text class="d-pub-plus">＋</text>发布动态</view>
      <view v-if="me" class="d-me" @click="openUser(me.id)">
        <cw-avatar :src="me.avatar" :user-id="me.id" :size="72" />
        <view class="d-me-info">
          <text class="d-me-name cw-ellipsis">{{ me.nickname }}</text>
          <text class="d-me-sub">@{{ me.username }}</text>
        </view>
      </view>
      <view v-else class="d-me d-me-guest" @click="goLogin">
        <text class="d-me-guest-ico">🔓</text>
        <text class="d-me-guest-txt">登录 / 注册</text>
      </view>
    </view>
    <!-- #endif -->

    <!-- ========== 中间主信息流（移动端与桌面共用） ========== -->
    <view class="main-col">
      <!-- 渐变品牌头部 -->
      <view class="hero">
        <view class="hero-top">
          <view class="hero-brand">
            <text class="hero-title">{{ siteName }}</text>
            <text class="hero-sub">{{ greeting }}，来看看同学们在聊什么</text>
          </view>
          <!-- 发布按钮收进首页顶部 -->
          <view class="publish-btn hover-press" @click="goCreate">
            <text class="publish-plus">＋</text>
            <text>发布</text>
          </view>
        </view>
        <view class="search-pill" @click="goSearch">
          <text class="search-ico">🔍</text>
          <text class="search-ph">搜索帖子或同学</text>
        </view>
      </view>
      <view class="body">
        <!-- 公告位（桌面端挪到右侧栏，这里隐藏） -->
        <view v-if="announcements.length" class="notice-bar m-only" @click="openSafeLink(currentAnnouncement.link_url)">
          <text class="notice-tag">公告</text>
          <view class="notice-viewport">
            <view class="notice-track" :style="{ transform: `translateY(-${annIndex * 100}%)` }">
              <view v-for="ann in announcements" :key="ann.id" class="notice-item">
                <text class="notice-text">{{ ann.content }}</text>
              </view>
            </view>
          </view>
        </view>
        <!-- 轮播 -->
        <swiper
          v-if="banners.length" class="banner-swiper" circular autoplay
          :interval="4000" :duration="500" indicator-dots
          indicator-color="rgba(255,255,255,0.45)" indicator-active-color="#ffffff"
        >
          <swiper-item v-for="b in banners" :key="b.id" @click="openSafeLink(b.link_url)">
            <view class="banner-slide" :class="'theme-' + (b.theme || 'blue')">
              <image v-if="b.image_url" class="banner-img" :src="mediaUrl(b.image_url)" mode="aspectFill" />
              <view v-else class="banner-inner">
                <text class="banner-title">{{ b.title }}</text>
                <text v-if="b.link_url" class="banner-cta">查看详情 ›</text>
              </view>
            </view>
          </swiper-item>
        </swiper>
        <!-- 分类 -->
        <scroll-view class="cats" scroll-x :show-scrollbar="false">
          <view class="cats-inner">
            <view class="cat-chip" :class="{ active: currentCategory === 0 }" @click="switchCategory(0)">
              <text class="cat-ico">✨</text><text>全部</text>
            </view>
            <view
              v-for="cat in categories.filter(c => c.id)" :key="cat.id"
              class="cat-chip" :class="{ active: currentCategory === cat.id }"
              @click="switchCategory(cat.id)"
            >
              <text class="cat-ico">{{ cat.icon || '📌' }}</text><text>{{ cat.name }}</text>
            </view>
          </view>
        </scroll-view>
        <!-- 排序 / 信息流切换 -->
        <view class="sort-bar">
          <view class="sort-tabs">
            <text class="sort-tab" :class="{ on: feedTab === 'new' }" @click="switchFeed('new')">最新</text>
            <text class="sort-tab" :class="{ on: feedTab === 'hot' }" @click="switchFeed('hot')">最热</text>
            <text class="sort-tab" :class="{ on: feedTab === 'following' }" @click="switchFeed('following')">关注</text>
          </view>
          <text class="sort-count">{{ keyword ? '搜索结果' : '共 ' + total + ' 帖' }}</text>
        </view>
        <!-- 搜索中提示条 -->
        <view v-if="keyword" class="search-tip">
          <text>关键词：{{ keyword }}</text>
          <text class="search-tip-x" @click="clearSearch">清除 ✕</text>
        </view>
        <!-- 骨架屏 -->
        <view v-if="loading && posts.length === 0" class="skeleton-wrap">
          <view v-for="i in 3" :key="i" class="sk-card cw-card">
            <view class="cw-flex">
              <view class="cw-skeleton" style="width:72rpx;height:72rpx;border-radius:50%"></view>
              <view style="flex:1;margin-left:18rpx">
                <view class="cw-skeleton" style="width:180rpx;height:26rpx"></view>
                <view class="cw-skeleton" style="width:120rpx;height:22rpx;margin-top:12rpx"></view>
              </view>
            </view>
            <view class="cw-skeleton" style="height:28rpx;margin-top:22rpx"></view>
            <view class="cw-skeleton" style="height:28rpx;margin-top:14rpx;width:80%"></view>
            <view class="cw-skeleton" style="height:220rpx;margin-top:20rpx"></view>
          </view>
        </view>
        <!-- 帖子流 -->
        <view v-else class="post-list stagger">
          <cw-post-card
            v-for="post in posts" :key="post.id" :post="post" :cat-map="catMap"
            @like="onLike" @follow="onFollowAuthor"
          />
          <view v-if="!loading && posts.length === 0" class="empty anim-fade">
            <text class="empty-emoji">🫧</text>
            <text class="empty-text">{{ emptyTitle }}</text>
            <text class="empty-sub">{{ emptySub }}</text>
          </view>
          <view v-if="loading" class="loading-text">加载中…</view>
          <view v-if="!loading && noMore && posts.length > 0" class="loading-text">— 已经到底啦 —</view>
        </view>
      </view>
    </view>

    <!-- ========== 桌面端右侧栏（仅 H5） ========== -->
    <!-- #ifdef H5 -->
    <view class="d-right">
      <!-- 社区公告 -->
      <view v-if="announcements.length" class="d-card d-notice">
        <view class="d-card-title"><text class="d-ct-bar"></text>社区公告</view>
        <view class="d-notice-body" @click="openSafeLink(currentAnnouncement.link_url)">
          <text class="d-notice-text">{{ currentAnnouncement.content || '暂无公告' }}</text>
        </view>
      </view>
      <!-- 热门分类 -->
      <view class="d-card">
        <view class="d-card-title"><text class="d-ct-bar"></text>热门板块</view>
        <view class="d-hotcats">
          <view
            class="d-hotcat" :class="{ on: currentCategory === c.id }"
            v-for="c in categories.filter(c => c.id)" :key="'r'+c.id"
            @click="switchCategory(c.id)"
          >{{ c.icon || '📌' }} {{ c.name }}</view>
        </view>
      </view>
      <!-- 推荐关注 -->
      <view class="d-card">
        <view class="d-card-title"><text class="d-ct-bar"></text>推荐关注</view>
        <view v-if="suggestions.length" class="d-sug-list">
          <view v-for="u in suggestions" :key="u.id" class="d-sug">
            <cw-avatar :src="u.avatar" :user-id="u.id" :size="68" />
            <view class="d-sug-info" @click="openUser(u.id)">
              <view class="d-sug-name-row">
                <text class="d-sug-name cw-ellipsis">{{ u.nickname }}</text>
                <text v-for="t in staffText(u.perm_tags, u.role)" :key="t" class="d-sug-tag" :class="tagClass(t)">{{ t }}</text>
              </view>
              <text class="d-sug-bio cw-ellipsis">{{ u.bio || ('Lv' + (u.level||1) + ' 校园墙用户') }}</text>
            </view>
            <view class="d-sug-btn" :class="{ on: u.is_following }" @click="toggleSuggest(u)">
              {{ u.is_following ? '已关注' : '+ 关注' }}
            </view>
          </view>
        </view>
        <view v-else class="d-sug-empty">暂无推荐，去逛逛更多同学吧</view>
      </view>
      <!-- 页脚 -->
      <view class="d-foot">
        <text class="d-foot-link" @click="openAgreement">隐私政策与用户协议</text>
        <text class="d-foot-copy">© 校园墙 · 友善交流社区</text>
      </view>
    </view>
    <!-- #endif -->
  </view>
</template>
<script setup>
import { ref, computed } from 'vue'
import { onShow, onHide, onUnload, onPullDownRefresh, onReachBottom } from '@dcloudio/uni-app'
import { api, mediaUrl } from '../../utils/api'
import { openSafeLink } from '../../utils/link'
const posts = ref([])
const categories = ref([{ id: 0, name: '全部' }])
const currentCategory = ref(0)
const feedTab = ref('new') // new/hot/following
const sort = computed(() => (feedTab.value === 'hot' ? 'hot' : 'new'))
const keyword = ref('')
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const noMore = ref(false)
const banners = ref([])
const announcements = ref([])
const annIndex = ref(0)
const suggestions = ref([])
const unreadTotal = ref(0)
const me = ref(null)
const siteName = ref('校园墙')
let annTimer = null
// #ifdef H5
const isDesktop = ref(false)
const updateDesktop = () => {
  isDesktop.value = window.innerWidth >= 1024 && !/Mobi|Android|iPhone|iPod|Windows Phone/i.test(navigator.userAgent || '')
}
updateDesktop()
window.addEventListener('resize', updateDesktop)
// #endif
const catMap = computed(() => {
  const m = {}
  categories.value.forEach((c) => { if (c.id) m[c.id] = c.name })
  return m
})
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})
const emptyTitle = computed(() => {
  if (keyword.value) return '没有找到相关帖子'
  if (feedTab.value === 'following') return '还没有关注的动态'
  return '这里还空空如也'
})
const emptySub = computed(() => {
  if (keyword.value) return '换个关键词试试吧'
  if (feedTab.value === 'following') return '去关注一些同学，TA 们的动态会出现在这里'
  return '点右上角「发布」，开启第一个话题吧'
})
const currentAnnouncement = computed(() => announcements.value[annIndex.value] || {})
const startAnnouncementLoop = () => {
  if (annTimer) clearInterval(annTimer)
  if (announcements.value.length <= 1) return
  annTimer = setInterval(() => { annIndex.value = (annIndex.value + 1) % announcements.value.length }, 3500)
}
const stopAnnouncementLoop = () => { if (annTimer) { clearInterval(annTimer); annTimer = null } }
const loadPromotions = async () => {
  try {
    const data = await api.getPromotions()
    banners.value = (data.banners || []).map((b) => ({ ...b, image_url: mediaUrl(b.image_url) }))
    announcements.value = data.announcements || []
    annIndex.value = 0
    startAnnouncementLoop()
  } catch (e) { /* 运营位失败不影响浏览 */ }
}
const loadMeAndBadge = async () => {
  try {
    const cfg = JSON.parse(uni.getStorageSync('public_settings') || '{}')
    if (cfg.site_name) siteName.value = cfg.site_name
  } catch (e) {}
  if (!uni.getStorageSync('token')) { me.value = null; unreadTotal.value = 0; return }
  try { me.value = JSON.parse(uni.getStorageSync('userInfo') || 'null') } catch (e) { me.value = null }
  try {
    const [n, m] = await Promise.all([
      api.getUnreadCount().catch(() => ({ count: 0 })),
      api.getMessageUnreadCount().catch(() => ({ count: 0 })),
    ])
    unreadTotal.value = (n?.count || 0) + (m?.count || 0)
  } catch (e) {}
}
const loadSuggestions = async () => {
  // 访客也展示推荐；真正点关注时再要求登录
  try { suggestions.value = (await api.getSuggestions()) || [] } catch (e) {}
}
const goCreate = () => {
  if (!uni.getStorageSync('token')) { uni.showToast({ title: '请先登录', icon: 'none' }); return }
  uni.navigateTo({ url: '/pages/post/create' })
}
const goLogin = () => uni.navigateTo({ url: '/pages/login/login' })
const goTab = (url) => uni.switchTab({ url })
const openUser = (id) => id && uni.navigateTo({ url: `/pages/user/profile?id=${id}` })
const openAgreement = () => uni.navigateTo({ url: '/pages/agreement/privacy' })
// #ifdef H5
const scrollTop = () => window.scrollTo({ top: 0, behavior: 'smooth' })
// #endif
const goSearch = () => uni.navigateTo({ url: '/pages/search/search' })
const doSearch = () => { if (keyword.value.trim()) { keyword.value = keyword.value.trim(); loadPosts(true) } }
const clearSearch = () => { keyword.value = ''; loadPosts(true) }
const loadCategories = async () => {
  try {
    const data = await api.getCategories()
    categories.value = [{ id: 0, name: '全部' }, ...data]
  } catch (e) { /* 保留全部 */ }
}
const loadPosts = async (reset = false) => {
  if (loading.value) return
  if (reset) { page.value = 1; noMore.value = false; posts.value = [] }
  if (noMore.value) return
  loading.value = true
  try {
    const params = { page: page.value, page_size: 10, sort: sort.value }
    if (currentCategory.value) params.category_id = currentCategory.value
    if (feedTab.value === 'following') params.feed = 'following'
    if (keyword.value) params.keyword = keyword.value
    const data = await api.getPosts(params)
    total.value = data.total || 0
    if (reset) posts.value = data.items
    else posts.value.push(...data.items)
    if (data.items.length < 10) noMore.value = true
    else page.value++
  } finally { loading.value = false }
}
const switchCategory = (id) => { if (currentCategory.value !== id) { currentCategory.value = id; loadPosts(true) } }
const switchFeed = (f) => {
  if (feedTab.value === f) return
  if (f === 'following' && !uni.getStorageSync('token')) {
    uni.showToast({ title: '登录后查看关注动态', icon: 'none' }); return
  }
  feedTab.value = f
  loadPosts(true)
}
const onLike = async (post) => {
  if (!uni.getStorageSync('token')) { uni.showToast({ title: '请先登录', icon: 'none' }); return }
  try {
    const data = await api.likePost(post.id)
    post.is_liked = data.liked
    post.like_count = data.like_count
  } catch (e) { /* 卡片已乐观更新 */ }
}
const onFollowAuthor = async (post) => {
  const uid = post.author?.id || post.user_id
  if (!uid) return
  try {
    const data = await api.toggleFollow(uid)
    if (post.author) post.author.is_following = data.following
    // 同步推荐位
    const sug = suggestions.value.find((s) => s.id === uid)
    if (sug) sug.is_following = data.following
    // 关注流下取消关注，即时移除该作者的帖子
    if (!data.following && feedTab.value === 'following') {
      posts.value = posts.value.filter((p) => p.author?.id !== uid)
    }
    uni.showToast({ title: data.following ? '已关注' : '已取消关注', icon: 'none' })
  } catch (e) {}
}
const toggleSuggest = async (u) => {
  if (!uni.getStorageSync('token')) { uni.showToast({ title: '请先登录', icon: 'none' }); return }
  try {
    const data = await api.toggleFollow(u.id)
    u.is_following = data.following
    posts.value.forEach((p) => { if (p.author?.id === u.id && p.author) p.author.is_following = data.following })
    uni.showToast({ title: data.following ? '已关注' : '已取消关注', icon: 'none' })
  } catch (e) {}
}
// 审核身份标签文案
const STAFF_LABELS = { admin: '管理员', content_review: '审核员', report_review: '审查员' }
const staffText = (tags, role) => {
  const list = Array.isArray(tags) ? tags : (role === 'admin' ? ['admin'] : [])
  return list.map((t) => STAFF_LABELS[t]).filter(Boolean)
}
const tagClass = (label) => ({ 管理员: 'tag-admin', 审核员: 'tag-review', 审查员: 'tag-audit' }[label] || '')
// 帖子在详情页/卡片被删除后，同步从信息流移除
const onPostDeleted = (id) => { posts.value = posts.value.filter((p) => p.id !== id) }
uni.$on('campus:post-deleted', onPostDeleted)
let lastToken = ''
onShow(() => {
  loadMeAndBadge()
  const curToken = uni.getStorageSync('token') || ''
  // 首次进入或登录态变化（登录/退出）时整体刷新，避免关注状态等停留在旧数据
  if (posts.value.length === 0 || curToken !== lastToken) {
    lastToken = curToken
    loadCategories(); loadPosts(true); loadPromotions(); loadSuggestions()
  }
  else { startAnnouncementLoop(); loadSuggestions() }
})
onHide(stopAnnouncementLoop)
onUnload(() => { stopAnnouncementLoop(); uni.$off('campus:post-deleted', onPostDeleted) })
onPullDownRefresh(async () => {
  await Promise.all([loadPosts(true), loadPromotions(), loadMeAndBadge(), loadSuggestions()])
  uni.stopPullDownRefresh()
})
onReachBottom(() => loadPosts())
</script>
<style scoped>
.page { min-height: 100vh; background: var(--bg); padding-bottom: 40rpx; }
.hero { background: var(--grad); padding: calc(48rpx + var(--status-bar-height, 0px)) 36rpx 40rpx; border-radius: 0 0 44rpx 44rpx; position: relative; overflow: hidden; }
.hero::after { content: ''; position: absolute; right: -80rpx; top: -80rpx; width: 280rpx; height: 280rpx; border-radius: 50%; background: rgba(255,255,255,0.12); }
.hero-top { display: flex; align-items: center; justify-content: space-between; position: relative; z-index: 1; }
.hero-brand { flex: 1; min-width: 0; margin-right: 20rpx; }
.hero-title { font-size: 56rpx; font-weight: 800; color: #fff; letter-spacing: 3rpx; display: block; }
.hero-sub { font-size: 25rpx; color: rgba(255,255,255,0.85); margin-top: 10rpx; display: block; }
.publish-btn {
  flex-shrink: 0;
  display: flex; align-items: center; gap: 6rpx;
  background: rgba(255,255,255,0.95); color: var(--brand-deep);
  font-size: 27rpx; font-weight: 700; padding: 0 28rpx; height: 68rpx;
  border-radius: 999rpx; box-shadow: 0 8rpx 22rpx rgba(67,56,202,.25);
}
.publish-plus { font-size: 38rpx; font-weight: 700; line-height: 1; }
.search-pill { position: relative; z-index: 1; margin-top: 32rpx; height: 80rpx; background: rgba(255,255,255,0.95); border-radius: 999rpx; display: flex; align-items: center; padding: 0 28rpx; box-shadow: 0 8rpx 24rpx rgba(67,56,202,.18); }
.search-ico { font-size: 28rpx; margin-right: 14rpx; }
.search-input { flex: 1; font-size: 26rpx; color: #1f2345; height: 80rpx; }
.search-pill .uni-input-input, .search-pill input { color: #1f2345 !important; }
.search-ph { color: #8a8fb8; font-size: 26rpx; }
.search-clear { font-size: 24rpx; color: #8a8fb8; padding: 10rpx; }
.body { padding: 0 24rpx; margin-top: 22rpx; position: relative; z-index: 2; }
.notice-bar { background: var(--surface); border-radius: var(--radius); padding: 0 24rpx; height: 76rpx; display: flex; align-items: center; box-shadow: var(--shadow-sm); overflow: hidden; }
.notice-tag { flex-shrink: 0; font-size: 20rpx; color: #fff; background: var(--grad-warm); padding: 6rpx 16rpx; border-radius: 8rpx; margin-right: 18rpx; font-weight: 700; }
.notice-viewport { flex: 1; height: 76rpx; overflow: hidden; }
.notice-track { transition: transform .45s ease; }
.notice-item { height: 76rpx; display: flex; align-items: center; }
.notice-text { font-size: 25rpx; color: var(--ink-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.banner-swiper { height: 280rpx; margin-top: 20rpx; }
.banner-slide { height: 252rpx; border-radius: var(--radius-lg); overflow: hidden; position: relative; box-shadow: var(--shadow); }
.theme-blue { background: linear-gradient(135deg,#6366f1,#8b5cf6); }
.theme-teal { background: linear-gradient(135deg,#0ea5e9,#14b8a6); }
.theme-gold { background: linear-gradient(135deg,#fb7185,#f59e0b); }
.theme-ink { background: linear-gradient(135deg,#312e81,#6d28d9); }
.banner-img { width: 100%; height: 100%; }
.banner-inner { height: 100%; padding: 0 40rpx; display: flex; flex-direction: column; justify-content: center; }
.banner-title { color: #fff; font-size: 36rpx; font-weight: 800; }
.banner-cta { margin-top: 18rpx; align-self: flex-start; color: #fff; font-size: 23rpx; border: 1rpx solid rgba(255,255,255,.7); padding: 8rpx 26rpx; border-radius: 999rpx; }
.cats { margin-top: 28rpx; white-space: nowrap; }
.cats-inner { display: inline-flex; padding: 4rpx; }
.cat-chip { display: inline-flex; align-items: center; flex-shrink: 0; white-space: nowrap; padding: 14rpx 28rpx; margin-right: 16rpx; background: var(--surface); border-radius: 999rpx; font-size: 26rpx; color: var(--ink-2); box-shadow: var(--shadow-sm); }
.cat-ico { margin-right: 8rpx; font-size: 28rpx; }
.cat-chip.active { background: var(--grad); color: #fff; font-weight: 700; box-shadow: var(--shadow-brand); }
.sort-bar { display: flex; align-items: center; justify-content: space-between; margin: 32rpx 8rpx 16rpx; }
.sort-tabs { display: flex; align-items: center; }
.sort-tab { font-size: 30rpx; color: var(--ink-3); margin-right: 32rpx; font-weight: 600; position: relative; padding-bottom: 8rpx; }
.sort-tab.on { color: var(--ink); font-size: 34rpx; font-weight: 800; }
.sort-tab.on::after { content: ''; position: absolute; left: 50%; bottom: 0; transform: translateX(-50%); width: 36rpx; height: 8rpx; border-radius: 999rpx; background: var(--grad); }
.sort-count { font-size: 23rpx; color: var(--ink-3); }
.search-tip { display: flex; align-items: center; justify-content: space-between; margin: 0 8rpx 16rpx; padding: 12rpx 22rpx; font-size: 23rpx; color: var(--brand2, #6ee7ff); background: rgba(110,231,255,.08); border-radius: 14rpx; }
.search-tip-x { padding: 4rpx 10rpx; }
.sk-card { padding: 28rpx; margin-bottom: 22rpx; }
.post-list { padding-top: 4rpx; }
.empty { text-align: center; padding: 120rpx 0; }
.empty-emoji { font-size: 96rpx; display: block; }
.empty-text { display: block; margin-top: 28rpx; color: var(--ink); font-size: 30rpx; font-weight: 700; }
.empty-sub { display: block; margin-top: 12rpx; color: var(--ink-3); font-size: 25rpx; padding: 0 40rpx; line-height: 1.6; }
.loading-text { text-align: center; padding: 40rpx; color: var(--ink-3); font-size: 24rpx; }

/* ===================== 桌面端三栏布局（仅 H5 宽屏） ===================== */
/* #ifdef H5 */
.d-left, .d-right { display: none; }
@media (min-width: 1024px) {
  .page.is-d {
    display: grid;
    grid-template-columns: 224px minmax(0, 620px) 300px;
    gap: 24px;
    justify-content: center;
    align-items: start;
    max-width: 1200px;
    margin: 0 auto;
    padding: 26px 20px 60px;
  }
  .main-col { min-width: 0; }
  .page.is-d .hero { border-radius: 20px; padding: 26px 28px 24px; }
  .page.is-d .hero-title { font-size: 30px; letter-spacing: 1px; }
  .page.is-d .hero-sub { font-size: 13px; margin-top: 6px; }
  .page.is-d .publish-btn { height: 36px; padding: 0 18px; font-size: 14px; border-radius: 999px; }
  .page.is-d .publish-plus { font-size: 20px; }
  .page.is-d .search-pill { height: 40px; margin-top: 16px; border-radius: 999px; }
  .page.is-d .search-input { height: 40px; font-size: 14px; }
  .page.is-d .search-ico { font-size: 14px; }
  .page.is-d .body { padding: 0; margin-top: 16px; }
  .page.is-d .m-only { display: none !important; }
  .page.is-d .banner-swiper { height: 150px; margin-top: 14px; }
  .page.is-d .banner-slide { height: 136px; border-radius: 16px; }
  .page.is-d .banner-title { font-size: 19px; }
  .page.is-d .cats { margin-top: 16px; }
  .page.is-d .cat-chip { padding: 7px 15px; font-size: 13px; margin-right: 8px; border-radius: 999px; }
  .page.is-d .cat-ico { font-size: 14px; }
  .page.is-d .sort-bar { margin: 18px 4px 10px; }
  .page.is-d .sort-tab { font-size: 15px; margin-right: 20px; padding-bottom: 4px; }
  .page.is-d .sort-tab.on { font-size: 17px; }
  .page.is-d .sort-count { font-size: 12px; }
  .page.is-d .search-tip { font-size: 12px; padding: 6px 12px; margin: 0 4px 10px; border-radius: 8px; }
  .page.is-d .loading-text { padding: 22px; font-size: 12px; }
  .page.is-d .empty { padding: 60px 0; }
  .page.is-d .empty-emoji { font-size: 48px; }
  .page.is-d .empty-text { font-size: 16px; margin-top: 14px; }
  .page.is-d .empty-sub { font-size: 13px; }

  /* 左栏 */
  .d-left { display: block; position: sticky; top: 20px; }
  .d-brand { display: flex; align-items: center; gap: 10px; padding: 6px 8px 18px; }
  .d-brand-logo { font-size: 34px; }
  .d-brand-name { display: block; font-size: 20px; font-weight: 800; color: var(--text); letter-spacing: 1px; }
  .d-brand-sub { display: block; font-size: 11px; color: var(--text3); margin-top: 2px; }
  .d-nav { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 8px; backdrop-filter: blur(18px); }
  .d-nav-item {
    display: flex; align-items: center; gap: 12px; padding: 11px 14px; border-radius: 12px;
    font-size: 15px; color: var(--text2); font-weight: 600; cursor: pointer; margin-bottom: 2px; position: relative;
  }
  .d-nav-item:hover { background: rgba(255,255,255,.06); color: var(--text); }
  .d-nav-item.on { background: var(--brand-soft); color: #c4b5fd; }
  .d-ni-ico { font-size: 18px; }
  .d-nav-badge {
    margin-left: auto; min-width: 20px; height: 20px; line-height: 20px; text-align: center;
    padding: 0 6px; border-radius: 999px; background: #f43f5e; color: #fff; font-size: 11px;
  }
  .d-pub { height: 44px; margin-top: 14px; border-radius: 999px; font-size: 15px; font-weight: 700; gap: 6px; }
  .d-pub-plus { font-size: 20px; }
  .d-me {
    display: flex; align-items: center; gap: 10px; margin-top: 16px; padding: 12px;
    background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  }
  .d-me-info { min-width: 0; flex: 1; }
  .d-me-name { display: block; font-size: 14px; font-weight: 700; color: var(--text); }
  .d-me-sub { display: block; font-size: 11px; color: var(--text3); margin-top: 2px; }
  .d-me-guest { justify-content: center; gap: 8px; color: #c4b5fd; font-size: 14px; font-weight: 600; cursor: pointer; }
  .d-me-guest-ico { font-size: 18px; }

  /* 右栏 */
  .d-right { display: block; position: sticky; top: 20px; }
  .d-card {
    background: var(--card); border: 1px solid var(--line); border-radius: 16px;
    padding: 16px; margin-bottom: 16px; backdrop-filter: blur(18px);
  }
  .d-card-title { display: flex; align-items: center; font-size: 14px; font-weight: 800; color: var(--text); margin-bottom: 12px; }
  .d-ct-bar { width: 4px; height: 14px; border-radius: 4px; background: var(--grad); margin-right: 8px; }
  .d-notice-body { font-size: 12.5px; color: var(--text2); line-height: 1.7; }
  .d-notice-text { display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
  .d-hotcats { display: flex; flex-wrap: wrap; gap: 8px; }
  .d-hotcat {
    font-size: 12.5px; color: var(--text2); padding: 5px 12px; border-radius: 999px;
    background: rgba(255,255,255,.05); border: 1px solid var(--line); cursor: pointer;
  }
  .d-hotcat.on { background: var(--grad); color: #fff; border-color: transparent; font-weight: 700; }
  .d-sug-list { display: flex; flex-direction: column; gap: 14px; }
  .d-sug { display: flex; align-items: center; gap: 10px; }
  .d-sug-info { flex: 1; min-width: 0; }
  .d-sug-name-row { display: flex; align-items: center; gap: 6px; }
  .d-sug-name { font-size: 13.5px; font-weight: 700; color: var(--text); max-width: 130px; }
  .d-sug-tag { font-size: 10px; line-height: 1; padding: 3px 7px; border-radius: 999px; font-weight: 700; white-space: nowrap; }
  .tag-admin { color: #fde68a; background: rgba(251,191,36,.16); border: 1px solid rgba(251,191,36,.35); }
  .tag-review { color: #a5b4fc; background: rgba(139,124,246,.16); border: 1px solid rgba(139,124,246,.35); }
  .tag-audit { color: #67e8f9; background: rgba(103,232,249,.12); border: 1px solid rgba(103,232,249,.3); }
  .d-sug-bio { display: block; font-size: 11.5px; color: var(--text3); margin-top: 3px; }
  .d-sug-btn {
    flex-shrink: 0; font-size: 12px; font-weight: 700; color: #fff; padding: 6px 12px;
    border-radius: 999px; background: var(--grad); cursor: pointer;
  }
  .d-sug-btn.on { background: rgba(255,255,255,.08); color: var(--text2); border: 1px solid var(--line); }
  .d-sug-empty { font-size: 12.5px; color: var(--text3); text-align: center; padding: 10px 0; }
  .d-foot { text-align: center; padding: 4px 0; }
  .d-foot-link { display: block; font-size: 11.5px; color: var(--text3); }
  .d-foot-copy { display: block; font-size: 11px; color: var(--text3); opacity: .7; margin-top: 6px; }
}
/* #endif */
</style>
