<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '@/api/request'
import { ElMessage } from 'element-plus'

type ChartItem = {
  id: number
  title: string
  templateId?: string
  engine?: string
  createdAt?: string
}

type ChartsResponse = {
  list?: ChartItem[]
  total?: number
}

const router = useRouter()
const charts = ref<ChartItem[]>([])
const total = ref(0)
const search = ref('')
const filter = ref('all')
const page = ref(1)
const loading = ref(false)

const tabs = [
  { key: 'all', label: '全部' },
  { key: 'data', label: '数据图表' },
  { key: 'flow', label: '流程/架构' },
]

async function loadCharts() {
  loading.value = true
  try {
    const data = await request.get('/charts', {
      params: { page: page.value, pageSize: 10, keyword: search.value },
    }) as unknown as ChartsResponse
    charts.value = data.list || []
    total.value = data.total || 0
  } catch {
    charts.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const filtered = computed(() => {
  if (filter.value === 'all') return charts.value
  return charts.value.filter((c) => {
    if (filter.value === 'flow') return c.engine === 'vue-component' || c.engine === 'drawio'
    return c.engine !== 'vue-component' && c.engine !== 'drawio'
  })
})

function editChart(chart: ChartItem) {
  router.push(`/chart-editor/${chart.id}`)
}

async function deleteChart(id: number) {
  await request.delete(`/charts/${id}`)
  ElMessage.success('已删除')
  loadCharts()
}

onMounted(loadCharts)
</script>

<template>
  <div style="max-width: 960px; margin: 0 auto; padding: 32px 24px">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px">
      <div>
        <h1 style="font-size: 24px; font-weight: 700; color: #0f172a; margin-bottom: 4px">我的图表</h1>
        <p style="font-size: 14px; color: #94a3b8">管理你创建的所有图表</p>
      </div>
      <button @click="router.push('/templates')" style="display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px; font-size: 14px; font-weight: 500; border-radius: 8px; background: #1a56db; color: #fff; border: none; cursor: pointer; font-family: inherit">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        新建图表
      </button>
    </div>

    <div style="display: flex; gap: 16px; margin-bottom: 20px; align-items: center; flex-wrap: wrap">
      <div style="position: relative; width: 280px; flex-shrink: 0">
        <span style="position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: #94a3b8">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        </span>
        <input v-model="search" placeholder="搜索图表..." @keyup.enter="loadCharts" style="box-sizing: border-box; width: 100%; padding: 10px 16px 10px 40px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; font-family: inherit; color: #1e293b; background: #fff; outline: none" />
      </div>
      <div style="display: inline-flex; gap: 4px; background: #f1f5f9; border-radius: 8px; padding: 3px; flex-shrink: 0; overflow: visible">
        <button v-for="t in tabs" :key="t.key" @click="filter = t.key"
          :style="{
            minWidth: t.key === 'all' ? '56px' : '86px', padding: '7px 16px', fontSize: '13px', lineHeight: '18px', borderRadius: '6px', border: 'none', cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.2s', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', whiteSpace: 'nowrap', overflow: 'visible',
            background: filter === t.key ? '#fff' : 'transparent',
            color: filter === t.key ? '#2563eb' : '#64748b',
            boxShadow: filter === t.key ? '0 1px 2px rgba(15,23,42,0.05)' : 'none',
            fontWeight: filter === t.key ? 600 : 400
          }">{{ t.label }}</button>
      </div>
    </div>

    <div style="display: flex; flex-direction: column; gap: 8px">
      <div v-for="chart in filtered" :key="chart.id"
        style="background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 16px 20px; cursor: pointer; transition: all 0.2s"
        @mouseenter="(e) => { (e.currentTarget as HTMLElement).style.boxShadow = '0 12px 32px rgba(15,23,42,0.12)'; (e.currentTarget as HTMLElement).style.borderColor = '#bfdbfe'; (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)' }"
        @mouseleave="(e) => { (e.currentTarget as HTMLElement).style.boxShadow = 'none'; (e.currentTarget as HTMLElement).style.borderColor = '#e2e8f0'; (e.currentTarget as HTMLElement).style.transform = 'none' }">
        <div style="display: flex; align-items: center; gap: 16px">
          <div :style="{ width: '44px', height: '44px', borderRadius: '10px', background: chart.engine === 'vue-component' ? '#f5f3ff' : chart.engine === 'drawio' ? '#fff7ed' : '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }">
            <svg v-if="chart.engine === 'vue-component'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><path d="M10 6.5h4.5a2 2 0 0 1 2 2V14"/></svg>
            <svg v-else-if="chart.engine === 'drawio'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ea580c" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="9" x2="15" y2="15"/><line x1="15" y1="9" x2="9" y2="15"/></svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
          </div>
          <div style="flex: 1">
            <div style="font-size: 15px; font-weight: 600; color: #1e293b; margin-bottom: 2px">{{ chart.title }}</div>
            <div style="display: flex; gap: 12px; font-size: 12px; color: #94a3b8">
              <span>{{ chart.templateId }}</span>
              <span style="display: flex; align-items: center; gap: 4px">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                {{ chart.createdAt ? new Date(chart.createdAt).toLocaleString() : '' }}
              </span>
            </div>
          </div>
          <div style="display: flex; gap: 4px">
            <button @click.stop="editChart(chart)" title="编辑"
              style="width: 32px; height: 32px; border-radius: 6px; border: 1px solid #bfdbfe; background: transparent; cursor: pointer; display: flex; align-items: center; justify-content: center; color: #2563eb; transition: all 0.15s"
              @mouseenter="(e) => { (e.currentTarget as HTMLElement).style.background = '#eff6ff' }"
              @mouseleave="(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent' }">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
            <button @click.stop title="复制"
              style="width: 32px; height: 32px; border-radius: 6px; border: 1px solid #bfdbfe; background: transparent; cursor: pointer; display: flex; align-items: center; justify-content: center; color: #2563eb; transition: all 0.15s"
              @mouseenter="(e) => { (e.currentTarget as HTMLElement).style.background = '#eff6ff' }"
              @mouseleave="(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent' }">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            </button>
            <button @click.stop="deleteChart(chart.id)" title="删除"
              style="width: 32px; height: 32px; border-radius: 6px; border: 1px solid #fca5a5; background: transparent; cursor: pointer; display: flex; align-items: center; justify-content: center; color: #ef4444; transition: all 0.15s"
              @mouseenter="(e) => { (e.currentTarget as HTMLElement).style.background = '#fef2f2' }"
              @mouseleave="(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent' }">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="filtered.length === 0" style="text-align: center; padding: 64px 24px">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin: 0 auto 16px; display: block"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
      <div style="font-size: 18px; font-weight: 600; color: #334155; margin-bottom: 8px">暂无图表</div>
      <div style="font-size: 14px; color: #94a3b8; margin-bottom: 24px">开始创建你的第一个图表吧</div>
      <button @click="router.push('/templates')" style="display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px; font-size: 14px; font-weight: 500; border-radius: 8px; background: #1a56db; color: #fff; border: none; cursor: pointer; font-family: inherit">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        新建图表
      </button>
    </div>

    <div v-if="total > 10" style="display: flex; justify-content: center; padding: 16px">
      <el-pagination v-model:current-page="page" :page-size="10" :total="total" layout="prev, pager, next" @current-change="loadCharts" />
    </div>
  </div>
</template>
