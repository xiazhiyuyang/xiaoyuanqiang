import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuth } from './stores/auth'
import { useApp } from './stores/app'
import './styles/tokens.css'
import './styles/variables.css'
import './styles/base.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

const auth = useAuth()
const appStore = useApp()
appStore.applyTheme()

router.isReady().then(() => {
  Promise.all([
    auth.bootstrap(),
    appStore.loadSettings(),
  ]).finally(() => app.mount('#app'))
})
