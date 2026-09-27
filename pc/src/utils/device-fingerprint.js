/**
 * 轻量级浏览器设备指纹采集（参考 FingerprintJS 开源版核心原理）
 * 采集多维度浏览器/设备信号，计算稳定的指纹哈希。
 * 不依赖 Cookie/LocalStorage，清除数据或隐身模式下同一设备仍可识别。
 */

function fnv1a32(str) {
  let hash = 0x811c9dc5
  for (let i = 0; i < str.length; i++) {
    hash ^= str.charCodeAt(i)
    hash = (hash + ((hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24))) >>> 0
  }
  return hash.toString(16).padStart(8, '0')
}

function getCanvasFingerprint() {
  try {
    const canvas = document.createElement('canvas')
    canvas.width = 220
    canvas.height = 30
    const ctx = canvas.getContext('2d')
    if (!ctx) return 'no-canvas'
    ctx.textBaseline = 'top'
    ctx.font = "14px 'Arial'"
    ctx.fillStyle = '#f60'
    ctx.fillRect(0, 0, 220, 30)
    ctx.fillStyle = '#069'
    ctx.fillText('CampusWall-Fingerprint-中文', 2, 4)
    ctx.fillStyle = 'rgba(102, 204, 0, 0.7)'
    ctx.fillText('CampusWall-Fingerprint-中文', 4, 6)
    return fnv1a32(canvas.toDataURL())
  } catch (e) {
    return 'canvas-error'
  }
}

function getWebglFingerprint() {
  try {
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl')
    if (!gl) return 'no-webgl'
    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info')
    const renderer = debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : 'masked'
    const vendor = debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : 'masked'
    return fnv1a32(`${renderer}|${vendor}`)
  } catch (e) {
    return 'webgl-error'
  }
}

export function collectDeviceFingerprint() {
  const nav = navigator
  const signals = {
    ua: navigator.userAgent,
    platform: nav.platform || '',
    language: navigator.language || '',
    languages: (navigator.languages || []).join(','),
    screen: `${screen.width}x${screen.height}`,
    colorDepth: String(screen.colorDepth),
    pixelRatio: String(window.devicePixelRatio || 1),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
    timezoneOffset: String(new Date().getTimezoneOffset()),
    cpu: String(nav.hardwareConcurrency || 0),
    memory: String(nav.deviceMemory || 0),
    touch: String(nav.maxTouchPoints || 0),
    canvas: getCanvasFingerprint(),
    webgl: getWebglFingerprint(),
  }
  const raw = Object.keys(signals).sort().map(k => `${k}=${signals[k]}`).join('|')
  return { fingerprint: 'fp_' + fnv1a32(raw), signals }
}

export function getOrCreateDeviceCode() {
  try {
    let code = localStorage.getItem('device_code')
    if (!code) {
      const { fingerprint } = collectDeviceFingerprint()
      const salt = Math.random().toString(36).slice(2, 8)
      code = `${fingerprint}_${salt}`
      localStorage.setItem('device_code', code)
    }
    return code
  } catch (e) {
    return 'dev_unknown'
  }
}

export function getFingerprintHash() {
  try {
    return collectDeviceFingerprint().fingerprint
  } catch (e) {
    return 'fp_unknown'
  }
}
