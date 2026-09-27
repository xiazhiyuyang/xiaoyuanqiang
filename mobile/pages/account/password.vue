<template>
  <view class="page" :class="cwRootClass">
    <view class="card anim-up">
      <view class="field">
        <text class="label">原密码</text>
        <input class="input" password v-model="form.old_password" placeholder="请输入当前密码" placeholder-class="ph" />
      </view>
      <view class="field">
        <text class="label">新密码</text>
        <input class="input" password v-model="form.new_password" placeholder="至少8位，含字母和数字" placeholder-class="ph" />
      </view>
      <view class="field">
        <text class="label">确认新密码</text>
        <input class="input" password v-model="confirm" placeholder="再输入一次新密码" placeholder-class="ph" />
      </view>
      <button class="btn mt" :disabled="loading" @click="submit">确认修改</button>
      <view class="tips muted small mt">为了账号安全，修改成功后其他设备需要重新登录。</view>
    </view>
  </view>
</template>

<script>
import { api } from '@/utils/api.js'
export default {
  data() {
    return { form: { old_password: '', new_password: '' }, confirm: '', loading: false }
  },
  methods: {
    async submit() {
      if (!this.form.old_password) return uni.showToast({ title: '请输入原密码', icon: 'none' })
      if (this.form.new_password.length < 8) return uni.showToast({ title: '新密码至少8位', icon: 'none' })
      if (this.form.new_password !== this.confirm) return uni.showToast({ title: '两次输入不一致', icon: 'none' })
      this.loading = true
      try {
        await api.changePassword(this.form)
        uni.showToast({ title: '修改成功', icon: 'success' })
        setTimeout(() => uni.navigateBack(), 800)
      } catch (e) {
      } finally { this.loading = false }
    },
  },
}
</script>

<style  scoped>
.field { margin-bottom: 26rpx; }
.label { display: block; font-size: 26rpx; color: var(--text2); margin-bottom: 12rpx; }
.input { width: 100%; height: 88rpx; padding: 0 24rpx; }
.ph { color: var(--text3); }
.tips { line-height: 1.6; }
</style>
