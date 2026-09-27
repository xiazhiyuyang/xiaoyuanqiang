// API 请求封装
// 打包APK前需将 SERVER 改为后端公网地址，必须使用HTTPS域名。
// H5端走同源相对路径；App/小程序必须用完整地址。
const SERVER = 'https://cy.ihyuan.cn'
let SERVER_URL = SERVER
// #ifdef H5
SERVER_URL = ''
// #endif
export { SERVER_URL }

let BASE_URL = '/api'
// #ifndef H5
BASE_URL = SERVER + '/api'
// #endif
export const API_BASE_URL = BASE_URL

// WebSocket地址：H5同源自动继承协议；App/小程序必须完整地址。
export const WS_URL = (() => {
  // #ifdef H5
  const proto = typeof location !== 'undefined' && location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = typeof location !== 'undefined' ? location.host : ''
  return `${proto}//${host}/ws/realtime`
  // #endif
  // #ifndef H5
  return SERVER.replace(/^http/, 'ws') + '/ws/realtime'
  // #endif
})()

// 把后端返回的相对媒体路径（/uploads/xxx）补成可访问的完整地址。
// App 端没有 host，直接用相对路径必然加载失败——所有 <image>/<video> 都必须走这里。
export const resolveServerUrl = (url) => {
  if (!url) return ''
  if (/^https?:\/\//i.test(url) || /^blob:/i.test(url)) return url
  if (url.startsWith('//')) return 'http:' + url
  return SERVER_URL + (url.startsWith('/') ? url : `/${url}`)
}
export const mediaUrl = resolveServerUrl

// 默认头像（本地静态图，避免再发一次网络请求）
export const DEFAULT_AVATAR = '/static/default-avatar.png'

const friendlyError = (err) => {
  const msg = (err && (err.errMsg || err.message)) || ''
  if (/timeout/i.test(msg)) return '请求超时，请检查网络后重试'
  if (/abort/i.test(msg)) return '请求已取消'
  if (/fail|network|connect/i.test(msg)) return '无法连接服务器，请检查网络或稍后再试'
  return '网络异常，请稍后再试'
}

const request = (options) => {
  return new Promise((resolve, reject) => {
    const token = uni.getStorageSync('token')
    if (options.loading) uni.showLoading({ title: options.loadingText || '加载中', mask: true })
    uni.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data,
      timeout: options.timeout || 15000,
      header: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.header,
      },
      success: (res) => {
        const data = res.data || {}
        let message = '请求失败'
        if (Array.isArray(data.detail)) {
          message = data.detail.map((item) => String(item?.msg || '参数有误').replace(/^Value error,\s*/, '')).join('；')
        } else if (typeof data.detail === 'string') {
          message = data.detail
        } else {
          message = data.msg || data.message || (res.statusCode >= 500 ? '服务器开小差了，请稍后再试' : '请求失败')
        }
        if (res.statusCode === 401) {
          if (!options.url.startsWith('/auth/') && !options.silent) {
            uni.removeStorageSync('token')
            uni.removeStorageSync('userInfo')
            uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
            setTimeout(() => uni.navigateTo({ url: '/pages/login/login' }), 600)
          } else if (!options.silent) {
            uni.showToast({ title: message || '账号或密码不正确', icon: 'none' })
          }
          reject(data)
          return
        }
        if (res.statusCode >= 400 || data.code !== 0) {
          if (res.statusCode === 403) message = message || '没有权限执行此操作'
          if (res.statusCode === 404) message = message || '内容不存在或已被删除'
          if (!options.silent) uni.showToast({ title: message, icon: 'none' })
          reject(data)
          return
        }
        resolve(data.data)
      },
      fail: (err) => {
        if (!options.silent) uni.showToast({ title: friendlyError(err), icon: 'none' })
        reject(err)
      },
      complete: () => { if (options.loading) uni.hideLoading() },
    })
  })
}

// 通用上传（图片/视频），onProgress 回调进度 0-100
const uploadFile = (url, filePath, { onProgress, loadingText } = {}) => {
  return new Promise((resolve, reject) => {
    const token = uni.getStorageSync('token')
    if (loadingText) uni.showLoading({ title: loadingText, mask: true })
    const task = uni.uploadFile({
      url: BASE_URL + url,
      filePath,
      name: 'file',
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        let data
        try { data = JSON.parse(res.data) } catch (e) { data = {} }
        if (res.statusCode === 413 || (data && data.code === 413)) {
          reject({ msg: '文件过大，请压缩后再上传' }); return
        }
        if (data.code === 0) resolve(data.data)
        else reject(data.msg ? data : { ...data, msg: data.msg || '上传失败，请重试' })
      },
      fail: (err) => reject({ ...err, msg: friendlyError(err) }),
      complete: () => uni.hideLoading(),
    })
    if (onProgress && task && task.onProgressUpdate) {
      task.onProgressUpdate((p) => onProgress(p.progress || 0))
    }
  })
}

export const api = {
  // 认证
  register: (data, opts) => request({ url: '/auth/register', method: 'POST', data, ...opts }),
  login: (data, opts) => request({ url: '/auth/login', method: 'POST', data, ...opts }),
  wechatLogin: (code, scene = 'mp') => request({ url: '/auth/wechat', method: 'POST', data: { code, scene } }),
  // 用户
  getMe: () => request({ url: '/users/me' }),
  getMyOverview: () => request({ url: '/users/me/overview' }),
  updateMe: (data) => request({ url: '/users/me', method: 'PUT', data }),
  getUserProfile: (id, opts) => request({ url: `/users/${id}`, ...opts }),
  getUserPosts: (id, params) => request({ url: `/users/${id}/posts`, data: params }),
  // 我的发布 / 我的收藏 / 用户搜索
  getMyPosts: (params) => request({ url: '/users/me/posts', data: params, silent: true }),
  getMyFavorites: (params) => request({ url: '/users/me/favorites', data: params, silent: true }),
  searchUsers: (params) => request({ url: '/users/search', data: params, silent: true }),
  // 关注 / 粉丝
  toggleFollow: (id) => request({ url: `/users/${id}/follow`, method: 'POST', silent: true }),
  getFollowStatus: (id, opts) => request({ url: `/users/${id}/follow`, ...(opts || { silent: true }) }),
  getMyFollows: (type) => request({ url: '/users/me/follows', data: { type }, silent: true }),
  getUserFollows: (id, type) => request({ url: `/users/${id}/follows`, data: { type }, silent: true }),
  getSuggestions: () => request({ url: '/users/suggestions?limit=5', silent: true }),
  // 帖子
  getPosts: (params) => request({ url: '/posts', data: params }),
  getPost: (id) => request({ url: `/posts/${id}` }),
  createPost: (data) => request({ url: '/posts', method: 'POST', data }),
  likePost: (id) => request({ url: `/posts/${id}/like`, method: 'POST', silent: true }),
  favoritePost: (id) => request({ url: `/posts/${id}/favorite`, method: 'POST', silent: true }),
  updatePost: (id, data) => request({ url: `/posts/${id}`, method: 'PUT', data }),
  deletePost: (id) => request({ url: `/posts/${id}`, method: 'DELETE' }),
  // 分类
  getCategories: () => request({ url: '/posts/categories/list' }),
  getPromotions: () => request({ url: '/promotions' }),
  getAppVersion: (params) => request({ url: '/app/version', data: params }),
  getPublicSettings: () => request({ url: '/settings/app', method: 'GET', auth: false }),
  // 评论
  getComments: (postId, params) => request({ url: `/posts/${postId}/comments`, data: params }),
  createComment: (postId, data) => request({ url: `/posts/${postId}/comments`, method: 'POST', data }),
  likeComment: (postId, commentId) => request({ url: `/posts/${postId}/comments/${commentId}/like`, method: 'POST', silent: true }),
  // 互动通知（私信红点走 messages/unread-count，二者分开）
  getNotifications: (params) => request({ url: '/notifications', data: params }),
  getUnreadCount: () => request({ url: '/notifications/unread-count', silent: true }),
  readAllNotifications: () => request({ url: '/notifications/read-all', method: 'POST' }),
  readNotification: (id) => request({ url: `/notifications/${id}/read`, method: 'POST', silent: true }),
  // 私信
  getConversations: () => request({ url: '/messages/conversations' }),
  createConversation: (targetUserId) => request({ url: '/messages/conversations', method: 'POST', data: { target_user_id: targetUserId } }),
  getMessages: (conversationId, params) => request({ url: `/messages/conversations/${conversationId}/messages`, data: params }),
  sendMessage: (conversationId, content) => request({ url: `/messages/conversations/${conversationId}/messages`, method: 'POST', data: { content }, silent: true }),
  getMessageUnreadCount: () => request({ url: '/messages/unread-count', silent: true }),
  readConversation: (conversationId) => request({ url: `/messages/conversations/${conversationId}/read`, method: 'POST', silent: true }),
  // 举报
  createReport: (data) => request({ url: '/reports', method: 'POST', data }),
  // 等级 / 账号安全
  getLevels: () => request({ url: '/users/levels', silent: true }),
  getReviewAccess: () => request({ url: '/users/me/review-access', silent: true }),
  changePassword: (data) => request({ url: '/users/me/password', method: 'PUT', data }),
  setSecurity: (data) => request({ url: '/users/me/security-question', method: 'PUT', data }),
  forgotQuestion: (username) => request({ url: '/auth/forgot/question', method: 'POST', data: { username }, silent: true }),
  forgotReset: (data) => request({ url: '/auth/forgot/reset', method: 'POST', data }),
  // 审查中心（被授权普通用户）
  reviewOverview: () => request({ url: '/review/overview', silent: true }),
  reviewPosts: (params) => request({ url: '/review/posts', data: params, silent: true }),
  reviewPostAction: (id, action) => request({ url: `/review/posts/${id}/action`, method: 'POST', data: { action } }),
  reviewReports: (params) => request({ url: '/review/reports', data: params, silent: true }),
  reviewHandleReport: (id, data) => request({ url: `/review/reports/${id}/handle`, method: 'POST', data }),
  // 上传
  uploadImage: (filePath, onProgress) => uploadFile('/upload/image', filePath, { onProgress, loadingText: '图片上传中' }),
  uploadVideo: (filePath, onProgress) => uploadFile('/upload/video', filePath, { onProgress, loadingText: '视频上传中' }),
}
