<template>
  <span
    v-if="label"
    class="level-badge"
    :style="{ color: textColor, background: bg }"
    :title="`Lv.${level} ${label}`"
  >
    <svg viewBox="0 0 24 24" width="11" height="11" :fill="hex"><path d="m12 2 2.9 6.2 6.8.8-5 4.6 1.3 6.7L12 17.2 6 20.3l1.3-6.7-5-4.6 6.8-.8z"/></svg>
    <span class="lv-name">{{ label }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  badge: { type: Object, default: null },
  level: { type: [Number, String], default: null },
  name: { type: String, default: '' },
  color: { type: String, default: '' },
})

const level = computed(() => props.badge?.level ?? props.level ?? 1)
const label = computed(() => props.badge?.name || props.name || '')
const hex = computed(() => props.badge?.color || props.color || '#94a3b8')
const textColor = computed(() => {
  // 高饱和等级色直接做文字，浅底深字保证对比
  return shade(hex.value, -18)
})
const bg = computed(() => hex.value + '1f')

// 简单加深，保证浅底上的文字对比
function shade(hexColor, percent) {
  const m = hexColor.replace('#', '')
  if (m.length !== 6) return hexColor
  const num = parseInt(m, 16)
  let r = (num >> 16) & 255, g = (num >> 8) & 255, b = num & 255
  const t = percent < 0 ? 0 : 255
  const p = Math.abs(percent) / 100
  r = Math.round((t - r) * p) + r; g = Math.round((t - g) * p) + g; b = Math.round((t - b) * p) + b
  return `rgb(${r},${g},${b})`
}
</script>

<style scoped>
.level-badge {
  display: inline-flex; align-items: center; gap: 3px;
  height: 20px; padding: 0 7px; border-radius: 999px;
  font-size: 11.5px; font-weight: 600; line-height: 1; white-space: nowrap;
}
.lv-name { font-weight: 650; }
</style>
