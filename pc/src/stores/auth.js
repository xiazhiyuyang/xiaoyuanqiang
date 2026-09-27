import { defineStore } from 'pinia'
import api, { TOKEN_KEY } from '../api'
import { getOrCreateDeviceCode, getFingerprintHash } from '../utils/device-fingerprint'

function buildDeviceInfo() {
  return { device_code: getOrCreateDeviceCode(), fingerprint_hash: getFingerprintHash() }
}

export const useAuth = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: null,
    ready: false,
    reviewAccess: { content_review: false, report_review: false, is_admin: false },
  }),
  getters: {
    isLoggedIn: (s) => !!s.token && !!s.user,
    isAdmin: (s) => s.user?.role === 'admin',
    canContentReview: (s) => s.reviewAccess.content_review || s.reviewAccess.is_admin,
    canReportReview: (s) => s.reviewAccess.report_review || s.reviewAccess.is_admin,
    canAnyReview() {
      return this.canContentReview || this.canReportReview
    },
  },
  actions: {
    setToken(token) {
      this.token = token
      if (token) localStorage.setItem(TOKEN_KEY, token)
      else localStorage.removeItem(TOKEN_KEY)
    },
    async bootstrap() {
      try {
        const tasks = [api.getPublicSettings().catch(() => null)]
        if (this.token) {
          tasks.push(this.fetchMe())
        }
        const [settings] = await Promise.all(tasks)
        this._settings = settings
      } finally {
        this.ready = true
      }
    },
    async fetchMe() {
      const me = await api.getMe()
      this.user = me
      try { this.reviewAccess = await api.getReviewAccess() } catch { /* 无权限则保持默认 */ }
      return me
    },
    async login(username, password) {
      const deviceInfo = buildDeviceInfo()
      const r = await api.login({ username, password, ...deviceInfo })
      this.setToken(r.access_token)
      this.user = r.user
      await this.fetchMe().catch(() => {})
      return r
    },
    async register(payload) {
      const deviceInfo = buildDeviceInfo()
      const r = await api.register({ ...payload, ...deviceInfo })
      this.setToken(r.access_token)
      this.user = r.user
      await this.fetchMe().catch(() => {})
      return r
    },
    async emailRegister(payload) {
      const deviceInfo = buildDeviceInfo()
      return await api.emailRegister({ ...payload, ...deviceInfo })
    },
    async emailVerify(token) {
      const r = await api.emailVerify(token)
      this.setToken(r.access_token)
      this.user = r.user
      await this.fetchMe().catch(() => {})
      return r
    },
    async emailLogin(email, password) {
      const deviceInfo = buildDeviceInfo()
      const r = await api.emailLogin({ email, password, ...deviceInfo })
      this.setToken(r.access_token)
      this.user = r.user
      await this.fetchMe().catch(() => {})
      return r
    },
    async emailForgot(email) { return await api.emailForgot(email) },
    async emailReset(token, password) { return await api.emailReset(token, password) },
    async completeProfile(data) {
      const r = await api.completeProfile(data)
      this.user = r
      return r
    },
    logout() {
      this.setToken('')
      this.user = null
      this.reviewAccess = { content_review: false, report_review: false, is_admin: false }
    },
  },
})
