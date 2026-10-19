<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import request from '@/api/request'
import { resolveApiStaticUrl } from '@/utils/apiStatic'
import { renderMarkdown } from '@/utils/markdown'

const ANNOUNCEMENT_ACK_KEY = 'zhihuitu_announcement_session_ack'

type AnnouncementPayload = {
  id: number
  title: string
  content: string
  version: string
  isHighlight?: boolean
  imageUrl?: string | null
}

const router = useRouter()
const route = useRoute()
const store = useUserStore()
const showMenu = ref(false)
const menuRef = ref<HTMLElement | null>(null)

const announcementVisible = ref(false)
const announcementTitle = ref('')
const announcementContent = ref('')
const announcementImageUrl = ref('')
const announcementIsHighlight = ref(false)
const announcementToken = ref('')

const announcementHtml = computed(() => renderMarkdown(announcementContent.value))

function logout() {
  store.logout()
  router.push('/login')
}

function handleClickOutside(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    showMenu.value = false
  }
}

async function fetchCurrentAnnouncement(): Promise<AnnouncementPayload | null> {
  try {
    const data = await request.get<AnnouncementPayload | null>('/announcements/current', { _silent: true })
    if (!data?.id || !data?.version) {
      announcementIsHighlight.value = false
      return null
    }
    announcementIsHighlight.value = !!data.isHighlight
    return data as AnnouncementPayload
  } catch {
    announcementIsHighlight.value = false
    return null
  }
}

function applyAnnouncement(data: AnnouncementPayload) {
  announcementTitle.value = (data.title && data.title.trim()) || '网站公告'
  announcementContent.value = data.content || ''
  announcementImageUrl.value = resolveApiStaticUrl(data.imageUrl || '')
  announcementIsHighlight.value = !!data.isHighlight
  announcementToken.value = `${data.id}:${data.version}`
}

/** 进入站点时自动弹窗（本会话未标记已读时） */
async function loadAnnouncement() {
  const data = await fetchCurrentAnnouncement()
  if (!data) {
    announcementIsHighlight.value = false
    return
  }
  const token = `${data.id}:${data.version}`
  if (sessionStorage.getItem(ANNOUNCEMENT_ACK_KEY) === token) return
  applyAnnouncement(data)
  announcementVisible.value = true
}

/** 导航「公告」：随时可查看 */
async function openAnnouncementFromNav() {
  const data = await fetchCurrentAnnouncement()
  if (!data) {
    ElMessage.info('暂无公告')
    return
  }
  applyAnnouncement(data)
  announcementVisible.value = true
}

function onAnnouncementClosed() {
  if (announcementToken.value) {
    sessionStorage.setItem(ANNOUNCEMENT_ACK_KEY, announcementToken.value)
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleClickOutside)
  loadAnnouncement()
})
onUnmounted(() => document.removeEventListener('mousedown', handleClickOutside))
</script>

<template>
  <div style="min-height: 100vh; background: #f8fafc">
    <header style="height: 56px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; background: #fff; border-bottom: 1px solid #e2e8f0; position: sticky; top: 0; z-index: 100">
      <div style="display: flex; align-items: center; gap: 16px">
        <div style="display: flex; align-items: center; gap: 10px; cursor: pointer" @click="router.push('/templates')">
          <img src="/logo.svg" alt="" aria-hidden="true" style="width: 32px; height: 32px; display: block" />
          <span style="font-weight: 700; font-size: 18px; color: #0f172a">智绘图</span>
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 8px">
        <button type="button" @click="openAnnouncementFromNav()"
          :style="{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontFamily: 'inherit', fontSize: '14px', fontWeight: announcementVisible || announcementIsHighlight ? 600 : 500, border: 'none', cursor: 'pointer', background: 'transparent', color: announcementVisible ? (announcementIsHighlight ? '#dc2626' : '#2563eb') : (announcementIsHighlight ? '#dc2626' : '#64748b'), padding: '6px 12px', borderRadius: '6px', transition: 'all 0.2s' }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
          公告
        </button>
        <button type="button" @click="router.push('/templates')"
          :style="{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontFamily: 'inherit', fontSize: '14px', fontWeight: route.path === '/templates' ? 600 : 500, border: 'none', cursor: 'pointer', background: 'transparent', color: route.path === '/templates' ? '#2563eb' : '#64748b', padding: '6px 12px', borderRadius: '6px', transition: 'all 0.2s' }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
          模板中心
        </button>
        <button @click="router.push('/my-charts')"
          :style="{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontFamily: 'inherit', fontSize: '14px', fontWeight: route.path === '/my-charts' ? 600 : 500, border: 'none', cursor: 'pointer', background: 'transparent', color: route.path === '/my-charts' ? '#2563eb' : '#64748b', padding: '6px 12px', borderRadius: '6px', transition: 'all 0.2s' }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
          我的图表
        </button>
        <button @click="router.push('/line-balance-studio')"
          :style="{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontFamily: 'inherit', fontSize: '14px', fontWeight: route.path === '/line-balance-studio' ? 600 : 500, border: 'none', cursor: 'pointer', background: 'transparent', color: route.path === '/line-balance-studio' ? '#2563eb' : '#64748b', padding: '6px 12px', borderRadius: '6px', transition: 'all 0.2s' }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/><circle cx="9" cy="6" r="2" fill="currentColor" stroke="none"/><circle cx="15" cy="12" r="2" fill="currentColor" stroke="none"/><circle cx="8" cy="18" r="2" fill="currentColor" stroke="none"/></svg>
          产线平衡
        </button>
        <button @click="router.push('/feedback')"
          :style="{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontFamily: 'inherit', fontSize: '14px', fontWeight: route.path === '/feedback' ? 600 : 500, border: 'none', cursor: 'pointer', background: 'transparent', color: route.path === '/feedback' ? '#2563eb' : '#64748b', padding: '6px 12px', borderRadius: '6px', transition: 'all 0.2s' }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          反馈
        </button>
        <div ref="menuRef" style="position: relative">
          <div @click="showMenu = !showMenu" style="width: 34px; height: 34px; border-radius: 50%; background: #dbeafe; display: flex; align-items: center; justify-content: center; color: #2563eb; cursor: pointer; margin-left: 4px">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          </div>
          <div v-if="showMenu" style="position: absolute; top: 42px; right: 0; width: 200px; background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 12px 32px rgba(15,23,42,0.12); padding: 6px; z-index: 200">
            <div style="padding: 10px 12px; border-bottom: 1px solid #f1f5f9; margin-bottom: 4px">
              <div style="font-size: 14px; font-weight: 600; color: #1e293b">{{ store.userInfo?.username || '用户' }}</div>
              <div style="font-size: 12px; color: #94a3b8">{{ store.userInfo?.email || '' }}</div>
            </div>
            <button @click="showMenu = false; router.push('/profile')" style="display: flex; align-items: center; gap: 8px; width: 100%; padding: 8px 12px; font-size: 13px; border-radius: 6px; background: transparent; color: #475569; border: none; cursor: pointer; font-family: inherit" @mouseenter="(e: any) => e.currentTarget.style.background = '#f8fafc'" @mouseleave="(e: any) => e.currentTarget.style.background = 'transparent'">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              个人信息
            </button>
            <button v-if="store.userInfo?.role === 'admin'" @click="showMenu = false; router.push('/admin')" style="display: flex; align-items: center; gap: 8px; width: 100%; padding: 8px 12px; font-size: 13px; border-radius: 6px; background: transparent; color: #475569; border: none; cursor: pointer; font-family: inherit" @mouseenter="(e: any) => e.currentTarget.style.background = '#f8fafc'" @mouseleave="(e: any) => e.currentTarget.style.background = 'transparent'">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
              管理后台
            </button>
            <div style="height: 1px; background: #f1f5f9; margin: 4px 0" />
            <button @click="showMenu = false; logout()" style="display: flex; align-items: center; gap: 8px; width: 100%; padding: 8px 12px; font-size: 13px; border-radius: 6px; background: transparent; color: #475569; border: none; cursor: pointer; font-family: inherit" @mouseenter="(e: any) => e.currentTarget.style.background = '#f8fafc'" @mouseleave="(e: any) => e.currentTarget.style.background = 'transparent'">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
              退出登录
            </button>
          </div>
        </div>
      </div>
    </header>
    <router-view />

    <el-dialog
      v-model="announcementVisible"
      width="min(520px, 92vw)"
      align-center
      :close-on-click-modal="false"
      :show-close="false"
      :class="['ann-dialog', { 'ann-dialog--highlight': announcementIsHighlight }]"
      @closed="onAnnouncementClosed"
    >
      <div class="ann-card">
        <button
          class="ann-close"
          type="button"
          aria-label="关闭"
          @click="announcementVisible = false"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <line x1="6" y1="6" x2="18" y2="18"/>
            <line x1="18" y1="6" x2="6" y2="18"/>
          </svg>
        </button>

        <div class="ann-head">
          <span class="ann-tag">
            <span class="ann-dot" />
            {{ announcementIsHighlight ? '重要公告' : '系统公告' }}
          </span>
          <h3 class="ann-title">{{ announcementTitle }}</h3>
        </div>

        <div v-if="announcementImageUrl" class="ann-image">
          <img :src="announcementImageUrl" alt="" />
        </div>

        <div v-if="announcementContent.trim()" class="ann-body markdown-body" v-html="announcementHtml"></div>

        <div class="ann-foot">
          <button type="button" class="ann-btn" @click="announcementVisible = false">
            我知道了
          </button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
/* 卡片本身 */
.ann-card {
  position: relative;
  display: flex;
  flex-direction: column;
}

.ann-close {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: 0;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  border-radius: 8px;
  transition: color 0.15s ease, background 0.15s ease;
}
.ann-close:hover { color: #0f172a; background: #f1f5f9; }
.ann-close svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
}

.ann-head {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-right: 36px;
  margin-bottom: 18px;
}
.ann-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  align-self: flex-start;
  padding: 4px 12px;
  font-size: 12px;
  letter-spacing: 0.06em;
  color: #2563eb;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
}
.ann-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}
.ann-title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.005em;
  color: #0f172a;
  line-height: 1.35;
  margin: 0;
}

.ann-image {
  margin-bottom: 16px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e5e7ef;
  background: #f8fafc;
}
.ann-image img {
  display: block;
  width: 100%;
  height: auto;
  max-height: min(48vh, 360px);
  object-fit: contain;
}

.ann-body {
  position: relative;
  word-break: break-word;
  line-height: 1.75;
  color: #334155;
  font-size: 14px;
  max-height: min(50vh, 320px);
  overflow-y: auto;
  padding: 16px 18px;
  background: #f8fafc;
  border: 1px solid #e5e7ef;
  border-radius: 12px;
}
.ann-body::-webkit-scrollbar { width: 6px; }
.ann-body::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

/* markdown 渲染排版 */
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 14px 0 8px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.4;
}
.markdown-body :deep(h1) { font-size: 19px; }
.markdown-body :deep(h2) { font-size: 17px; }
.markdown-body :deep(h3) { font-size: 15px; }
.markdown-body :deep(h4) { font-size: 14px; }
.markdown-body :deep(p) { margin: 8px 0; }
.markdown-body :deep(ul),
.markdown-body :deep(ol) { margin: 8px 0; padding-left: 22px; }
.markdown-body :deep(li) { margin: 4px 0; }
.markdown-body :deep(strong) { font-weight: 700; color: #0f172a; }
.markdown-body :deep(em) { font-style: italic; }
.markdown-body :deep(mark) {
  background: #fee2e2;
  color: #dc2626;
  padding: 0 3px;
  border-radius: 3px;
}
.markdown-body :deep(a) { color: #2563eb; text-decoration: underline; }
.markdown-body :deep(code) {
  background: #eef2f7;
  color: #db2777;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'SFMono-Regular', Consolas, monospace;
}
.markdown-body :deep(blockquote) {
  margin: 8px 0;
  padding: 4px 14px;
  border-left: 3px solid #cbd5e1;
  color: #64748b;
  background: #f1f5f9;
  border-radius: 0 6px 6px 0;
}
.markdown-body :deep(hr) {
  margin: 14px 0;
  border: 0;
  border-top: 1px solid #e2e8f0;
}
.markdown-body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 8px 0;
}

.ann-foot {
  display: flex;
  justify-content: flex-end;
  margin-top: 22px;
}
.ann-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 40px;
  padding: 0 22px;
  border: 0;
  border-radius: 10px;
  background: #2563eb;
  color: #fff;
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.04em;
  cursor: pointer;
  box-shadow: 0 4px 14px -6px rgba(37, 99, 235, 0.55);
  transition: background 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
}
.ann-btn:hover {
  background: #1d4ed8;
  transform: translateY(-1px);
}
.ann-btn:focus-visible {
  outline: 0;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.22),
              0 4px 14px -6px rgba(37, 99, 235, 0.55);
}

/* 高亮：左侧描红边、tag 改为红色 */
:deep(.ann-dialog--highlight) .ann-tag {
  color: #dc2626;
  background: #fef2f2;
  border-color: #fecaca;
}
:deep(.ann-dialog--highlight) .ann-dot {
  background: #dc2626;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.15);
}
:deep(.ann-dialog--highlight) .ann-btn {
  background: #dc2626;
  box-shadow: 0 4px 14px -6px rgba(220, 38, 38, 0.55);
}
:deep(.ann-dialog--highlight) .ann-btn:hover {
  background: #b91c1c;
}
</style>

<style>
/* 重设 el-dialog 容器外观，让它显得"无框"——只剩我们的卡片 */
.ann-dialog {
  background: transparent !important;
  box-shadow: none !important;
  border-radius: 18px !important;
  overflow: visible;
}
.ann-dialog .el-dialog__header {
  display: none;
}
.ann-dialog .el-dialog__body {
  padding: 28px 28px 24px !important;
  background: #fff;
  border-radius: 18px;
  border: 1px solid #e5e7ef;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 30px 60px -30px rgba(15, 23, 42, 0.25);
}
.ann-dialog.ann-dialog--highlight .el-dialog__body {
  border-top: 3px solid #dc2626;
}
</style>
