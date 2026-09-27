<template>
  <view class="page" :class="cwRootClass">
    <view class="tabs">
      <view class="tab" :class="{ on: status === 'pending' }" @click="switchTab('pending')">待处理</view>
      <view class="tab" :class="{ on: status === 'approved' }" @click="switchTab('approved')">已处理</view>
      <view class="tab" :class="{ on: status === 'rejected' }" @click="switchTab('rejected')">已驳回</view>
    </view>

    <view class="empty" v-if="!loading && list.length === 0">暂无举报</view>

    <view class="rcard card anim-up" v-for="r in list" :key="r.id">
      <view class="row between">
        <view class="row gap">
          <text class="tag tag-red">{{ r.reason_text }}</text>
          <text class="tag tag-gray">{{ typeText(r.target_type) }}</text>
          <text class="tag tag-green" v-if="r.status === 'pending'">待处理</text>
        </view>
        <text class="small muted">{{ fmt(r.created_at) }}</text>
      </view>
      <view class="snapshot muted" v-if="r.snapshot">"{{ r.snapshot }}"</view>
      <view class="detail" v-if="r.detail">补充：{{ r.detail }}</view>
      <view class="muted small mt">举报人：{{ r.reporter_name || '匿名' }}</view>
      <view class="actions" v-if="r.status === 'pending'">
        <button class="btn btn-ghost act" @click="handle(r, 'rejected')">驳回</button>
        <button class="btn btn-danger act" @click="handle(r, 'approved')">删除内容</button>
      </view>
      <view class="muted small" v-else>处理结果：{{ r.status === 'approved' ? '已处理' : '已驳回' }}</view>
    </view>
  </view>
</template>

<script>
import { api } from '@/utils/api.js'
export default {
  data() {
    return { status: 'pending', list: [], loading: false }
  },
  onLoad() { this.load() },
  methods: {
    fmt(t) { return t ? String(t).replace('T', ' ').slice(0, 16) : '' },
    typeText(t) { return { post: '帖子', comment: '评论', user: '用户', message: '私信' }[t] || t },
    switchTab(s) { if (s === this.status) return; this.status = s; this.list = []; this.load() },
    async load() {
      this.loading = true
      try {
        const d = await api.reviewReports({ status: this.status, page: 1, page_size: 30 })
        this.list = d.items || []
      } catch (e) {
      } finally { this.loading = false }
    },
    async handle(r, status) {
      let ban = false
      if (status === 'approved') {
        const res = await uni.showModal({
          title: '处理举报',
          content: '确定删除被举报内容？',
          confirmText: '删除',
        }).catch(() => ({ confirm: false }))
        if (!res.confirm) return
      } else {
        const res = await uni.showModal({ title: '驳回举报', content: '确定驳回该举报？' }).catch(() => ({ confirm: false }))
        if (!res.confirm) return
      }
      try {
        const d = await api.reviewHandleReport(r.id, { status, ban_user: ban })
        uni.showToast({ title: d.msg || '处理完成', icon: 'none' })
        this.list = this.list.filter((x) => x.id !== r.id)
      } catch (e) {}
    },
  },
}
</script>

<style  scoped>
.tabs { display: flex; gap: 14rpx; margin-bottom: 24rpx; }
.tab { padding: 14rpx 28rpx; border-radius: 999rpx; background: rgba(255,255,255,.06); color: var(--text2); border: 1rpx solid var(--line); font-size: 25rpx; }
.tab.on { background: var(--grad); color: #fff; border-color: transparent; }
.snapshot { margin-top: 16rpx; padding: 16rpx; background: rgba(255,255,255,.04); border-radius: 14rpx; font-size: 26rpx; line-height: 1.6; }
.detail { margin-top: 12rpx; color: var(--text2); font-size: 26rpx; }
.actions { display: flex; gap: 16rpx; margin-top: 20rpx; }
.act { height: 72rpx; font-size: 26rpx; flex: 1; }
</style>
