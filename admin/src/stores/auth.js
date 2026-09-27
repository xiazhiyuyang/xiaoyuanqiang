import { defineStore } from 'pinia'
import api from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('admin_token') || '',
    user: JSON.parse(localStorage.getItem('admin_user') || 'null'),
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    async login(username, password) {
      const res = await api.post('/auth/login', { username, password })
      this.token = res.data.access_token
      this.user = res.data.user
      localStorage.setItem('admin_token', this.token)
      localStorage.setItem('admin_user', JSON.stringify(this.user))
      return res.data.user
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_user')
    },
  },
})
