// 全局主题系统：两层维度
// 1) 配色主题 key：galaxy/ocean/forest/sunset/rose/midnight（只换品牌色与氛围）
// 2) 显示模式 mode：dark 深色 / light 浅色 / auto 跟随系统
// 所有页面根节点统一用全局 mixin 的 cwRootClass 同时挂「配色类 + 明暗类」。
import { reactive } from 'vue'
// navBg 为深色不透明导航栏底色；swatch 用于设置页色卡预览
export const THEMES = [
  {
    key: 'galaxy', name: '星云紫', desc: '深邃宇宙 · 默认',
    swatch: ['#8b7cf6', '#6ee7ff'], navBg: '#0a0c2b',
  },
  {
    key: 'ocean', name: '深海蓝', desc: '静谧海洋',
    swatch: ['#38bdf8', '#22d3ee'], navBg: '#062033',
  },
  {
    key: 'forest', name: '极光青', desc: '极光森林',
    swatch: ['#34d399', '#2dd4bf'], navBg: '#052b20',
  },
  {
    key: 'sunset', name: '落日橙', desc: '黄昏暖光',
    swatch: ['#fb923c', '#f472b6'], navBg: '#2a120a',
  },
  {
    key: 'rose', name: '樱花粉', desc: '柔和夜樱',
    swatch: ['#f472b6', '#c084fc'], navBg: '#2a0f22',
  },
  {
    key: 'midnight', name: '极夜青', desc: '极简克制',
    swatch: ['#818cf8', '#67e8f9'], navBg: '#0a0b14',
  },
]
export const MODES = [
  { key: 'light', name: '浅色', icon: '☀️' },
  { key: 'dark', name: '深色', icon: '🌙' },
  { key: 'auto', name: '跟随系统', icon: '📱' },
]
const STORAGE_KEY = 'cw_theme'
const MODE_KEY = 'cw_mode'
const USER_SET_KEY = 'cw_theme_chosen_by_user'
const VALID_MODE_KEYS = MODES.map((m) => m.key)
function stored() {
  const k = uni.getStorageSync(STORAGE_KEY)
  return THEMES.some((t) => t.key === k) ? k : 'galaxy'
}
function storedMode() {
  const m = uni.getStorageSync(MODE_KEY)
  return VALID_MODE_KEYS.includes(m) ? m : 'dark'
}
// 全局唯一响应式主题状态，所有页面通过全局 mixin 的 cwTheme / cwMode 读取
export const themeState = reactive({ key: stored(), mode: storedMode() })
export function getTheme() {
  return THEMES.find((t) => t.key === themeState.key) || THEMES[0]
}
// 系统当前是否为浅色外观
export function systemPrefersLight() {
  // #ifdef H5
  try {
    return !!window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches
  } catch (e) { /* ignore */ }
  // #endif
  // #ifdef APP-PLUS
  try {
    // plus.navigator.getUIStyle: 'light'（浅色界面）/ 'dark'
    return plus.navigator.getUIStyle() === 'light'
  } catch (e) { /* ignore */ }
  // #endif
  return false
}
// 实际生效的明暗：auto 时解析系统偏好
export function effectiveMode() {
  if (themeState.mode === 'auto') return systemPrefersLight() ? 'light' : 'dark'
  return themeState.mode
}
export function isLight() {
  return effectiveMode() === 'light'
}
// H5：把明暗类挂到 <html>，用于切换 body 背景 / 隐藏星空
function applyRootClass() {
  // #ifdef H5
  try {
    const light = isLight()
    document.documentElement.classList.toggle('cw-light', light)
    document.documentElement.classList.toggle('cw-dark', !light)
  } catch (e) { /* ignore */ }
  // #endif
}
// 同步系统导航栏 / 底部 TabBar 颜色（主题切换、页面 onShow 时调用）
export function applyNavColor() {
  const light = isLight()
  const t = getTheme()
  try {
    uni.setNavigationBarColor({
      frontColor: light ? '#000000' : '#ffffff',
      backgroundColor: light ? '#f4f5fb' : t.navBg,
      animation: { duration: 120 },
    })
  } catch (e) { /* 部分平台不支持 */ }
  try {
    uni.setTabBarStyle({
      color: light ? '#6b6f92' : '#9a9daf',
      selectedColor: light ? '#7c6cf0' : '#8b7cf6',
      backgroundColor: light ? '#ffffff' : '#10123259',
      borderStyle: light ? 'black' : 'black',
    })
  } catch (e) { /* 未渲染 tabBar 时忽略 */ }
}
function applyAll() {
  applyRootClass()
  applyNavColor()
}
// 用户手动选择配色
export function setTheme(key) {
  if (!THEMES.some((t) => t.key === key)) return
  themeState.key = key
  uni.setStorageSync(STORAGE_KEY, key)
  uni.setStorageSync(USER_SET_KEY, 1)
  applyAll()
}
// 用户手动选择明暗模式
export function setMode(mode) {
  if (!VALID_MODE_KEYS.includes(mode)) return
  themeState.mode = mode
  uni.setStorageSync(MODE_KEY, mode)
  uni.setStorageSync(USER_SET_KEY, 1)
  applyAll()
}
// App 启动：若用户从未手动选过，则跟随后台配置的默认配色
export function applyServerDefault(key) {
  if (uni.getStorageSync(USER_SET_KEY)) {
    applyAll()
    return
  }
  if (key && THEMES.some((t) => t.key === key) && key !== themeState.key) {
    themeState.key = key
    uni.setStorageSync(STORAGE_KEY, key)
  }
  applyAll()
}
// 登录后用后端保存的个人偏好同步（主题/明暗），未手动选择过也以账号偏好为准
export function applyUserPreferences(prefs) {
  if (!prefs || typeof prefs !== 'object') { applyAll(); return }
  let changed = false
  if (prefs.theme && THEMES.some((t) => t.key === prefs.theme)) {
    themeState.key = prefs.theme
    uni.setStorageSync(STORAGE_KEY, prefs.theme)
    changed = true
  }
  if (prefs.mode && VALID_MODE_KEYS.includes(prefs.mode)) {
    themeState.mode = prefs.mode
    uni.setStorageSync(MODE_KEY, prefs.mode)
    changed = true
  }
  if (changed) uni.setStorageSync(USER_SET_KEY, 1)
  applyAll()
}
// 页面根节点 class：配色类 + 明暗类（三端通用，CSS 变量沿根 view 继承覆盖）
export function rootClass() {
  return ['cw-t-' + themeState.key, 'cw-' + effectiveMode()]
}
// #ifdef H5
// auto 模式下系统外观变化时实时跟随
try {
  const mq = window.matchMedia('(prefers-color-scheme: light)')
  const listener = () => { if (themeState.mode === 'auto') applyAll() }
  if (mq.addEventListener) mq.addEventListener('change', listener)
  else if (mq.addListener) mq.addListener(listener)
} catch (e) { /* ignore */ }
// #endif
// 模块加载即应用一次，避免 H5 首屏闪烁
applyRootClass()
