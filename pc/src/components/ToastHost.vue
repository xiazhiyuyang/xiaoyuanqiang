<template>
  <Teleport to="body">
    <div class="toast-host" role="status" aria-live="polite">
      <TransitionGroup name="toast">
        <div v-for="t in toasts" :key="t.id" class="toast" :class="'toast-' + t.type">
          <Icon :name="iconOf(t.type)" :size="17" />
          <span>{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import Icon from './Icon.vue'
import { onToast } from '../utils/toast'

const toasts = ref([])
onToast((t) => {
  toasts.value.push(t)
  setTimeout(() => {
    toasts.value = toasts.value.filter((x) => x.id !== t.id)
  }, t.timeout)
})
const iconOf = (type) => ({ success: 'check', error: 'alert', info: 'info' }[type] || 'info')
</script>

<style scoped>
.toast-host {
  position: fixed; top: 18px; left: 50%; transform: translateX(-50%);
  z-index: var(--z-toast); display: flex; flex-direction: column; gap: 10px;
  pointer-events: none; width: max-content; max-width: min(92vw, 520px);
}
.toast {
  display: flex; align-items: center; gap: 9px;
  background: var(--ink); color: var(--surface);
  padding: 11px 16px; border-radius: 12px; box-shadow: var(--shadow-pop);
  font-size: 14px; font-weight: 500; line-height: 1.4;
}
.toast-success { background: #106a5d; color: #fff; }
.toast-error { background: #b53d35; color: #fff; }
.toast-enter-active, .toast-leave-active { transition: all var(--t-base) var(--ease-out); }
.toast-enter-from { opacity: 0; transform: translateY(-10px) scale(.97); }
.toast-leave-to { opacity: 0; transform: translateY(-6px) scale(.98); }
</style>
