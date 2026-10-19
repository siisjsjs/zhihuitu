<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '@/api/request'

const feedbacks = ref<any[]>([])
const showForm = ref(false)
const newTitle = ref('')
const newContent = ref('')
const expId = ref<number | null>(null)

async function loadFeedbacks() {
  const data = await request.get('/feedback')
  feedbacks.value = data.list || []
}

async function submitFeedback() {
  if (!newTitle.value.trim() || !newContent.value.trim()) return
  await request.post('/feedback', { title: newTitle.value, content: newContent.value })
  newTitle.value = ''
  newContent.value = ''
  showForm.value = false
  loadFeedbacks()
}

onMounted(loadFeedbacks)

function statusColor(s: string) {
  if (s === 'replied') return { bg: '#f0fdf4', text: '#16a34a', bd: '#bbf7d0', label: '已回复' }
  if (s === 'processing') return { bg: '#fffbeb', text: '#d97706', bd: '#fde68a', label: '处理中' }
  if (s === 'closed') return { bg: '#f1f5f9', text: '#475569', bd: '#e2e8f0', label: '已关闭' }
  return { bg: '#f1f5f9', text: '#475569', bd: '#e2e8f0', label: '待处理' }
}
</script>

<template>
  <div style="max-width: 720px; margin: 0 auto; padding: 32px 24px">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px">
      <div>
        <h1 style="font-size: 24px; font-weight: 700; color: #0f172a; margin-bottom: 4px">意见反馈</h1>
        <p style="font-size: 14px; color: #94a3b8">帮助我们改进产品</p>
      </div>
      <button @click="showForm = !showForm" style="display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px; font-size: 14px; font-weight: 500; border-radius: 8px; background: #1a56db; color: #fff; border: none; cursor: pointer; font-family: inherit">
        <svg v-if="!showForm" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        {{ showForm ? '取消' : '提交反馈' }}
      </button>
    </div>

    <div v-if="showForm" style="background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 24px; margin-bottom: 20px">
      <div style="font-size: 16px; font-weight: 600; color: #1e293b; margin-bottom: 16px">新建反馈</div>
      <div style="display: flex; flex-direction: column; gap: 12px">
        <div>
          <label style="display: block; font-size: 13px; font-weight: 500; color: #475569; margin-bottom: 6px">标题</label>
          <input v-model="newTitle" placeholder="简要描述你的问题或建议" style="width: 100%; padding: 10px 16px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; font-family: inherit; color: #1e293b; background: #fff; outline: none; box-sizing: border-box" @focus="(e: any) => e.target.style.borderColor = '#60a5fa'" @blur="(e: any) => e.target.style.borderColor = '#e2e8f0'" />
        </div>
        <div>
          <label style="display: block; font-size: 13px; font-weight: 500; color: #475569; margin-bottom: 6px">详细描述</label>
          <textarea v-model="newContent" placeholder="请详细描述..." rows="5" style="width: 100%; padding: 10px 16px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; font-family: inherit; color: #1e293b; background: #fff; outline: none; resize: vertical; line-height: 1.6; box-sizing: border-box" @focus="(e: any) => e.target.style.borderColor = '#60a5fa'" @blur="(e: any) => e.target.style.borderColor = '#e2e8f0'" />
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 8px">
          <button @click="showForm = false" style="padding: 10px 20px; font-size: 14px; font-weight: 500; border-radius: 8px; background: #f1f5f9; color: #334155; border: 1px solid #e2e8f0; cursor: pointer; font-family: inherit">取消</button>
          <button @click="submitFeedback" style="display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px; font-size: 14px; font-weight: 500; border-radius: 8px; background: #1a56db; color: #fff; border: none; cursor: pointer; font-family: inherit">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            提交
          </button>
        </div>
      </div>
    </div>

    <div style="display: flex; flex-direction: column; gap: 10px">
      <div v-for="fb in feedbacks" :key="fb.id" style="background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden">
        <div @click="expId = expId === fb.id ? null : fb.id" style="padding: 16px 20px; cursor: pointer; display: flex; align-items: center; gap: 12px">
          <div style="flex: 1">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px">
              <span style="font-size: 15px; font-weight: 600; color: #1e293b">{{ fb.title }}</span>
              <span :style="{ display: 'inline-flex', padding: '2px 10px', fontSize: '12px', fontWeight: 500, borderRadius: '100px', background: statusColor(fb.status).bg, color: statusColor(fb.status).text, border: `1px solid ${statusColor(fb.status).bd}` }">{{ statusColor(fb.status).label }}</span>
            </div>
            <div style="font-size: 13px; color: #94a3b8">{{ fb.createdAt ? new Date(fb.createdAt).toLocaleString() : '' }}</div>
          </div>
          <span :style="{ color: '#94a3b8', transition: 'transform 0.2s', display: 'inline-block', transform: expId === fb.id ? 'rotate(90deg)' : 'rotate(0)' }">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
          </span>
        </div>
        <div v-if="expId === fb.id" style="padding: 0 20px 16px">
          <div style="padding: 14px; background: #f8fafc; border-radius: 8px; font-size: 14px; color: #475569; line-height: 1.7; margin-bottom: 10px">{{ fb.content }}</div>
          <div v-if="fb.adminReply" style="padding: 14px; background: #eff6ff; border-radius: 8px; font-size: 14px; color: #1d4ed8; line-height: 1.7; border-left: 3px solid #60a5fa">
            <div style="font-size: 12px; font-weight: 600; color: #3b82f6; margin-bottom: 4px">管理员回复</div>
            {{ fb.adminReply }}
          </div>
        </div>
      </div>
    </div>
    <div v-if="feedbacks.length === 0" style="text-align: center; padding: 64px 24px; color: #94a3b8">
      <p>暂无反馈</p>
    </div>
  </div>
</template>
