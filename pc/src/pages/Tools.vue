<template>
  <div class="tools-page">
    <div class="tools-empty card">
      <EmptyState
        icon="tool"
        title="工具箱暂未开放"
        description="开发者工具箱正在筹备中，更多实用小工具将陆续上线，敬请期待。"
      />
    </div>
  </div>
</template>

<script setup>
import EmptyState from '../components/EmptyState.vue'
</script>

<style scoped>
.tools-page { padding-bottom: 40px; }
.tools-empty {
  max-width: 640px; margin: 24px auto 0;
}
</style>
