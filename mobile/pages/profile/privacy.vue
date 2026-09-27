<template>
  <view class="page" :class="cwRootClass">
    <view class="head-tip anim-fade">
      你可以分别控制每一项资料「谁可以看」。设置会立即在你的个人主页生效。
    </view>

    <view class="card cw-card anim-up">
      <view v-for="(item, idx) in items" :key="item.key" class="row" :class="{ last: idx === items.length - 1 }">
        <view class="row-left">
          <text class="row-ico">{{ item.icon }}</text>
          <view>
            <text class="row-name">{{ item.name }}</text>
            <text class="row-desc">{{ levelLabel(privacy[item.key]) }}</text>
          </view>
        </view>
        <view class="seg">
          <text
            v-for="lv in levels" :key="lv.v"
            class="seg-item" :class="{ on: privacy[item.key] === lv.v }"
            @click="setLevel(item.key, lv.v)"
          >{{ lv.t }}</text>
        </view>
      </view>
    </view>

    <view class="card cw-card anim-up delay-1">
      <view class="row last">
        <view class="row-left">
          <text class="row-ico">📇</text>
          <view>
            <text class="row-name">联系方式（手机/学号）</text>
            <text class="row-desc">出于安全，仅自己可见，不可公开</text>
          </view>
        </view>
        <text class="lock">🔒</text>
      </view>
    </view>

    <button class="save hover-press" @click="save" :loading="saving">保存设置</button>
    <view class="legend">
      <text>所有人可见：任何访客可见</text>
      <text>仅登录用户：未登录访客看不到</text>
      <text>仅自己：除你之外都看不到</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { api } from '../../utils/api'
const saving = ref(false)
const levels = [
  { v: 'public', t: '所有人' },
  { v: 'members', t: '登录' },
  { v: 'private', t: '仅自己' },
]
const items = [
  { key: 'gender', name: '性别', icon: '⚧' },
  { key: 'school', name: '学校信息（年级/学院/专业）', icon: '🎓' },
  { key: 'location', name: '所在地', icon: '📍' },
  { key: 'birthday', name: '生日', icon: '🎂' },
]
const privacy = ref({ gender: 'public', school: 'public', location: 'members', birthday: 'private' })
const levelLabel = (lv) => ({ public: '所有人可见', members: '仅登录用户可见', private: '仅自己可见' }[lv] || '')
onLoad(async () => {
  try {
    const me = await api.getMe()
    if (me.privacy) privacy.value = { ...privacy.value, ...me.privacy }
  } catch (e) {}
})
const setLevel = (key, v) => { privacy.value[key] = v }
const save = async () => {
  saving.value = true
  try {
    await api.updateMe({ privacy: privacy.value })
    uni.showToast({ title: '已保存', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 600)
  } catch (e) {} finally { saving.value = false }
}
</script>

<style scoped>
.page { padding: 24rpx; }
.head-tip { background: var(--brand-soft); color: var(--brand-deep); font-size: 24rpx; line-height: 1.6; padding: 22rpx 26rpx; border-radius: var(--radius); margin-bottom: 22rpx; }
.card { padding: 0 28rpx; margin-bottom: 22rpx; }
.row { display: flex; align-items: center; justify-content: space-between; padding: 28rpx 0; border-bottom: 1rpx solid var(--line); gap: 16rpx; }
.row.last { border-bottom: none; }
.row-left { display: flex; align-items: center; }
.row-ico { font-size: 36rpx; margin-right: 18rpx; }
.row-name { font-size: 27rpx; color: var(--ink); font-weight: 600; display: block; }
.row-desc { font-size: 21rpx; color: var(--ink-3); margin-top: 6rpx; display: block; }
.seg { display: flex; background: #f1f2f8; border-radius: 999rpx; padding: 4rpx; flex-shrink: 0; }
.seg-item { font-size: 21rpx; color: var(--ink-2); padding: 10rpx 18rpx; border-radius: 999rpx; }
.seg-item.on { background: var(--grad); color: #fff; font-weight: 700; }
.lock { font-size: 34rpx; }
.save { height: 92rpx; line-height: 92rpx; background: var(--grad); color: #fff; border-radius: 999rpx; font-size: 30rpx; font-weight: 700; border: none; box-shadow: var(--shadow-brand); margin-top: 10rpx; }
.save::after { border: none; }
.legend { margin-top: 30rpx; padding: 0 12rpx; }
.legend text { display: block; font-size: 22rpx; color: var(--ink-3); line-height: 2; }
</style>
