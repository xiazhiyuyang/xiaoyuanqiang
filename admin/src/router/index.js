import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
  },
  {
    path: '/',
    component: () => import('../layouts/AdminLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '数据概览' } },
      { path: 'users', name: 'Users', component: () => import('../views/Users.vue'), meta: { title: '用户管理' } },
      { path: 'posts', name: 'Posts', component: () => import('../views/Posts.vue'), meta: { title: '帖子管理' } },
      { path: 'comments', name: 'Comments', component: () => import('../views/Comments.vue'), meta: { title: '评论管理' } },
      { path: 'reports', name: 'Reports', component: () => import('../views/Reports.vue'), meta: { title: '举报审核' } },
      { path: 'ai-review', name: 'AiReview', component: () => import('../views/AiReview.vue'), meta: { title: 'AI 智能审查' } },
      { path: 'sensitive', name: 'SensitiveWords', component: () => import('../views/SensitiveWords.vue'), meta: { title: '敏感词管理' } },
      { path: 'categories', name: 'Categories', component: () => import('../views/Categories.vue'), meta: { title: '分类管理' } },
      { path: 'promotions', name: 'Promotions', component: () => import('../views/Promotions.vue'), meta: { title: '广告与公告' } },
      { path: 'logs', name: 'Logs', component: () => import('../views/Logs.vue'), meta: { title: '操作日志' } },
      { path: 'settings', name: 'Settings', component: () => import('../views/Settings.vue'), meta: { title: '系统设置' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory('/admin/'),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.path !== '/login' && !auth.isLoggedIn) return '/login'
  if (to.path === '/login' && auth.isLoggedIn) return '/dashboard'
})

export default router
