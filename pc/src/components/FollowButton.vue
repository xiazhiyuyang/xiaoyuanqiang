<template>
  <button
    class="follow-btn"
    :class="[following ? 'is-following' : '', size]"
    :disabled="loading"
    @click.stop="onClick"
  >
    <Icon :name="following ? 'check' : 'plus'" :size="iconSize" />
    <span>{{ following ? '已关注' : '关注' }}</span>
  </button>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Icon from './Icon.vue'
import api from '../api'
import { useAuth } from '../stores/auth'

const props = defineProps({
  userId: { type: [Number, String], required: true },
  modelValue: { type: Boolean, default: false },
  size: { type: String, default: 'sm' },
})
const emit = defineEmits(['update:modelValue', 'change'])
const router = useRouter()
const auth = useAuth()
const following = ref(props.modelValue)
const loading = ref(false)
const iconSize = props.size === 'lg' ? 16 : 14

async function onClick() {
  if (!auth.isLoggedIn) {
    router.push({ path: '/login', query: { next: router.currentRoute.value.fullPath } })
    return
  }
  loading.value = true
  const prev = following.value
  following.value = !prev
  emit('update:modelValue', following.value)
  try {
    const r = await api.toggleFollow(props.userId)
    following.value = r.following
    emit('update:modelValue', r.following)
    emit('change', r)
  } catch (e) {
    following.value = prev
    emit('update:modelValue', prev)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.follow-btn {
  display: inline-flex; align-items: center; gap: 5px;
  border-radius: 999px; font-weight: 600; white-space: nowrap;
  background: var(--brand-btn-bg); color: var(--brand-btn-fg);
  transition: transform var(--t-fast) var(--ease-out), background var(--t-base), color var(--t-base);
}
.follow-btn.sm { height: 30px; padding: 0 13px; font-size: 13px; }
.follow-btn.lg { height: 36px; padding: 0 18px; font-size: 14px; }
.follow-btn:hover:not(:disabled) { background: var(--brand-btn-hover); color: var(--brand-btn-fg); }
.follow-btn:active { transform: scale(.96); }
.follow-btn.is-following { background: var(--surface); color: var(--ink-3); border: 1px solid var(--line-strong); }
.follow-btn.is-following:hover { background: var(--danger-bg); color: var(--danger-strong); border-color: var(--danger); }
.follow-btn:disabled { opacity: .6; cursor: default; }
</style>
