<template>
  <div class="redirecting faint"><span class="spinner" /> 正在打开你的主页…</div>
</template>

<script setup>
import { watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'

const router = useRouter()
const auth = useAuth()

function go() {
  if (auth.user) router.replace(`/u/${auth.user.id}`)
  else if (!auth.ready) return
  else router.replace('/login')
}
watch(() => auth.ready, go)
onMounted(go)
</script>

<style scoped>
.redirecting { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 100px 0; font-size: 14px; }
.spinner { width: 16px; height: 16px; border: 2px solid var(--line-strong); border-top-color: var(--brand-600); border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
