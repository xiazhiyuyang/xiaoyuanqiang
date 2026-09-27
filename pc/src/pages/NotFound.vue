<template>
  <div class="nf">
    <div class="nf-mark"><Icon name="compass" :size="40" /></div>
    <h1>页面走丢了</h1>
    <p class="muted">你访问的内容不存在，或已被作者删除。</p>
    <RouterLink to="/" class="btn btn-primary" style="margin-top:18px">
      <Icon name="home" :size="16" /> 回到首页
    </RouterLink>
  </div>
</template>

<script setup>
import Icon from '../components/Icon.vue'
</script>

<style scoped>
.nf { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 90px 20px; }
.nf-mark { width: 84px; height: 84px; border-radius: 26px; background: var(--brand-50); color: var(--brand-700); display: flex; align-items: center; justify-content: center; margin-bottom: 22px; }
.nf h1 { font-size: 22px; margin-bottom: 8px; }
.nf p { font-size: 14px; }
</style>
