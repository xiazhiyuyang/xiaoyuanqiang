import axios from 'axios'
import { toast } from '../utils/toast'

export const TOKEN_KEY = 'pc_token'

const client = axios.create({ baseURL: '/api', timeout: 20000 })

client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

function errMessage(error) {
  const d = error.response?.data
  if (Array.isArray(d?.detail)) {
    return d.detail.map((i) => String(i?.msg || '参数有误').replace(/^Value error,\s*/, '')).join('；')
  }
  if (typeof d?.detail === 'string' && d.detail) return d.detail
  if (d?.msg) return d.msg
  if (error.code === 'ECONNABORTED') return '请求超时，请稍后重试'
  if (!error.response) return '无法连接服务器，请检查网络'
  const status = error.response.status
  if (status === 403) return '没有权限执行此操作'
  if (status === 404) return '内容不存在或已被删除'
  if (status >= 500) return '服务器开小差了，请稍后再试'
  return '请求失败，请稍后再试'
}

client.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res && typeof res === 'object' && 'code' in res) {
      if (res.code !== 0) {
        const msg = res.msg || '请求失败'
        if (!response.config?.silent) toast.error(msg)
        return Promise.reject(Object.assign(new Error(msg), { business: res }))
      }
      // 把后端 msg 挂到返回对象上，供提交后判断审核提示
      const _data = res.data
      if (_data && typeof _data === 'object' && !Array.isArray(_data)) {
        _data._msg = res.msg || ''
      }
      return _data
    }
    return res
  },
  (error) => {
    const status = error.response?.status
    const url = error.config?.url || ''
    const isAuthCall = url.includes('/auth/')
    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      if (!isAuthCall) {
        if (!error.config?.silent) toast.info('登录已过期，请重新登录')
        if (!location.pathname.endsWith('/login')) {
          const next = encodeURIComponent(location.pathname + location.search)
          location.assign(import.meta.env.BASE_URL + 'login?next=' + next)
        }
      } else if (!error.config?.silent) {
        toast.error(errMessage(error))
      }
      return Promise.reject(error)
    }
    const msg = errMessage(error)
    if (!error.config?.silent) toast.error(msg)
    return Promise.reject(error)
  }
)

export default client
