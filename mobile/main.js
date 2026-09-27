import { createSSRApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { themeState, applyNavColor, effectiveMode, rootClass } from './utils/theme.js'
export function createApp() {
  const app = createSSRApp(App)
  app.use(createPinia())
  // 全局注入主题：页面根节点用 :class="cwRootClass" 套用配色与明暗；
  // 页面显示时同步导航栏颜色。
  app.mixin({
    computed: {
      cwTheme() {
        return themeState.key
      },
      cwMode() {
        return effectiveMode()
      },
      cwRootClass() {
        return rootClass()
      },
    },
    onShow() {
      applyNavColor()
    },
  })
  return { app }
}
