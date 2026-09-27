<template>
  <view class="page" :class="cwRootClass">
    <!-- 外观主题 -->
    <view class="card anim-up">
      <view class="sec-title">显示模式</view>
      <view class="muted small">浅色 / 深色 / 跟随系统，登录后自动同步到你的账号</view>
      <view class="mode-seg">
        <view
          v-for="m in modes" :key="m.key"
          class="mode-item" :class="{ on: mode === m.key }"
          @click="chooseMode(m.key)"
        >{{ m.icon }} {{ m.name }}</view>
      </view>
      <view class="sec-title mt24">配色主题</view>
      <view class="muted small">切换配色与背景，页面布局保持不变</view>
      <view class="theme-grid">
        <view
          v-for="t in themes" :key="t.key"
          class="theme-cell" @click="chooseTheme(t.key)"
        >
          <view
            class="theme-swatch"
            :class="{ on: currentTheme === t.key }"
            :style="{ background: 'linear-gradient(135deg,' + t.swatch[0] + ',' + t.swatch[1] + ')' }"
          >
            <text v-if="currentTheme === t.key" class="theme-check">✓</text>
          </view>
          <text class="theme-name" :class="{ on: currentTheme === t.key }">{{ t.name }}</text>
        </view>
      </view>
    </view>

    <!-- 消息通知 -->
    <view class="card list anim-up" v-if="userStore.isLoggedIn">
      <view class="sec-title">消息通知</view>
      <view class="muted small" style="margin-bottom:8rpx">关闭后不再接收对应类型的站内提醒</view>
      <view class="switch-item" v-for="n in notifyItems" :key="n.key">
        <view class="sw-left">
          <text class="sw-ic">{{ n.icon }}</text>
          <view>
            <view class="sw-name">{{ n.name }}</view>
            <view class="sw-desc">{{ n.desc }}</view>
          </view>
        </view>
        <switch :checked="notify[n.key]" color="#8b7cf6" @change="onNotifyChange(n.key, $event)" />
      </view>
    </view>
    <!-- 账号与安全 -->
    <view class="card list anim-up">
      <view class="sec-title">账号与安全</view>
      <view class="list-item" @click="go('/pages/account/password')">
        <text class="li-ic">🔑</text><text class="li-name">修改密码</text><text class="chev">›</text>
      </view>
      <view class="list-item" @click="go('/pages/account/security')">
        <text class="li-ic">❓</text><text class="li-name">密保设置</text><text class="chev">›</text>
      </view>
      <view class="list-item" @click="go('/pages/profile/privacy')">
        <text class="li-ic">🔒</text><text class="li-name">隐私设置</text><text class="chev">›</text>
      </view>
    </view>

    <!-- 通用 -->
    <view class="card list anim-up">
      <view class="sec-title">通用</view>
      <view class="list-item" @click="clearCache">
        <text class="li-ic">🧹</text><text class="li-name">清除缓存</text>
        <text class="li-extra">{{ cacheSize }}</text><text class="chev">›</text>
      </view>
    </view>

    <!-- 关于与更新 -->
    <view class="card list anim-up">
      <view class="sec-title">关于</view>
      <view class="list-item" @click="checkUpdate">
        <text class="li-ic">⬆️</text><text class="li-name">检查更新</text>
        <text class="li-extra">v{{ appVersion }}</text><text class="chev">›</text>
      </view>
      <view class="list-item" @click="go('/pages/agreement/privacy')">
        <text class="li-ic">🛡️</text><text class="li-name">隐私政策与用户协议</text><text class="chev">›</text>
      </view>
      <view class="list-item" @click="showAbout">
        <text class="li-ic">ℹ️</text><text class="li-name">关于{{ siteName }}</text><text class="chev">›</text>
      </view>
      <view class="list-item" v-if="contact" @click="copyContact">
        <text class="li-ic">📮</text><text class="li-name">联系我们</text>
        <text class="li-extra">{{ contact }}</text><text class="chev">›</text>
      </view>
    </view>

    <button class="btn btn-ghost logout" @click="logout">退出登录</button>
  </view>
</template>

<script>
import { useUserStore } from '@/stores/user.js'
import { THEMES, MODES, setTheme, setMode, themeState } from '@/utils/theme.js'
import { checkAppUpdate } from '@/utils/updater.js'
import { api } from '@/utils/api.js'

export default {
  data() {
    return {
      themes: THEMES,
      modes: MODES,
      mode: themeState.mode,
      notify: {
        notify_like: true, notify_comment: true,
        notify_follow: true, notify_system: true,
      },
      notifyItems: [
        { key: 'notify_like', name: '点赞提醒', desc: '有人赞了你的动态', icon: '❤️' },
        { key: 'notify_comment', name: '评论与回复', desc: '评论、回复你的内容', icon: '💬' },
        { key: 'notify_follow', name: '新增关注', desc: '有人关注了你', icon: '＋' },
        { key: 'notify_system', name: '系统通知', desc: '审核结果与社区公告', icon: '✉️' },
      ],
      appVersion: '1.0.0',
      cacheSize: '0KB',
      siteName: '校园墙',
      contact: '',
    }
  },
  computed: {
    currentTheme() { return themeState.key },
    userStore() { return useUserStore() },
  },
  onShow() {
    this.loadVersion()
    this.calcCache()
    this.loadPublic()
    this.mode = themeState.mode
    this.loadPreferences()
  },
  methods: {
    go(url) { uni.navigateTo({ url }) },
    applyPrefs(prefs) {
      if (!prefs) return
      if (prefs.mode) this.mode = prefs.mode
      ;['notify_like', 'notify_comment', 'notify_follow', 'notify_system'].forEach((k) => {
        if (typeof prefs[k] === 'boolean') this.notify[k] = prefs[k]
      })
    },
    async loadPreferences() {
      try {
        const cached = JSON.parse(uni.getStorageSync('userInfo') || 'null')
        if (cached && cached.preferences) this.applyPrefs(cached.preferences)
      } catch (e) {}
      if (!uni.getStorageSync('token')) return
      try {
        const me = await api.getMe()
        this.userStore.setUser(me)
        this.applyPrefs(me.preferences)
      } catch (e) {}
    },
    async savePreferences(patch) {
      if (!uni.getStorageSync('token')) return
      try {
        const me = await api.updateMe({ preferences: patch })
        this.userStore.setUser(me)
      } catch (e) {
        uni.showToast({ title: (e && e.msg) || '设置保存失败', icon: 'none' })
      }
    },
    chooseTheme(key) {
      setTheme(key)
      this.savePreferences({ theme: key })
      uni.showToast({ title: '已切换主题', icon: 'none' })
    },
    chooseMode(key) {
      this.mode = key
      setMode(key)
      this.savePreferences({ mode: key })
    },
    onNotifyChange(key, e) {
      const val = e.detail.value
      this.notify[key] = val
      this.savePreferences({ [key]: val })
    },
    loadVersion() {
      // #ifdef APP-PLUS
      try { this.appVersion = plus.runtime.version || '1.0.0' } catch (e) {}
      // #endif
    },
    loadPublic() {
      try {
        const cfg = JSON.parse(uni.getStorageSync('public_settings') || '{}')
        if (cfg.site_name) this.siteName = cfg.site_name
        this.contact = cfg.contact || ''
      } catch (e) {}
    },
    calcCache() {
      try {
        const info = uni.getStorageInfoSync()
        const kb = info.currentSize || 0
        this.cacheSize = kb >= 1024 ? (kb / 1024).toFixed(1) + 'MB' : kb + 'KB'
      } catch (e) { this.cacheSize = '' }
    },
    clearCache() {
      uni.showModal({
        title: '清除缓存', content: '将清理本地缓存（保留登录状态与主题设置），确定吗？',
        success: (res) => {
          if (!res.confirm) return
          const keep = {}
          ;['token', 'userInfo', 'cw_theme', 'cw_mode', 'cw_theme_chosen_by_user', 'public_settings'].forEach((k) => {
            keep[k] = uni.getStorageSync(k)
          })
          uni.clearStorageSync()
          Object.keys(keep).forEach((k) => {
            if (keep[k] !== '' && keep[k] !== null && keep[k] !== undefined) uni.setStorageSync(k, keep[k])
          })
          this.calcCache()
          uni.showToast({ title: '缓存已清理', icon: 'success' })
        },
      })
    },
    checkUpdate() {
      // #ifdef APP-PLUS
      uni.showLoading({ title: '检查中...' })
      checkAppUpdate({ silent: false }).finally(() => uni.hideLoading())
      // #endif
      // #ifndef APP-PLUS
      uni.showToast({ title: '请在 App 内检查更新', icon: 'none' })
      // #endif
    },
    showAbout() {
      uni.showModal({
        title: this.siteName,
        content: `版本 v${this.appVersion}\n一个安全、温暖、匿名的校园交流空间。`,
        showCancel: false,
      })
    },
    copyContact() {
      uni.setClipboardData({ data: this.contact, success: () => uni.showToast({ title: '联系方式已复制', icon: 'none' }) })
    },
    logout() {
      uni.showModal({
        title: '提示', content: '确定退出登录吗？',
        success: (res) => {
          if (res.confirm) {
            this.userStore.logout()
            uni.showToast({ title: '已退出', icon: 'none' })
            setTimeout(() => uni.switchTab({ url: '/pages/index/index' }), 500)
          }
        },
      })
    },
  },
}
</script>

<style scoped>
.sec-title { font-size: 26rpx; font-weight: 700; color: var(--text2); margin-bottom: 16rpx; }
.theme-grid { display: flex; flex-wrap: wrap; gap: 28rpx 0; margin-top: 18rpx; }
.theme-cell { width: 33.33%; display: flex; flex-direction: column; align-items: center; gap: 12rpx; }
.theme-swatch {
  width: 96rpx; height: 96rpx; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  border: 4rpx solid transparent; box-shadow: 0 8rpx 24rpx rgba(0,0,0,.35);
}
.theme-swatch.on { border-color: #fff; box-shadow: 0 0 24rpx var(--brand); }
.theme-check { color: #fff; font-size: 40rpx; font-weight: 800; }
.theme-name { font-size: 24rpx; color: var(--text2); }
.theme-name.on { color: var(--text); font-weight: 700; }
.list-item { display: flex; align-items: center; gap: 18rpx; padding: 22rpx 0; border-bottom: 1rpx solid var(--line); }
.list-item:last-child { border-bottom: none; }
.li-ic { font-size: 38rpx; }
.li-name { flex: 1; font-weight: 600; font-size: 29rpx; }
.li-extra { font-size: 24rpx; color: var(--text3); margin-right: 8rpx; }
.chev { color: var(--text3); font-size: 40rpx; }
.logout { margin-top: 10rpx; }
.mt24 { margin-top: 24rpx; }
.mode-seg { display: flex; gap: 12rpx; margin: 18rpx 0 6rpx; }
.mode-item {
  flex: 1; text-align: center; padding: 18rpx 0; border-radius: 18rpx;
  font-size: 25rpx; color: var(--text2); background: rgba(255,255,255,.06);
  border: 1rpx solid var(--line);
}
.mode-item.on { background: var(--grad); color: #fff; font-weight: 700; border-color: transparent; box-shadow: var(--shadow-brand); }
.switch-item { display: flex; align-items: center; justify-content: space-between; padding: 22rpx 0; border-bottom: 1rpx solid var(--line); }
.switch-item:last-child { border-bottom: none; }
.sw-left { display: flex; align-items: center; gap: 18rpx; }
.sw-ic {
  width: 64rpx; height: 64rpx; border-radius: 18rpx; background: var(--brand-soft);
  display: flex; align-items: center; justify-content: center; font-size: 32rpx;
}
.sw-name { font-size: 28rpx; font-weight: 600; color: var(--text); }
.sw-desc { font-size: 22rpx; color: var(--text3); margin-top: 4rpx; }
</style>
