<template>
  <view class="page" :class="cwRootClass">
    <!-- 当前等级星环 -->
    <view class="hero card anim-pop">
      <view class="ring" :style="{ '--c': mine?.color || '#8b7cf6' }">
        <text class="ring-lv">Lv{{ mine?.level || 1 }}</text>
      </view>
      <view class="hero-info">
        <view class="hero-name galaxy-text">{{ mine?.name || '星尘' }}</view>
        <view class="muted small">累计经验 {{ mine?.exp || 0 }}</view>
        <view class="bar">
          <view class="bar-fill" :style="{ width: (mine?.progress || 0) + '%' }"></view>
        </view>
        <view class="small muted mt">
          <text v-if="mine && !mine.is_max">再获 {{ mine.remain }} 经验升级</text>
          <text v-else>已达最高星轨等级</text>
        </view>
      </view>
    </view>

    <!-- 经验规则 -->
    <view class="card anim-up">
      <view class="sec-title">如何获得经验</view>
      <view class="rule-row" v-for="r in rules" :key="r.k">
        <text>{{ r.label }}</text>
        <text class="tag tag-gold">+{{ r.v }}</text>
      </view>
    </view>

    <!-- 等级阶梯 -->
    <view class="card anim-up">
      <view class="sec-title">星轨等级与功能解锁</view>
      <view class="ladder">
        <view
          class="lv-item"
          v-for="item in ladder"
          :key="item.level"
          :class="{ active: mine && item.level === mine.level, done: mine && item.level < mine.level }"
        >
          <view class="lv-badge" :style="{ background: item.color + '22', color: item.color, borderColor: item.color + '66' }">
            {{ item.level }}
          </view>
          <view class="lv-body">
            <view class="row between">
              <text class="lv-name">{{ item.name }}</text>
              <text class="small muted">{{ item.need }} 经验</text>
            </view>
            <view class="mt" v-if="item.unlock && item.unlock.length">
              <text class="tag tag-cyan" style="margin-right:10rpx" v-for="u in item.unlock" :key="u.key">解锁 · {{ u.label }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '@/utils/api.js'
export default {
  data() {
    return {
      mine: null,
      ladder: [],
      rules: [
        { k: 'login', label: '每日首次登录', v: 2 },
        { k: 'post', label: '发布一条动态', v: 8 },
        { k: 'comment', label: '发表一条评论', v: 2 },
        { k: 'liked', label: '内容被点赞', v: 2 },
      ],
    }
  },
  onShow() { this.load() },
  methods: {
    async load() {
      try {
        const d = await api.getLevels()
        this.mine = d.mine || null
        this.ladder = (d.ladder || []).slice().reverse()
      } catch (e) {}
    },
  },
}
</script>

<style  scoped>
.hero { display: flex; align-items: center; gap: 30rpx; }
.ring {
  width: 150rpx; height: 150rpx; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: radial-gradient(circle at 30% 30%, color-mix(in srgb, var(--c) 55%, transparent), transparent 70%);
  border: 3rpx solid var(--c);
  box-shadow: 0 0 34rpx color-mix(in srgb, var(--c) 60%, transparent);
}
.ring-lv { font-size: 44rpx; font-weight: 800; color: var(--c); }
.hero-info { flex: 1; }
.hero-name { font-size: 40rpx; font-weight: 800; }
.bar { height: 14rpx; border-radius: 999rpx; background: rgba(255,255,255,.08); margin-top: 16rpx; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 999rpx; background: var(--grad); box-shadow: 0 0 16rpx rgba(139,124,246,.7); transition: width .6s; }
.sec-title { font-weight: 700; font-size: 30rpx; margin-bottom: 20rpx; }
.rule-row { display: flex; justify-content: space-between; align-items: center; padding: 16rpx 0; color: var(--text2); border-bottom: 1rpx solid rgba(255,255,255,.05); }
.rule-row:last-child { border-bottom: none; }
.lv-item { display: flex; gap: 20rpx; padding: 20rpx 0; border-bottom: 1rpx solid rgba(255,255,255,.05); }
.lv-item:last-child { border-bottom: none; }
.lv-item.done { opacity: .65; }
.lv-item.active .lv-badge { transform: scale(1.12); box-shadow: 0 0 24rpx rgba(139,124,246,.6); }
.lv-badge { width: 64rpx; height: 64rpx; border-radius: 50%; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-weight: 800; border: 1rpx solid; }
.lv-body { flex: 1; }
.lv-name { font-weight: 700; }
</style>
