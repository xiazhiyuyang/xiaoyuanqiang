<template>
  <div>
    <div class="welcome">
      <h3>欢迎回来 👋</h3>
      <p>今天也要守护好校园墙的社区氛围</p>
    </div>
    <div class="stat-grid">
      <div v-for="card in cards" :key="card.label" class="stat-card">
        <div class="stat-icon" :style="{ background: card.bg, color: card.color }">
          <el-icon :size="24"><component :is="card.icon" /></el-icon>
        </div>
        <div class="stat-meta">
          <div class="stat-num">{{ stats[card.key] ?? '-' }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'
const stats = ref({})
const cards = [
  { key: 'user_count', label: '用户总数', icon: 'User', color: '#6366f1', bg: '#eef0fe' },
  { key: 'post_count', label: '帖子总数', icon: 'Document', color: '#14b8a6', bg: '#e6faf7' },
  { key: 'comment_count', label: '评论总数', icon: 'ChatDotRound', color: '#f59e0b', bg: '#fef5e7' },
  { key: 'report_pending_count', label: '待处理举报', icon: 'Warning', color: '#f43f5e', bg: '#fff1f3' },
]
onMounted(async () => {
  const res = await api.get('/admin/stats')
  stats.value = res.data
})
</script>
<style scoped>
.welcome { margin-bottom: 20px; }
.welcome h3 { margin: 0 0 6px; font-size: 22px; color: #1b2030; }
.welcome p { margin: 0; color: #9aa1ae; font-size: 13px; }
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
}
.stat-card {
  background: #fff; border-radius: 16px; padding: 24px;
  display: flex; align-items: center; gap: 18px;
  box-shadow: 0 1px 3px rgba(27,32,48,0.05), 0 6px 18px rgba(27,32,48,0.04);
  transition: transform 0.2s, box-shadow 0.2s;
}
.stat-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(27,32,48,0.1); }
.stat-icon {
  width: 54px; height: 54px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.stat-num { font-size: 30px; font-weight: 700; color: #1b2030; line-height: 1.1; font-variant-numeric: tabular-nums; }
.stat-label { color: #9aa1ae; font-size: 13px; margin-top: 4px; }
@media (max-width: 640px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); gap: 12px; }
  .stat-card { padding: 16px; gap: 12px; }
  .stat-icon { width: 42px; height: 42px; border-radius: 11px; }
  .stat-num { font-size: 23px; }
}
</style>
