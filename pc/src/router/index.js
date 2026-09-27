import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('../pages/Login.vue'), meta: { bare: true } },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('../pages/Home.vue') },
      { path: 'post/:id', name: 'post', component: () => import('../pages/PostDetail.vue') },
      { path: 'u/:id', name: 'profile', component: () => import('../pages/Profile.vue') },
      { path: 'u/:id/follows', name: 'user-follows', component: () => import('../pages/Follows.vue') },
      { path: 'me', name: 'me', meta: { auth: true }, component: () => import('../pages/MeRedirect.vue') },
      { path: 'me/follows', name: 'my-follows', meta: { auth: true, selfFollows: true }, component: () => import('../pages/Follows.vue') },
      { path: 'messages', name: 'messages', meta: { auth: true }, component: () => import('../pages/Messages.vue') },
      { path: 'messages/:cid', name: 'conversation', meta: { auth: true }, component: () => import('../pages/Messages.vue') },
      { path: 'notifications', name: 'notifications', meta: { auth: true }, component: () => import('../pages/Notifications.vue') },
      { path: 'settings', name: 'settings', meta: { auth: true }, component: () => import('../pages/Settings.vue') },
      { path: 'levels', name: 'levels', component: () => import('../pages/Levels.vue') },
      { path: 'tools', name: 'tools', component: () => import('../pages/Tools.vue') },
      { path: 'tools/:slug', name: 'tool-detail', component: () => import('../pages/ToolDetail.vue') },
      { path: 'review', name: 'review', meta: { auth: true, review: true }, component: () => import('../pages/Review.vue') },
      { path: ':pathMatch(.*)*', name: 'not-found', component: () => import('../pages/NotFound.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const auth = useAuth()
  // 刷新/直达受保护页面时，鉴权信息（含审查权限）可能仍在拉取，先等待就绪
  if (auth.token && !auth.ready) {
    await auth.bootstrap().catch(() => {})
  }
  if (to.meta.auth && !auth.token) {
    return { path: '/login', query: { next: to.fullPath } }
  }
  if (to.meta.review && !auth.canAnyReview) {
    return { path: '/' }
  }
  return true
})

export default router
