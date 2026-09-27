<template>
  <section v-if="banners.length || announcements.length" class="promo card">
    <div v-if="banners.length" class="banner" @click="openBanner(banners[0])">
      <img v-if="banners[0].image_url" :src="mediaUrl(banners[0].image_url)" :alt="banners[0].title" referrerpolicy="no-referrer" />
      <div v-else class="banner-fallback" :style="{ background: bannerBg(banners[0].theme) }">
        <Icon name="sparkles" :size="20" /><span>{{ banners[0].title }}</span>
      </div>
      <span v-if="banners.length > 1" class="banner-count">{{ banners.length }}</span>
    </div>
    <div v-if="announcements.length" class="ann-marquee" @mouseenter="paused=true" @mouseleave="paused=false">
      <div class="ann-tag"><Icon name="bell" :size="12" /> 公告</div>
      <div class="ann-viewport">
        <div
          :key="currentIdx" class="ann-item"
          :class="[paused, { single: announcements.length === 1 }]"
          @animationend="next"
        >
          <a v-if="current.link_url" :href="current.link_url" target="_blank" rel="noopener">{{ current.content }}</a>
          <span v-else>{{ current.content }}</span>
        </div>
      </div>
      <span v-if="announcements.length > 1" class="ann-count">{{ currentIdx + 1 }}/{{ announcements.length }}</span>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Icon from './Icon.vue'
import api from '../api'
import { mediaUrl } from '../utils/format'

const banners = ref([])
const announcements = ref([])
const currentIdx = ref(0)
const paused = ref(false)

const current = computed(() => announcements.value[currentIdx.value] || { content: '' })

onMounted(async () => {
  try {
    const r = await api.getPromotions()
    banners.value = r.banners || []
    announcements.value = r.announcements || []
  } catch { /* 静默 */ }
})
function next() {
  if (announcements.value.length > 1) {
    currentIdx.value = (currentIdx.value + 1) % announcements.value.length
  }
}
function openBanner(b) { if (b.link_url) window.open(b.link_url, '_blank', 'noopener') }
function bannerBg(theme) {
  const map = {
    teal: 'linear-gradient(135deg,#1f9685,#106a5d)',
    blue: 'linear-gradient(135deg,#3f7fd4,#2c5fa8)',
    orange: 'linear-gradient(135deg,#e0913f,#c46f1f)',
    rose: 'linear-gradient(135deg,#d96a8a,#b9476b)',
  }
  return map[theme] || map.teal
}
</script>

<style scoped>
.promo { overflow: hidden; }
.banner { position: relative; cursor: pointer; aspect-ratio: 16/8; background: var(--surface-3); }
.banner img { width: 100%; height: 100%; object-fit: cover; }
.banner-fallback { height: 100%; display: flex; align-items: center; justify-content: center; gap: 10px; color: #fff; font-weight: 600; font-size: 15px; padding: 12px; text-align: center; }
.banner-count {
  position: absolute; right: 10px; bottom: 10px; background: rgba(0,0,0,.55); color: #fff;
  font-size: 11px; border-radius: 999px; padding: 2px 8px;
}
.ann-marquee {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-top: 1px solid var(--line);
  background: var(--warning-bg);
}
.ann-tag {
  flex: none; display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; font-weight: 650; color: var(--warning);
  background: var(--surface); padding: 3px 8px; border-radius: 4px;
}
.ann-viewport { flex: 1; position: relative; overflow: hidden; height: 20px; }
.ann-item {
  position: absolute; top: 0; left: 0;
  white-space: nowrap; font-size: 13px; color: var(--ink-2);
  line-height: 20px;
  animation: ann-scroll 10s linear forwards;
}
.ann-item.single { animation-iteration-count: infinite; }
.ann-item.paused { animation-play-state: paused; }
.ann-item a { color: inherit; text-decoration: none; }
.ann-item a:hover { color: var(--brand-700); }
.ann-count {
  flex: none; font-size: 11px; color: var(--ink-3);
  background: var(--surface); padding: 2px 7px; border-radius: 4px;
}
@keyframes ann-scroll {
  from { left: 100%; transform: translateX(0); }
  to { left: 0; transform: translateX(-100%); }
}
</style>
