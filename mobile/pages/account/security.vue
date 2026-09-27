<template>
  <view class="page" :class="cwRootClass">
    <view class="card anim-up">
      <view class="sec-title">设置密保问题</view>
      <view class="muted small" style="line-height:1.7">
        忘记密码时，可通过「用户名 + 密保答案」在登录页自助重置密码。请选择只有你知道答案的问题。
      </view>
      <view class="field mt">
        <text class="label">密保问题</text>
        <picker :range="questions" @change="onPick">
          <view class="input picker">{{ form.question || '点击选择密保问题' }}</view>
        </picker>
      </view>
      <view class="field">
        <text class="label">你的答案</text>
        <input class="input" v-model="form.answer" placeholder="输入答案（不区分大小写）" placeholder-class="ph" />
      </view>
      <button class="btn" :disabled="loading" @click="submit">保存密保</button>
    </view>
  </view>
</template>

<script>
import { api } from '@/utils/api.js'
export default {
  data() {
    return {
      questions: ['你的小学名称是？', '你出生的城市是？', '你最喜欢的一本书是？', '你第一只宠物的名字是？'],
      form: { question: '', answer: '' },
      loading: false,
    }
  },
  methods: {
    onPick(e) { this.form.question = this.questions[e.detail.value] },
    async submit() {
      if (!this.form.question || !this.form.answer.trim()) {
        return uni.showToast({ title: '请选择问题并填写答案', icon: 'none' })
      }
      this.loading = true
      try {
        await api.setSecurity(this.form)
        uni.showToast({ title: '密保已设置', icon: 'success' })
        setTimeout(() => uni.navigateBack(), 800)
      } catch (e) {
      } finally { this.loading = false }
    },
  },
}
</script>

<style  scoped>
.sec-title { font-weight: 700; font-size: 32rpx; margin-bottom: 14rpx; }
.field { margin-bottom: 26rpx; }
.label { display: block; font-size: 26rpx; color: var(--text2); margin-bottom: 12rpx; }
.input { width: 100%; height: 88rpx; padding: 0 24rpx; display: flex; align-items: center; }
.picker { color: var(--text); }
.ph { color: var(--text3); }
</style>
