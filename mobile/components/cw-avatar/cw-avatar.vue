<template>
  <view
    class="cw-avatar hover-press"
    :class="{ ring: ring, online: online }"
    :style="{ width: size + 'rpx', height: size + 'rpx' }"
    @click.stop="onTap"
  >
    <image
      class="cw-avatar__img"
      :src="fixed || '/static/default-avatar.png'"
      mode="aspectFill"
      lazy-load
      @error="onError"
    />
    <view v-if="badge" class="cw-avatar__badge">{{ badge > 99 ? '99+' : badge }}</view>
  </view>
</template>

<script>
import { mediaUrl } from '@/utils/api.js'
export default {
  name: 'cw-avatar',
  props: {
    src: { type: String, default: '' },
    size: { type: Number, default: 80 },
    // 点击后跳转的用户 id；传 0/不传则仅触发 @tap
    userId: { type: [Number, String], default: 0 },
    ring: { type: Boolean, default: false },
    online: { type: Boolean, default: false },
    badge: { type: Number, default: 0 },
  },
  computed: {
    fixed() { return mediaUrl(this.src) },
  },
  methods: {
    onError(e) { /* 兜底走默认头像 */ },
    onTap() {
      this.$emit('tap')
      const id = Number(this.userId)
      if (id > 0) {
        uni.navigateTo({ url: `/pages/user/profile?id=${id}` })
      }
    },
  },
}
</script>

<style scoped>
.cw-avatar {
  position: relative; border-radius: 50%; overflow: visible; flex-shrink: 0;
  background: #e9ebf3;
}
.cw-avatar__img { width: 100%; height: 100%; border-radius: 50%; background: #e9ebf3; }
.cw-avatar.ring::before {
  content: ''; position: absolute; inset: -5rpx; border-radius: 50%;
  background: var(--grad); z-index: -1;
}
.cw-avatar__badge {
  position: absolute; top: -6rpx; right: -6rpx; min-width: 30rpx; height: 30rpx;
  padding: 0 8rpx; border-radius: 30rpx; background: var(--accent-deep); color: #fff;
  font-size: 20rpx; line-height: 30rpx; text-align: center; border: 3rpx solid #fff;
}
</style>
