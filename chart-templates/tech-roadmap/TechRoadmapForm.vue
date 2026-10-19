<template>
  <div class="roadmap-container" :class="{ 'preview-mode': mode === 'preview' }">
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
            <el-input v-model="model.title" placeholder="技术路线图标题" />
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="block" v-for="(stage, si) in model.stages" :key="si">
        <template #header>
          <div class="hdr">
            <span>{{ stage.name?.split('\n')[0] || `阶段 ${si + 1}` }}</span>
            <el-button link type="danger" size="small" @click="removeStage(si)">删除阶段</el-button>
          </div>
        </template>
        <el-form label-width="70px" size="small">
          <el-form-item label="阶段名称">
            <el-input v-model="stage.name" type="textarea" :rows="2" placeholder="如 第一阶段\n理论分析" />
          </el-form-item>
          <el-form-item label="主题色">
            <el-color-picker v-model="stage.color" size="small" />
          </el-form-item>
        </el-form>

        <div class="tbl-actions">
          <el-button link type="primary" size="small" @click="addNode(si)">新增节点</el-button>
        </div>
        <el-table :data="stage.nodes" border size="small" max-height="260">
          <el-table-column label="标签" min-width="100">
            <template #default="{ row }">
              <el-input v-model="row.label" size="small" placeholder="节点标题" />
            </template>
          </el-table-column>
          <el-table-column label="详情" min-width="140">
            <template #default="{ row }">
              <el-input v-model="row.detail" size="small" type="textarea" :rows="2" placeholder="多行内容(换行分隔)" />
            </template>
          </el-table-column>
          
          <el-table-column label="" width="44" align="center">
            <template #default="{ $index }">
              <el-button link type="danger" size="small" @click="removeNode(si, $index)">删</el-button>
            </template>
          </el-table-column>
        </el-table>

        <p style="margin: 8px 0 0; font-size: 12px; color: #94a3b8">连线自动生成，如需调整请到 Draw.io 编辑器进行修改</p>
      </el-card>

      <el-button type="primary" plain size="small" style="width: 100%; margin-top: 4px" @click="addStage">+ 新增阶段</el-button>

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
        title="AI 已生成技术路线图数据"
        description="请核对下方预览；确认后点击左侧「确认生成，进入编辑」打开 Draw.io。"
        class="preview-alert"
      />

      <div class="chart-container">
        <div class="chart-scroll">
          <div class="roadmap-paper">
            <svg
              class="roadmap-svg"
              :width="layout.svgW"
              :height="layout.svgH"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <marker v-for="(stage, si) in model.stages" :key="'mk-'+si"
                  :id="'arrow-' + si" viewBox="0 0 10 10" refX="10" refY="5"
                  markerWidth="8" markerHeight="8" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" :fill="stage.color" />
                </marker>
              </defs>

              <!-- Title -->
              <rect x="0" y="0" :width="layout.svgW" height="40" fill="#f5f5f5" stroke="#ccc" />
              <text :x="layout.svgW / 2" y="24" text-anchor="middle" dominant-baseline="central" class="svg-title">{{ model.title }}</text>

              <!-- Stages -->
              <g v-for="(sr, si) in layout.stageRows" :key="'s-' + si">
                <!-- Label -->
                <rect :x="0" :y="sr.y" :width="layout.labelW" :height="sr.h"
                  fill="#f5f5f5" :stroke="sr.color" stroke-dasharray="4 4" />
                <text :x="layout.labelW / 2" :y="sr.y + sr.h / 2"
                  text-anchor="middle" dominant-baseline="central" class="svg-stage-label">
                  <tspan v-for="(line, li) in sr.nameLines" :key="li"
                    :x="layout.labelW / 2" :dy="li === 0 ? 0 : 16">{{ line }}</tspan>
                </text>

                <!-- Background -->
                <rect :x="layout.labelW + 8" :y="sr.y" :width="layout.contentW" :height="sr.h"
                  :fill="sr.bgFill" :stroke="sr.color" fill-opacity="0.3" rx="6" />

                <!-- Nodes -->
                <g v-for="nr in sr.nodeRects" :key="nr.id">
                  <rect :x="nr.x" :y="nr.y" :width="nr.w" :height="nr.h"
                    :fill="nr.fill" :stroke="nr.stroke" rx="6" />
                  <text :x="nr.x + nr.w / 2" :y="nr.y + 16"
                    text-anchor="middle" dominant-baseline="central"
                    class="svg-node-label">{{ nr.label }}</text>
                  <text v-if="nr.detailLines.length" :x="nr.x + nr.w / 2" :y="nr.y + 32"
                    text-anchor="middle" class="svg-node-detail">
                    <tspan v-for="(dl, dli) in nr.detailLines" :key="dli"
                      :x="nr.x + nr.w / 2" :dy="dli === 0 ? 0 : 14">{{ dl }}</tspan>
                  </text>
                </g>

                <!-- Connections (orthogonal edge-to-edge) -->
                <path v-for="(edge, ei) in sr.edges" :key="'e-' + ei"
                  :d="edge.path" fill="none"
                  :stroke="sr.color" stroke-width="2" :marker-end="`url(#arrow-${si})`" />
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
import type { RoadmapPayload } from './buildMxGraphXml'
import { coerceRoadmapPayload, exampleRoadmapPayload } from './buildMxGraphXml'

const STAGE_COLORS = ['#6c8ebf', '#d79b00', '#82b366', '#9673a6', '#b85450', '#2E75B6']
const STAGE_FILLS: Record<string, string> = {
  '#6c8ebf': '#dae8fc', '#d79b00': '#ffe6cc', '#82b366': '#d5e8d4',
  '#9673a6': '#e1d5e7', '#b85450': '#f8cecc', '#2E75B6': '#BDD7EE',
}

const props = withDefaults(
  defineProps<{ data: Record<string, any> | null; mode?: 'edit' | 'preview' }>(),
  { mode: 'edit' }
)
const emit = defineEmits<{ 'update:data': [RoadmapPayload] }>()

const model = reactive<RoadmapPayload>(coerceRoadmapPayload(props.data))

interface NodeRect {
  id: string; x: number; y: number; w: number; h: number
  fill: string; stroke: string; label: string; detailLines: string[]
}
interface Edge { path: string }
interface StageRow {
  y: number; h: number; color: string; bgFill: string; nameLines: string[]
  nodeRects: NodeRect[]; edges: Edge[]
}

interface Rect { x: number; y: number; w: number; h: number }

type EdgeDir = 'ltr' | 'rtl' | 'down' | 'down-enter-right' | 'down-enter-left'

function edgePath(from: Rect, to: Rect, dir: EdgeDir): string {
  const fromCy = from.y + from.h / 2
  const toCy = to.y + to.h / 2
  const fromCx = from.x + from.w / 2

  if (dir === 'ltr') {
    const x1 = from.x + from.w, x2 = to.x
    const mx = (x1 + x2) / 2
    return `M ${x1} ${fromCy} H ${mx} V ${toCy} H ${x2}`
  }
  if (dir === 'rtl') {
    const x1 = from.x, x2 = to.x + to.w
    const mx = (x1 + x2) / 2
    return `M ${x1} ${fromCy} H ${mx} V ${toCy} H ${x2}`
  }
  if (dir === 'down') {
    return `M ${fromCx} ${from.y + from.h} V ${to.y}`
  }
  // Cross-row different column: bottom → side
  const y1 = from.y + from.h
  const enterX = dir === 'down-enter-right' ? to.x + to.w : to.x
  return `M ${fromCx} ${y1} V ${toCy} H ${enterX}`
}

const layout = computed(() => {
  const LABEL_W = 100
  const CONTENT_W = 700
  const SVG_W = LABEL_W + CONTENT_W + 16
  const NODE_H_BASE = 36
  const LINE_H = 14
  const PAD = 16
  const NODE_GAP = 24
  const ROW_GAP = 28
  const STAGE_GAP = 12
  const AVAIL_W = CONTENT_W - PAD * 2

  let curY = 48
  const stageRows: StageRow[] = []

  for (const stage of model.stages) {
    const nodeCount = stage.nodes.length
    if (nodeCount === 0) continue

    // Uniform node size within stage
    const uniformW = Math.max(140, ...stage.nodes.map(n => {
      const chars = n.label.length
      return Math.min(chars * 16 + 40, 220)
    }))
    const uniformH = Math.max(NODE_H_BASE, ...stage.nodes.map(n => {
      const lines = n.detail ? n.detail.split('\n').length : 0
      return NODE_H_BASE + lines * LINE_H
    }))

    const maxPerRow = Math.max(1, Math.floor((AVAIL_W + NODE_GAP) / (uniformW + NODE_GAP)))
    const rowCount = Math.ceil(nodeCount / maxPerRow)

    const stageContentH = rowCount * uniformH + (rowCount - 1) * ROW_GAP + PAD * 2
    const stageH = Math.max(stageContentH, 80)

    const bgFill = STAGE_FILLS[stage.color] || '#f5f5f5'
    const nodeRects: NodeRect[] = []
    const rectMap = new Map<string, Rect>()
    const nodeRowInfo = new Map<string, { row: number; isRTL: boolean }>()

    const totalGridW = maxPerRow * uniformW + (maxPerRow - 1) * NODE_GAP
    const gridBaseX = LABEL_W + PAD + 16 + Math.max((AVAIL_W - totalGridW) / 2, 0)
    const slotX = (s: number) => gridBaseX + s * (uniformW + NODE_GAP)

    let ny = curY + PAD
    for (let ri = 0; ri < rowCount; ri++) {
      const start = ri * maxPerRow
      const end = Math.min(start + maxPerRow, nodeCount)
      const count = end - start
      const isRTL = ri % 2 === 1

      for (let ci = 0; ci < count; ci++) {
        const idx = start + ci
        const node = stage.nodes[idx]
        const slot = isRTL ? (maxPerRow - 1 - ci) : ci
        const nx = slotX(slot)
        const detailLines = node.detail ? node.detail.split('\n') : []

        nodeRects.push({
          id: node.id, x: nx, y: ny, w: uniformW, h: uniformH,
          fill: '#ffffff', stroke: stage.color,
          label: node.label, detailLines,
        })
        rectMap.set(node.id, { x: nx, y: ny, w: uniformW, h: uniformH })
        nodeRowInfo.set(node.id, { row: ri, isRTL })
      }
      ny += uniformH + ROW_GAP
    }

    const edges: Edge[] = []
    for (let i = 0; i < nodeCount - 1; i++) {
      const fromRect = rectMap.get(stage.nodes[i].id)
      const toRect = rectMap.get(stage.nodes[i + 1].id)
      const fromInfo = nodeRowInfo.get(stage.nodes[i].id)
      const toInfo = nodeRowInfo.get(stage.nodes[i + 1].id)
      if (fromRect && toRect && fromInfo && toInfo) {
        let dir: EdgeDir
        if (fromInfo.row === toInfo.row) {
          dir = fromInfo.isRTL ? 'rtl' : 'ltr'
        } else if (Math.abs(fromRect.x - toRect.x) < 2) {
          dir = 'down'
        } else {
          dir = toInfo.isRTL ? 'down-enter-right' : 'down-enter-left'
        }
        edges.push({ path: edgePath(fromRect, toRect, dir) })
      }
    }

    stageRows.push({
      y: curY, h: stageH, color: stage.color, bgFill,
      nameLines: stage.name.split('\n'),
      nodeRects, edges,
    })
    curY += stageH + STAGE_GAP
  }

  return { svgW: SVG_W, svgH: curY, labelW: LABEL_W, contentW: CONTENT_W, stageRows }
})

function emitAll() {
  emit('update:data', JSON.parse(JSON.stringify(model)) as RoadmapPayload)
}

watch(() => model, () => { if (props.mode !== 'preview') emitAll() }, { deep: true })
if (props.mode !== 'preview') emitAll()

let nodeCounter = 100
function addStage() {
  const idx = model.stages.length
  const nid = `n${++nodeCounter}`
  model.stages.push({
    name: `第${idx + 1}阶段`,
    color: STAGE_COLORS[idx % STAGE_COLORS.length],
    nodes: [{ id: nid, label: '新节点', detail: '' }],
  })
}

function removeStage(si: number) {
  if (model.stages.length <= 1) return
  model.stages.splice(si, 1)
}

function addNode(si: number) {
  const nid = `n${++nodeCounter}`
  model.stages[si].nodes.push({ id: nid, label: '', detail: '' })
}

function removeNode(si: number, ni: number) {
  model.stages[si].nodes.splice(ni, 1)
}

function loadExample() {
  const ex = exampleRoadmapPayload()
  model.title = ex.title
  model.stages.splice(
    0, model.stages.length,
    ...ex.stages.map(s => ({
      ...s,
      nodes: s.nodes.map(n => ({ ...n })),
    }))
  )
}
</script>

<style scoped>
.roadmap-container {
  display: flex;
  height: 100%;
  gap: 16px;
  overflow: hidden;
}
.roadmap-container.preview-mode .right-panel {
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
.preview-alert { flex-shrink: 0; }
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
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  height: max-content;
}
.roadmap-paper {
  background: #fff;
  padding: 8px;
}
.roadmap-svg { display: block; }
.svg-title { font-size: 14px; font-weight: 700; fill: #333; }
.svg-stage-label { font-size: 11px; font-weight: 600; fill: #333; }
.svg-node-label { font-size: 10px; fill: #333; }
.svg-node-detail { font-size: 9px; fill: #555; }
.block { border-radius: 10px; }
.block :deep(.el-card__body) { padding: 8px 10px; }
.block :deep(.el-card__header) { padding: 8px 12px; }
.hdr { display: flex; align-items: center; justify-content: space-between; }
.tbl-actions { margin-bottom: 8px; }
</style>
