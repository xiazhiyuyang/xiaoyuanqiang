import { defineStore } from 'pinia'
import { api } from '../utils/api'
import { applyUserPreferences } from '../utils/theme'

const readUser = () => {
  try {
    const raw = uni.getStorageSync('userInfo')
    return raw ? JSON.parse(raw) : null
  } catch (e) {
    return null
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: uni.getStorageSync('token') || '',
    userInfo: readUser(),
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    setLogin(token, user) {
      this.token = token
      this.userInfo = user
      uni.setStorageSync('token', token)
      uni.setStorageSync('userInfo', JSON.stringify(user))
      // 登录后应用账号内保存的主题 / 明暗偏好
      applyUserPreferences(user && user.preferences)
    },
    setUser(user) {
      this.userInfo = user
      uni.setStorageSync('userInfo', JSON.stringify(user))
    },
    async login(username, password) {
      const data = await api.login({ username, password })
      this.setLogin(data.access_token, data.user)
      return data.user
    },
    async register(data) {
      const res = await api.register(data)
      this.setLogin(res.access_token, res.user)
      return res.user
    },
    async wechatLogin(code, scene = 'mp') {
      const data = await api.wechatLogin(code, scene)
      this.setLogin(data.access_token, data.user)
      return data.user
    },
    logout() {
      this.token = ''
      this.userInfo = null
      uni.removeStorageSync('token')
      uni.removeStorageSync('userInfo')
    },
  },
})
