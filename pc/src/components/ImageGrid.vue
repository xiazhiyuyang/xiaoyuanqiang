<template>
  <div v-if="urls.length" class="img-grid" :class="gridClass" :style="gridStyle">
    <button
      v-for="(u, i) in urls" :key="i" type="button"
      class="img-cell"
      :class="{ single: urls.length === 1 }"
      @click="open(i)"
    >
      <img :src="mediaUrl(u)" :alt="`配图 ${i + 1}`" loading="lazy" referrerpolicy="no-referrer" />
    </button>

    <Teleport to="body">
      <Transition name="lb">
        <div v-if="index !== null" class="lb-mask" @click.self="close" role="dialog" aria-modal="true">
          <button class="lb-nav lb-prev" aria-label="上一张" @click="step(-1)" v-if="urls.length > 1"><Icon name="chevron-left" :size="24" /></button>
          <img class="lb-img" :src="mediaUrl(urls[index])" :alt="`配图 ${index + 1}`" @click.stop />
          <button class="lb-nav lb-next" aria-label="下一张" @click="step(1)" v-if="urls.length > 1"><Icon name="chevron-right" :size="24" /></button>
          <button class="lb-close" aria-label="关闭" @click="close"><Icon name="x" :size="22" /></button>
          <span v-if="urls.length > 1" class="lb-count">{{ index + 1 }} / {{ urls.length }}</span>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import Icon from './Icon.vue'
import { mediaUrl } from '../utils/format'

const props = defineProps({
  images: { type: Array, default: () => [] },
  maxHeight: { type: Number, default: 420 },
})

const urls = computed(() =>
  (props.images || []).map((x) => (typeof x === 'string' ? x : x.url)).filter(Boolean)
)
const n = computed(() => urls.value.length)
const gridClass = computed(() => `g${Math.min(n.value, 9)}`)
const gridStyle = computed(() => (n.value === 1 ? { maxWidth: props.maxHeight + 'px' } : {}))

const index = ref(null)
function open(i) { index.value = i }
function close() { index.value = null }
function step(d) {
  if (index.value === null) return
  index.value = (index.value + d + n.value) % n.value
}
function onKey(e) {
  if (index.value === null) return
  if (e.key === 'Escape') close()
  if (e.key === 'ArrowLeft') step(-1)
  if (e.key === 'ArrowRight') step(1)
}
watch(index, (v) => { document.body.style.overflow = v !== null ? 'hidden' : '' ; window[v !== null ? 'addEventListener' : 'removeEventListener']('keydown', onKey) })
onBeforeUnmount(() => { document.body.style.overflow = ''; window.removeEventListener('keydown', onKey) })
</script>

<style scoped>
.img-grid { display: grid; gap: 4px; width: 100%; }
.img-cell {
  position: relative; width: 100%; padding-top: 100%;
  border-radius: var(--r-sm); overflow: hidden; background: var(--surface-3);
}
.img-cell img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; transition: transform .35s var(--ease-out); }
.img-cell:hover img { transform: scale(1.03); }
.g1 { grid-template-columns: 1fr; }
.g1 .single { padding-top: 62%; max-height: var(--maxH, 420px); }
.g1 .single img { object-fit: cover; }
.g2, .g4 { grid-template-columns: repeat(2, 1fr); }
.g3 { grid-template-columns: repeat(3, 1fr); }
.g5, .g6 { grid-template-columns: repeat(3, 1fr); }
.g7, .g8, .g9 { grid-template-columns: repeat(3, 1fr); }

.lb-mask {
  position: fixed; inset: 0; z-index: var(--z-modal);
  background: rgba(8, 14, 12, .86); backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center; padding: 40px;
}
.lb-img { max-width: min(92vw, 1100px); max-height: 88vh; border-radius: var(--r-md); box-shadow: var(--shadow-lg); }
.lb-nav, .lb-close {
  position: absolute; width: 44px; height: 44px; border-radius: 50%;
  background: rgba(255,255,255,.12); color: #fff; display: flex; align-items: center; justify-content: center;
  transition: background var(--t-fast);
}
.lb-nav:hover, .lb-close:hover { background: rgba(255,255,255,.24); }
.lb-prev { left: 24px; } .lb-next { right: 24px; }
.lb-close { top: 22px; right: 24px; }
.lb-count { position: absolute; bottom: 26px; left: 50%; transform: translateX(-50%); color: rgba(255,255,255,.85); font-size: 13px; font-variant-numeric: tabular-nums; }
.lb-enter-active, .lb-leave-active { transition: opacity var(--t-base) var(--ease-out); }
.lb-enter-from, .lb-leave-to { opacity: 0; }
</style>
