<template>
  <div class="login-page">
    <div class="login-card">
      <div class="brand">
        <span class="brand-mark">校</span>
        <h2>校园墙管理后台</h2>
        <p>CampusWall Admin</p>
      </div>
      <el-form :model="form" @submit.prevent="handleLogin" class="form">
        <el-form-item>
          <el-input v-model="form.username" placeholder="管理员账号" prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="Lock" size="large"
            show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-button type="primary" size="large" class="submit" :loading="loading" @click="handleLogin">
          登 录
        </el-button>
      </el-form>
      <p class="hint">仅授权管理员可登录 · 操作均有审计记录</p>
    </div>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
const router = useRouter()
const auth = useAuthStore()
const form = ref({ username: 'admin', password: 'admin123456' })
const loading = ref(false)
const handleLogin = async () => {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    const user = await auth.login(form.value.username, form.value.password)
    if (user.role !== 'admin') {
      auth.logout()
      ElMessage.error('需要管理员权限')
      return
    }
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } finally {
    loading.value = false
  }
}
</script>
<style scoped>
.login-page {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #312e81 0%, #6d28d9 55%, #a855f7 100%);
  padding: 20px; position: relative; overflow: hidden;
}
.login-page::before, .login-page::after {
  content: ''; position: absolute; border-radius: 50%;
  background: rgba(255,255,255,0.08);
}
.login-page::before { width: 420px; height: 420px; top: -140px; right: -120px; }
.login-page::after { width: 320px; height: 320px; bottom: -120px; left: -100px; }
.login-card {
  position: relative; z-index: 1;
  width: 100%; max-width: 400px; background: #fff; border-radius: 24px;
  padding: 44px 40px 32px;
  box-shadow: 0 12px 40px rgba(49, 46, 129, 0.35);
}
.brand { text-align: center; margin-bottom: 34px; }
.brand-mark {
  display: inline-flex; align-items: center; justify-content: center;
  width: 60px; height: 60px; border-radius: 18px;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  color: #fff; font-size: 27px; font-weight: 800; margin-bottom: 16px;
  box-shadow: 0 10px 24px rgba(139, 92, 246, 0.4);
}
.brand h2 { margin: 0; font-size: 21px; color: #181826; letter-spacing: 1px; }
.brand p { margin: 8px 0 0; font-size: 12px; color: #9a9daf; letter-spacing: 2px; }
.form { margin-top: 8px; }
.submit { width: 100%; height: 46px; font-size: 15px; letter-spacing: 6px; margin-top: 4px; }
.hint { text-align: center; margin: 22px 0 0; color: #b3b9c4; font-size: 12px; }
</style>
