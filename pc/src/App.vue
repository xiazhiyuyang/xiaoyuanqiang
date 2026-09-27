<template>
  <div v-if="maintenance" class="maintenance-banner">
    🛠️ 系统正在维护升级中，部分功能暂不可用，我们会尽快恢复
  </div>
  <RouterView v-slot="{ Component }">
    <Transition name="page" mode="out-in">
      <component :is="Component" />
    </Transition>
  </RouterView>
  <ToastHost />
</template>

<script setup>
import { watch, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import ToastHost from './components/ToastHost.vue'
import { useAuth } from './stores/auth'
import { useApp } from './stores/app'

const route = useRoute()
const auth = useAuth()
const appStore = useApp()

const maintenance = computed(() => !!appStore.settings?.maintenance)

onMounted(() => {
  appStore.loadSettings().catch(() => {})
})

watch(
  () => auth.token,
  (token) => {
    if (token) {
      auth.fetchMe().catch(() => {})
      appStore.startPolling()
    } else {
      appStore.stopPolling()
      appStore.unreadNotify = 0
      appStore.unreadMessage = 0
    }
  },
  { immediate: true }
)

watch(
  () => route.fullPath,
  () => {
    if (auth.token) appStore.refreshUnread()
  }
)
</script>

<style>
.page-enter-active { transition: opacity var(--t-base) var(--ease-out); }
.page-enter-from { opacity: 0; }
.maintenance-banner {
  position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
  background: linear-gradient(135deg, #b7791f, #d97706);
  color: #fff; text-align: center; padding: 10px 16px; font-size: 14px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
}
</style>
