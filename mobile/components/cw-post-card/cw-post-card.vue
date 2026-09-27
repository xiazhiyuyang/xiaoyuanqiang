<template>
  <view class="card cw-card anim-up hover-press" @click="open">
    <!-- 作者行 -->
    <view class="card__head">
      <cw-avatar
        :src="avatar"
        :user-id="anonymous ? 0 : (post.author?.id || post.user_id || 0)"
        :size="72"
        @tap="onUser"
      />
      <view class="card__headinfo">
        <view class="card__name-row">
          <text class="card__name">{{ anonymous ? '匿名同学' : (post.author?.nickname || '同学') }}</text>
          <text
            v-if="levelBadge && showLevel"
            class="card__lv"
            :style="{ color: levelBadge.color, borderColor: levelBadge.color + '66', background: levelBadge.color + '1a' }"
          >Lv{{ levelBadge.level }} · {{ levelBadge.name }}</text>
          <text
            v-for="t in staffLabels" :key="t.label"
            class="card__staff" :class="t.cls"
          >{{ t.label }}</text>
        </view>
        <view class="card__sub">
          <text v-if="catName" class="card__tag">{{ catName }}</text>
          <text class="card__time">{{ post.created_at_text || timeText }}</text>
        </view>
      </view>
      <!-- 本人帖子：编辑/删除入口 -->
      <view v-if="canManage" class="card__manage hover-press" @click.stop="manage">⋯</view>
      <!-- 关注按钮：非匿名、非本人、未关注时展示 -->
      <view
        v-else-if="canFollow" class="card__follow hover-press"
        :class="{ on: post.author?.is_following }"
        @click.stop="onFollow"
      >{{ post.author?.is_following ? '已关注' : '+ 关注' }}</view>
      <view v-else-if="post.is_top" class="card__top">置顶</view>
    </view>

    <!-- 正文 -->
    <view v-if="post.title" class="card__title">{{ post.title }}</view>
    <view class="card__content cw-ellipsis-2">{{ post.content }}</view>

    <!-- 视频 -->
    <view v-if="post.video_url" class="card__video" @click.stop="open">
      <video
        v-if="playInline"
        :src="videoSrc"
        class="card__video-el"
        object-fit="cover"
        :controls="false"
        :show-center-play-btn="false"
        :show-play-btn="false"
        :enable-progress-gesture="false"
        @click="open"
      />
      <view v-else class="card__video-ph">
        <view class="card__play">▶</view>
        <text>视频动态</text>
      </view>
    </view>

    <!-- 图片 -->
    <view v-else-if="imgs.length" class="card__imgs" :class="'n' + colClass">
      <image
        v-for="(img, i) in showImgs" :key="i"
        :src="img" mode="aspectFill" class="card__img"
        lazy-load @click.stop="preview(i)"
      />
    </view>

    <!-- 操作栏 -->
    <view class="card__bar">
      <view class="card__stat"><text class="ico">👁</text>{{ post.view_count || 0 }}</view>
      <view class="card__actions">
        <view class="card__act" @click.stop="toggleLike">
          <text class="ico" :class="{ liked: post.is_liked, 'heart-pop': pop }">{{ post.is_liked ? '❤️' : '🤍' }}</text>
          <text :class="{ liked: post.is_liked }">{{ post.like_count || 0 }}</text>
        </view>
        <view class="card__act" @click.stop="open">
          <text class="ico">💬</text>{{ post.comment_count || 0 }}
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { api, mediaUrl } from '@/utils/api.js'
export default {
  name: 'cw-post-card',
  props: {
    post: { type: Object, required: true },
    catMap: { type: Object, default: () => ({}) },
  },
  data() {
    let myId = 0
    try { myId = JSON.parse(uni.getStorageSync('userInfo') || 'null')?.id || 0 } catch (e) {}
    return { pop: false, playInline: false, myId }
  },
  computed: {
    anonymous() { return !!this.post.is_anonymous },
    staffLabels() {
      if (this.anonymous) return []
      const tags = this.post.author?.staff_tags
        || (this.post.author?.role === 'admin' ? ['admin'] : [])
      const map = {
        admin: { label: '管理员', cls: 'staff-admin' },
        content_review: { label: '审核员', cls: 'staff-review' },
        report_review: { label: '审查员', cls: 'staff-audit' },
      }
      return tags.map((t) => map[t]).filter(Boolean)
    },
    canFollow() {
      const a = this.post.author
      if (this.anonymous || !a || !a.id) return false
      if (this.myId && a.id === this.myId) return false
      return true
    },
    // 本人的非匿名帖：显示「编辑/删除」入口（匿名帖在列表不暴露作者身份，请到详情页管理）
    canManage() {
      if (!this.myId || this.anonymous) return false
      const ownerId = this.post.author?.id || this.post.user_id
      return ownerId === this.myId
    },
    levelBadge() { return this.post.level_badge || this.post.author?.level_name ? (this.post.level_badge || {
      level: this.post.author?.level, name: this.post.author?.level_name, color: this.post.author?.level_color || '#8b7cf6',
    }) : null },
    showLevel() {
      try {
        const cfg = JSON.parse(uni.getStorageSync('public_settings') || '{}')
        return cfg.show_level !== false
      } catch (e) { return true }
    },
    avatar() { return this.anonymous ? '' : (this.post.author?.avatar || '') },
    catName() {
      const c = this.post.category
      if (c?.name) return c.name
      return this.catMap[this.post.category_id] || ''
    },
    timeText() {
      const t = this.post.created_at
      if (!t) return ''
      const d = new Date(String(t).replace(/-/g, '/'))
      const diff = (Date.now() - d.getTime()) / 1000
      if (isNaN(diff)) return ''
      if (diff < 60) return '刚刚'
      if (diff < 3600) return Math.floor(diff / 60) + '分钟前'
      if (diff < 86400) return Math.floor(diff / 3600) + '小时前'
      if (diff < 86400 * 7) return Math.floor(diff / 86400) + '天前'
      return String(t).slice(0, 10)
    },
    imgs() { return (this.post.images || []).map((i) => mediaUrl(i.url || i)).filter(Boolean) },
    videoSrc() { return mediaUrl(this.post.video_url) },
    showImgs() { return this.imgs.slice(0, 9) },
    colClass() {
      const n = this.imgs.length
      if (n === 1) return 1
      if (n === 2 || n === 4) return 2
      return 3
    },
  },
  methods: {
    onFollow() { this.$emit('follow', this.post) },
    manage() {
      uni.showActionSheet({
        itemList: ['编辑', '删除'],
        success: ({ tapIndex }) => {
          if (tapIndex === 0) {
            uni.navigateTo({ url: `/pages/post/edit?id=${this.post.id}` })
          } else if (tapIndex === 1) {
            this.confirmDelete()
          }
        },
      })
    },
    confirmDelete() {
      uni.showModal({
        title: '删除帖子',
        content: '确定删除这条动态吗？删除后不可恢复。',
        confirmText: '删除',
        confirmColor: '#f43f5e',
        success: async (r) => {
          if (!r.confirm) return
          try {
            await api.deletePost(this.post.id)
            uni.$emit('campus:post-deleted', this.post.id)
            this.$emit('deleted', this.post)
            uni.showToast({ title: '已删除', icon: 'none' })
          } catch (e) { /* request 已统一提示 */ }
        },
      })
    },
    open() { this.$emit('open', this.post); uni.navigateTo({ url: `/pages/post/detail?id=${this.post.id}` }) },
    onUser() {
      if (this.anonymous) return
      this.$emit('user', this.post)
    },
    preview(i) {
      uni.previewImage({ urls: this.imgs, current: this.imgs[i] })
    },
    toggleLike() {
      this.post.is_liked = !this.post.is_liked
      this.post.like_count += this.post.is_liked ? 1 : -1
      if (this.post.is_liked) { this.pop = true; setTimeout(() => (this.pop = false), 450) }
      this.$emit('like', this.post)
    },
  },
}
</script>

<style scoped>
.card { padding: 28rpx; margin-bottom: 22rpx; }
.card__head { display: flex; align-items: center; }
.card__headinfo { flex: 1; margin-left: 18rpx; min-width: 0; }
.card__name-row { display: flex; align-items: center; gap: 12rpx; min-width: 0; }
.card__name { font-size: 28rpx; font-weight: 600; color: var(--ink); flex-shrink: 0; }
.card__lv {
  font-size: 18rpx; font-weight: 700; line-height: 1; padding: 6rpx 12rpx;
  border-radius: 999rpx; border: 1rpx solid; white-space: nowrap; flex-shrink: 0;
}
.card__staff {
  font-size: 18rpx; font-weight: 700; line-height: 1; padding: 6rpx 12rpx;
  border-radius: 999rpx; white-space: nowrap; flex-shrink: 0; border: 1rpx solid;
}
.staff-admin { color: #fde68a; background: rgba(251,191,36,.16); border-color: rgba(251,191,36,.4); }
.staff-review { color: #a5b4fc; background: rgba(139,124,246,.16); border-color: rgba(139,124,246,.4); }
.staff-audit { color: #67e8f9; background: rgba(103,232,249,.12); border-color: rgba(103,232,249,.35); }
.card__follow {
  flex-shrink: 0; margin-left: 12rpx; font-size: 22rpx; font-weight: 700;
  color: #fff; background: var(--grad); padding: 10rpx 22rpx; border-radius: 999rpx;
  box-shadow: 0 6rpx 16rpx rgba(139,124,246,.35);
}
.card__follow.on { background: rgba(255,255,255,.08); color: var(--ink-3); box-shadow: none; border: 1rpx solid var(--line); }
.card__manage {
  flex-shrink: 0; margin-left: 12rpx; width: 60rpx; height: 60rpx;
  display: flex; align-items: center; justify-content: center;
  font-size: 40rpx; line-height: 1; color: var(--ink-3);
  background: rgba(255,255,255,.06); border: 1rpx solid var(--line); border-radius: 50%;
}
.card__sub { display: flex; align-items: center; margin-top: 4rpx; }
.card__tag {
  font-size: 20rpx; color: var(--brand-deep); background: var(--brand-soft);
  padding: 2rpx 14rpx; border-radius: 20rpx; margin-right: 12rpx;
}
.card__time { font-size: 22rpx; color: var(--ink-3); }
.card__top {
  font-size: 20rpx; color: #fff; background: var(--grad-warm);
  padding: 4rpx 14rpx; border-radius: 8rpx;
}
.card__title { font-size: 32rpx; font-weight: 700; margin: 20rpx 0 10rpx; line-height: 1.4; }
.card__content { font-size: 28rpx; color: var(--ink-2); line-height: 1.6; }
.card__imgs { margin-top: 18rpx; display: flex; flex-wrap: wrap; gap: 8rpx; }
.card__img { background: #eceef5; border-radius: 14rpx; }
.n1 .card__img { width: 100%; max-height: 440rpx; }
.n2 .card__img { width: calc(50% - 4rpx); height: 280rpx; }
.n3 .card__img { width: calc(33.33% - 6rpx); height: 200rpx; }
.card__video {
  margin-top: 18rpx; border-radius: 18rpx; overflow: hidden;
  height: 380rpx; background: #000;
}
.card__video-el { width: 100%; height: 100%; }
.card__video-ph {
  width: 100%; height: 100%; display: flex; flex-direction: column;
  align-items: center; justify-content: center; color: #fff;
  background: linear-gradient(135deg, #4f46e5, #7c3aed); gap: 16rpx; font-size: 26rpx;
}
.card__play {
  width: 96rpx; height: 96rpx; border-radius: 50%; background: rgba(255,255,255,.92);
  color: var(--brand-deep); display: flex; align-items: center; justify-content: center;
  font-size: 38rpx; padding-left: 8rpx; box-shadow: 0 8rpx 24rpx rgba(0,0,0,.25);
}
.card__bar { display: flex; align-items: center; justify-content: space-between; margin-top: 22rpx; }
.card__stat { font-size: 24rpx; color: var(--ink-3); }
.card__actions { display: flex; gap: 36rpx; }
.card__act { display: flex; align-items: center; font-size: 24rpx; color: var(--ink-2); }
.card__act .ico { margin-right: 8rpx; font-size: 30rpx; }
.card__act .liked { color: var(--accent-deep); }
.ico { display: inline-block; }
</style>
