import { defineStore } from 'pinia'
import api from '../api'
import { useAuth } from './auth'

export const useApp = defineStore('app', {
  state: () => ({
    settings: null,
    theme: localStorage.getItem('pc_theme') || 'system', // light | dark | system（明暗模式）
    colorTheme: localStorage.getItem('pc_color_theme') || 'galaxy', // galaxy|ocean|forest|sunset|rose|midnight（配色主题）
    unreadNotify: 0,
    unreadMessage: 0,
    pollTimer: null,
    feedTick: 0, // 发帖/编辑/删除后自增，信息流页面据此刷新
  }),
  getters: {
    siteName: (s) => s.settings?.site_name || '校园墙',
    slogan: (s) => s.settings?.site_slogan || '同校人的校园社区',
  },
  actions: {
    async loadSettings() {
      try { this.settings = await api.getPublicSettings() } catch { /* 静默 */ }
    },
    applyTheme() {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      const dark = this.theme === 'dark' || (this.theme === 'system' && prefersDark)
      // 双轴主题：data-mode = 明暗，data-theme = 配色
      document.documentElement.setAttribute('data-mode', dark ? 'dark' : 'light')
      document.documentElement.setAttribute('data-theme', this.colorTheme)
    },
    setTheme(t) {
      this.theme = t
      localStorage.setItem('pc_theme', t)
      this.applyTheme()
    },
    setColorTheme(t) {
      this.colorTheme = t
      localStorage.setItem('pc_color_theme', t)
      this.applyTheme()
    },
    bumpFeed() { this.feedTick += 1 },
    async refreshUnread() {
      const auth = useAuth()
      if (!auth.token) { this.unreadNotify = 0; this.unreadMessage = 0; return }
      try {
        const [n, m] = await Promise.all([api.getNotificationUnread(), api.getMessageUnread()])
        this.unreadNotify = n?.count ?? 0
        this.unreadMessage = m?.count ?? 0
      } catch { /* 静默 */ }
    },
    startPolling() {
      this.stopPolling()
      this.refreshUnread()
      this.pollTimer = setInterval(() => this.refreshUnread(), 45000)
      this._onFocus = () => this.refreshUnread()
      window.addEventListener('focus', this._onFocus)
    },
    stopPolling() {
      if (this.pollTimer) clearInterval(this.pollTimer)
      this.pollTimer = null
      if (this._onFocus) window.removeEventListener('focus', this._onFocus)
      this._onFocus = null
    },
  },
})
