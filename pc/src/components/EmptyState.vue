<template>
  <div class="empty">
    <div class="empty-icon"><Icon :name="icon" :size="26" /></div>
    <p class="empty-title">{{ title }}</p>
    <p v-if="description" class="empty-desc">{{ description }}</p>
    <div v-if="$slots.default" class="empty-action"><slot /></div>
  </div>
</template>

<script setup>
import Icon from './Icon.vue'
defineProps({
  icon: { type: String, default: 'inbox' },
  title: { type: String, default: '还没有内容' },
  description: { type: String, default: '' },
})
</script>

<style scoped>
.empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; padding: 64px 24px; gap: 4px;
}
.empty-icon {
  width: 64px; height: 64px; border-radius: 20px;
  display: flex; align-items: center; justify-content: center;
  background: color-mix(in srgb, var(--brand-500) 10%, var(--surface-2));
  color: var(--brand-600); margin-bottom: 12px;
}
.empty-title { font-size: 15.5px; font-weight: 650; color: var(--ink); }
.empty-desc { font-size: 13.5px; color: var(--ink-3); max-width: 320px; margin-top: 2px; line-height: 1.6; }
.empty-action { margin-top: 18px; }
</style>
