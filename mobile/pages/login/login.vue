<template>
  <view class="login-page" :class="cwRootClass">
    <view class="brand anim-up">
      <image src="/static/logo.png" class="brand-logo" mode="aspectFit" />
      <text class="brand-name">校园墙</text>
      <text class="brand-desc">分享校园生活的每一刻</text>
    </view>

    <view class="form-card anim-up delay-1">
      <view class="tab-switch">
        <view class="tab" :class="{ active: mode === 'login' }" @click="switchMode('login')">登录</view>
        <view class="tab" :class="{ active: mode === 'register' }" @click="switchMode('register')">注册</view>
      </view>

      <!-- 用户名 -->
      <view class="field" :class="fieldState('username')">
        <view class="field-row">
          <text class="field-ico">👤</text>
          <input
            v-model="form.username" class="input" placeholder-class="ph"
            :placeholder="mode === 'register' ? '设置用户名' : '请输入用户名'"
            @input="onUsername"
          />
          <text v-if="form.username && usernameOk" class="field-ok">✓</text>
        </view>
      </view>
      <view v-if="mode==='register' && form.username && !usernameOk" class="hint err">{{ usernameHint }}</view>
      <view v-else-if="mode==='register' && form.username && usernameOk" class="hint ok">用户名可用</view>

      <!-- 密码 -->
      <view class="field mt" :class="fieldState('password')">
        <view class="field-row">
          <text class="field-ico">🔒</text>
          <input
            v-model="form.password" class="input" placeholder-class="ph" password
            :placeholder="mode === 'register' ? '设置密码' : '请输入密码'"
            @input="onPassword"
          />
        </view>
      </view>
      <template v-if="mode === 'register' && form.password">
        <view class="strength">
          <view class="strength-bar" :class="['s' + pwdStrength]"></view>
        </view>
        <view class="hint" :class="passwordOk ? 'ok' : 'err'">{{ passwordHint }}</view>
      </template>

      <!-- 昵称 -->
      <template v-if="mode === 'register'">
        <view class="field mt" :class="fieldState('nickname')">
          <view class="field-row">
            <text class="field-ico">😊</text>
            <input
              v-model="form.nickname" class="input" placeholder-class="ph"
              placeholder="昵称（别人看到的名字）" maxlength="32" @input="onNickname"
            />
            <text v-if="form.nickname && nicknameOk" class="field-ok">✓</text>
          </view>
        </view>
        <view v-if="form.nickname && !nicknameOk" class="hint err">昵称不能为空，最多 32 个字</view>
      </template>

      <view class="forgot-row" v-if="mode === 'login'">
        <text></text>
        <text class="forgot" @click="goForgot">忘记密码？</text>
      </view>
      <!-- 隐私政策与用户协议勾选 -->
      <view class="agree-row" @click="toggleAgree">
        <view class="agree-box" :class="{ on: agreed }">
          <text v-if="agreed" class="agree-tick">✓</text>
        </view>
        <view class="agree-text">
          <text>我已阅读并同意</text>
          <text class="agree-link" @click.stop="openAgreement">《隐私政策与用户协议》</text>
        </view>
      </view>
      <button class="submit-btn hover-press" :disabled="!canSubmit" :class="{ disabled: !canSubmit }"
        @click="handleSubmit" :loading="loading">
        {{ mode === 'login' ? '登 录' : '注 册' }}
      </button>
      <view v-if="mode==='register'" class="rule-tip">
        <text>用户名 3-32 位字母/数字/下划线；密码至少 8 位且同时含字母和数字</text>
      </view>

      <!-- #ifdef MP-WEIXIN || APP-PLUS -->
      <view class="divider"><text class="divider-text">其他登录方式</text></view>
      <button class="wechat-btn" @click="handleWechatLogin" :loading="wechatLoading">微信一键登录</button>
      <!-- #endif -->
      <!-- #ifdef H5 -->
      <template v-if="isWechatBrowser">
        <view class="divider"><text class="divider-text">其他登录方式</text></view>
        <button class="wechat-btn" @click="handleWechatH5" :loading="wechatLoading">微信一键登录</button>
      </template>
      <!-- #endif -->
    </view>
    <text class="agreement">文明发帖、友善交流，共同维护校园社区</text>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { useUserStore } from '../../stores/user'
const userStore = useUserStore()
const mode = ref('login')
const loading = ref(false)
const wechatLoading = ref(false)
// 隐私协议同意状态：一旦同意在本地记住，下次自动勾选
const agreed = ref(uni.getStorageSync('agreement_accepted') === 1)
const touched = ref({ username: false, password: false, nickname: false })
const WECHAT_H5_APPID = ''
// #ifdef H5
const isWechatBrowser = ref(/MicroMessenger/i.test(navigator.userAgent))
// #endif
const form = ref({ username: '', password: '', nickname: '' })

const usernameOk = computed(() => /^[A-Za-z0-9_]{3,32}$/.test(form.value.username.trim()))
const usernameHint = computed(() => {
  const v = form.value.username.trim()
  if (!v) return '请输入用户名'
  if (v.length < 3) return '用户名至少 3 位'
  if (v.length > 32) return '用户名最多 32 位'
  if (!/^[A-Za-z0-9_]+$/.test(v)) return '只能包含字母、数字和下划线'
  return ''
})
const passwordOk = computed(() => /^(?=.*[A-Za-z])(?=.*\d).{8,}$/.test(form.value.password))
const pwdStrength = computed(() => {
  const v = form.value.password
  let s = 0
  if (v.length >= 8) s++
  if (/[A-Za-z]/.test(v) && /\d/.test(v)) s++
  if (v.length >= 12 && /[^A-Za-z0-9]/.test(v)) s++
  return s
})
const passwordHint = computed(() => {
  const v = form.value.password
  if (v.length < 8) return '密码至少 8 位'
  if (!/[A-Za-z]/.test(v)) return '密码需要包含字母'
  if (!/\d/.test(v)) return '密码需要包含数字'
  return '密码符合要求'
})
const nicknameOk = computed(() => form.value.nickname.trim().length > 0 && form.value.nickname.trim().length <= 32)
const canSubmit = computed(() => {
  if (!form.value.username.trim() || !form.value.password) return false
  return mode.value === 'register' ? (usernameOk.value && passwordOk.value && nicknameOk.value) : true
})
const fieldState = (k) => {
  if (!touched.value[k] && !form.value[k]) return ''
  if (k === 'username') return usernameOk.value ? 'ok' : 'err'
  if (k === 'password') return passwordOk.value ? 'ok' : (form.value.password ? 'err' : '')
  if (k === 'nickname') return nicknameOk.value ? 'ok' : 'err'
  return ''
}
const onUsername = () => { touched.value.username = true; form.value.username = form.value.username.trim() }
const onPassword = () => { touched.value.password = true }
const onNickname = () => { touched.value.nickname = true }
const switchMode = (m) => { mode.value = m }
const goForgot = () => uni.navigateTo({ url: '/pages/account/forgot' })
const toggleAgree = () => {
  agreed.value = !agreed.value
  if (agreed.value) uni.setStorageSync('agreement_accepted', 1)
  else uni.removeStorageSync('agreement_accepted')
}
const openAgreement = () => uni.navigateTo({ url: '/pages/agreement/privacy?from=login' })
// 提交前确保协议已同意：未勾选时弹出「是/否」二次询问
const ensureAgreement = () => new Promise((resolve) => {
  if (agreed.value) return resolve(true)
  uni.showModal({
    title: '隐私政策与用户协议',
    content: '您尚未同意《隐私政策与用户协议》，是否阅读并同意？选择「是」表示同意并继续，选择「否」返回。',
    confirmText: '是，我同意',
    cancelText: '否',
    success: (res) => {
      if (res.confirm) {
        agreed.value = true
        uni.setStorageSync('agreement_accepted', 1)
        resolve(true)
      } else {
        uni.showToast({ title: '需同意协议后才可继续', icon: 'none' })
        resolve(false)
      }
    },
    fail: () => resolve(false),
  })
})

const afterLogin = () => {
  uni.showToast({ title: mode.value === 'login' ? '登录成功' : '注册成功', icon: 'success' })
  setTimeout(() => uni.switchTab({ url: '/pages/index/index' }), 500)
}
const handleWechatLogin = async () => {
  if (!(await ensureAgreement())) return
  // #ifdef MP-WEIXIN || APP-PLUS
  wechatLoading.value = true
  uni.login({
    provider: 'weixin',
    success: async (res) => {
      if (!res.code) { wechatLoading.value = false; uni.showToast({ title: '微信登录失败', icon: 'none' }); return }
      let scene = 'mp'
      // #ifdef APP-PLUS
      scene = 'open'
      // #endif
      try { await userStore.wechatLogin(res.code, scene); afterLogin() } catch (e) {} finally { wechatLoading.value = false }
    },
    fail: () => { wechatLoading.value = false; uni.showToast({ title: '已取消微信登录', icon: 'none' }) },
  })
  // #endif
}
const handleWechatH5 = async () => {
  if (!(await ensureAgreement())) return
  // #ifdef H5
  if (!WECHAT_H5_APPID) { uni.showToast({ title: '请在 login.vue 配置公众号 AppID', icon: 'none' }); return }
  const redirect = encodeURIComponent(location.href.split('?')[0])
  location.href = `https://open.weixin.qq.com/connect/oauth2/authorize?appid=${WECHAT_H5_APPID}&redirect_uri=${redirect}&response_type=code&scope=snsapi_userinfo&state=login#wechat_redirect`
  // #endif
}
onLoad((options) => {
  // #ifdef H5
  const code = options?.code || new URLSearchParams(location.search).get('code')
  if (code) {
    wechatLoading.value = true
    userStore.wechatLogin(code, 'open').then(afterLogin).catch(() => {}).finally(() => { wechatLoading.value = false })
  }
  // #endif
})
const handleSubmit = async () => {
  // 提交前再做一次逐字段提示
  if (!form.value.username.trim()) return uni.showToast({ title: '请输入用户名', icon: 'none' })
  if (!form.value.password) return uni.showToast({ title: '请输入密码', icon: 'none' })
  if (mode.value === 'register') {
    if (!usernameOk.value) return uni.showToast({ title: usernameHint.value, icon: 'none' })
    if (!passwordOk.value) return uni.showToast({ title: passwordHint.value, icon: 'none' })
    if (!nicknameOk.value) return uni.showToast({ title: '请填写昵称', icon: 'none' })
  }
  // 隐私协议：未勾选时弹出是/否询问
  if (!(await ensureAgreement())) return
  loading.value = true
  try {
    if (mode.value === 'login') await userStore.login(form.value.username.trim(), form.value.password)
    else await userStore.register({
      username: form.value.username.trim(),
      password: form.value.password,
      nickname: form.value.nickname.trim(),
      agree: true,
    })
    afterLogin()
  } catch (e) {
    // 后端返回的具体原因（用户名已存在/密码错误等）已由请求层 toast
  } finally { loading.value = false }
}
</script>

<style scoped>
.login-page { min-height: 100vh; padding: 0 48rpx; display: flex; flex-direction: column; justify-content: center; position: relative; z-index: 1; }
.brand { text-align: center; margin-bottom: 48rpx; }
.brand-logo { width: 120rpx; height: 120rpx; filter: drop-shadow(0 0 20rpx rgba(139,124,246,.7)); }
.brand-name { font-size: 60rpx; font-weight: 800; letter-spacing: 8rpx; display: block; margin-top: 12rpx; background: linear-gradient(120deg,#c4b5fd,#6ee7ff 55%,#f0abfc); -webkit-background-clip: text; background-clip: text; color: transparent; }
.brand-desc { font-size: 26rpx; color: var(--text2); margin-top: 12rpx; display: block; }
.form-card { background: var(--card); border: 1rpx solid var(--line); backdrop-filter: blur(20rpx); border-radius: 32rpx; padding: 48rpx 40rpx; box-shadow: var(--shadow); }
.tab-switch { display: flex; margin-bottom: 40rpx; gap: 64rpx; }
.tab { font-size: 34rpx; color: var(--text3); padding-bottom: 14rpx; border-bottom: 4rpx solid transparent; }
.tab.active { color: #c4b5fd; font-weight: 700; border-bottom-color: #8b7cf6; }
.field { background: rgba(255,255,255,.05); border-radius: 18rpx; border: 2rpx solid transparent; transition: all .2s; }
.field.ok { border-color: #34d399; background: rgba(52,211,153,.08); }
.field.err { border-color: #fb7185; background: rgba(251,113,133,.08); }
.field.mt { margin-top: 22rpx; }
.field-row { display: flex; align-items: center; height: 92rpx; padding: 0 24rpx; }
.field-ico { margin-right: 14rpx; font-size: 30rpx; }
.input { flex: 1; font-size: 28rpx; color: var(--text); }
.ph { color: var(--text3); font-size: 26rpx; }
.field-ok { color: #34d399; font-weight: 700; }
.hint { font-size: 22rpx; margin: 10rpx 8rpx 0; }
.hint.err { color: #fb7185; }
.hint.ok { color: #34d399; }
.strength { height: 8rpx; background: rgba(255,255,255,.08); border-radius: 99rpx; margin: 14rpx 8rpx 0; overflow: hidden; }
.strength-bar { height: 100%; border-radius: 99rpx; transition: all .3s; width: 33%; }
.strength-bar.s1 { width: 33%; background: #fb7185; }
.strength-bar.s2 { width: 66%; background: #fbbf24; }
.strength-bar.s3 { width: 100%; background: #34d399; }
.forgot-row { display: flex; justify-content: space-between; align-items: center; margin-top: 18rpx; }
.forgot { color: #a5b4fc; font-size: 24rpx; }
.submit-btn { width: 100%; height: 92rpx; line-height: 92rpx; background: var(--grad); color: #fff; border-radius: 999rpx; font-size: 31rpx; font-weight: 700; margin-top: 20rpx; border: none; letter-spacing: 8rpx; box-shadow: 0 12rpx 34rpx rgba(139,124,246,.5); }
.submit-btn.disabled { opacity: .5; box-shadow: none; color: #fff; }
.submit-btn::after { border: none; }
.rule-tip { margin-top: 16rpx; font-size: 20rpx; color: var(--text3); line-height: 1.5; padding: 0 8rpx; }
.agree-row { display: flex; align-items: flex-start; gap: 14rpx; margin-top: 26rpx; padding: 0 6rpx; }
.agree-box {
  width: 36rpx; height: 36rpx; border-radius: 50%; flex-shrink: 0; margin-top: 4rpx;
  border: 2rpx solid var(--text3); display: flex; align-items: center; justify-content: center;
}
.agree-box.on { background: var(--grad); border-color: transparent; box-shadow: 0 4rpx 14rpx rgba(139,124,246,.5); }
.agree-tick { color: #fff; font-size: 24rpx; font-weight: 800; line-height: 1; }
.agree-text { font-size: 24rpx; color: var(--text2); line-height: 1.5; flex: 1; }
.agree-link { color: #a5b4fc; font-size: 24rpx; }
.agreement { text-align: center; color: var(--text3); font-size: 22rpx; margin-top: 40rpx; }
.divider { display: flex; align-items: center; margin: 40rpx 0 28rpx; color: var(--text3); font-size: 22rpx; }
.divider::before, .divider::after { content: ''; flex: 1; height: 1rpx; background: var(--line); }
.divider-text { padding: 0 20rpx; }
.wechat-btn { width: 100%; height: 92rpx; line-height: 92rpx; background: #2e9e6b; color: #fff; border-radius: 999rpx; font-size: 30rpx; border: none; }
.wechat-btn::after { border: none; }
</style>
