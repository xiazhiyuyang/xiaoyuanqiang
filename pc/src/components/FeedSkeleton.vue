<template>
  <div v-for="i in count" :key="i" class="sk-card card" :style="{ animationDelay: i * 70 + 'ms' }">
    <div class="sk-head">
      <div class="skeleton" style="width:42px;height:42px;border-radius:50%"></div>
      <div class="grow">
        <div class="skeleton" style="width:120px;height:13px;margin-bottom:8px"></div>
        <div class="skeleton" style="width:80px;height:11px"></div>
      </div>
    </div>
    <div class="skeleton" style="width:70%;height:17px;margin:14px 0 10px"></div>
    <div class="skeleton" style="width:100%;height:12px;margin-bottom:7px"></div>
    <div class="skeleton" style="width:92%;height:12px;margin-bottom:14px"></div>
    <div class="skeleton" style="width:100%;height:150px;border-radius:12px"></div>
  </div>
</template>

<script setup>
defineProps({ count: { type: Number, default: 4 } })
</script>

<style scoped>
.sk-card { padding: 18px 20px; margin-bottom: 16px; animation: rise-in .4s var(--ease-out) both; }
.sk-head { display: flex; gap: 11px; align-items: center; }
</style>
