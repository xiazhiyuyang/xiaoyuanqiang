// 媒体地址与文本/时间格式化工具

// 后端返回的相对媒体路径（/uploads/...）在部署时位于站点根，而非 /pc 下；
// 直接补成根绝对路径，开发环境由 vite 代理转发。
export function mediaUrl(url) {
  if (!url) return ''
  if (/^https?:\/\//i.test(url) || url.startsWith('blob:') || url.startsWith('data:')) return url
  if (url.startsWith('//')) return window.location.protocol + url
  return url.startsWith('/') ? url : `/${url}`
}

// 匿名头像占位（基于 id 的稳定色块，内联 SVG，无额外请求）
export function anonymousAvatar(seed = '') {
  const key = String(seed)
  let h = 0
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0
  const hue = h % 360
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'>
    <rect width='120' height='120' rx='24' fill='hsl(${hue} 28% 88%)'/>
    <circle cx='60' cy='48' r='22' fill='hsl(${hue} 24% 62%)'/>
    <path d='M24 104c6-22 20-32 36-32s30 10 36 32z' fill='hsl(${hue} 24% 62%)'/></svg>`
  return 'data:image/svg+xml;utf8,' + encodeURIComponent(svg)
}

function pad(n) { return String(n).padStart(2, '0') }

export function formatDateTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

// 中文相对时间
export function timeAgo(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = Date.now()
  const diff = (now - d.getTime()) / 1000
  if (diff < 0) return '刚刚'
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 86400 * 2) return '昨天'
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} 天前`
  if (d.getFullYear() === new Date().getFullYear()) return `${d.getMonth() + 1}月${d.getDate()}日`
  return formatDate(iso)
}
