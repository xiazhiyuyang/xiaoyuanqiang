// 轻量全局提示（不依赖组件库），API 层与页面都可调用
let seq = 0
const listeners = new Set()

function pushToast(message, type = 'info', timeout = 2600) {
  const id = ++seq
  const toast = { id, message, type, timeout }
  listeners.forEach((fn) => fn(toast))
  return id
}

export const toast = {
  info: (m) => pushToast(m, 'info'),
  success: (m) => pushToast(m, 'success'),
  error: (m) => pushToast(m, 'error'),
}

export function onToast(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
