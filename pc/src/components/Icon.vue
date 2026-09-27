<template>
  <svg
    class="cw-icon"
    viewBox="0 0 24 24"
    :width="size"
    :height="size"
    :class="{ filled }"
    fill="none"
    stroke="currentColor"
    :stroke-width="stroke"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <!-- 安全：图标来自内置静态白名单，编译为元素描述后用动态组件渲染，绝不使用 v-html -->
    <component
      v-for="(el, i) in body"
      :key="i"
      :is="el.tag"
      v-bind="el.attrs"
    />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 20 },
  stroke: { type: [Number, String], default: 1.8 },
})

// 统一 24x24、round 线帽的线性图标；FILLED 集合改为实心。
// 注意：这是源码内硬编码的可信 SVG 片段白名单，不接受任何用户输入。
const PATHS = {
  home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h5v-6h4v6h5V9.5"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  bell: '<path d="M18 8a6 6 0 1 0-12 0c0 7-3 8-3 8h18s-3-1-3-8"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
  message: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.4A8 8 0 1 1 21 12z"/>',
  send: '<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6 8-6s8 2 8 6"/>',
  users: '<circle cx="9" cy="8" r="3.4"/><path d="M2.5 20c0-3.4 2.9-5 6.5-5s6.5 1.6 6.5 5"/><path d="M16 5.2a3.4 3.4 0 0 1 0 6.4"/><path d="M17.5 15.2c2.6.6 4 2.2 4 4.8"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.2A1.6 1.6 0 0 0 7 19.4l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 4.6 15H4a2 2 0 1 1 0-4h.2A1.6 1.6 0 0 0 5 8.3l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 11 4.6V4a2 2 0 1 1 4 0v.2a1.6 1.6 0 0 0 2.7 1.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1A1.6 1.6 0 0 0 20.8 11H21a2 2 0 1 1 0 4z"/>',
  medal: '<circle cx="12" cy="14" r="5"/><path d="M8.5 13.5 7 3l5 3 5-3-1.5 10.5"/><path d="m12 12 .8 1.6 1.7.2-1.3 1.2.4 1.7L12 15.9l-1.6.8.4-1.7-1.3-1.2 1.7-.2z"/>',
  shield: '<path d="M12 3 5 6v5c0 4.5 3 8 7 10 4-2 7-5.5 7-10V6z"/><path d="m9 12 2 2 4-4"/>',
  tool: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.5-.5-.5-2.5z"/>',
  heart: '<path d="M12 20s-7.5-4.6-10-9.3C.4 7.6 2 4.5 5.2 4.5c2 0 3.3 1.1 4 2.3.7-1.2 2-2.3 4-2.3 3.2 0 4.8 3.1 3.2 6.2C19.5 15.4 12 20 12 20z"/>',
  bookmark: '<path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/>',
  comment: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.4A8 8 0 1 1 21 12z"/>',
  eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
  eyeOff: '<path d="M3 3l18 18"/><path d="M10.6 5.2A9.8 9.8 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a16 16 0 0 1-2.4 3.1M6.2 6.8A15.6 15.6 0 0 0 2.5 12S6 18.5 12 18.5c1.2 0 2.3-.3 3.3-.7"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2.5"/><circle cx="8.5" cy="9.5" r="1.6"/><path d="m4 17 5-4.5 3.5 3 2.5-2 5 4.5"/>',
  video: '<rect x="3" y="6" width="13" height="12" rx="2.5"/><path d="m16 10 5-3v10l-5-3z"/>',
  more: '<circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  trash: '<path d="M4 7h16"/><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/><path d="M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13"/><path d="M10 11v6M14 11v6"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  'chevron-down': '<path d="m6 9 6 6 6-6"/>',
  'chevron-up': '<path d="m6 15 6-6 6 6"/>',
  'chevron-right': '<path d="m9 6 6 6-6 6"/>',
  'chevron-left': '<path d="m15 6-6 6 6 6"/>',
  'arrow-left': '<path d="M19 12H5"/><path d="m11 6-6 6 6 6"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
  login: '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="m10 17 5-5-5-5"/><path d="M15 12H3"/>',
  'user-plus': '<circle cx="9" cy="8" r="3.4"/><path d="M2.5 20c0-3.4 2.9-5 6.5-5 1.2 0 2.3.2 3.3.6"/><path d="M18 8v6M15 11h6"/>',
  camera: '<path d="M4 8h3l1.5-2.5h7L17 8h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/><circle cx="12" cy="13" r="3.2"/>',
  lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/><circle cx="12" cy="15.5" r="1.2"/>',
  flag: '<path d="M5 21V4"/><path d="M5 4h11l-2 4 2 4H5"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4"/><path d="M21 3v6h-6"/>',
  pin: '<path d="M9 21l3-8 5-9-9 5-8 3z"/>',
  mask: '<path d="M12 3c-4 0-7 2.6-7 6.5 0 3 1.4 7 3.2 9.2.8 1 2.4 1 3.2 0 .5-.6 1.1-.6 1.6 0 .8 1 2.4 1 3.2 0C17.6 16.5 19 12.5 19 9.5 19 5.6 16 3 12 3z"/><path d="M8.5 10h.01M15.5 10h.01M9 13.5c.8.7 1.9 1 3 1s2.2-.3 3-1"/>',
  sun: '<circle cx="12" cy="12" r="4.2"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5z"/>',
  monitor: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
  location: '<path d="M12 21s-7-5.6-7-11a7 7 0 0 1 14 0c0 5.4-7 11-7 11z"/><circle cx="12" cy="10" r="2.6"/>',
  calendar: '<rect x="4" y="5" width="16" height="16" rx="2.5"/><path d="M8 3v4M16 3v4M4 10h16"/>',
  school: '<path d="m3 9 9-5 9 5-9 5z"/><path d="M7 11v5c0 1.4 2.2 2.5 5 2.5s5-1.1 5-2.5v-5"/><path d="M21 9v5"/>',
  sparkles: '<path d="M12 4l1.6 4.4L18 10l-4.4 1.6L12 16l-1.6-4.4L6 10l4.4-1.6z"/><path d="M18 15l.8 2.2L21 18l-2.2.8L18 21l-.8-2.2L15 18l2.2-.8z"/>',
  alert: '<circle cx="12" cy="12" r="9"/><path d="M12 7.5V13M12 16.5h.01"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5h.01"/>',
  ban: '<circle cx="12" cy="12" r="9"/><path d="m5.6 5.6 12.8 12.8"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.1.5l2-2a5 5 0 0 0-7.1-7.1l-1.2 1.2"/><path d="M14 11a5 5 0 0 0-7.1-.5l-2 2a5 5 0 0 0 7.1 7.1l1.2-1.2"/>',
  grid: '<rect x="3" y="3" width="7.5" height="7.5" rx="1.5"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5"/>',
  fire: '<path d="M12 3s4.5 4 4.5 8.5A4.5 4.5 0 0 1 12 16a4.5 4.5 0 0 1-4.5-4.5C7.5 8 12 3 12 3z"/><path d="M12 21a6 6 0 0 0 6-6c0-1.2-.4-2.3-1-3.2"/>',
  verified: '<path d="m12 2 2.4 1.8 3 .2.2 3L19.4 10l-1.4 2.7.9 2.9-2.7 1.3-2.2 2-2.2-2-2.7-1.3.9-2.9L8.6 10l1.8-3 .2-3 3-.2z"/><path d="m9.3 10 1.8 1.8 3.6-3.6"/>',
  inbox: '<path d="M4 13 6.5 5h11L20 13"/><path d="M4 13v6a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-6h-4.5a3.5 3.5 0 0 1-7 0z"/>',
  'check-double': '<path d="m2 12.5 4 4L14 8"/><path d="m10 14.5 2 2L22 7"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M19 19H6a2 2 0 0 0-2 2M9 7h6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
}

const FILLED = new Set(['heart', 'bookmark', 'pin', 'fire', 'verified'])

// 把可信的静态 SVG 片段字符串编译成 [{ tag, attrs }] 描述数组。
// 只在模块加载时对源码内白名单字符串执行一次，运行时不接触任何用户输入，
// 因此最终渲染不经过 innerHTML / v-html，彻底消除 XSS 面。
function compileIcon(svg) {
  const out = []
  const tagRe = /<(\w+)\s+([^>]*?)\/?\s*>/g
  let m
  while ((m = tagRe.exec(svg))) {
    const attrs = {}
    const attrRe = /([\w-]+)="([^"]*)"/g
    let am
    while ((am = attrRe.exec(m[2]))) attrs[am[1]] = am[2]
    out.push({ tag: m[1], attrs })
  }
  return out
}
const ICON_BODY = Object.fromEntries(
  Object.entries(PATHS).map(([k, v]) => [k, compileIcon(v)])
)

const body = computed(() => ICON_BODY[props.name] || ICON_BODY.info)
const filled = computed(() => FILLED.has(props.name))
</script>

<style scoped>
.cw-icon { flex: none; vertical-align: middle; }
.cw-icon.filled { fill: currentColor; stroke: none; }
</style>
