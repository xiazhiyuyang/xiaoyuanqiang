<template>
  <div class="levels">
    <div v-if="mine" class="mine-card">
      <div class="mine-glow" :style="{ background: `radial-gradient(circle at 80% 0%, ${mine.color}33, transparent 60%)` }" />
      <div class="mine-row">
        <span class="mine-star" :style="{ color: mine.color }">
          <svg viewBox="0 0 24 24" width="34" height="34" fill="currentColor"><path d="m12 2 2.9 6.2 6.8.8-5 4.6 1.3 6.7L12 17.2 6 20.3l1.3-6.7-5-4.6 6.8-.8z"/></svg>
        </span>
        <div class="grow">
          <h2>Lv.{{ mine.level }} {{ mine.name }}</h2>
          <p class="muted">当前经验 <span class="tabular">{{ mine.exp }}</span>{{ mine.is_max ? '，已达最高等级' : ` · 距下一级还需 ${mine.remain} 经验` }}</p>
        </div>
      </div>
      <div class="progress">
        <div class="progress-bar" :style="{ width: mine.progress + '%', background: mine.color }" />
      </div>
      <div class="feature-gates">
        <span v-for="(ok, key) in features" :key="key" class="gate" :class="{ on: ok }">
          <Icon :name="ok ? 'check' : 'lock'" :size="13" /> {{ featureLabel(key) }}
        </span>
      </div>
    </div>

    <div class="card ladder">
      <h3 class="ladder-title">星轨等级表</h3>
      <ul>
        <li v-for="lv in ladder" :key="lv.level" class="lv-row" :class="{ current: mine && lv.level === mine.level, passed: mine && lv.level < mine.level }">
          <span class="lv-badge" :style="{ color: lv.color, background: lv.color + '1f' }">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="m12 2 2.9 6.2 6.8.8-5 4.6 1.3 6.7L12 17.2 6 20.3l1.3-6.7-5-4.6 6.8-.8z"/></svg>
          </span>
          <div class="grow">
            <div class="lv-name">
              <strong>Lv.{{ lv.level }} {{ lv.name }}</strong>
              <span v-if="mine && lv.level === mine.level" class="lv-current">当前等级</span>
            </div>
            <div class="lv-unlock faint">
              <template v-if="lv.unlock.length">{{ lv.unlock.map((u) => u.label).join(' · ') }} 解锁</template>
              <template v-else>基础体验</template>
            </div>
          </div>
          <span class="lv-need tabular">{{ lv.need }} 经验</span>
        </li>
      </ul>
      <p class="ladder-tip faint">经验可通过每日登录、发布动态、评论互动和收获点赞获得，具体以社区规则为准。</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Icon from '../components/Icon.vue'
import api from '../api'

const ladder = ref([])
const mine = ref(null)
const features = ref({})
const LABELS = { post: '发布动态', comment: '评论互动', like: '点赞收藏', message: '私信', video: '发布视频', promotion: '推广位' }
function featureLabel(k) { return LABELS[k] || k }

onMounted(async () => {
  try {
    const r = await api.getLevels()
    ladder.value = r.ladder || []
    mine.value = r.mine || null
    features.value = r.features || {}
  } catch { /* */ }
})
</script>

<style scoped>
.mine-card {
  position: relative; overflow: hidden; background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--r-lg); box-shadow: var(--shadow-sm); padding: 22px 24px; margin-bottom: 16px;
}
.mine-glow { position: absolute; inset: 0; pointer-events: none; }
.mine-row { position: relative; display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.mine-star { width: 60px; height: 60px; border-radius: 18px; background: var(--surface-2); display: flex; align-items: center; justify-content: center; flex: none; }
.mine-row h2 { font-size: 20px; margin-bottom: 4px; }
.progress { height: 9px; border-radius: 999px; background: var(--surface-3); overflow: hidden; margin-bottom: 16px; }
.progress-bar { height: 100%; border-radius: 999px; transition: width .8s var(--ease-out); }
.feature-gates { display: flex; flex-wrap: wrap; gap: 8px; }
.gate { display: inline-flex; align-items: center; gap: 5px; font-size: 12.5px; padding: 4px 11px; border-radius: 999px; background: var(--surface-3); color: var(--ink-4); }
.gate.on { background: var(--brand-50); color: var(--brand-700); font-weight: 560; }

.ladder { padding: 20px 22px; }
.ladder-title { font-size: 16px; margin-bottom: 8px; }
.lv-row { display: flex; align-items: center; gap: 14px; padding: 13px 8px; border-radius: var(--r-md); }
.lv-row + .lv-row { border-top: 1px solid var(--line); }
.lv-badge { width: 38px; height: 38px; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex: none; }
.lv-name { display: flex; align-items: center; gap: 9px; }
.lv-name strong { font-size: 14.5px; color: var(--ink); }
.lv-current { font-size: 11px; font-weight: 650; color: var(--brand-700); background: var(--brand-50); padding: 1px 8px; border-radius: 999px; }
.lv-unlock { font-size: 12.5px; margin-top: 2px; }
.lv-need { font-size: 13px; color: var(--ink-3); flex: none; }
.lv-row.passed { opacity: .62; }
.ladder-tip { font-size: 12.5px; margin-top: 14px; line-height: 1.7; }
</style>
