<template>
  <view class="splash" :style="{ paddingTop: statusBar + 'px' }" @click="enter">
    <!-- 背景柔光装饰 -->
    <view class="glow glow-a" />
    <view class="glow glow-b" />
    <view class="glow glow-c" />

    <!-- 中部品牌区 -->
    <view class="brand">
      <image class="logo anim-pop floaty" src="/static/logo.png" mode="aspectFit" />
      <text class="app-name anim-up delay-1">{{ siteName }}</text>
      <text class="slogan anim-up delay-2">在这里，遇见同频的校园生活</text>
    </view>

    <!-- 底部加载与版本 -->
    <view class="foot" :style="{ paddingBottom: (safeBottom + 16) + 'px' }">
      <view class="dots">
        <view class="dot d1" />
        <view class="dot d2" />
        <view class="dot d3" />
      </view>
      <text class="ver" v-if="version">v{{ version }}</text>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      statusBar: 20,
      safeBottom: 0,
      siteName: '校园墙',
      version: '',
      gone: false,
      timer: null,
    }
  },
  onLoad() {
    try {
      const info = uni.getSystemInfoSync()
      this.statusBar = info.statusBarHeight || 20
      this.safeBottom = (info.safeAreaInsets && info.safeAreaInsets.bottom) || 0
      const sn = uni.getStorageSync('site_name')
      if (sn) this.siteName = sn
    } catch (e) { /* 用默认值 */ }

    // #ifdef APP-PLUS
    try {
      plus.runtime.getProperty(plus.runtime.appid, (w) => {
        if (w && w.version) this.version = w.version
      })
    } catch (e) { /* 忽略 */ }
    const hold = 1500 // App 端品牌页停留，保证露出且不拖沓
    // #endif
    // #ifdef H5
    const hold = 700 // 网页端快速进入，避免刷新时久等
    // #endif
    // #ifdef MP-WEIXIN
    const hold = 1000
    // #endif

    this.timer = setTimeout(() => this.enter(), hold)
  },
  onUnload() {
    if (this.timer) clearTimeout(this.timer)
  },
  methods: {
    enter() {
      if (this.gone) return
      this.gone = true
      if (this.timer) clearTimeout(this.timer)
      uni.reLaunch({ url: '/pages/index/index' })
    },
  },
}
</script>

<style scoped>
.splash {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: hidden;
  background: linear-gradient(160deg, #6366f1 0%, #7c6cf0 46%, #9a5cf0 100%);
}
/* 柔光圆，增加层次 */
.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(8rpx);
  opacity: 0.5;
  pointer-events: none;
}
.glow-a {
  width: 460rpx; height: 460rpx;
  top: -120rpx; right: -140rpx;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.35), rgba(255, 255, 255, 0) 70%);
}
.glow-b {
  width: 380rpx; height: 380rpx;
  bottom: 60rpx; left: -130rpx;
  background: radial-gradient(circle, rgba(167, 139, 250, 0.55), rgba(167, 139, 250, 0) 70%);
}
.glow-c {
  width: 240rpx; height: 240rpx;
  top: 30%; left: 12%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0) 70%);
}

.brand {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-top: -40rpx;
}
.logo {
  width: 208rpx;
  height: 208rpx;
  border-radius: 46rpx;
  box-shadow: 0 18rpx 48rpx rgba(46, 32, 120, 0.4), 0 0 0 6rpx rgba(255, 255, 255, 0.92);
}
.app-name {
  margin-top: 40rpx;
  font-size: 56rpx;
  font-weight: 800;
  letter-spacing: 6rpx;
  color: #ffffff;
  text-shadow: 0 6rpx 20rpx rgba(46, 32, 120, 0.3);
}
.slogan {
  margin-top: 18rpx;
  font-size: 27rpx;
  letter-spacing: 2rpx;
  color: rgba(255, 255, 255, 0.86);
}

.foot {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18rpx;
}
.dots {
  display: flex;
  align-items: center;
  gap: 14rpx;
}
.dot {
  width: 14rpx;
  height: 14rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  animation: splash-bounce 1s ease-in-out infinite;
}
.d2 { animation-delay: 0.16s; }
.d3 { animation-delay: 0.32s; }
@keyframes splash-bounce {
  0%, 80%, 100% { transform: scale(0.7); opacity: 0.45; }
  40% { transform: scale(1.15); opacity: 1; }
}
.ver {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.72);
  letter-spacing: 1rpx;
}
</style>
