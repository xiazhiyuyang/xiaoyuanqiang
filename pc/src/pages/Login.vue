<template>
  <div class="auth-page">
    <aside class="auth-hero">
      <div class="hero-inner">
        <RouterLink to="/" class="hero-brand">
          <span class="brand-mark"><Icon name="compass" :size="22" /></span>
          <span>{{ app.siteName }}</span>
        </RouterLink>
        <h1 class="hero-title">{{ app.slogan }}</h1>
        <p class="hero-sub">发布校园新鲜事、交流互助、记录你的大学时光，在同校社区里遇见有趣的人。</p>
        <ul class="hero-points">
          <li><Icon name="shield" :size="18" /><span>实名校园环境，匿名树洞也安心</span></li>
          <li><Icon name="message" :size="18" /><span>动态、评论、私信，互动一气呵成</span></li>
          <li><Icon name="medal" :size="18" /><span>星轨等级体系，记录你的成长轨迹</span></li>
        </ul>
      </div>
      <div class="hero-glow" />
    </aside>

    <main class="auth-main">
      <div class="auth-card pop">
        <div class="auth-tabs">
          <button :class="{ on: mode === 'login' }" @click="switchMode('login')">登录</button>
          <button v-if="registerOpen" :class="{ on: mode === 'register' }" @click="switchMode('register')">注册</button>
          <button :class="{ on: mode === 'forgot' }" @click="switchMode('forgot')">找回密码</button>
        </div>

        <!-- 登录 -->
        <form v-if="mode === 'login'" class="auth-form" @submit.prevent="onLogin">
          <h2 class="form-title">欢迎回来</h2>
          <p class="form-sub muted">登录后继续你的校园社区</p>
          <div class="login-type-tabs">
            <button type="button" :class="{ active: loginType === 'username' }" @click="loginType = 'username'">账号密码</button>
            <button type="button" :class="{ active: loginType === 'email' }" @click="loginType = 'email'">邮箱</button>
          </div>
          <template v-if="loginType === 'username'">
            <div class="field">
              <label>用户名</label>
              <input v-model.trim="login.username" class="input" autocomplete="username" placeholder="3–32 位字母、数字或下划线" />
            </div>
          </template>
          <template v-else>
            <div class="field">
              <label>邮箱</label>
              <input v-model.trim="emailLogin.email" class="input" type="email" placeholder="请输入邮箱" />
            </div>
          </template>
          <div class="field">
            <label>密码</label>
            <div class="pwd">
              <input v-if="loginType === 'username'" v-model="login.password" class="input" :type="showPwd ? 'text' : 'password'" autocomplete="current-password" placeholder="请输入密码" />
              <input v-else v-model="emailLogin.password" class="input" :type="showPwd ? 'text' : 'password'" autocomplete="current-password" placeholder="请输入密码" />
              <button type="button" class="pwd-toggle" @click="showPwd = !showPwd"><Icon :name="showPwd ? 'eyeOff' : 'eye'" :size="17" /></button>
            </div>
          </div>
          <p v-if="error" class="field-error">{{ error }}</p>
          <button class="btn btn-primary btn-block submit" :disabled="loading">
            {{ loading ? '登录中…' : '登 录' }}
          </button>
          <p class="form-foot muted">还没有账号？<a href="javascript:;" @click="switchMode('register')">立即注册</a></p>
        </form>

        <!-- 注册 -->
        <form v-else-if="mode === 'register'" class="auth-form" @submit.prevent="onRegister">
          <h2 class="form-title">创建账号</h2>
          <div class="login-type-tabs">
            <button type="button" :class="{ active: loginType === 'username' }" @click="loginType = 'username'">账号密码</button>
            <button type="button" :class="{ active: loginType === 'email' }" @click="loginType = 'email'">邮箱</button>
          </div>
          <template v-if="loginType === 'username'">
            <div class="grid-2">
              <div class="field"><label>用户名</label><input v-model.trim="reg.username" class="input" placeholder="登录名，唯一" /></div>
              <div class="field"><label>昵称</label><input v-model.trim="reg.nickname" class="input" placeholder="社区展示名" /></div>
            </div>
            <div class="grid-2">
              <div class="field"><label>密码</label><input v-model="reg.password" class="input" type="password" placeholder="≥8 位" /></div>
              <div class="field"><label>确认密码</label><input v-model="reg.confirm" class="input" type="password" placeholder="再输一次" /></div>
            </div>
            <div v-if="reg.password" class="pwd-feedback">
              <div class="strength-bar"><div class="strength-fill" :class="'s' + pwdStrength"></div></div>
              <span class="strength-text" :class="pwdStrength >= 2 ? 'ok' : 'warn'">{{ pwdStrengthText }}</span>
            </div>
            <div v-if="reg.confirm && reg.password !== reg.confirm" class="field-error inline-err">两次输入的密码不一致</div>
            <div class="grid-2">
              <div class="field"><label>学号（选填）</label><input v-model.trim="reg.student_id" class="input" placeholder="便于同校认证" /></div>
              <div class="field"><label>手机号（选填）</label><input v-model.trim="reg.phone" class="input" placeholder="11 位手机号" /></div>
            </div>
          </template>
          <template v-else>
            <div class="field"><label>邮箱</label><input v-model.trim="emailReg.email" class="input" type="email" placeholder="请输入邮箱" /></div>
            <div class="grid-2">
              <div class="field"><label>用户名</label><input v-model.trim="emailReg.username" class="input" placeholder="登录名，唯一" /></div>
              <div class="field"><label>昵称</label><input v-model.trim="emailReg.nickname" class="input" placeholder="社区展示名" /></div>
            </div>
            <div class="field"><label>密码</label><input v-model="emailReg.password" class="input" type="password" placeholder="≥8 位" /></div>
            <div v-if="emailReg.password && emailReg.password.length < 8" class="field-error inline-err">密码至少8位</div>
          </template>
          <label class="agree">
            <input type="checkbox" v-model="reg.agree" />
            <span>我已阅读并同意<a href="javascript:;" @click.prevent="agreeOpen = true">《隐私政策与用户协议》</a></span>
          </label>
          <p v-if="error" class="field-error">{{ error }}</p>
          <button class="btn btn-primary btn-block submit" :disabled="loading">{{ loading ? '注册中…' : '注 册' }}</button>
        </form>

        <!-- 找回密码 -->
        <form v-else class="auth-form" @submit.prevent="onForgot">
          <h2 class="form-title">找回密码</h2>
          <div class="field">
            <label>用户名</label>
            <input v-model.trim="fg.username" class="input" :disabled="fg.step > 1" placeholder="输入你的用户名" />
          </div>
          <template v-if="fg.step >= 2">
            <div class="field"><label>密保问题</label><input class="input" :value="fg.question" disabled /></div>
            <div class="field"><label>密保答案</label><input v-model.trim="fg.answer" class="input" placeholder="输入你设置的答案" /></div>
            <div class="field"><label>新密码</label><input v-model="fg.newPassword" class="input" type="password" placeholder="≥8 位" /></div>
          </template>
          <p v-if="error" class="field-error">{{ error }}</p>
          <button class="btn btn-primary btn-block submit" :disabled="loading">
            {{ loading ? '处理中…' : (fg.step === 1 ? '下一步' : '重置密码') }}
          </button>
        </form>
      </div>
    </main>

    <Modal v-model="agreeOpen" title="隐私政策与用户协议" size="md">
      <div class="agreement">
        <p>欢迎使用{{ app.siteName }}。我们重视你的隐私与账号安全：</p>
        <ul>
          <li>仅在你主动填写时收集昵称、学号、手机号等资料，可随时在设置中修改或隐藏。</li>
          <li>密码经加密存储，我们不会以明文形式保存或向他人透露你的密码。</li>
          <li>你发布的公开内容对同校用户可见，匿名发布不会展示你的身份信息。</li>
          <li>请勿发布违法违规、辱骂攻击、色情暴力或侵犯他人隐私的内容。</li>
          <li>完整条款以站点管理员公布的版本为准，如有疑问可通过站内设置的联系方式反馈。</li>
        </ul>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue"
import { useRoute, useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import Modal from '../components/Modal.vue'
import api from '../api'
import { useAuth } from '../stores/auth'
import { useApp } from '../stores/app'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const app = useApp()

const mode = ref('login')
const loading = ref(false)
const error = ref('')
const showPwd = ref(false)
const agreeOpen = ref(false)
const registerOpen = ref(true)

const login = reactive({ username: '', password: '' })
const reg = reactive({ username: '', nickname: '', password: '', confirm: '', student_id: '', phone: '', agree: false })
const loginType = ref('username')
const emailLogin = reactive({ email: '', password: '' })
const emailReg = reactive({ email: '', username: '', nickname: '', password: '' })
const fg = reactive({ step: 1, username: '', question: '', answer: '', newPassword: '' })

// 密码强度计算
const pwdStrength = computed(() => {
  const v = reg.password
  let s = 0
  if (v.length >= 8) s++
  if (/[A-Za-z]/.test(v) && /\d/.test(v)) s++
  if (v.length >= 12 && /[^A-Za-z0-9]/.test(v)) s++
  return s
})
const pwdStrengthText = computed(() => {
  if (!reg.password) return ''
  if (pwdStrength.value <= 1) return '密码强度：弱'
  if (pwdStrength.value === 2) return '密码强度：中'
  return '密码强度：强'
})

onMounted(async () => {
  await app.loadSettings()
  registerOpen.value = app.settings?.allow_register !== false
  if (!registerOpen.value && mode.value === 'register') mode.value = 'login'
  if (route.query.mode) mode.value = route.query.mode
})

function switchMode(m) { mode.value = m; error.value = '' }

function afterAuth() {
  const next = route.query.next ? decodeURIComponent(route.query.next) : '/'
  router.replace(next.startsWith('/') ? next : '/')
}

async function onLogin() {
  error.value = ''
  if (loginType.value === 'email') {
    if (!emailLogin.email || !emailLogin.password) { error.value = '请输入邮箱和密码'; return }
    if (!/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(emailLogin.email)) { error.value = '邮箱格式不正确'; return }
    loading.value = true
    try {
      await auth.emailLogin(emailLogin.email, emailLogin.password)
      afterAuth()
    } catch (e) { error.value = e.response?.data?.detail || e.message || '登录失败' } finally { loading.value = false }
    return
  }
  if (!login.username || !login.password) { error.value = '请输入用户名和密码'; return }
  loading.value = true
  try {
    await auth.login(login.username, login.password)
    afterAuth()
  } catch (e) { error.value = e.response?.data?.detail || e.message || '登录失败' } finally { loading.value = false }
}

function validateReg() {
  if (!/^[a-zA-Z0-9_]{3,32}$/.test(reg.username)) return '用户名需为 3–32 位字母、数字或下划线'
  if (!reg.nickname.trim()) return '昵称不能为空'
  if (reg.password.length < 8) return '密码至少 8 位'
  if (reg.password !== reg.confirm) return '两次输入的密码不一致'
  if (reg.phone && !/^1[3-9]\d{9}$/.test(reg.phone)) return '请输入正确的 11 位手机号'
  if (!reg.agree) return '请先阅读并同意隐私政策与用户协议'
  return ''
}
async function onRegister() {
  error.value = ''
  if (loginType.value === 'email') {
    if (!/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(emailReg.email)) { error.value = '邮箱格式不正确'; return }
    if (emailReg.username.length < 3) { error.value = '用户名至少3位'; return }
    if (!emailReg.nickname.trim()) { error.value = '昵称不能为空'; return }
    if (emailReg.password.length < 8) { error.value = '密码至少8位'; return }
    if (!reg.agree) { error.value = '请先阅读并同意隐私政策与用户协议'; return }
    loading.value = true
    try {
      const r = await auth.emailRegister({
        email: emailReg.email, username: emailReg.username,
        nickname: emailReg.nickname, password: emailReg.password,
      })
      if (r.dev_verify_url) {
        error.value = ''
        alert('开发模式：验证链接已生成，请复制到浏览器打开完成验证\n\n' + r.dev_verify_url)
      } else {
        alert('注册成功，请查收邮件完成验证')
      }
      switchMode('login')
    } catch (e) { error.value = e.response?.data?.detail || e.message || '注册失败' } finally { loading.value = false }
    return
  }
  error.value = validateReg()
  if (error.value) return
  loading.value = true
  try {
    await auth.register({
      username: reg.username, nickname: reg.nickname, password: reg.password,
      student_id: reg.student_id || null, phone: reg.phone || null, agree: reg.agree,
    })
    afterAuth()
  } catch (e) { error.value = e.response?.data?.detail || e.message || '注册失败' } finally { loading.value = false }
}

async function onForgot() {
  error.value = ''
  if (!fg.username) { error.value = '请输入用户名'; return }
  loading.value = true
  try {
    if (fg.step === 1) {
      const r = await api.forgotQuestion(fg.username)
      fg.question = r.question || r.security_question || '未设置密保问题'
      fg.step = 2
    } else {
      if (!fg.answer) { error.value = '请输入密保答案'; loading.value = false; return }
      if (fg.newPassword.length < 8) {
        error.value = '新密码至少 8 位'; loading.value = false; return
      }
      await api.forgotReset({ username: fg.username, answer: fg.answer, new_password: fg.newPassword })
      mode.value = 'login'
      fg.step = 1
    }
  } catch (e) { error.value = e.response?.data?.detail || e.message || '操作失败' } finally { loading.value = false }
}
</script>

<style scoped>
.auth-page { display: grid; grid-template-columns: 1.05fr 1fr; min-height: 100dvh; }
.auth-hero {
  position: relative; overflow: hidden; color: #fff;
  background: linear-gradient(155deg, #14806f 0%, #0f554c 55%, #0d463f 100%);
  display: flex; align-items: center; padding: 64px;
}
.hero-glow {
  position: absolute; width: 520px; height: 520px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255,255,255,.16), transparent 65%);
  top: -160px; right: -160px; pointer-events: none;
}
.hero-inner { position: relative; max-width: 440px; }
.hero-brand { display: flex; align-items: center; gap: 10px; color: #fff; font-size: 20px; font-weight: 700; margin-bottom: 56px; }
.hero-brand .brand-mark { width: 40px; height: 40px; border-radius: 12px; background: rgba(255,255,255,.16); display: flex; align-items: center; justify-content: center; }
.hero-title { color: #fff; font-size: 38px; line-height: 1.25; letter-spacing: -0.02em; margin-bottom: 18px; }
.hero-sub { color: rgba(255,255,255,.82); font-size: 15.5px; line-height: 1.8; margin-bottom: 40px; }
.hero-points { display: flex; flex-direction: column; gap: 16px; }
.hero-points li { display: flex; align-items: center; gap: 12px; color: rgba(255,255,255,.9); font-size: 14.5px; }
.hero-points svg { flex: none; opacity: .9; }

.auth-main { display: flex; align-items: center; justify-content: center; padding: 40px 24px; }
.auth-card { width: 100%; max-width: 440px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-xl); box-shadow: var(--shadow-md); padding: 32px 34px; }
.auth-tabs { display: flex; gap: 4px; background: var(--surface-3); padding: 4px; border-radius: var(--r-pill); margin-bottom: 26px; }
.auth-tabs button { flex: 1; height: 36px; border-radius: var(--r-pill); font-size: 14px; font-weight: 560; color: var(--ink-3); transition: all var(--t-fast) var(--ease-out); }
.auth-tabs button.on { background: var(--surface); color: var(--brand-700); box-shadow: var(--shadow-xs); }
.form-title { font-size: 23px; margin-bottom: 4px; }
.form-sub { font-size: 13.5px; margin-bottom: 22px; }
.auth-form { display: flex; flex-direction: column; gap: 15px; }
.login-type-tabs { display: flex; gap: 8px; margin: 4px 0; padding: 4px; background: var(--bg-soft); border-radius: 10px; }
.login-type-tabs button { flex: 1; padding: 10px 0; border: none; background: transparent; border-radius: 8px; font-size: 14px; color: var(--text-muted); cursor: pointer; transition: all .25s; }
.login-type-tabs button.active { background: var(--card); color: var(--text); font-weight: 600; box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.pwd { position: relative; }
.pwd .input { padding-right: 42px; }
.pwd-toggle { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); width: 30px; height: 30px; border-radius: 50%; color: var(--ink-4); display: flex; align-items: center; justify-content: center; }
.pwd-toggle:hover { color: var(--ink); background: var(--surface-3); }
.submit { height: 44px; margin-top: 6px; font-size: 15px; }
.form-foot { text-align: center; font-size: 13.5px; margin-top: 4px; }
.agree { display: flex; align-items: flex-start; gap: 8px; font-size: 13px; color: var(--ink-3); }
.agree input { accent-color: var(--brand-600); margin-top: 2px; }
.pwd-feedback { display: flex; align-items: center; gap: 10px; margin: -4px 0 10px; }
.strength-bar { flex: 1; height: 4px; background: var(--surface-3); border-radius: 2px; overflow: hidden; }
.strength-fill { height: 100%; border-radius: 2px; transition: width .3s, background .3s; }
.strength-fill.s0 { width: 0; }
.strength-fill.s1 { width: 33%; background: #f56c6c; }
.strength-fill.s2 { width: 66%; background: #e6a23c; }
.strength-fill.s3 { width: 100%; background: #67c23a; }
.strength-text { font-size: 12px; white-space: nowrap; }
.strength-text.ok { color: #67c23a; }
.strength-text.warn { color: #e6a23c; }
.inline-err { margin: -6px 0 8px; font-size: 12px; }
.agreement { font-size: 14px; line-height: 1.9; color: var(--ink-2); display: flex; flex-direction: column; gap: 10px; }
.agreement ul { display: flex; flex-direction: column; gap: 8px; padding-left: 18px; list-style: disc; }

@media (max-width: 900px) {
  .auth-page { grid-template-columns: 1fr; }
  .auth-hero { display: none; }
}
</style>
