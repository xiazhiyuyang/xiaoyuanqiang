<template>
  <view class="page" :class="cwRootClass">
    <view class="hero card anim-pop">
      <view class="hero-badge">🛡️</view>
      <view>
        <view class="hero-title galaxy-text">审查中心</view>
        <view class="muted small mt">你已被管理员授予审查权限，协助维护社区环境。审查操作会被记录。</view>
      </view>
    </view>

    <view class="grid stagger">
      <view class="entry" v-if="access.content_review" @click="go('/pages/review/posts')">
        <view class="entry-ic" style="background:linear-gradient(135deg,#8b7cf6,#6ee7ff)">📝</view>
        <view class="entry-name">内容审查</view>
        <view class="entry-sub">待审帖子 {{ overview.pending_posts }}</view>
        <view class="entry-badge" v-if="overview.pending_posts">{{ overview.pending_posts }}</view>
      </view>
      <view class="entry" v-if="access.report_review" @click="go('/pages/review/reports')">
        <view class="entry-ic" style="background:linear-gradient(135deg,#e879f9,#8b7cf6)">🚩</view>
        <view class="entry-name">举报审查</view>
        <view class="entry-sub">待处理举报 {{ overview.pending_reports }}</view>
        <view class="entry-badge" v-if="overview.pending_reports">{{ overview.pending_reports }}</view>
      </view>
    </view>

    <view class="card anim-up" v-if="!access.content_review && !access.report_review">
      <view class="empty">你当前没有任何审查权限，请联系管理员授权。</view>
    </view>

    <view class="card note anim-up">
      <view class="note-title">权限说明</view>
      <view class="muted small" style="line-height:1.8">
        · 审查权限由管理员单独授予，仅能访问被授权的审查页面；<br />
        · 审查员不能登录管理后台，也不能管理用户、设置等；<br />
        · 所有通过、删除、处理举报的操作均留痕可查。
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '@/utils/api.js'
export default {
  data() {
    return {
      access: { content_review: false, report_review: false },
      overview: { pending_posts: 0, pending_reports: 0 },
    }
  },
  onShow() { this.load() },
  methods: {
    go(url) { uni.navigateTo({ url }) },
    async load() {
      try {
        const [a, o] = await Promise.all([
          api.getReviewAccess().catch(() => null),
          api.reviewOverview().catch(() => null),
        ])
        if (a) this.access = a
        if (o) this.overview = o
      } catch (e) {}
    },
  },
}
</script>

<style  scoped>
.hero { display: flex; gap: 24rpx; align-items: center; }
.hero-badge { font-size: 56rpx; }
.hero-title { font-size: 40rpx; font-weight: 800; }
.grid { display: flex; gap: 24rpx; margin-bottom: 24rpx; }
.entry {
  flex: 1; position: relative; background: var(--card); border: 1rpx solid var(--line);
  border-radius: 28rpx; padding: 32rpx 24rpx; backdrop-filter: blur(18rpx);
  box-shadow: var(--shadow);
}
.entry-ic { width: 88rpx; height: 88rpx; border-radius: 24rpx; display: flex; align-items: center; justify-content: center; font-size: 44rpx; margin-bottom: 18rpx; }
.entry-name { font-weight: 700; font-size: 32rpx; }
.entry-sub { color: var(--text2); font-size: 24rpx; margin-top: 8rpx; }
.entry-badge { position: absolute; top: 24rpx; right: 24rpx; min-width: 38rpx; height: 38rpx; padding: 0 10rpx; border-radius: 999rpx; background: linear-gradient(135deg,#fb7185,#f43f5e); color: #fff; font-size: 22rpx; display: flex; align-items: center; justify-content: center; }
.note-title { font-weight: 700; margin-bottom: 12rpx; }
</style>
