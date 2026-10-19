<template>
  <div class="vsm-container" :class="{ 'preview-mode': mode === 'preview' }">
    <div v-if="mode !== 'preview'" class="left-panel">
      <el-card shadow="never" class="block">
        <template #header>
          <div class="hdr">
            <span>基本信息</span>
            <el-button link type="primary" size="small" @click="loadExample">加载示例</el-button>
          </div>
        </template>
        <el-form :model="model" label-width="92px" size="small">
          <el-form-item label="图表标题">
            <el-input v-model="model.title" placeholder="如 某装配线当前状态价值流程图" />
          </el-form-item>
          <el-row :gutter="8">
            <el-col :span="14">
              <el-form-item label="有效工时">
                <el-input-number v-model="model.workingTimePerDay" :min="0" :step="600" size="small" :controls="false" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="10">
              <el-form-item label="节拍框">
                <el-switch v-model="model.showTakt" />
              </el-form-item>
            </el-col>
          </el-row>
          <div class="hint">有效工时单位：秒/天（用于计算节拍时间 Takt）</div>
        </el-form>
      </el-card>

      <el-card shadow="never" class="block">
        <template #header><span>客户 / 供应商 / 生产控制</span></template>
        <el-form label-width="92px" size="small">
          <el-form-item label="客户名称">
            <el-input v-model="model.customer.name" placeholder="客户" />
          </el-form-item>
          <el-row :gutter="8">
            <el-col :span="9">
              <el-form-item label="日需求">
                <el-input-number v-model="model.customer.dailyDemand" :min="0" size="small" :controls="false" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="单位">
                <el-input v-model="model.customer.unit" placeholder="件" />
              </el-form-item>
            </el-col>
            <el-col :span="9">
              <el-form-item label="发货频率">
                <el-input v-model="model.customer.deliveryFreq" placeholder="每日1次" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="客户信息流">
            <el-input v-model="model.customer.infoLabel" placeholder="如 月客户订单（生产控制→客户，必备）" />
          </el-form-item>
          <el-divider content-position="left">供应商</el-divider>
          <el-row :gutter="8">
            <el-col :span="14">
              <el-form-item label="供应商">
                <el-input v-model="model.supplier.name" placeholder="供应商" />
              </el-form-item>
            </el-col>
            <el-col :span="10">
              <el-form-item label="送货频率">
                <el-input v-model="model.supplier.deliveryFreq" placeholder="每周2次" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="供应商信息流">
            <el-input v-model="model.supplier.infoLabel" placeholder="如 月采购订单（生产控制→供应商，必备）" />
          </el-form-item>
          <el-form-item label="生产控制">
            <el-input v-model="model.control.name" placeholder="生产控制 / MRP" />
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="block">
        <template #header>
          <div class="hdr">
            <span>工序（左→右）</span>
            <el-button link type="primary" size="small" @click="addProcess">新增工序</el-button>
          </div>
        </template>
        <el-table :data="model.processes" border size="small" max-height="300">
          <el-table-column label="工序名称" min-width="110">
            <template #default="{ row }">
              <el-input v-model="row.name" size="small" placeholder="如 冲压" />
            </template>
          </el-table-column>
          <el-table-column label="C/T(秒)" width="78">
            <template #default="{ row }">
              <el-input-number v-model="row.cycleTime" :min="0" size="small" :controls="false" style="width:100%" />
            </template>
          </el-table-column>
          <el-table-column label="C/O(分)" width="78">
            <template #default="{ row }">
              <el-input-number v-model="row.changeover" :min="0" size="small" :controls="false" style="width:100%" />
            </template>
          </el-table-column>
          <el-table-column label="可用率%" width="72">
            <template #default="{ row }">
              <el-input-number v-model="row.uptime" :min="0" :max="100" size="small" :controls="false" style="width:100%" />
            </template>
          </el-table-column>
          <el-table-column label="良品率%" width="72">
            <template #default="{ row }">
              <el-input-number v-model="row.firstYield" :min="0" :max="100" size="small" :controls="false" style="width:100%" />
            </template>
          </el-table-column>
          <el-table-column label="人数" width="56">
            <template #default="{ row }">
              <el-input-number v-model="row.operators" :min="0" size="small" :controls="false" style="width:100%" />
            </template>
          </el-table-column>
          <el-table-column label="后继工序（并联多选）" min-width="150">
            <template #default="{ row }">
              <el-select
                v-model="row.next" multiple collapse-tags size="small" style="width:100%"
                placeholder="留空=默认下一行"
              >
                <el-option
                  v-for="op in successorOptions(row)" :key="op.value" :value="op.value" :label="op.label"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="" width="40" align="center">
            <template #default="{ $index }">
              <el-button link type="danger" size="small" @click="removeProcess($index)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="hint">后继工序：选填。任一工序填了后继，整图按有向图（支持并联）布局；都不填则按行顺序串联。</div>
      </el-card>

      <el-card shadow="never" class="block">
        <template #header>
          <div class="hdr">
            <span>库存三角</span>
            <el-button link type="primary" size="small" @click="addInventory">新增库存</el-button>
          </div>
        </template>
        <el-table :data="model.inventories" border size="small" max-height="240">
          <el-table-column label="位置" min-width="120">
            <template #default="{ row }">
              <el-select v-model="row.afterIndex" size="small" style="width:100%">
                <el-option :value="-1" label="供应商之后" />
                <el-option v-for="(p, i) in model.processes" :key="i" :value="i" :label="`${p.name || '工序' + (i + 1)} 之后`" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="数量(件)" width="84">
            <template #default="{ row }">
              <el-input-number v-model="row.qty" :min="0" size="small" :controls="false" style="width:100%" />
            </template>
          </el-table-column>
          <el-table-column label="天数" width="74">
            <template #default="{ row }">
              <el-input-number v-model="row.days" :min="0" :step="0.5" size="small" :controls="false" style="width:100%" />
            </template>
          </el-table-column>
          <el-table-column label="类型" width="96">
            <template #default="{ row }">
              <el-select v-model="row.invType" size="small" style="width:100%">
                <el-option value="inventory" label="库存" />
                <el-option value="supermarket" label="超市" />
                <el-option value="fifo" label="FIFO" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="" width="40" align="center">
            <template #default="{ $index }">
              <el-button link type="danger" size="small" @click="removeInventory($index)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="block">
        <template #header>
          <div class="hdr">
            <span>生产控制 → 工序 计划</span>
            <el-button link type="primary" size="small" @click="addInfoFlow">新增计划</el-button>
          </div>
        </template>
        <el-table :data="model.infoFlows" border size="small" max-height="240">
          <el-table-column label="下达到工序" min-width="120">
            <template #default="{ row }">
              <el-select v-model="row.toId" size="small" style="width:100%" placeholder="选择工序">
                <el-option v-for="o in processOptions" :key="o.value" :value="o.value" :label="o.label" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="标签" min-width="110">
            <template #default="{ row }">
              <el-input v-model="row.label" size="small" placeholder="如 日计划" />
            </template>
          </el-table-column>
          <el-table-column label="" width="40" align="center">
            <template #default="{ $index }">
              <el-button link type="danger" size="small" @click="removeInfoFlow($index)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="hint">生产控制→供应商、生产控制→客户为必备信息流（已自动绘制，标签在上方「客户/供应商」处填写）。此处只配置下达到各工序的生产计划。</div>
      </el-card>

      <el-card shadow="never" class="block">
        <template #header>
          <div class="hdr">
            <span>改善闪电 (Kaizen)</span>
            <el-button link type="primary" size="small" @click="addKaizen">新增</el-button>
          </div>
        </template>
        <el-table :data="model.kaizens" border size="small" max-height="200">
          <el-table-column label="位置" width="130">
            <template #default="{ row }">
              <el-select v-model="row.afterIndex" size="small" style="width:100%">
                <el-option :value="-1" label="供应商之后" />
                <el-option v-for="(p, i) in model.processes" :key="i" :value="i" :label="p.name || '工序' + (i + 1)" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="改善点" min-width="120">
            <template #default="{ row }">
              <el-input v-model="row.label" size="small" placeholder="如 换模时间过长" />
            </template>
          </el-table-column>
          <el-table-column label="" width="40" align="center">
            <template #default="{ $index }">
              <el-button link type="danger" size="small" @click="removeKaizen($index)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

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
        title="AI 已生成价值流程图数据"
        description="请核对下方预览；确认后点击左侧「确认生成，进入编辑」打开 Draw.io。"
        class="preview-alert"
      />

      <div class="chart-container">
        <div class="chart-scroll">
          <svg
            class="vsm-svg"
            :viewBox="`0 0 ${svg.w} ${svg.h}`"
            :width="svg.w"
            :height="svg.h"
            preserveAspectRatio="xMidYMin meet"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <marker id="vsmArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L8,3 L0,6 Z" fill="#000" />
              </marker>
              <marker id="vsmArrowOpen" markerWidth="12" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L8,3 L0,6" fill="none" stroke="#000" stroke-width="1" />
              </marker>
            </defs>

            <rect :x="6" :y="6" :width="layout.width" :height="layout.height + 36" rx="6" fill="#fff" stroke="#000" />
            <text :x="6 + layout.width / 2" :y="22" text-anchor="middle" dominant-baseline="central" class="svg-title">{{ model.title || '价值流程图' }}</text>

            <g :transform="`translate(${OX}, ${OY})`">
              <template v-for="(pr, i) in layout.primitives" :key="i">
                <g v-if="pr.kind === 'box'">
                  <rect :x="pr.x" :y="pr.y" :width="pr.w" :height="pr.h" :rx="pr.style === 'process' ? 0 : 2" :fill="boxFill(pr.style)" :stroke="boxStroke(pr.style)" />
                  <text
                    v-for="(ln, li) in String(pr.label).split('\n')" :key="li"
                    :x="boxTextX(pr)" :y="boxTextY(pr, li, String(pr.label).split('\n').length)"
                    :text-anchor="boxAnchor(pr.style)" dominant-baseline="central"
                    class="svg-box-label" :class="{ bold: boxBold(pr.style) }"
                  >{{ ln }}</text>
                </g>

                <g v-else-if="pr.kind === 'dataRows'">
                  <template v-for="(kv, ri) in pr.rows" :key="ri">
                    <rect :x="pr.x" :y="pr.y + ri * pr.rowH" :width="pr.w / 2" :height="pr.rowH" fill="#f5f5f5" stroke="#9e9e9e" />
                    <rect :x="pr.x + pr.w / 2" :y="pr.y + ri * pr.rowH" :width="pr.w / 2" :height="pr.rowH" fill="#fff" stroke="#9e9e9e" />
                    <text :x="pr.x + 5" :y="pr.y + ri * pr.rowH + pr.rowH / 2" dominant-baseline="central" class="svg-data">{{ kv[0] }}</text>
                    <text :x="pr.x + pr.w * 0.75" :y="pr.y + ri * pr.rowH + pr.rowH / 2" text-anchor="middle" dominant-baseline="central" class="svg-data">{{ kv[1] }}</text>
                  </template>
                </g>

                <g v-else-if="pr.kind === 'operator'">
                  <circle :cx="pr.x" :cy="pr.y" :r="OP_R" fill="#ffe6cc" stroke="#d79b00" />
                  <text :x="pr.x" :y="pr.y" text-anchor="middle" dominant-baseline="central" class="svg-op">{{ pr.count }}</text>
                </g>

                <g v-else-if="pr.kind === 'triangle'">
                  <polygon :points="triPoints(pr)" fill="#ffe6cc" stroke="#d79b00" />
                  <text :x="pr.x" :y="pr.y + TRI_HALF - 7" text-anchor="middle" dominant-baseline="central" class="svg-tri-i">{{ invTypeName(pr.invType) }}</text>
                  <text :x="pr.x" :y="pr.y - TRI_HALF - 8" text-anchor="middle" dominant-baseline="central" class="svg-tag">{{ invTag(pr) }}</text>
                </g>

                <g v-else-if="pr.kind === 'truck'">
                  <g :transform="`translate(${pr.x}, ${pr.y})`">
                    <!-- 货箱 -->
                    <rect :x="-TRUCK_W / 2" :y="-TRUCK_H / 2 + 2" :width="TRUCK_W * 0.6" :height="TRUCK_H - 12" rx="3" fill="#eceff1" stroke="#546e7a" stroke-width="1.4" />
                    <line :x1="-TRUCK_W / 2 + 8" :y1="-TRUCK_H / 2 + 2" :x2="-TRUCK_W / 2 + 8" :y2="TRUCK_H / 2 - 10" stroke="#cfd8dc" stroke-width="1" />
                    <!-- 驾驶室 -->
                    <path :d="truckCab(TRUCK_W * 0.6 - TRUCK_W / 2)" fill="#90a4ae" stroke="#546e7a" stroke-width="1.4" stroke-linejoin="round" />
                    <!-- 车窗 -->
                    <path :d="truckWindow(TRUCK_W * 0.6 - TRUCK_W / 2)" fill="#cfe8f5" stroke="#546e7a" stroke-width="1" stroke-linejoin="round" />
                    <!-- 车轮 -->
                    <circle :cx="-TRUCK_W * 0.2" :cy="TRUCK_H / 2 - 9" r="7.5" fill="#37474f" stroke="#263238" />
                    <circle :cx="-TRUCK_W * 0.2" :cy="TRUCK_H / 2 - 9" r="3" fill="#b0bec5" />
                    <circle :cx="TRUCK_W * 0.34" :cy="TRUCK_H / 2 - 9" r="7.5" fill="#37474f" stroke="#263238" />
                    <circle :cx="TRUCK_W * 0.34" :cy="TRUCK_H / 2 - 9" r="3" fill="#b0bec5" />
                  </g>
                  <text v-if="pr.freq" :x="pr.x" :y="pr.y - TRUCK_H / 2 - 9" text-anchor="middle" dominant-baseline="central" class="svg-tag">{{ pr.freq }}</text>
                </g>

                <g v-else-if="pr.kind === 'kaizen'">
                  <polygon :points="burstPoints(pr)" fill="#ffcccc" stroke="#b85450" />
                  <text :x="pr.x" :y="pr.y" text-anchor="middle" dominant-baseline="central" class="svg-kaizen">{{ pr.label }}</text>
                </g>

                <text
                  v-else-if="pr.kind === 'text'"
                  :x="textX(pr)" :y="pr.y + 9"
                  :text-anchor="svgAnchor(pr.align)" dominant-baseline="central"
                  class="svg-free" :class="{ bold: pr.bold }" :style="{ fontSize: (pr.fontSize || 11) + 'px' }"
                >{{ pr.value }}</text>

                <g v-else-if="pr.kind === 'sawtooth'">
                  <polyline :points="sawPoints(pr)" fill="none" stroke="#000" stroke-width="1.2" />
                  <text
                    v-for="(lb, si) in sawLabels(pr)" :key="si"
                    :x="lb.x" :y="lb.y" text-anchor="middle" dominant-baseline="central" class="svg-tag"
                  >{{ lb.text }}</text>
                </g>

                <g v-else-if="pr.kind === 'edge'">
                  <polyline
                    :points="edgePoints(pr)" fill="none"
                    stroke="#1f2937"
                    :stroke-width="pr.flow === 'info-thick' ? 2 : pr.flow === 'ship' ? 1.5 : pr.flow === 'push' ? 1.6 : 1"
                    stroke-linejoin="round" stroke-linecap="round"
                    :stroke-dasharray="pr.flow === 'info-m' ? '4 3' : ''"
                    :marker-end="pr.flow === 'info-e' || pr.flow === 'info-m' || pr.flow === 'manual-mat' ? 'url(#vsmArrowOpen)' : 'url(#vsmArrow)'"
                  />
                  <g v-if="pr.label">
                    <rect :x="edgeLabel(pr).x - edgeLabel(pr).w / 2" :y="edgeLabel(pr).y - 8" :width="edgeLabel(pr).w" height="15" rx="2" fill="#fff" fill-opacity="0.85" />
                    <text :x="edgeLabel(pr).x" :y="edgeLabel(pr).y" text-anchor="middle" dominant-baseline="central" class="svg-edge-label">{{ pr.label }}</text>
                  </g>
                </g>
              </template>
            </g>
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch, computed } from 'vue'
import {
  coerceVsmPayload,
  exampleVsmPayload,
  computeVsmLayout,
  invTypeName,
  TRI_HALF,
  OP_R,
  TRUCK_W,
  TRUCK_H,
  type VsmPayload,
  type VsmPrimitive,
  type BoxStyle,
} from './vsmLayout'

const props = withDefaults(
  defineProps<{ data: Record<string, any> | null; mode?: 'edit' | 'preview' }>(),
  { mode: 'edit' }
)
const emit = defineEmits<{ 'update:data': [VsmPayload] }>()

const model = reactive<VsmPayload>(coerceVsmPayload(props.data))

// 与 buildMxGraphXml 一致的渲染偏移：外框 FRAME_X=6，primitive 整体下移 OFF_Y=40
const OX = 6
const OY = 40

const layout = computed(() => computeVsmLayout(JSON.parse(JSON.stringify(model)) as VsmPayload))
const svg = computed(() => ({
  w: Math.ceil(layout.value.width + 12),
  h: Math.ceil(layout.value.height + 36 + 12),
}))

const processOptions = computed(() =>
  model.processes.map((p, i) => ({ value: p.id, label: p.name || `工序${i + 1}` }))
)

// 后继工序候选：除自身外的所有工序
function successorOptions(row: { id: string }) {
  return model.processes
    .map((p, i) => ({ value: p.id, label: p.name || `工序${i + 1}` }))
    .filter((o) => o.value !== row.id)
}

// __VSM_SCRIPT__

type BoxPrim = Extract<VsmPrimitive, { kind: 'box' }>
type TriPrim = Extract<VsmPrimitive, { kind: 'triangle' }>
type KaizenPrim = Extract<VsmPrimitive, { kind: 'kaizen' }>
type TextPrim = Extract<VsmPrimitive, { kind: 'text' }>
type SawPrim = Extract<VsmPrimitive, { kind: 'sawtooth' }>
type EdgePrim = Extract<VsmPrimitive, { kind: 'edge' }>

const FILL: Record<BoxStyle, string> = {
  process: '#dae8fc', customer: '#ffe6cc', supplier: '#ffe6cc',
  control: '#fff2cc', datatable: '#f5f5f5', taktbox: '#d5e8d4', summary: '#e1d5e7',
}
const STROKE: Record<BoxStyle, string> = {
  process: '#6c8ebf', customer: '#d79b00', supplier: '#d79b00',
  control: '#d6b656', datatable: '#666666', taktbox: '#82b366', summary: '#9673a6',
}
function boxFill(s: BoxStyle): string { return FILL[s] }
function boxStroke(s: BoxStyle): string { return STROKE[s] }
function boxBold(s: BoxStyle): boolean { return s !== 'datatable' && s !== 'summary' }
function boxAnchor(s: BoxStyle): string { return s === 'summary' ? 'start' : 'middle' }

function boxTextX(pr: BoxPrim): number {
  if (pr.style === 'summary') return pr.x + 8
  return pr.x + pr.w / 2
}
function boxTextY(pr: BoxPrim, lineIdx: number, total: number): number {
  const lh = 14
  if (pr.style === 'summary') return pr.y + 14 + lineIdx * 16
  // process / supplier / customer / control / takt：垂直居中
  const start = pr.y + pr.h / 2 - ((total - 1) * lh) / 2
  return start + lineIdx * lh
}

function triPoints(pr: TriPrim): string {
  const { x, y } = pr
  return `${x},${y - TRI_HALF} ${x - TRI_HALF},${y + TRI_HALF} ${x + TRI_HALF},${y + TRI_HALF}`
}
function invTag(pr: TriPrim): string {
  return `${pr.qty}件 / ${pr.days}天`
}

// 卡车贴图：货箱用模板矩形绘制，驾驶室/车窗用以下路径（坐标相对卡车中心）
function truckCab(boxRight: number): string {
  const cabTop = -8, hoodTop = 5, cabBottom = TRUCK_H / 2 - 10, frontX = TRUCK_W / 2
  return `M ${boxRight},${cabTop} L ${boxRight + 26},${cabTop} L ${boxRight + 38},${hoodTop} L ${frontX},${hoodTop} L ${frontX},${cabBottom} L ${boxRight},${cabBottom} Z`
}
function truckWindow(boxRight: number): string {
  const frontX = TRUCK_W / 2
  return `M ${boxRight + 28},${-3} L ${boxRight + 37},${6} L ${frontX - 4},${6} L ${frontX - 4},${-3} Z`
}

function burstPoints(pr: KaizenPrim): string {
  const { x, y } = pr
  const R = 32, r = 18, spikes = 10
  const pts: string[] = []
  for (let i = 0; i < spikes * 2; i++) {
    const rad = i % 2 === 0 ? R : r
    const a = (Math.PI / spikes) * i - Math.PI / 2
    pts.push(`${(x + rad * Math.cos(a)).toFixed(1)},${(y + rad * 0.55 * Math.sin(a)).toFixed(1)}`)
  }
  return pts.join(' ')
}

function textX(pr: TextPrim): number {
  const a = pr.align || 'left'
  if (a === 'center') return pr.x + pr.w / 2
  if (a === 'right') return pr.x + pr.w
  return pr.x
}
function svgAnchor(align?: string): string {
  if (align === 'center') return 'middle'
  if (align === 'right') return 'end'
  return 'start'
}

function edgePoints(pr: EdgePrim): string {
  return pr.points.map((p) => `${p.x},${p.y}`).join(' ')
}
function edgeLabel(pr: EdgePrim): { x: number; y: number; w: number } {
  const txt = pr.label || ''
  const w = Math.max(28, txt.length * 11 + 10)
  if (pr.labelPos) return { x: pr.labelPos.x, y: pr.labelPos.y, w }
  const pts = pr.points
  const a = pts[0]
  const b = pts[pts.length - 1]
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 - 8, w }
}

// 时间线方波：复刻 buildMxGraphXml.emitSawtooth 的坐标
function sawGeom(pr: SawPrim) {
  const LOW = pr.y + 30
  const HIGH = pr.y
  let x = pr.x
  const pts: { x: number; y: number }[] = []
  const labels: { x: number; y: number; text: string }[] = []
  for (const s of pr.segments) {
    const yTop = s.high ? HIGH : LOW
    pts.push({ x, y: yTop })
    pts.push({ x: x + s.w, y: yTop })
    labels.push({ x: x + s.w / 2, y: s.high ? HIGH - 9 : LOW + 25, text: s.label })
    x += s.w
  }
  return { pts, labels }
}
function sawPoints(pr: SawPrim): string {
  return sawGeom(pr).pts.map((p) => `${p.x},${p.y}`).join(' ')
}
function sawLabels(pr: SawPrim) {
  return sawGeom(pr).labels
}

// ---------------- emit ----------------
function emitAll() {
  emit('update:data', JSON.parse(JSON.stringify(model)) as VsmPayload)
}
watch(() => model, () => { if (props.mode !== 'preview') emitAll() }, { deep: true })
if (props.mode !== 'preview') emitAll()

// ---------------- CRUD ----------------
let procSeq = model.processes.length
function addProcess() {
  procSeq += 1
  model.processes.push({ id: `p${procSeq}_${Date.now()}`, name: `工序${model.processes.length + 1}`, cycleTime: 0, changeover: 0, operators: 1, uptime: 100, firstYield: 100, next: [] })
}
function removeProcess(i: number) {
  if (model.processes.length <= 1) return
  const removedId = model.processes[i].id
  model.processes.splice(i, 1)
  model.processes.forEach((p) => { if (p.next) p.next = p.next.filter((nx) => nx !== removedId) })
}
function addInventory() {
  model.inventories.push({ afterIndex: model.processes.length - 1, qty: 0, days: 0, invType: 'inventory' })
}
function removeInventory(i: number) { model.inventories.splice(i, 1) }
function addInfoFlow() {
  model.infoFlows.push({ fromId: 'control', toId: model.processes[0]?.id ?? '', label: '', type: 'electronic' })
}
function removeInfoFlow(i: number) { model.infoFlows.splice(i, 1) }
function addKaizen() {
  model.kaizens.push({ afterIndex: 0, label: '' })
}
function removeKaizen(i: number) { model.kaizens.splice(i, 1) }

function loadExample() {
  const ex = exampleVsmPayload()
  Object.assign(model, JSON.parse(JSON.stringify(ex)))
  procSeq = model.processes.length
}
</script>

<style scoped>
.vsm-container {
  display: flex;
  height: 100%;
  gap: 16px;
  overflow: hidden;
}
.vsm-container.preview-mode .right-panel { flex: 1; width: 100%; }
.save-slot-wrapper { padding: 12px 0 4px; display: flex; justify-content: center; flex-shrink: 0; }
.left-panel {
  width: 440px;
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
  align-items: flex-start;
  padding: 20px;
  border-radius: 4px;
  min-height: 0;
}
.chart-scroll {
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  width: 100%;
  height: max-content;
}
.vsm-svg {
  display: block;
  width: 100%;
  height: auto;
}
.svg-title { font-size: 21px; font-weight: 700; fill: #1f2937; }
.svg-box-label { font-size: 12px; fill: #1f2937; }
.svg-box-label.bold { font-weight: 700; }
.svg-data { font-size: 10px; fill: #374151; }
.svg-op { font-size: 10px; font-weight: 700; fill: #92400e; }
.svg-tri-i { font-size: 13px; font-weight: 700; fill: #92400e; }
.svg-tag { font-size: 9px; fill: #4b5563; }
.svg-edge-label { font-size: 10px; font-weight: 600; fill: #1f2937; }
.svg-kaizen { font-size: 9px; fill: #7f1d1d; }
.svg-free { fill: #374151; }
.svg-free.bold { font-weight: 700; }
.block { border-radius: 10px; }
.block :deep(.el-card__body) { padding: 8px 10px; }
.block :deep(.el-card__header) { padding: 8px 12px; }
.hdr { display: flex; align-items: center; justify-content: space-between; }
.hint { font-size: 11px; color: #94a3b8; padding: 0 4px 4px; }
</style>

