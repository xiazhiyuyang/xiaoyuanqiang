<template>
  <view class="page" :class="cwRootClass">
    <view class="tabs">
      <view class="tab" :class="{ on: status === 'pending' }" @click="switchTab('pending')">待审核</view>
      <view class="tab" :class="{ on: status === 'published' }" @click="switchTab('published')">已发布</view>
    </view>

    <view class="empty" v-if="!loading && list.length === 0">暂无内容</view>

    <view class="pcard card anim-up" v-for="p in list" :key="p.id">
      <view class="row between">
        <view class="row gap">
          <text class="tag" v-if="p.category_name">{{ p.category_name }}</text>
          <text class="tag tag-cyan" v-if="p.is_anonymous">匿名</text>
        </view>
        <text class="small muted">{{ fmt(p.created_at) }}</text>
      </view>
      <view class="p-title">{{ p.title }}</view>
      <view class="p-content">{{ p.content }}</view>
      <view class="imgs" v-if="p.images && p.images.length">
        <image v-for="(img, i) in p.images" :key="i" :src="mediaUrl(img)" mode="aspectFill" class="p-img" @click="preview(p.images, i)" />
      </view>
      <view class="p-meta muted small mt">作者：{{ p.author_name }} · 👍 {{ p.like_count }} · 👀 {{ p.view_count }}</view>
      <view class="actions">
        <button class="btn btn-ghost act" @click="act(p, 'remove')">删除违规</button>
        <button class="btn act" v-if="p.status === 'pending'" @click="act(p, 'approve')">通过</button>
      </view>
    </view>

    <view class="loadmore muted small" v-if="list.length">— 已加载全部 —</view>
  </view>
</template>

<script>
import { api, mediaUrl } from '@/utils/api.js'
export default {
  data() {
    return { status: 'pending', list: [], loading: false, page: 1 }
  },
  onLoad() { this.load() },
  onReachBottom() {},
  methods: {
    mediaUrl,
    fmt(t) { return t ? String(t).replace('T', ' ').slice(0, 16) : '' },
    preview(imgs, i) {
      uni.previewImage({ urls: imgs.map(mediaUrl), current: i })
    },
    switchTab(s) { if (s === this.status) return; this.status = s; this.list = []; this.load() },
    async load() {
      this.loading = true
      try {
        const d = await api.reviewPosts({ status: this.status, page: 1, page_size: 30 })
        this.list = d.items || []
      } catch (e) {
      } finally { this.loading = false }
    },
    async act(p, action) {
      const word = action === 'approve' ? '通过' : '删除'
      const { confirm } = await uni.showModal({ title: '确认操作', content: `确定${word}这条内容？` }).catch(() => ({ confirm: false }))
      if (!confirm) return
      try {
        await api.reviewPostAction(p.id, action)
        uni.showToast({ title: '已' + word, icon: 'success' })
        this.list = this.list.filter((x) => x.id !== p.id)
      } catch (e) {}
    },
  },
}
</script>

<style  scoped>
.tabs { display: flex; gap: 16rpx; margin-bottom: 24rpx; }
.tab { padding: 14rpx 36rpx; border-radius: 999rpx; background: rgba(255,255,255,.06); color: var(--text2); border: 1rpx solid var(--line); font-size: 26rpx; }
.tab.on { background: var(--grad); color: #fff; border-color: transparent; box-shadow: var(--glow); }
.p-title { font-size: 32rpx; font-weight: 700; margin: 16rpx 0 10rpx; }
.p-content { color: var(--text2); font-size: 27rpx; line-height: 1.7; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
.imgs { display: flex; flex-wrap: wrap; gap: 12rpx; margin-top: 16rpx; }
.p-img { width: 180rpx; height: 180rpx; border-radius: 16rpx; }
.actions { display: flex; gap: 16rpx; margin-top: 20rpx; }
.act { height: 72rpx; font-size: 26rpx; flex: 1; }
.loadmore { text-align: center; padding: 30rpx 0; }
</style>
