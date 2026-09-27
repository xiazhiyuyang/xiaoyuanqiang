<template>
  <div class="tool-detail-page">
    <div v-loading="loading">
      <template v-if="tool">
        <!-- 工具头部 -->
        <div class="tool-header">
          <RouterLink to="/tools" class="back-btn">← 返回工具箱</RouterLink>
          <div class="tool-head-main">
            <div class="tool-icon-lg">{{ tool.icon }}</div>
            <div class="tool-head-info">
              <h1>{{ tool.name }}
                <span v-if="tool.is_featured" class="featured-tag">推荐</span>
              </h1>
              <p class="tool-desc">{{ tool.description }}</p>
              <div class="tool-head-meta">
                <span v-if="tool.category" class="meta-chip">{{ tool.category.icon }} {{ tool.category.name }}</span>
                <span class="meta-chip">{{ tool.view_count }} 次使用</span>
                <a v-if="tool.github_url" :href="tool.github_url" target="_blank" rel="noopener" class="meta-chip github">GitHub 源码 ↗</a>
              </div>
            </div>
          </div>
        </div>

        <!-- 工具内容区 -->
        <div class="tool-canvas">
          <!-- iframe 嵌入 -->
          <iframe v-if="tool.tool_type === 'iframe'" :src="tool.embed_url"
            class="tool-iframe" frameborder="0" allowfullscreen></iframe>

          <!-- 内置 HTML（用 iframe srcdoc 渲染，支持 JS 执行） -->
          <iframe v-else-if="tool.tool_type === 'builtin'" :srcdoc="tool.content"
            class="tool-builtin-iframe" frameborder="0"></iframe>

          <!-- 外链跳转 -->
          <div v-else-if="tool.tool_type === 'link'" class="tool-link-wrap">
            <p>此工具为外链跳转，点击下方按钮在新标签页打开。</p>
            <a :href="tool.embed_url" target="_blank" rel="noopener" class="open-btn">打开工具 ↗</a>
          </div>

          <div v-else class="tool-empty">工具内容配置有误，请联系管理员</div>
        </div>
      </template>
      <div v-else-if="!loading" class="not-found">
        <div class="nf-icon">🔍</div>
        <h2>工具不存在</h2>
        <RouterLink to="/tools" class="back-btn">返回工具箱</RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'

const route = useRoute()
const loading = ref(false)
const tool = ref(null)

const loadTool = async () => {
  loading.value = true
  try {
    const res = await api.getTool(route.params.slug)
    tool.value = res
    // 记录使用次数
    api.recordToolView(route.params.slug).catch(() => {})
  } catch (e) {
    tool.value = null
  } finally { loading.value = false }
}

onMounted(loadTool)
watch(() => route.params.slug, loadTool)
</script>

<style scoped>
.tool-detail-page { max-width: 1200px; margin: 0 auto; padding: 20px; }
.back-btn {
  display: inline-block; color: var(--brand); text-decoration: none;
  font-size: 13px; margin-bottom: 16px;
}
.back-btn:hover { text-decoration: underline; }

.tool-header {
  background: var(--surface); border: 1px solid var(--line); border-radius: 16px;
  padding: 24px; margin-bottom: 20px;
}
.tool-head-main { display: flex; gap: 20px; align-items: flex-start; }
.tool-icon-lg {
  width: 72px; height: 72px; border-radius: 16px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 40px;
  background: linear-gradient(135deg, var(--brand-50), var(--brand-100));
}
.tool-head-info { flex: 1; min-width: 0; }
.tool-head-info h1 { font-size: 24px; font-weight: 800; margin: 0 0 6px; display: flex; align-items: center; gap: 8px; }
.featured-tag {
  font-size: 11px; font-weight: 600; color: #fff;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  padding: 2px 8px; border-radius: 6px;
}
.tool-desc { color: var(--ink-3); font-size: 14px; margin: 0 0 12px; line-height: 1.6; }
.tool-head-meta { display: flex; gap: 8px; flex-wrap: wrap; }
.meta-chip {
  font-size: 12px; color: var(--ink-2); background: var(--bg);
  padding: 4px 12px; border-radius: 999px;
}
.meta-chip.github { color: var(--brand); text-decoration: none; }
.meta-chip.github:hover { background: var(--brand-50); }

.tool-canvas {
  background: var(--surface); border: 1px solid var(--line); border-radius: 16px;
  overflow: hidden; min-height: 600px;
}
.tool-iframe { width: 100%; height: 80vh; min-height: 600px; border: none; display: block; }
.tool-builtin-iframe { width: 100%; height: 80vh; min-height: 600px; border: none; display: block; background: #fff; }
.tool-link-wrap { text-align: center; padding: 80px 20px; }
.tool-link-wrap p { color: var(--ink-3); margin-bottom: 20px; }
.open-btn {
  display: inline-block; padding: 12px 32px; background: var(--brand); color: #fff;
  border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 15px;
}
.open-btn:hover { opacity: .9; }
.tool-empty { text-align: center; padding: 80px; color: var(--ink-3); }

.not-found { text-align: center; padding: 80px 20px; }
.nf-icon { font-size: 56px; margin-bottom: 16px; }
.not-found h2 { color: var(--ink-2); margin: 0 0 16px; }
</style>
