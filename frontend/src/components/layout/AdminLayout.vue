<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const store = useUserStore()

const menus = [
  { label: '数据看板', path: '/admin/dashboard', icon: 'grid' },
  { label: '用户管理', path: '/admin/users', icon: 'users' },
  { label: '模板管理', path: '/admin/templates', icon: 'folder' },
  { label: '反馈管理', path: '/admin/feedback', icon: 'message' },
  { label: '系统配置', path: '/admin/system', icon: 'settings' },
]

function logout() {
  store.logout()
  router.push('/login')
}
</script>

<template>
  <div style="display: flex; height: 100vh">
    <aside style="width: 220px; background: #0f172a; display: flex; flex-direction: column; flex-shrink: 0">
      <div style="padding: 20px 20px 24px; display: flex; align-items: center; gap: 10px; cursor: pointer" @click="router.push('/templates')">
        <img src="/logo-on-dark.svg" alt="" aria-hidden="true" style="width: 32px; height: 32px; display: block" />
        <span style="font-weight: 700; font-size: 16px; color: #fff">智绘图管理</span>
      </div>
      <nav style="flex: 1; padding: 0 10px">
        <button v-for="m in menus" :key="m.path" @click="router.push(m.path)"
          :style="{
            display: 'flex', alignItems: 'center', gap: '10px', width: '100%', padding: '10px 14px',
            marginBottom: '2px', borderRadius: '8px', fontSize: '13px', border: 'none', cursor: 'pointer',
            fontFamily: 'inherit', textAlign: 'left',
            background: route.path.startsWith(m.path) ? 'rgba(59,130,246,0.15)' : 'transparent',
            color: route.path.startsWith(m.path) ? '#60a5fa' : '#94a3b8',
          }"
          @mouseenter="(e: any) => { if (!route.path.startsWith(m.path)) e.currentTarget.style.background = 'rgba(255,255,255,0.05)' }"
          @mouseleave="(e: any) => { if (!route.path.startsWith(m.path)) e.currentTarget.style.background = 'transparent' }">
          <!-- grid -->
          <svg v-if="m.icon === 'grid'" width="18" height="18" viewBox="0 0 24 24" fill="none" :stroke="route.path.startsWith(m.path) ? '#60a5fa' : '#64748b'" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
          <!-- users -->
          <svg v-else-if="m.icon === 'users'" width="18" height="18" viewBox="0 0 24 24" fill="none" :stroke="route.path.startsWith(m.path) ? '#60a5fa' : '#64748b'" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          <!-- folder -->
          <svg v-else-if="m.icon === 'folder'" width="18" height="18" viewBox="0 0 24 24" fill="none" :stroke="route.path.startsWith(m.path) ? '#60a5fa' : '#64748b'" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
          <!-- message -->
          <svg v-else-if="m.icon === 'message'" width="18" height="18" viewBox="0 0 24 24" fill="none" :stroke="route.path.startsWith(m.path) ? '#60a5fa' : '#64748b'" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <!-- settings -->
          <svg v-else-if="m.icon === 'settings'" width="18" height="18" viewBox="0 0 24 24" fill="none" :stroke="route.path.startsWith(m.path) ? '#60a5fa' : '#64748b'" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          <span>{{ m.label }}</span>
        </button>
      </nav>
      <div style="padding: 16px; border-top: 1px solid rgba(255,255,255,0.08)">
        <button @click="router.push('/templates')" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 14px; border-radius: 8px; font-size: 13px; border: none; cursor: pointer; font-family: inherit; text-align: left; background: transparent; color: #64748b; margin-bottom: 2px" @mouseenter="(e: any) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'" @mouseleave="(e: any) => e.currentTarget.style.background = 'transparent'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
          <span>返回用户端</span>
        </button>
        <button @click="logout" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 14px; border-radius: 8px; font-size: 13px; border: none; cursor: pointer; font-family: inherit; text-align: left; background: transparent; color: #64748b" @mouseenter="(e: any) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'" @mouseleave="(e: any) => e.currentTarget.style.background = 'transparent'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          <span>退出登录</span>
        </button>
      </div>
    </aside>
    <main style="flex: 1; overflow: auto; background: #f8fafc">
      <router-view />
    </main>
  </div>
</template>
