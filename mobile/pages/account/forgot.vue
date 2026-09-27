<template>
  <view class="page" :class="cwRootClass">
    <view class="card anim-up">
      <!-- 步骤1：输入用户名 -->
      <block v-if="step === 1">
        <view class="sec-title">找回密码</view>
        <view class="muted small">输入你的登录用户名，我们将验证你设置的密保问题。</view>
        <view class="field mt">
          <input class="input" v-model="username" placeholder="登录用户名" placeholder-class="ph" />
        </view>
        <button class="btn" :disabled="loading" @click="next1">下一步</button>
      </block>

      <!-- 步骤2：回答密保 + 新密码 -->
      <block v-if="step === 2">
        <view class="sec-title">验证密保</view>
        <view class="q-box">{{ question }}</view>
        <view class="field mt">
          <input class="input" v-model="answer" placeholder="密保答案" placeholder-class="ph" />
        </view>
        <view class="field">
          <input class="input" password v-model="newPassword" placeholder="新密码（至少8位，含字母和数字）" placeholder-class="ph" />
        </view>
        <view class="field">
          <input class="input" password v-model="confirm" placeholder="确认新密码" placeholder-class="ph" />
        </view>
        <button class="btn" :disabled="loading" @click="submit">重置密码</button>
        <view class="muted small mt center-tip">若未设置密保或答案遗忘，请联系管理员重置。</view>
      </block>

      <!-- 步骤3：完成 -->
      <block v-if="step === 3">
        <view class="done">
          <view class="done-icon">✓</view>
          <view class="sec-title">密码已重置</view>
          <view class="muted small">请使用新密码返回登录。</view>
          <button class="btn mt" @click="backLogin">返回登录</button>
        </view>
      </block>
    </view>
  </view>
</template>

<script>
import { api } from '@/utils/api.js'
export default {
  data() {
    return {
      step: 1, loading: false, username: '', question: '',
      answer: '', newPassword: '', confirm: '',
    }
  },
  methods: {
    async next1() {
      if (!this.username.trim()) return uni.showToast({ title: '请输入用户名', icon: 'none' })
      this.loading = true
      try {
        const d = await api.forgotQuestion(this.username.trim())
        if (!d.question) {
          return uni.showToast({ title: d.msg || '该账号未设置密保', icon: 'none' })
        }
        this.question = d.question
        this.step = 2
      } catch (e) {
      } finally { this.loading = false }
    },
    async submit() {
      if (!this.answer.trim()) return uni.showToast({ title: '请输入密保答案', icon: 'none' })
      if (this.newPassword.length < 8) return uni.showToast({ title: '密码至少8位', icon: 'none' })
      if (this.newPassword !== this.confirm) return uni.showToast({ title: '两次密码不一致', icon: 'none' })
      this.loading = true
      try {
        await api.forgotReset({
          username: this.username.trim(), answer: this.answer, new_password: this.newPassword,
        })
        this.step = 3
      } catch (e) {
      } finally { this.loading = false }
    },
    backLogin() { uni.redirectTo({ url: '/pages/login/login' }) },
  },
}
</script>

<style  scoped>
.sec-title { font-weight: 700; font-size: 34rpx; margin-bottom: 14rpx; }
.field { margin: 24rpx 0; }
.input { width: 100%; height: 92rpx; padding: 0 24rpx; }
.ph { color: var(--text3); }
.q-box { background: rgba(139,124,246,.14); border: 1rpx solid rgba(139,124,246,.3); border-radius: 20rpx; padding: 24rpx; color: #c4b5fd; font-weight: 600; }
.center-tip { text-align: center; }
.done { text-align: center; padding: 30rpx 0; }
.done-icon {
  width: 120rpx; height: 120rpx; margin: 0 auto 24rpx; border-radius: 50%;
  background: var(--grad); color: #fff; font-size: 60rpx; line-height: 120rpx;
  box-shadow: var(--glow);
}
</style>
