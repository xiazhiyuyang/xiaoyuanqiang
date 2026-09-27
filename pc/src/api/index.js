import client, { TOKEN_KEY } from './client'
import axios from 'axios'

export { TOKEN_KEY }

const api = {
  TOKEN_KEY,

  /* ---------------- 认证 ---------------- */
  register: (data) => client.post('/auth/register', data),
  login: (data) => client.post('/auth/login', data),
  emailRegister: (data) => client.post('/auth/email/register', data),
  emailVerify: (token) => client.post('/auth/email/verify', { token }),
  emailLogin: (data) => client.post('/auth/email/login', data),
  emailForgot: (email) => client.post('/auth/email/forgot', { email }),
  emailReset: (token, password) => client.post('/auth/email/reset', { token, password }),
  completeProfile: (data) => client.post('/auth/me/complete-profile', data),
  forgotQuestion: (username) => client.post('/auth/forgot/question', { username }, { silent: true }),
  forgotReset: (data) => client.post('/auth/forgot/reset', data),

  /* ---------------- 当前用户 ---------------- */
  getMe: () => client.get('/users/me'),
  getOverview: () => client.get('/users/me/overview'),
  updateMe: (data) => client.put('/users/me', data),
  changePassword: (data) => client.put('/users/me/password', data),
  setSecurityQuestion: (data) => client.put('/users/me/security-question', data),
  getDeletionStatus: () => client.get('/users/me/deletion-status'),
  requestDeletion: (password) => client.post('/users/me/deletion-request', { password }),
  cancelDeletion: () => client.post('/users/me/deletion-cancel'),
  getLevels: () => client.get('/users/levels'),
  getToolCategories: () => client.get('/tools/categories'),
  getTools: (params) => client.get('/tools', { params }),
  getTool: (slug) => client.get(`/tools/${slug}`),
  recordToolView: (slug) => client.post(`/tools/${slug}/view`),
  getReviewAccess: () => client.get('/users/me/review-access', { silent: true }),
  getMyPosts: (params) => client.get('/users/me/posts', { params, silent: true }),
  getMyFavorites: (params) => client.get('/users/me/favorites', { params, silent: true }),
  searchUsers: (params) => client.get('/users/search', { params, silent: true }),
  getSuggestions: () => client.get('/users/suggestions', { params: { limit: 5 }, silent: true }),

  /* ---------------- 他人主页 / 关注 ---------------- */
  getUser: (id) => client.get(`/users/${id}`),
  getUserPosts: (id, params) => client.get(`/users/${id}/posts`, { params, silent: true }),
  getFollows: (id, params) => client.get(`/users/${id}/follows`, { params, silent: true }),
  toggleFollow: (id) => client.post(`/users/${id}/follow`),
  getFollowStatus: (id) => client.get(`/users/${id}/follow`, { silent: true }),

  /* ---------------- 帖子 ---------------- */
  getPosts: (params) => client.get('/posts', { params, silent: true }),
  getPost: (id) => client.get(`/posts/${id}`),
  createPost: (data) => client.post('/posts', data),
  updatePost: (id, data) => client.put(`/posts/${id}`, data),
  deletePost: (id) => client.delete(`/posts/${id}`),
  likePost: (id) => client.post(`/posts/${id}/like`, {}, { silent: true }),
  favoritePost: (id) => client.post(`/posts/${id}/favorite`, {}, { silent: true }),
  getCategories: () => client.get('/posts/categories/list', { silent: true }),

  /* ---------------- 评论 ---------------- */
  getComments: (postId, params) => client.get(`/posts/${postId}/comments`, { params, silent: true }),
  createComment: (postId, data) => client.post(`/posts/${postId}/comments`, data),
  deleteComment: (postId, commentId) => client.delete(`/posts/${postId}/comments/${commentId}`),
  likeComment: (postId, commentId) => client.post(`/posts/${postId}/comments/${commentId}/like`, {}, { silent: true }),

  /* ---------------- 通知 ---------------- */
  getNotifications: (params) => client.get('/notifications', { params, silent: true }),
  getNotificationUnread: () => client.get('/notifications/unread-count', { silent: true }),
  readNotification: (id) => client.post(`/notifications/${id}/read`, {}, { silent: true }),
  readAllNotifications: () => client.post('/notifications/read-all'),
  submitAppeal: (data) => client.post('/ai-review/appeals', data),

  /* ---------------- 私信 ---------------- */
  getConversations: () => client.get('/messages/conversations', { silent: true }),
  createConversation: (data) =>
    client.post('/messages/conversations', typeof data === 'object' ? data : { target_user_id: data }),
  getMessages: (cid, params) => client.get(`/messages/conversations/${cid}/messages`, { params, silent: true }),
  sendMessage: (cid, data) =>
    client.post(`/messages/conversations/${cid}/messages`, typeof data === 'object' ? data : { content: data }, { silent: true }),
  markConversationRead: (cid) => client.post(`/messages/conversations/${cid}/read`, {}, { silent: true }),
  getMessageUnread: () => client.get('/messages/unread-count', { silent: true }),

  /* ---------------- 举报 / 运营位 / 配置 ---------------- */
  createReport: (data) => client.post('/reports', data),
  getPromotions: () => client.get('/promotions', { silent: true }),
  getPublicSettings: () => client.get('/settings/app', { silent: true }),

  /* ---------------- 审查中心 ---------------- */
  getReviewOverview: () => client.get('/review/overview', { silent: true }),
  getReviewPosts: (params) => client.get('/review/posts', { params, silent: true }),
  reviewPostAction: (id, body) =>
    client.post(`/review/posts/${id}/action`, body && body.action ? body : { action: body }),
  getReviewReports: (params) => client.get('/review/reports', { params, silent: true }),
  handleReport: (id, data) => client.post(`/review/reports/${id}/handle`, data),

  /* ---------------- 上传（带进度） ---------------- */
  uploadMedia(file, kind = 'image', onProgress) {
    const form = new FormData()
    form.append('file', file)
    return axios
      .post(`/api/upload/${kind === 'video' ? 'video' : 'image'}`, form, {
        headers: {
          'Content-Type': 'multipart/form-data',
          ...(localStorage.getItem(TOKEN_KEY)
            ? { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` }
            : {}),
        },
        timeout: kind === 'video' ? 120000 : 30000,
        onUploadProgress: (e) => {
          if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
        },
      })
      .then((r) => r.data.data)
      .catch((error) => {
        const msg = error.response?.data?.msg || error.response?.data?.detail ||
          (kind === 'video' ? '视频上传失败' : '图片上传失败')
        return Promise.reject(new Error(typeof msg === 'string' ? msg : '上传失败'))
      })
  },
}

export default api
