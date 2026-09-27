<template>
  <span
    class="avatar"
    :class="{ ring }"
    :style="{ width: size + 'px', height: size + 'px', fontSize: Math.round(size * 0.4) + 'px' }"
  >
    <img v-if="imgUrl" :src="imgUrl" :alt="alt || name || '头像'" loading="lazy" referrerpolicy="no-referrer" @error="onError" />
    <span v-else class="avatar-fallback" :style="{ background: fallbackBg, color: fallbackFg }">{{ initial }}</span>
    <span v-if="online" class="avatar-online" :style="{ borderWidth: Math.max(2, Math.round(size * 0.07)) + 'px' }" />
  </span>
</template>

<script setup>
import { computed, ref } from 'vue'
import { mediaUrl, anonymousAvatar } from '../utils/format'

const props = defineProps({
  src: { type: String, default: null },
  name: { type: String, default: '' },
  anonymous: { type: Boolean, default: false },
  seed: { type: [String, Number], default: '' },
  size: { type: [Number, String], default: 40 },
  ring: { type: Boolean, default: false },
  alt: { type: String, default: '' },
  online: { type: Boolean, default: false },
})

const failed = ref(false)
const imgUrl = computed(() => {
  if (props.anonymous) return anonymousAvatar(props.seed || props.name || 'anon')
  if (failed.value) return ''
  return mediaUrl(props.src)
})
const initial = computed(() => {
  const n = (props.name || '?').trim()
  return n ? Array.from(n)[0].toUpperCase() : '?'
})
const fallbackBg = computed(() => {
  let h = 0
  const key = String(props.seed || props.name || 'x')
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0
  return `hsl(${h % 360} 42% 88%)`
})
const fallbackFg = computed(() => {
  let h = 0
  const key = String(props.seed || props.name || 'x')
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0
  return `hsl(${h % 360} 45% 38%)`
})
function onError() { failed.value = true }
</script>

<style scoped>
.avatar {
  position: relative;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 50%; overflow: visible; flex: none;
  background: var(--surface-3); color: var(--ink-3);
  font-weight: 650; user-select: none;
}
.avatar.ring { box-shadow: 0 0 0 2px var(--surface), 0 0 0 3.5px var(--brand-400); }
.avatar img { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; }
.avatar-fallback { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; border-radius: 50%; }
.avatar-online {
  position: absolute; right: 0; bottom: 0; width: 26%; height: 26%;
  min-width: 10px; min-height: 10px; border-radius: 50%;
  background: var(--success); border-style: solid; border-color: var(--surface);
}
</style>
