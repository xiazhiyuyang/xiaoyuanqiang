<template>
  <view class="page" :class="cwRootClass">
    <!-- 未登录 -->
    <view class="card login-card anim-pop" v-if="!userStore.isLoggedIn">
      <view class="guest-avatar floaty">🌌</view>
      <view class="galaxy-text welcome">登录后解锁完整星轨</view>
      <view class="muted small mt">发帖 · 私信 · 等级成长 · 社区互动</view>
      <button class="btn mt" @click="go('/pages/login/login')">登录 / 注册</button>
    </view>

    <block v-else>
      <!-- 用户星云卡 -->
      <view class="hero card anim-pop">
        <image class="avatar" :src="avatarUrl" mode="aspectFill" @click="editProfile" />
        <view class="hero-main">
          <view class="row gap">
            <text class="nick">{{ user.nickname }}</text>
            <text v-if="myStaffLabel" class="my-staff">{{ myStaffLabel }}</text>
            <text class="lv-chip" :style="{ color: level.color, borderColor: level.color + '88', background: level.color + '18' }">
              Lv{{ user.level || 1 }} {{ level.name }}
            </text>
          </view>
          <view class="muted small mt">@{{ user.username }}</view>
          <view class="exp-bar mt" @click="go('/pages/level/level')">
            <view class="exp-fill" :style="{ width: level.progress + '%', background: 'linear-gradient(90deg,' + level.color + ',#6ee7ff)' }"></view>
          </view>
          <view class="row between small muted mt">
            <text>经验 {{ user.exp || 0 }}</text>
            <text>{{ level.is_max ? '已满级' : '距下一级 ' + level.remain }}</text>
          </view>
        </view>
      </view>

      <!-- 数据统计 -->
      <view class="stats card anim-up">
        <view class="stat" @click="openMine('posts')"><text class="num">{{ stats.post_count }}</text><text class="lbl">动态</text></view>
        <view class="stat" @click="openMyFollows('following')"><text class="num">{{ stats.following_count || 0 }}</text><text class="lbl">关注</text></view>
        <view class="stat" @click="openMyFollows('followers')"><text class="num">{{ stats.followers_count || 0 }}</text><text class="lbl">粉丝</text></view>
        <view class="stat"><text class="num">{{ stats.like_count }}</text><text class="lbl">获赞</text></view>
        <view class="stat" @click="openMine('favs')"><text class="num">{{ stats.favorite_count }}</text><text class="lbl">收藏</text></view>
      </view>

      <!-- 审查入口（仅被授权用户可见） -->
      <view class="card review-entry anim-up" v-if="reviewAccess.content_review || reviewAccess.report_review" @click="go('/pages/review/center')">
        <view class="review-ic">🛡️</view>
        <view class="review-main">
          <view class="review-name">审查中心</view>
          <view class="muted small">你已被授权协助审查社区内容</view>
        </view>
        <view class="review-badge" v-if="reviewPending">{{ reviewPending }}</view>
        <text class="chev">›</text>
      </view>

      <!-- 功能宫格 -->
      <view class="card anim-up">
        <view class="grid">
          <view class="g-item" @click="go('/pages/profile/edit')"><text class="g-ic">✏️</text><text>编辑资料</text></view>
          <view class="g-item" @click="openMine('posts')"><text class="g-ic">📝</text><text>发布/收藏</text></view>
          <view class="g-item" @click="go('/pages/level/level')"><text class="g-ic">✨</text><text>我的等级</text></view>
          <view class="g-item" @click="go('/pages/notifications/list')"><text class="g-ic">🔔</text><text>互动消息</text></view>
        </view>
      </view>

      <!-- 设置与服务 -->
      <view class="card list anim-up">
        <view class="list-item" @click="go('/pages/settings/settings')">
          <text class="li-ic">🎨</text><text class="li-name">设置</text><text class="chev">›</text>
        </view>
        <view class="list-item" v-if="user.role === 'admin'" @click="goAdmin">
          <text class="li-ic">🛠️</text><text class="li-name">管理员后台</text><text class="chev">›</text>
        </view>
      </view>

      <button class="btn btn-ghost logout" @click="logout">退出登录</button>
    </block>
  </view>
</template>

<script>
import { useUserStore } from '@/stores/user.js'
import { api, mediaUrl, DEFAULT_AVATAR } from '@/utils/api.js'
export default {
  data() {
    return {
      stats: { post_count: 0, like_count: 0, comment_count: 0, favorite_count: 0, followers_count: 0, following_count: 0 },
      reviewAccess: { content_review: false, report_review: false },
      reviewPending: 0,
    }
  },
  computed: {
    userStore() { return useUserStore() },
    user() { return this.userStore.userInfo || {} },
    avatarUrl() { return this.user.avatar ? mediaUrl(this.user.avatar) : DEFAULT_AVATAR },
    level() {
      const exp = this.user.exp || 0
      const ladder = [
        [1, '星尘', 0], [2, '流星', 30], [3, '彗星', 100], [4, '行星', 240],
        [5, '恒星', 500], [6, '星云', 900], [7, '银河', 1500], [8, '星穹', 2400],
        [9, '超新星', 3800], [10, '宇宙之心', 6000],
      ]
      const colors = ['#94a3b8','#38bdf8','#22d3ee','#34d399','#fbbf24','#a78bfa','#818cf8','#e879f9','#fb7185','#f59e0b']
      let lv = 0
      for (let i = 0; i < ladder.length; i++) if (exp >= ladder[i][2]) lv = i
      const cur = ladder[lv], next = ladder[lv + 1]
      const span = next ? next[2] - cur[2] : 1
      const progress = next ? Math.min(100, Math.round((exp - cur[2]) / span * 100)) : 100
      return {
        level: cur[0], name: cur[1], color: colors[lv], progress,
        remain: next ? next[2] - exp : 0, is_max: !next,
      }
    },
    myStaffLabel() {
      const u = this.user || {}
      if (u.role === 'admin') return '管理员'
      const perms = u.perms || []
      if (perms.includes('content_review')) return '审核员'
      if (perms.includes('report_review')) return '审查员'
      return ''
    },
  },
  onShow() {
    if (this.userStore.isLoggedIn) {
      this.refreshMe()
      this.loadOverview()
      this.loadReview()
    }
  },
  onPullDownRefresh() {
    Promise.all([this.refreshMe(), this.loadOverview(), this.loadReview()]).finally(() => uni.stopPullDownRefresh())
  },
  methods: {
    mediaUrl,
    go(url) { uni.navigateTo({ url }) },
    openMyFollows(type) { uni.navigateTo({ url: `/pages/user/follows?type=${type}` }) },
    openMine(tab) { uni.navigateTo({ url: `/pages/profile/mine?tab=${tab}` }) },
    async refreshMe() {
      try {
        const me = await api.getMe()
        this.userStore.setUser(me)
      } catch (e) {}
    },
    async loadOverview() {
      try {
        const d = await api.getMyOverview()
        this.stats = d.stats
      } catch (e) {}
    },
    async loadReview() {
      try {
        const a = await api.getReviewAccess()
        this.reviewAccess = a
        if (a.content_review || a.report_review) {
          const o = await api.reviewOverview()
          this.reviewPending = (o.pending_posts || 0) + (o.pending_reports || 0)
        }
      } catch (e) {}
    },
    editProfile() { uni.navigateTo({ url: '/pages/profile/edit' }) },
    goAdmin() {
      // #ifdef H5
      window.open('/admin/', '_blank')
      // #endif
    },
    logout() {
      uni.showModal({
        title: '提示', content: '确定退出登录吗？',
        success: (res) => {
          if (res.confirm) {
            this.userStore.logout()
            this.stats = { post_count: 0, like_count: 0, comment_count: 0, favorite_count: 0, followers_count: 0, following_count: 0 }
            uni.showToast({ title: '已退出', icon: 'none' })
          }
        },
      })
    },
  },
}
</script>

<style  scoped>
.login-card { text-align: center; padding: 60rpx 32rpx; }
.guest-avatar { font-size: 90rpx; }
.welcome { font-size: 38rpx; font-weight: 800; margin-top: 16rpx; }
.hero { display: flex; gap: 26rpx; align-items: center; }
.avatar { width: 128rpx; height: 128rpx; border-radius: 50%; border: 3rpx solid rgba(139,124,246,.6); box-shadow: 0 0 30rpx rgba(139,124,246,.5); }
.hero-main { flex: 1; min-width: 0; }
.nick { font-size: 38rpx; font-weight: 800; }
.lv-chip { font-size: 20rpx; padding: 4rpx 14rpx; border-radius: 999rpx; border: 1rpx solid; font-weight: 700; }
.my-staff { font-size: 20rpx; font-weight: 700; padding: 4rpx 14rpx; border-radius: 999rpx; color: #fde68a; background: rgba(251,191,36,.16); border: 1rpx solid rgba(251,191,36,.4); }
.exp-bar { height: 12rpx; border-radius: 999rpx; background: rgba(255,255,255,.08); overflow: hidden; }
.exp-fill { height: 100%; border-radius: 999rpx; transition: width .6s; box-shadow: 0 0 12rpx rgba(139,124,246,.7); }
.stats { display: flex; }
.stat { flex: 1; text-align: center; display: flex; flex-direction: column; gap: 8rpx; }
.num { font-size: 38rpx; font-weight: 800; background: linear-gradient(120deg,#c4b5fd,#6ee7ff); -webkit-background-clip: text; background-clip: text; color: transparent; }
.lbl { font-size: 23rpx; color: var(--text2); }
.review-entry { display: flex; align-items: center; gap: 20rpx; }
.review-ic { font-size: 48rpx; }
.review-main { flex: 1; }
.review-name { font-weight: 700; font-size: 30rpx; }
.review-badge { min-width: 36rpx; height: 36rpx; padding: 0 10rpx; border-radius: 999rpx; background: linear-gradient(135deg,#fb7185,#f43f5e); color: #fff; font-size: 22rpx; display: flex; align-items: center; justify-content: center; }
.grid { display: flex; flex-wrap: wrap; }
.g-item { width: 33.33%; display: flex; flex-direction: column; align-items: center; gap: 12rpx; padding: 26rpx 0; color: var(--text); font-size: 25rpx; }
.g-ic { font-size: 46rpx; }
.list-item { display: flex; align-items: center; gap: 18rpx; padding: 10rpx 0; }
.li-ic { font-size: 38rpx; }
.li-name { flex: 1; font-weight: 600; }
.chev { color: var(--text3); font-size: 40rpx; }
.logout { margin-top: 10rpx; }
</style>
