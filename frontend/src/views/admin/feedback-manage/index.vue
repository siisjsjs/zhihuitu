<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '@/api/request'

const feedbacks = ref<any[]>([])
const total = ref(0)
const filterStatus = ref('')
const replyId = ref<number | null>(null)
const replyText = ref('')
const page = ref(1)
const pageSize = 10

async function loadFeedbacks() {
  const params: any = { page: page.value, pageSize }
  if (filterStatus.value) params.status = filterStatus.value
  const data = await request.get('/admin/feedback', { params })
  feedbacks.value = data.list || []
  total.value = data.total || 0
}

async function doReply(id: number) {
  await request.post(`/admin/feedback/${id}/reply`, { reply: replyText.value })
  replyId.value = null
  replyText.value = ''
  loadFeedbacks()
}

async function closeFeedback(id: number) {
  await request.post(`/admin/feedback/${id}/status`, { status: 'closed' })
  loadFeedbacks()
}

onMounted(loadFeedbacks)
</script>

<template>
  <div style="padding: 28px">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px">
      <div>
        <h1 style="font-size: 22px; font-weight: 700; color: #0f172a; margin: 0">反馈管理</h1>
        <p style="font-size: 13px; color: #94a3b8; margin-top: 2px">共 {{ total }} 条反馈</p>
      </div>
      <el-radio-group :model-value="filterStatus" @change="(v: any) => { filterStatus = String(v || ''); page = 1; loadFeedbacks() }" size="small">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="pending">待处理</el-radio-button>
        <el-radio-button value="processing">处理中</el-radio-button>
        <el-radio-button value="replied">已回复</el-radio-button>
      </el-radio-group>
    </div>

    <div style="display: flex; flex-direction: column; gap: 10px">
      <div v-for="fb in feedbacks" :key="fb.id" style="background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 20px">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px">
          <div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px">
              <span style="font-size: 15px; font-weight: 600; color: #0f172a">{{ fb.title }}</span>
              <el-tag v-if="fb.status === 'pending'" size="small">待处理</el-tag>
              <el-tag v-else-if="fb.status === 'processing'" type="warning" size="small">处理中</el-tag>
              <el-tag v-else-if="fb.status === 'replied'" type="success" size="small">已回复</el-tag>
              <el-tag v-else type="info" size="small">已关闭</el-tag>
            </div>
            <div style="font-size: 12px; color: #94a3b8; display: flex; gap: 12px">
              <span>来自: {{ fb.username || fb.userId }}</span>
              <span>{{ fb.createdAt ? new Date(fb.createdAt).toLocaleString() : '' }}</span>
            </div>
          </div>
          <div style="display: flex; gap: 4px">
            <el-button v-if="fb.status !== 'replied' && fb.status !== 'closed'" size="small" @click="replyId = fb.id; replyText = ''">回复</el-button>
            <el-button v-if="fb.status !== 'closed'" size="small" text @click="closeFeedback(fb.id)">关闭</el-button>
          </div>
        </div>
        <div style="padding: 12px; background: #f8fafc; border-radius: 8px; font-size: 13px; color: #475569; line-height: 1.7">{{ fb.content }}</div>
        <div v-if="fb.adminReply" style="margin-top: 8px; padding: 12px; background: #eff6ff; border-radius: 8px; font-size: 13px; color: #1d4ed8; line-height: 1.7; border-left: 3px solid #60a5fa">
          <span style="font-size: 11px; font-weight: 600; color: #3b82f6">管理员回复: </span>{{ fb.adminReply }}
        </div>
        <div v-if="replyId === fb.id" style="margin-top: 10px; display: flex; gap: 8px">
          <el-input v-model="replyText" type="textarea" :rows="2" placeholder="输入回复内容..." style="flex: 1" />
          <div style="display: flex; flex-direction: column; gap: 4px">
            <el-button type="primary" size="small" :disabled="!replyText.trim()" @click="doReply(fb.id)">发送</el-button>
            <el-button size="small" @click="replyId = null">取消</el-button>
          </div>
        </div>
      </div>
      <el-empty v-if="feedbacks.length === 0" description="暂无反馈" />
    </div>

    <div style="display: flex; justify-content: center; padding: 16px">
      <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="loadFeedbacks" />
    </div>
  </div>
</template>
