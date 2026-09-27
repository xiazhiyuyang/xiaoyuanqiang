<template>
  <el-container class="layout">
    <div v-if="drawer" class="mask" @click="drawer = false"></div>
    <el-aside class="aside" :class="{ open: drawer }" width="224px">
      <div class="logo">
        <span class="logo-mark">校</span>
        <span class="logo-text">校园墙后台</span>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        class="menu"
        background-color="transparent"
        text-color="rgba(255,255,255,0.72)"
        active-text-color="#ffffff"
        @select="drawer = false"
      >
        <el-menu-item index="/dashboard"><el-icon><DataAnalysis /></el-icon><span>数据概览</span></el-menu-item>
        <el-menu-item index="/users"><el-icon><User /></el-icon><span>用户管理</span></el-menu-item>
        <el-menu-item index="/posts"><el-icon><Document /></el-icon><span>帖子管理</span></el-menu-item>
        <el-menu-item index="/comments"><el-icon><ChatDotRound /></el-icon><span>评论管理</span></el-menu-item>
        <el-menu-item index="/reports"><el-icon><Warning /></el-icon><span>举报审核</span></el-menu-item>
        <el-menu-item index="/ai-review"><el-icon><MagicStick /></el-icon><span>AI 智能审查</span></el-menu-item>
        <el-menu-item index="/sensitive"><el-icon><Filter /></el-icon><span>敏感词管理</span></el-menu-item>
        <el-menu-item index="/categories"><el-icon><Menu /></el-icon><span>分类管理</span></el-menu-item>
        <el-menu-item index="/promotions"><el-icon><Promotion /></el-icon><span>广告与公告</span></el-menu-item>
        <el-menu-item index="/logs"><el-icon><Tickets /></el-icon><span>操作日志</span></el-menu-item>
        <el-menu-item index="/settings"><el-icon><Setting /></el-icon><span>系统设置</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container class="main-col">
      <el-header class="header">
        <span class="hamburger" @click="drawer = true"><el-icon><Expand /></el-icon></span>
        <span class="page-title">{{ $route.meta.title }}</span>
        <el-dropdown @command="handleCommand" class="user-dropdown">
          <span class="user-info">
            <el-avatar :size="30" class="user-avatar">{{ auth.user?.nickname?.[0] || 'A' }}</el-avatar>
            <span class="user-name">{{ auth.user?.nickname }}</span>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
const router = useRouter()
const auth = useAuthStore()
const drawer = ref(false)
const handleCommand = (cmd) => {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
}
</script>
<style scoped>
.layout { min-height: 100vh; }
.aside {
  position: fixed; left: 0; top: 0; bottom: 0; z-index: 1001;
  background: linear-gradient(180deg, #312e81 0%, #4c1d95 100%);
  transform: translateX(-100%);
  transition: transform 0.25s ease;
  overflow: hidden;
}
.aside.open { transform: translateX(0); box-shadow: 4px 0 24px rgba(0,0,0,0.2); }
.logo {
  height: 64px; display: flex; align-items: center; justify-content: center;
  gap: 10px; color: #fff; font-size: 17px; font-weight: 700;
  letter-spacing: 1px; border-bottom: 1px solid rgba(255,255,255,0.08);
}
.logo-mark {
  width: 32px; height: 32px; border-radius: 9px; background: var(--grad);
  display: inline-flex; align-items: center; justify-content: center; font-size: 15px;
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
}
.menu { padding: 12px 10px; }
.menu :deep(.el-menu-item) {
  border-radius: 10px; margin-bottom: 4px; height: 46px; line-height: 46px;
}
.menu :deep(.el-menu-item.is-active) {
  background: var(--grad); font-weight: 700;
  box-shadow: 0 6px 16px rgba(139, 92, 246, 0.35);
}
.menu :deep(.el-menu-item:hover) { background: rgba(255,255,255,0.1); }
.mask {
  position: fixed; inset: 0; background: rgba(20,26,40,0.4);
  z-index: 1000;
}
.main-col { margin-left: 0; min-height: 100vh; }
.header {
  display: flex; align-items: center; height: 60px;
  background: #fff; border-bottom: 1px solid var(--line);
  padding: 0 18px; position: sticky; top: 0; z-index: 100;
}
.hamburger { font-size: 20px; cursor: pointer; color: var(--ink-2); margin-right: 12px; display: inline-flex; }
.page-title { font-size: 17px; font-weight: 700; color: var(--ink); }
.user-dropdown { margin-left: auto; }
.user-info { display: flex; align-items: center; cursor: pointer; outline: none; }
.user-avatar { background: var(--brand); font-size: 13px; }
.user-name { margin-left: 8px; font-size: 14px; color: var(--ink); }
.main { padding: 20px; max-width: 1400px; width: 100%; margin: 0 auto; box-sizing: border-box; }
@media (min-width: 768px) {
  .aside { transform: none; }
  .main-col { margin-left: 224px; }
  .hamburger { display: none; }
  .mask { display: none; }
}
@media (max-width: 640px) {
  .main { padding: 12px; }
  .user-name { display: none; }
}
</style>
