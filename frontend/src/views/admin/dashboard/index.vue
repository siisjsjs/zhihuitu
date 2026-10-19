<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import request from '@/api/request'

const stats = ref<any>({})
const trendChart = ref<HTMLDivElement>()
const pieChart = ref<HTMLDivElement>()
let trendInstance: any = null
let pieInstance: any = null

const templateNameMap: Record<string, string> = {
  'process-flow': '流程程序图',
  'man-machine': '人机作业分析图',
  therblig: '动素分析图',
  'joint-operation': '联合作业分析图',
  'two-hand': '双手作业分析图',
  'operation-process': '工艺程序图',
  pareto: '帕累托图',
  fishbone: '鱼骨图',
  capability: '过程能力分析',
  histogram: '直方图',
  scatter: '散点图',
  'xbar-r': 'X̄-R 控制图',
  'x-mr': 'I-MR 控制图',
  'control-p': 'p 控制图',
  'control-c': 'c 控制图',
  dpmo: 'DPMO 控制图',
  'target-ix': '目标偏差图',
  eoq: '经济订货量模型',
  epq: '经济生产批量模型',
  'line-balance': '产线平衡分析',
  'learning-curve': '学习曲线',
  oee: '设备综合效率',
  reliability: '可靠性分析',
  yamazumi: '山积图',
  'value-stream': '价值流程图',
  matplotlib: '数据图表',
  'vue-component': '流程/架构图',
  drawio: 'Draw.io 图表',
}

function displayTemplateName(id: string) {
  return templateNameMap[id] || id
}

async function loadStats() {
  const data = await request.get('/admin/dashboard/stats')
  stats.value = data
}

async function loadCharts() {
  const trends = await request.get('/admin/dashboard/trends')
  const dist = await request.get('/admin/dashboard/chart-distribution')
  const hot = await request.get('/admin/dashboard/hot-templates')

  if (trendChart.value) {
    trendInstance = echarts.init(trendChart.value)
    trendInstance.setOption({
      title: { text: '近7天图表生成趋势', left: 'left', textStyle: { fontSize: 14, fontWeight: 600 } },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: trends.labels || ['周一','周二','周三','周四','周五','周六','周日'] },
      yAxis: { type: 'value', minInterval: 1 },
      series: [{ type: 'line', data: trends.values || [], smooth: true, lineStyle: { color: '#3b82f6', width: 2 }, areaStyle: { color: 'rgba(59,130,246,0.1)' }, itemStyle: { color: '#3b82f6' } }],
      grid: { left: 40, right: 20, top: 50, bottom: 30 }
    })
  }

  if (pieChart.value) {
    pieInstance = echarts.init(pieChart.value)
    pieInstance.setOption({
      title: { text: '图表类型分布', left: 'left', textStyle: { fontSize: 14, fontWeight: 600 } },
      tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
      series: [{
        type: 'pie', radius: ['40%', '65%'], center: ['50%', '55%'],
        data: (dist.labels || ['柱状图','折线图','饼图']).map((l: string, i: number) => ({
          name: displayTemplateName(l), value: (dist.values || [35,25,18])[i] || 10
        })),
        label: { show: true, formatter: '{b}\n{d}%' },
        itemStyle: { borderRadius: 4 }
      }]
    })
  }

  hotTemplates.value = (hot || []).map((item: any) => ({
    ...item,
    name: displayTemplateName(item.name),
  }))
}

const hotTemplates = ref<any[]>([])
const dailyActivity = ref<any[]>([])
const dailyLoading = ref(true)
const expandedDays = ref<Record<string, boolean>>({})

const engineMap: Record<string, string> = {
  matplotlib: 'ECharts 数据图',
  echarts: 'ECharts 数据图',
  'vue-component': '流程/架构图',
  drawio: 'Draw.io 图表',
}

function displayEngine(e: string) {
  return engineMap[e] || e || '—'
}

function weekday(dateStr: string) {
  const names = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return names[new Date(dateStr + 'T00:00:00').getDay()]
}

function dayLabel(dateStr: string) {
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const y = new Date(today.getTime() - 86400000)
  const yStr = `${y.getFullYear()}-${String(y.getMonth() + 1).padStart(2, '0')}-${String(y.getDate()).padStart(2, '0')}`
  if (dateStr === todayStr) return '今天'
  if (dateStr === yStr) return '昨天'
  return dateStr.slice(5)
}

function fmtTime(s: string) {
  if (!s) return ''
  const d = new Date(s)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function toggleDay(date: string) {
  expandedDays.value[date] = !expandedDays.value[date]
}

async function loadDailyActivity() {
  dailyLoading.value = true
  try {
    const data = await request.get('/admin/dashboard/daily-activity', { params: { days: 7 } })
    dailyActivity.value = data || []
    // 默认展开最近一个有数据的日期
    const firstWithData = dailyActivity.value.find((d: any) => d.total > 0)
    if (firstWithData) expandedDays.value[firstWithData.date] = true
  } finally {
    dailyLoading.value = false
  }
}

onMounted(() => {
  loadStats()
  loadCharts()
  loadDailyActivity()
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  trendInstance?.dispose()
  pieInstance?.dispose()
})

function resizeCharts() {
  trendInstance?.resize()
  pieInstance?.resize()
}
</script>

<template>
  <div style="padding: 28px">
    <div style="margin-bottom: 24px">
      <h1 style="font-size: 22px; font-weight: 700; color: #0f172a; margin: 0">数据看板</h1>
      <p style="font-size: 13px; color: #94a3b8; margin-top: 2px">平台运营数据概览</p>
    </div>

    <!-- Stats Cards -->
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px">
      <div v-for="(s, i) in [
        { label: '总用户数', val: stats.totalUsers ?? '--', icon: '👥', color: '#3b82f6', bg: '#eff6ff', delta: stats.userDelta },
        { label: '今日生成', val: stats.todayCharts ?? '--', icon: '📊', color: '#8b5cf6', bg: '#f5f3ff', delta: stats.chartDelta },
        { label: '活跃用户', val: stats.activeUsers ?? '--', icon: '📈', color: '#10b981', bg: '#f0fdf4', delta: stats.activeDelta },
        { label: '待处理反馈', val: stats.pendingFeedback ?? '--', icon: '💬', color: '#f59e0b', bg: '#fffbeb', delta: stats.feedbackDelta },
      ]" :key="i" style="background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 20px">
        <div style="display: flex; justify-content: space-between; align-items: flex-start">
          <div>
            <div style="font-size: 13px; color: #94a3b8; margin-bottom: 6px">{{ s.label }}</div>
            <div style="font-size: 28px; font-weight: 700; color: #0f172a">{{ s.val }}</div>
          </div>
          <div :style="{ width: 40, height: 40, borderRadius: 10, background: s.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20 }">{{ s.icon }}</div>
        </div>
        <div v-if="s.delta" :style="{ marginTop: 8, fontSize: 12, color: s.delta?.startsWith?.('+') ? '#10b981' : '#ef4444' }">
          {{ s.delta }} 较昨日
        </div>
      </div>
    </div>

    <!-- Charts -->
    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 24px">
      <div style="background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 20px">
        <div ref="trendChart" style="height: 280px"></div>
      </div>
      <div style="background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 20px">
        <div ref="pieChart" style="height: 280px"></div>
      </div>
    </div>

    <!-- Hot Templates -->
    <div style="background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 20px">
      <div style="font-size: 14px; font-weight: 600; color: #0f172a; margin-bottom: 12px">热门模板 Top 5</div>
      <div v-for="(t, i) in hotTemplates" :key="i" style="display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: i < hotTemplates.length - 1 ? '1px solid #f1f5f9' : 'none'">
        <span :style="{
          width: 22, height: 22, borderRadius: 6,
          background: i < 3 ? '#3b82f6' : '#e2e8f0',
          color: i < 3 ? '#fff' : '#94a3b8',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 11, fontWeight: 600
        }">{{ i + 1 }}</span>
        <span style="flex: 1; font-size: 13px; color: #334155">{{ t.name }}</span>
        <span style="font-size: 13px; font-weight: 500; color: #94a3b8">{{ t.count }} 次</span>
      </div>
      <div v-if="hotTemplates.length === 0" style="text-align: center; padding: 24px; color: #94a3b8">暂无数据</div>
    </div>

    <!-- Daily Activity Detail -->
    <div style="background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 20px; margin-top: 24px">
      <div style="display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 16px">
        <div style="font-size: 14px; font-weight: 600; color: #0f172a">每日生成明细</div>
        <div style="font-size: 12px; color: #94a3b8">近 7 天 · 每位用户生成的图表</div>
      </div>

      <!-- Loading skeleton -->
      <div v-if="dailyLoading">
        <div v-for="n in 3" :key="n" style="height: 52px; background: #f8fafc; border-radius: 8px; margin-bottom: 10px; animation: pulse 1.4s ease-in-out infinite"></div>
      </div>

      <!-- Empty state -->
      <div v-else-if="dailyActivity.every(d => d.total === 0)" style="text-align: center; padding: 40px; color: #94a3b8">
        <div style="font-size: 13px">近 7 天暂无图表生成记录</div>
      </div>

      <!-- Day groups -->
      <template v-else>
        <div v-for="day in dailyActivity" :key="day.date" style="margin-bottom: 8px">
          <!-- Day header (clickable) -->
          <div
            @click="day.total > 0 && toggleDay(day.date)"
            :style="{
              display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 14px',
              background: day.total > 0 ? '#f8fafc' : 'transparent',
              borderRadius: '8px', cursor: day.total > 0 ? 'pointer' : 'default',
              userSelect: 'none', transition: 'background 0.15s'
            }"
          >
            <span
              :style="{
                width: '18px', display: 'inline-flex', justifyContent: 'center',
                color: '#94a3b8', fontSize: '12px',
                transform: expandedDays[day.date] ? 'rotate(90deg)' : 'rotate(0deg)',
                transition: 'transform 0.2s', opacity: day.total > 0 ? 1 : 0.3
              }"
            >▶</span>
            <span style="font-size: 13px; font-weight: 600; color: #0f172a; min-width: 48px">{{ dayLabel(day.date) }}</span>
            <span style="font-size: 12px; color: #94a3b8">{{ weekday(day.date) }}</span>
            <div style="flex: 1"></div>
            <span v-if="day.total > 0" style="font-size: 12px; color: #64748b">
              <span style="font-variant-numeric: tabular-nums; font-weight: 600; color: #3b82f6">{{ day.userCount }}</span> 位用户 ·
              <span style="font-variant-numeric: tabular-nums; font-weight: 600; color: #8b5cf6">{{ day.total }}</span> 张图
            </span>
            <span v-else style="font-size: 12px; color: #cbd5e1">无生成</span>
          </div>

          <!-- Day items -->
          <div v-if="expandedDays[day.date] && day.total > 0" style="padding: 6px 0 6px 30px">
            <div
              v-for="item in day.items" :key="item.id"
              style="display: flex; align-items: center; gap: 10px; padding: 9px 12px; border-bottom: 1px solid #f5f7fa"
            >
              <div style="width: 26px; height: 26px; border-radius: 50%; background: #dbeafe; display: flex; align-items: center; justify-content: center; color: #3b82f6; font-size: 12px; font-weight: 600; flex-shrink: 0">
                {{ item.username?.[0] || '?' }}
              </div>
              <span style="font-size: 13px; color: #334155; font-weight: 500; min-width: 80px">{{ item.username }}</span>
              <span style="font-size: 13px; color: #0f172a; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap" :title="item.title">{{ item.title || '未命名图表' }}</span>
              <span style="font-size: 11px; color: #6366f1; background: #eef2ff; padding: 2px 8px; border-radius: 4px; flex-shrink: 0">{{ displayTemplateName(item.templateId) }}</span>
              <span style="font-size: 11px; color: #94a3b8; flex-shrink: 0; min-width: 70px">{{ displayEngine(item.engine) }}</span>
              <span style="font-size: 12px; color: #cbd5e1; font-variant-numeric: tabular-nums; flex-shrink: 0">{{ fmtTime(item.createdAt) }}</span>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
