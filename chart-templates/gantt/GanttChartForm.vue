<template>
  <div class="gantt-container" :class="{ 'preview-mode': mode === 'preview' }">
    <div v-if="mode !== 'preview'" class="left-panel">
      <el-card shadow="never" class="block">
        <template #header>
          <div class="hdr">
            <span>基本信息</span>
            <el-button link type="primary" size="small" @click="loadExample">加载示例</el-button>
          </div>
        </template>
        <el-form :model="model" label-width="80px" size="small">
          <el-form-item label="图表标题">
            <el-input v-model="model.title" placeholder="如 12个月实施里程碑" />
          </el-form-item>
          <el-form-item label="月份数量">
            <el-input-number v-model="monthCount" :min="1" :max="36" size="small" @change="onMonthCountChange" />
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="block" v-for="(phase, pi) in model.phases" :key="pi">
        <template #header>
          <div class="hdr">
            <span>{{ phase.name || `阶段 ${pi + 1}` }}</span>
            <el-button link type="danger" size="small" @click="removePhase(pi)">删除阶段</el-button>
          </div>
        </template>
        <el-form label-width="70px" size="small">
          <el-form-item label="阶段名称">
            <el-input v-model="phase.name" placeholder="如 阶段一：需求分析" />
          </el-form-item>
          <el-row :gutter="8">
            <el-col :span="8">
              <el-form-item label="颜色">
                <el-color-picker v-model="phase.color" size="small" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="开始月">
                <el-input-number v-model="phase.startMonth" :min="1" :max="monthCount" size="small" :controls="false" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="跨月数">
                <el-input-number v-model="phase.duration" :min="0.5" :step="0.5" size="small" :controls="false" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <div class="tbl-actions">
          <el-button link type="primary" size="small" @click="addTask(pi)">新增任务</el-button>
        </div>
        <el-table :data="phase.tasks" border size="small" max-height="280">
          <el-table-column label="任务名称" min-width="140">
            <template #default="{ row }">
              <el-input v-model="row.name" size="small" placeholder="任务名称" />
            </template>
          </el-table-column>
          <el-table-column label="开始月" width="80">
            <template #default="{ row }">
              <el-input-number v-model="row.startMonth" :min="1" :step="0.1" size="small" :controls="false" style="width: 100%" />
            </template>
          </el-table-column>
          <el-table-column label="跨月数" width="80">
            <template #default="{ row }">
              <el-input-number v-model="row.duration" :min="0.1" :step="0.1" size="small" :controls="false" style="width: 100%" />
            </template>
          </el-table-column>
          <el-table-column label="" width="44" align="center">
            <template #default="{ $index }">
              <el-button link type="danger" size="small" @click="removeTask(pi, $index)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-button type="primary" plain size="small" style="width: 100%; margin-top: 4px" @click="addPhase">+ 新增阶段</el-button>

      <div v-if="$slots['save-button']" class="save-slot-wrapper">
        <slot name="save-button" />
      </div>
    </div>

    <div class="right-panel">
      <el-alert
        v-if="mode === 'preview'"
        type="info"
        :closable="false"
        show-icon
        title="AI 已生成甘特图数据"
        description="请核对下方预览；确认后点击左侧「确认生成，进入编辑」打开 Draw.io。"
        class="preview-alert"
      />

      <div class="chart-container">
        <div class="chart-scroll">
          <div class="gantt-paper">
            <svg
              class="gantt-svg"
              :width="layout.svgW"
              :height="layout.svgH"
              xmlns="http://www.w3.org/2000/svg"
            >
              <!-- Title -->
              <text
                :x="layout.svgW / 2" :y="32"
                text-anchor="middle" dominant-baseline="central"
                class="svg-title"
              >{{ model.title }}</text>

              <!-- Header background -->
              <rect
                :x="0" :y="layout.titleH"
                :width="layout.svgW" :height="layout.headerH"
                fill="#4a4a4a"
              />

              <!-- Header: task column -->
              <rect
                :x="0" :y="layout.titleH"
                :width="layout.taskColW" :height="layout.headerH"
                fill="#4a4a4a" stroke="#333"
              />
              <text
                :x="layout.taskColW / 2" :y="layout.titleH + layout.headerH / 2"
                text-anchor="middle" dominant-baseline="central"
                fill="#fff" class="svg-header"
              >阶段 / 任务</text>

              <!-- Header: month columns -->
              <g v-for="(m, i) in model.months" :key="'mh-' + i">
                <rect
                  :x="layout.taskColW + i * layout.monthW" :y="layout.titleH"
                  :width="layout.monthW" :height="layout.headerH"
                  fill="#4a4a4a" stroke="#333"
                />
                <text
                  :x="layout.taskColW + i * layout.monthW + layout.monthW / 2"
                  :y="layout.titleH + layout.headerH / 2"
                  text-anchor="middle" dominant-baseline="central"
                  fill="#fff" class="svg-header"
                >{{ m }}</text>
              </g>

              <!-- Grid lines -->
              <line
                v-for="i in model.months.length - 1" :key="'gl-' + i"
                :x1="layout.taskColW + i * layout.monthW"
                :y1="layout.titleH + layout.headerH"
                :x2="layout.taskColW + i * layout.monthW"
                :y2="layout.svgH"
                stroke="#e0e0e0" stroke-dasharray="4 4"
              />

              <!-- Phase & task rows -->
              <g v-for="(row, ri) in layout.rows" :key="'row-' + ri">
                <!-- Phase header row -->
                <template v-if="row.type === 'phase'">
                  <rect
                    :x="0" :y="row.y"
                    :width="layout.taskColW" :height="row.h"
                    :fill="row.color" :stroke="row.strokeColor"
                  />
                  <text
                    :x="10" :y="row.y + row.h / 2"
                    dominant-baseline="central"
                    fill="#fff" class="svg-phase-label"
                  >{{ row.label }}</text>
                  <!-- Phase bar -->
                  <rect
                    :x="row.barX" :y="row.y"
                    :width="row.barW" :height="row.h"
                    :fill="row.color" :stroke="row.strokeColor"
                    opacity="0.4" rx="4"
                  />
                </template>

                <!-- Task row -->
                <template v-if="row.type === 'task'">
                  <rect
                    :x="0" :y="row.y"
                    :width="layout.taskColW" :height="row.h"
                    :fill="row.bgColor" stroke="#d9d9d9"
                  />
                  <text
                    :x="10" :y="row.y + row.h / 2"
                    dominant-baseline="central"
                    fill="#333" class="svg-task-label"
                  >{{ row.label }}</text>
                  <!-- Task bar -->
                  <rect
                    :x="row.barX" :y="row.y + 3"
                    :width="row.barW" :height="row.h - 6"
                    :fill="row.barColor" :stroke="row.barStroke"
                    rx="4"
                  />
                </template>
              </g>
            </svg>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch, computed } from 'vue'
import type { GanttPayload, GanttPhase, GanttTask } from './buildMxGraphXml'
import { coerceGanttPayload, exampleGanttPayload } from './buildMxGraphXml'

const DEFAULT_PHASE_COLORS = [
  '#4472C4', '#548235', '#BF8F00', '#C00000', '#7030A0', '#2E75B6',
  '#ED7D31', '#70AD47', '#FFC000', '#5B9BD5',
]

const props = withDefaults(
  defineProps<{ data: Record<string, any> | null; mode?: 'edit' | 'preview' }>(),
  { mode: 'edit' }
)
const emit = defineEmits<{ 'update:data': [GanttPayload] }>()

function mergePayload(raw: Record<string, any> | null): GanttPayload {
  return coerceGanttPayload(raw)
}

const model = reactive<GanttPayload>(mergePayload(props.data))
const monthCount = ref(model.months.length)

function onMonthCountChange(val: number) {
  if (val > model.months.length) {
    for (let i = model.months.length; i < val; i++) {
      model.months.push(`${i + 1}月`)
    }
  } else if (val < model.months.length) {
    model.months.splice(val)
  }
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex)
  if (!m) return null
  return { r: parseInt(m[1], 16), g: parseInt(m[2], 16), b: parseInt(m[3], 16) }
}

function darkenHex(hex: string, amount = 0.2): string {
  const rgb = hexToRgb(hex)
  if (!rgb) return hex
  const r = Math.round(rgb.r * (1 - amount))
  const g = Math.round(rgb.g * (1 - amount))
  const b = Math.round(rgb.b * (1 - amount))
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
}

function lightenHex(hex: string, amount = 0.7): string {
  const rgb = hexToRgb(hex)
  if (!rgb) return hex
  const r = Math.round(rgb.r + (255 - rgb.r) * amount)
  const g = Math.round(rgb.g + (255 - rgb.g) * amount)
  const b = Math.round(rgb.b + (255 - rgb.b) * amount)
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
}

interface RowLayout {
  type: 'phase' | 'task'
  y: number
  h: number
  label: string
  color?: string
  strokeColor?: string
  bgColor?: string
  barX: number
  barW: number
  barColor?: string
  barStroke?: string
}

const layout = computed(() => {
  const TITLE_H = 56
  const HEADER_H = 40
  const PHASE_ROW_H = 36
  const TASK_ROW_H = 32
  const TASK_COL_W = 220
  const MONTH_W = 72

  const mc = model.months.length
  const svgW = TASK_COL_W + mc * MONTH_W
  const rows: RowLayout[] = []
  let curY = TITLE_H + HEADER_H

  for (const phase of model.phases) {
    const strokeColor = darkenHex(phase.color)
    const barX = TASK_COL_W + (phase.startMonth - 1) * MONTH_W
    const barW = phase.duration * MONTH_W

    rows.push({
      type: 'phase',
      y: curY,
      h: PHASE_ROW_H,
      label: phase.name,
      color: phase.color,
      strokeColor,
      barX,
      barW,
    })
    curY += PHASE_ROW_H

    phase.tasks.forEach((task, ti) => {
      const bgColor = ti % 2 === 0 ? '#f2f2f2' : '#ffffff'
      const tbX = TASK_COL_W + (task.startMonth - 1) * MONTH_W
      const tbW = task.duration * MONTH_W

      rows.push({
        type: 'task',
        y: curY,
        h: TASK_ROW_H,
        label: task.name,
        bgColor,
        barX: tbX,
        barW: tbW,
        barColor: lightenHex(phase.color, 0.75),
        barStroke: lightenHex(phase.color, 0.3),
      })
      curY += TASK_ROW_H
    })
  }

  return {
    svgW,
    svgH: curY,
    titleH: TITLE_H,
    headerH: HEADER_H,
    taskColW: TASK_COL_W,
    monthW: MONTH_W,
    rows,
  }
})

function emitAll() {
  emit('update:data', JSON.parse(JSON.stringify(model)) as GanttPayload)
}

watch(
  () => model,
  () => { if (props.mode !== 'preview') emitAll() },
  { deep: true }
)

if (props.mode !== 'preview') {
  emitAll()
}

function addPhase() {
  const idx = model.phases.length
  model.phases.push({
    name: `阶段${idx + 1}`,
    color: DEFAULT_PHASE_COLORS[idx % DEFAULT_PHASE_COLORS.length],
    startMonth: Math.min(idx * 2 + 1, monthCount.value),
    duration: 2,
    tasks: [{ name: '新任务', startMonth: Math.min(idx * 2 + 1, monthCount.value), duration: 1 }],
  })
}

function removePhase(pi: number) {
  if (model.phases.length <= 1) return
  model.phases.splice(pi, 1)
}

function addTask(pi: number) {
  const phase = model.phases[pi]
  phase.tasks.push({
    name: '',
    startMonth: phase.startMonth,
    duration: 1,
  })
}

function removeTask(pi: number, ti: number) {
  model.phases[pi].tasks.splice(ti, 1)
}

function loadExample() {
  const ex = exampleGanttPayload()
  model.title = ex.title
  model.months.splice(0, model.months.length, ...ex.months)
  monthCount.value = ex.months.length
  model.phases.splice(
    0,
    model.phases.length,
    ...ex.phases.map(p => ({
      ...p,
      tasks: p.tasks.map(t => ({ ...t })),
    }))
  )
}
</script>

<style scoped>
.gantt-container {
  display: flex;
  height: 100%;
  gap: 16px;
  overflow: hidden;
}

.gantt-container.preview-mode .right-panel {
  flex: 1;
  width: 100%;
}

.save-slot-wrapper {
  padding: 12px 0 4px;
  display: flex;
  justify-content: center;
  flex-shrink: 0;
}

.left-panel {
  width: 420px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  padding-bottom: 20px;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  padding: 16px;
  overflow: hidden;
}

.preview-alert {
  flex-shrink: 0;
}

.chart-container {
  flex: 1;
  overflow: auto;
  background: #f8fafc;
  display: flex;
  justify-content: center;
  padding: 20px;
  border-radius: 4px;
  min-height: 0;
}

.chart-scroll {
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  height: max-content;
}

.gantt-paper {
  background: #fff;
  padding: 8px;
}

.gantt-svg {
  display: block;
}

.svg-title {
  font-size: 18px;
  font-weight: 700;
  fill: #333;
}

.svg-header {
  font-size: 12px;
  font-weight: 600;
}

.svg-phase-label {
  font-size: 12px;
  font-weight: 600;
}

.svg-task-label {
  font-size: 11px;
}

.block {
  border-radius: 10px;
}

.block :deep(.el-card__body) {
  padding: 8px 10px;
}

.block :deep(.el-card__header) {
  padding: 8px 12px;
}

.hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tbl-actions {
  margin-bottom: 8px;
}
</style>
