import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import axios from 'axios'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/templates' },
    { path: '/login', component: () => import('@/views/user/auth/Login.vue') },
    {
      path: '/',
      component: () => import('@/components/layout/UserLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: 'templates', component: () => import('@/views/user/template-center/index.vue') },
        { path: 'mode-select/:templateId', component: () => import('@/views/user/mode-select/index.vue') },
        { path: 'form/:templateId', component: () => import('@/views/user/form-mode/index.vue') },
        { path: 'ai-chat/:templateId', component: () => import('@/views/user/ai-chat/index.vue') },
        { path: 'chart-editor/:chartId', component: () => import('@/views/user/chart-editor/index.vue') },
        { path: 'drawio-editor/:chartId', component: () => import('@/views/user/drawio-editor/index.vue') },
        { path: 'my-charts', component: () => import('@/views/user/my-charts/index.vue') },
        { path: 'line-balance-studio', component: () => import('@/views/user/line-balance-studio/index.vue') },
        { path: 'feedback', component: () => import('@/views/user/feedback/index.vue') },
        { path: 'profile', component: () => import('@/views/user/profile/index.vue') },
      ],
    },
    {
      path: '/admin',
      component: () => import('@/components/layout/AdminLayout.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        { path: '', redirect: '/admin/dashboard' },
        { path: 'dashboard', component: () => import('@/views/admin/dashboard/index.vue') },
        { path: 'users', component: () => import('@/views/admin/user-manage/index.vue') },
        { path: 'templates', component: () => import('@/views/admin/template-manage/index.vue') },
        { path: 'feedback', component: () => import('@/views/admin/feedback-manage/index.vue') },
        { path: 'system', component: () => import('@/views/admin/system-config/index.vue') },
        { path: 'ai-config', component: () => import('@/views/admin/ai-config/index.vue') },
        { path: 'operation-log', component: () => import('@/views/admin/operation-log/index.vue') },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const store = useUserStore()
  if (to.meta.requiresAuth && !store.token) return '/login'
  if (to.meta.requiresAdmin) {
    if (!store.userInfo && store.token) {
      try {
        const res = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/users/me`, {
          headers: { Authorization: `Bearer ${store.token}` }
        })
        if (res.data?.code === 200) store.setUserInfo(res.data.data)
      } catch {
        return '/login'
      }
    }
    if (store.userInfo?.role !== 'admin') return '/templates'
  }
})

export default router
