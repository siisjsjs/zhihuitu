<template>
  <div class="op-process-container" :class="{ 'preview-mode': mode === 'preview' }">
    <div v-if="mode !== 'preview'" class="left-panel">
      <el-card shadow="never" class="block">
        <template #header>
          <div class="hdr">
            <span>页眉信息</span>
            <el-button link type="primary" size="small" @click="loadExample">加载示例</el-button>
          </div>
        </template>
        <el-form :model="model.header" label-width="80px" size="small">
          <el-form-item label="制品名称"><el-input v-model="model.header.productName" /></el-form-item>
          <el-form-item label="工作部门"><el-input v-model="model.header.department" /></el-form-item>
          <el-form-item label="研究者"><el-input v-model="model.header.researcher" /></el-form-item>
          <el-form-item label="日期"><el-input v-model="model.header.date" placeholder="如 2025.3.3-2025.3.6" /></el-form-item>
        </el-form>
        <div class="auto-summary">
          <span class="auto-summary-label">汇总（自动统计）：</span>
          <span>加工 {{ autoSummary[0].count }} 次 / {{ autoSummary[0].time }}min</span>
          <span style="margin-left:12px">检验 {{ autoSummary[1].count }} 次 / {{ autoSummary[1].time }}min</span>
        </div>
      </el-card>

      <el-card shadow="never" class="block">
        <template #header><span>主干</span></template>
        <el-form label-width="56px" size="small">
          <el-form-item label="标题"><el-input v-model="model.mainTitle" placeholder="如 整经准备" /></el-form-item>
          <el-form-item label="原料"><el-input v-model="model.mainMaterialLine" placeholder="如 —整经纱线原料—" /></el-form-item>
        </el-form>
        <div class="tbl-actions">
          <el-button link type="primary" size="small" @click="addMainStep">新增一步</el-button>
        </div>
        <el-table :data="model.mainSteps" border size="small" max-height="420">
          <el-table-column label="类型" width="88">
            <template #default="{ row }">
              <el-select v-model="row.kind" size="small">
                <el-option label="○ 加工" value="operation" />
                <el-option label="□ 检验" value="inspection" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="序号" width="64">
            <template #default="{ row }"><el-input v-model="row.badge" size="small" /></template>
          </el-table-column>
          <el-table-column label="时间(min)" width="96">
            <template #default="{ row }"><el-input-number v-model="row.timeMin" :min="0" size="small" controls-position="right" class="full" /></template>
          </el-table-column>
          <el-table-column label="说明" min-width="120">
            <template #default="{ row }"><el-input v-model="row.label" size="small" /></template>
          </el-table-column>
          <el-table-column label="" width="44" align="center">
            <template #default="{ $index }">
              <el-button link type="danger" size="small" @click="removeMainStep($index)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="block">
        <template #header>
          <div class="hdr">
            <span>侧分支</span>
            <el-button link type="primary" size="small" @click="addBranch">新增分支</el-button>
          </div>
        </template>
        <el-collapse v-if="model.branches.length">
          <el-collapse-item v-for="(br, bi) in model.branches" :key="bi" :title="br.title || `分支 ${bi + 1}`">
            <div class="branch-top-row">
              <el-form label-width="70px" size="small" class="branch-form" inline>
                <el-form-item label="名称"><el-input v-model="br.title" style="width:120px" @change="onBranchTitleChange(bi)" /></el-form-item>
                <el-form-item label="原料"><el-input v-model="br.materialLine" style="width:160px" placeholder="如 —花梳纱线原料—" /></el-form-item>
                <el-form-item label="汇入标注"><el-input v-model="br.mergeLabel" style="width:140px" placeholder="如 —花梳完成—" /></el-form-item>
                <el-form-item label="汇入位置">
                  <el-select v-model="br.mergeAfterMainIndex" size="small" style="width:160px">
                    <el-option
                      v-for="(ms, mi) in model.mainSteps.slice(0, -1)"
                      :key="mi"
                      :label="`「${ms.label || '第' + (mi+1) + '步'}」之后`"
                      :value="mi"
                    />
                  </el-select>
                </el-form-item>
              </el-form>
              <el-button link type="danger" size="small" @click="removeBranch(bi)">删除分支</el-button>
            </div>
            <div class="tbl-actions">
              <el-button link type="primary" size="small" @click="addBranchStep(bi)">新增步骤</el-button>
            </div>
            <el-table :data="br.steps" border size="small" max-height="220">
              <el-table-column label="类型" width="88">
                <template #default="{ row }">
                  <el-select v-model="row.kind" size="small">
                    <el-option label="○ 加工" value="operation" />
                    <el-option label="□ 检验" value="inspection" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="序号" width="64">
                <template #default="{ row }"><el-input v-model="row.badge" size="small" /></template>
              </el-table-column>
              <el-table-column label="时间(min)" width="96">
                <template #default="{ row }"><el-input-number v-model="row.timeMin" :min="0" size="small" controls-position="right" class="full" /></template>
              </el-table-column>
              <el-table-column label="说明" min-width="120">
                <template #default="{ row }"><el-input v-model="row.label" size="small" /></template>
              </el-table-column>
              <el-table-column width="44" align="center">
                <template #default="{ $index }">
                  <el-button link type="danger" size="small" @click="removeBranchStep(bi, $index)">删</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-collapse-item>
        </el-collapse>
        <p v-else class="muted small">暂无侧分支，点「新增分支」添加并行准备线。</p>
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
        title="AI 已生成结构化数据"
        description="请核对下方示意图；确认后点击左侧「确认生成，进入编辑」打开 Draw.io。"
        class="preview-alert"
      />

      <div class="chart-container">
        <div class="chart-scroll">
          <div class="op-chart-paper">
            <div class="op-chart-main-title">工艺程序图</div>

            <table class="op-top-table">
              <tbody>
                <tr>
                  <td class="op-top-left">
                    <table class="op-info-mini">
                      <tbody>
                        <tr><td class="k">制品名称：</td><td class="v">{{ model.header.productName || '—' }}</td></tr>
                        <tr><td class="k">工作部门：</td><td class="v">{{ model.header.department || '—' }}</td></tr>
                        <tr><td class="k">研究者：</td><td class="v">{{ model.header.researcher || '—' }}</td></tr>
                        <tr><td class="k">日期：</td><td class="v">{{ model.header.date || '—' }}</td></tr>
                      </tbody>
                    </table>
                  </td>
                  <td class="op-top-right">
                    <table class="op-sum-mini">
                      <tbody>
                        <tr><th>内容</th><th>次数</th><th>时间</th></tr>
                        <tr v-for="(sr, ri) in autoSummary" :key="'sr' + ri">
                          <td>{{ sr.label || '—' }}</td>
                          <td>{{ sr.count }}</td>
                          <td>{{ sr.time }}</td>
                        </tr>
                        <tr class="sum-total-row">
                          <td>总和</td>
                          <td>{{ autoSummary[0].count + autoSummary[1].count }}</td>
                          <td>{{ autoSummary[0].time + autoSummary[1].time }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </td>
                </tr>
              </tbody>
            </table>

            <div class="op-svg-wrap">
            <svg
              class="op-schematic-svg"
              :width="layout.svgW"
              :height="layout.svgH"
              xmlns="http://www.w3.org/2000/svg"
            >
              <!-- 各列标题框 -->
              <g v-for="col in layout.columns" :key="'tbox-' + col.id" v-show="col.title">
                <rect
                  :x="col.cx - 55" :y="layout.TITLE_Y" width="110" :height="layout.TITLE_H"
                  fill="none" stroke="#0f172a" stroke-width="1.2"
                />
                <text
                  :x="col.cx" :y="layout.TITLE_Y + layout.TITLE_H / 2 + 1"
                  text-anchor="middle" dominant-baseline="central"
                  class="svg-col-title"
                >{{ col.title }}</text>
              </g>

              <!-- 各列原料线（虚线 + 文字） -->
              <g v-for="col in layout.columns" :key="'mat-' + col.id" v-show="col.materialLine">
                <line
                  :x1="col.cx - 80" :y1="layout.MATERIAL_Y"
                  :x2="col.cx" :y2="layout.MATERIAL_Y"
                  stroke="#0f172a" stroke-width="1" stroke-dasharray="5 3"
                />
                <text
                  :x="col.cx - 40" :y="layout.MATERIAL_Y - 6"
                  text-anchor="middle" class="svg-material"
                >{{ col.materialLine }}</text>
                <!-- 竖线到首步 -->
                <line
                  v-if="col.firstStepY != null"
                  :x1="col.cx" :y1="layout.MATERIAL_Y"
                  :x2="col.cx" :y2="col.firstStepY - layout.R"
                  stroke="#0f172a" stroke-width="1.2"
                />
              </g>

              <!-- 主干连线 -->
              <g class="spine">
                <line
                  v-for="(seg, i) in layout.spineSegs"
                  :key="'sp' + i"
                  :x1="seg.x1" :y1="seg.y1" :x2="seg.x2" :y2="seg.y2"
                  stroke="#0f172a" stroke-width="1.2"
                />
              </g>

              <!-- 主干节点 -->
              <g v-for="(p, i) in layout.mainPts" :key="'mn' + i">
                <circle
                  v-if="p.step.kind === 'operation'"
                  :cx="p.cx" :cy="p.cy" :r="layout.R"
                  fill="#fff" stroke="#0f172a" stroke-width="1.5"
                />
                <rect
                  v-else
                  :x="p.cx - layout.SQ" :y="p.cy - layout.SQ"
                  :width="layout.SQ * 2" :height="layout.SQ * 2"
                  fill="#fff" stroke="#0f172a" stroke-width="1.5"
                />
                <text :x="p.cx" :y="p.cy" text-anchor="middle" dominant-baseline="central" class="svg-badge">{{ p.step.badge }}</text>
                <text :x="p.cx - layout.R - 6" :y="p.cy" text-anchor="end" dominant-baseline="central" class="svg-time">{{ p.step.timeMin }}min</text>
                <text :x="p.cx + layout.R + 6" :y="p.cy" dominant-baseline="central" class="svg-label">{{ p.step.label }}</text>
              </g>

              <!-- 分支连线 -->
              <g v-for="(br, bi) in layout.branchLayouts" :key="'bsp' + bi">
                <line
                  v-for="(seg, si) in br.spineSegs"
                  :key="'bseg' + bi + '-' + si"
                  :x1="seg.x1" :y1="seg.y1" :x2="seg.x2" :y2="seg.y2"
                  stroke="#0f172a" stroke-width="1.2"
                />
              </g>

              <!-- 分支节点 -->
              <g v-for="(br, bi) in layout.branchLayouts" :key="'bn' + bi">
                <g v-for="(s, si) in br.steps" :key="'bns' + bi + '-' + si">
                  <circle
                    v-if="s.step.kind === 'operation'"
                    :cx="s.cx" :cy="s.cy" :r="layout.R"
                    fill="#fff" stroke="#0f172a" stroke-width="1.5"
                  />
                  <rect
                    v-else
                    :x="s.cx - layout.SQ" :y="s.cy - layout.SQ"
                    :width="layout.SQ * 2" :height="layout.SQ * 2"
                    fill="#fff" stroke="#0f172a" stroke-width="1.5"
                  />
                  <text :x="s.cx" :y="s.cy" text-anchor="middle" dominant-baseline="central" class="svg-badge">{{ s.step.badge }}</text>
                  <text :x="s.cx - layout.R - 6" :y="s.cy" text-anchor="end" dominant-baseline="central" class="svg-time">{{ s.step.timeMin }}min</text>
                  <text :x="s.cx + layout.R + 6" :y="s.cy" dominant-baseline="central" class="svg-label">{{ s.step.label }}</text>
                </g>
              </g>

              <!-- 汇入线（分支底部→垂直到mergeY→水平到主干） -->
              <g v-for="(br, bi) in layout.branchLayouts" :key="'mg' + bi">
                <polyline
                  v-if="br.mergePath.length"
                  :points="br.mergePath.map(p => p.x + ',' + p.y).join(' ')"
                  fill="none" stroke="#0f172a" stroke-width="1.2"
                />
                <!-- 汇入标注：在支流转折拐角内侧上方 -->
                <text
                  v-if="br.mergePath.length && br.mergeLabel"
                  :x="br.colX + 4"
                  :y="br.mergeY - 6"
                  text-anchor="start" dominant-baseline="auto" class="svg-merge"
                >{{ br.mergeLabel }}</text>
              </g>
            </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch, computed } from 'vue'
import type { OpProcPayload, OpProcStep } from './buildMxGraphXml'
import { coerceOperationProcessPayload, exampleOperationProcessPayload } from './buildMxGraphXml'

const props = withDefaults(
  defineProps<{ data: Record<string, any> | null; mode?: 'edit' | 'preview' }>(),
  { mode: 'edit' }
)
const emit = defineEmits<{ 'update:data': [OpProcPayload] }>()

function mergePayload(raw: Record<string, any> | null): OpProcPayload {
  return coerceOperationProcessPayload(raw)
}

const model = reactive<OpProcPayload>(mergePayload(props.data))

function deriveMaterialLine(title: string): string {
  const core = title.replace(/准备$/, '').trim()
  return core ? `—${core}纱线原料—` : '—原料—'
}

function deriveMergeLabel(title: string): string {
  const core = title.replace(/准备$/, '').trim()
  return core ? `—${core}完成—` : '—完成—'
}

const autoSummary = computed(() => {
  let opCount = 0, opTime = 0, inCount = 0, inTime = 0
  const allSteps = [...model.mainSteps, ...model.branches.flatMap(b => b.steps)]
  for (const s of allSteps) {
    if (s.kind === 'operation') { opCount++; opTime += s.timeMin || 0 }
    else { inCount++; inTime += s.timeMin || 0 }
  }
  return [
    { label: '加工', count: opCount, time: opTime },
    { label: '检验', count: inCount, time: inTime },
  ]
})

const layout = computed(() => {
  const R = 22
  const SQ = 20
  const STEP_PITCH = 78
  const MERGE_GAP = 40

  const branchCount = model.branches.filter(b => b.steps.length > 0).length
  const COL_GAP = Math.max(130, 160 - (branchCount - 1) * 8)
  const LEFT_MARGIN = 50
  const MAIN_X = LEFT_MARGIN + branchCount * COL_GAP + (branchCount > 0 ? 60 : 80)
  const SVG_W = MAIN_X + 110

  const TITLE_Y = 14
  const TITLE_H = 30
  const MATERIAL_Y = TITLE_Y + TITLE_H + 22
  const FIRST_STEP_Y = MATERIAL_Y + 42

  const mergeSet = new Set<number>()
  for (const br of model.branches) {
    if (br.steps.length > 0) mergeSet.add(br.mergeAfterMainIndex)
  }

  let cy = FIRST_STEP_Y
  const mainPts: Array<{ cx: number; cy: number; step: OpProcStep }> = []
  for (let i = 0; i < model.mainSteps.length; i++) {
    mainPts.push({ cx: MAIN_X, cy, step: model.mainSteps[i] })
    cy += STEP_PITCH
    if (mergeSet.has(i)) cy += MERGE_GAP
  }

  function nodeBottom(p: { cy: number; step: OpProcStep }) {
    return p.cy + (p.step.kind === 'operation' ? R : SQ)
  }
  function nodeTop(p: { cy: number; step: OpProcStep }) {
    return p.cy - (p.step.kind === 'operation' ? R : SQ)
  }

  const spineSegs: Array<{ x1: number; y1: number; x2: number; y2: number }> = []
  for (let i = 0; i < mainPts.length - 1; i++) {
    spineSegs.push({
      x1: mainPts[i].cx, y1: nodeBottom(mainPts[i]),
      x2: mainPts[i + 1].cx, y2: nodeTop(mainPts[i + 1]),
    })
  }

  function getMergeY(idx: number): number {
    const i = Math.min(idx, mainPts.length - 1)
    const j = i + 1
    if (j >= mainPts.length) return nodeBottom(mainPts[i]) + STEP_PITCH * 0.5
    return (nodeBottom(mainPts[i]) + nodeTop(mainPts[j])) / 2
  }

  type ColInfo = { id: string; cx: number; title: string; materialLine: string; firstStepY: number | null }
  const columns: ColInfo[] = []

  type BrLayout = {
    title: string; materialLine: string; mergeLabel: string
    colX: number; mergeY: number; mergeLabelX: number
    steps: Array<{ cx: number; cy: number; step: OpProcStep }>
    spineSegs: Array<{ x1: number; y1: number; x2: number; y2: number }>
    mergePath: Array<{ x: number; y: number }>
  }

  let branchIdx = 0
  const branchLayouts: BrLayout[] = model.branches.map((br, bi) => {
    const colX = LEFT_MARGIN + branchIdx * COL_GAP + 50
    if (br.steps.length > 0) branchIdx++
    const mY = getMergeY(br.mergeAfterMainIndex)

    const steps = br.steps.map((st, si) => ({
      cx: colX,
      cy: FIRST_STEP_Y + si * STEP_PITCH,
      step: st,
    }))

    const bSegs: Array<{ x1: number; y1: number; x2: number; y2: number }> = []
    for (let i = 0; i < steps.length - 1; i++) {
      bSegs.push({
        x1: steps[i].cx, y1: nodeBottom(steps[i]),
        x2: steps[i + 1].cx, y2: nodeTop(steps[i + 1]),
      })
    }

    const mergePath: Array<{ x: number; y: number }> = []
    if (steps.length > 0) {
      const last = steps[steps.length - 1]
      const lastBot = nodeBottom(last)
      mergePath.push({ x: last.cx, y: lastBot })
      mergePath.push({ x: last.cx, y: mY })
      mergePath.push({ x: MAIN_X, y: mY })
    }

    columns.push({
      id: 'br' + bi,
      cx: colX,
      title: br.title,
      materialLine: br.materialLine || '',
      firstStepY: steps.length > 0 ? steps[0].cy : null,
    })

    return {
      title: br.title, materialLine: br.materialLine || '', mergeLabel: br.mergeLabel,
      colX, mergeY: mY, mergeLabelX: (colX + MAIN_X) / 2, steps, spineSegs: bSegs, mergePath,
    }
  })

  columns.push({
    id: 'main',
    cx: MAIN_X,
    title: model.mainTitle || '',
    materialLine: model.mainMaterialLine || '',
    firstStepY: mainPts.length > 0 ? mainPts[0].cy : null,
  })

  let maxY = FIRST_STEP_Y + 40
  mainPts.forEach(p => { maxY = Math.max(maxY, p.cy + R + 20) })
  branchLayouts.forEach(b => {
    b.steps.forEach(s => { maxY = Math.max(maxY, s.cy + R + 20) })
    maxY = Math.max(maxY, b.mergeY + 28)
  })

  return {
    svgW: SVG_W, svgH: maxY,
    R, SQ, TITLE_Y, TITLE_H, MATERIAL_Y, MAIN_X,
    columns, mainPts, spineSegs, branchLayouts,
  }
})

function emitAll() {
  const data = JSON.parse(JSON.stringify(model)) as OpProcPayload
  data.summaryRows = autoSummary.value
  emit('update:data', data)
}

watch(
  () => model,
  () => {
    if (props.mode !== 'preview') emitAll()
  },
  { deep: true }
)

if (props.mode !== 'preview') {
  emitAll()
}

function addMainStep() {
  model.mainSteps.push({ kind: 'operation', badge: String(model.mainSteps.length + 1), timeMin: 0, label: '' })
}

function removeMainStep(i: number) {
  if (model.mainSteps.length <= 1) return
  model.mainSteps.splice(i, 1)
}

function addBranch() {
  model.branches.push({
    title: '',
    materialLine: '',
    steps: [{ kind: 'operation', badge: '1', timeMin: 0, label: '' }],
    mergeLabel: '',
    mergeAfterMainIndex: Math.max(0, model.mainSteps.length - 2),
    column: 'left',
  })
}

function onBranchTitleChange(bi: number) {
  const br = model.branches[bi]
  if (!br.materialLine) br.materialLine = deriveMaterialLine(br.title)
  if (!br.mergeLabel) br.mergeLabel = deriveMergeLabel(br.title)
}

function removeBranch(i: number) {
  model.branches.splice(i, 1)
}

function addBranchStep(bi: number) {
  const br = model.branches[bi]
  br.steps.push({ kind: 'operation', badge: String(br.steps.length + 1), timeMin: 0, label: '' })
}

function removeBranchStep(bi: number, si: number) {
  const br = model.branches[bi]
  if (br.steps.length <= 1) return
  br.steps.splice(si, 1)
}

function loadExample() {
  const ex = exampleOperationProcessPayload()
  model.header = { ...ex.header }
  model.mainTitle = ex.mainTitle
  model.mainMaterialLine = ex.mainMaterialLine
  model.summaryRows = autoSummary.value
  model.mainSteps.splice(0, model.mainSteps.length, ...ex.mainSteps.map((s) => ({ ...s })))
  model.branches.splice(
    0,
    model.branches.length,
    ...ex.branches.map((b) => ({
      ...b,
      steps: b.steps.map((s) => ({ ...s })),
    }))
  )
}
</script>

<style scoped>
.op-process-container {
  display: flex;
  height: 100%;
  gap: 16px;
  overflow: hidden;
}

.op-process-container.preview-mode .right-panel {
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

.op-chart-paper {
  background: #fff;
  border: 1px solid #64748b;
}

.op-svg-wrap {
  display: flex;
  justify-content: center;
  padding: 12px 8px 16px;
}

.op-schematic-svg {
  display: block;
  margin: 0 auto;
}

.op-chart-main-title {
  font-size: 16px;
  font-weight: 600;
  text-align: center;
  padding: 14px 0 10px;
  border-bottom: 1px solid #64748b;
  color: #0f172a;
}

.op-top-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.op-top-table td {
  border: 1px solid #64748b;
  vertical-align: top;
  padding: 0;
}

.op-top-left {
  width: 55%;
  padding: 0 !important;
}

.op-top-right {
  width: 45%;
  height: 100%;
  padding: 0 !important;
}

.op-info-mini {
  width: 100%;
  height: 100%;
  border-collapse: collapse;
}

.op-info-mini .k {
  border: 1px solid #94a3b8;
  padding: 6px 8px;
  width: 88px;
  background: #f8fafc;
  color: #475569;
}

.op-info-mini .v {
  border: 1px solid #94a3b8;
  padding: 6px 10px;
  color: #0f172a;
}

.op-sum-mini {
  width: 100%;
  height: 100%;
  border-collapse: collapse;
  text-align: center;
  table-layout: fixed;
}

.op-sum-mini th,
.op-sum-mini td {
  border: 1px solid #94a3b8;
  padding: 6px 8px;
  height: 1px;
}

.op-sum-mini th {
  background: #f1f5f9;
  font-weight: 600;
}

.op-sum-mini tr {
  height: 25%;
}

.sum-total-row td {
  font-weight: 600;
  background: #f1f5f9;
}

.svg-col-title {
  font-size: 13px;
  font-weight: 600;
  fill: #0f172a;
}

.svg-material {
  fill: #0f172a;
  font-size: 10px;
}

.svg-badge {
  font-size: 13px;
  font-weight: 600;
  fill: #0f172a;
  pointer-events: none;
}

.svg-time {
  font-size: 11px;
  fill: #0f172a;
}

.svg-label {
  font-size: 11px;
  fill: #0f172a;
  pointer-events: none;
}

.svg-merge {
  font-size: 10px;
  fill: #0f172a;
  font-style: italic;
}

.auto-summary {
  margin-top: 8px;
  padding: 6px 10px;
  background: #f8fafc;
  border-radius: 4px;
  font-size: 12px;
  color: #334155;
}

.auto-summary-label {
  color: #64748b;
  margin-right: 4px;
}

.branch-top-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.branch-form {
  flex: 1;
}

.branch-form :deep(.el-form-item) {
  margin-bottom: 4px;
  margin-right: 8px;
}

.block {
  border-radius: 10px;
}

.block :deep(.el-card__body) {
  padding: 8px 10px;
}

.hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.block :deep(.el-card__header) {
  padding: 8px 12px;
}

.tbl-actions {
  margin-bottom: 8px;
}

.full {
  width: 100%;
}

.muted {
  color: #64748b;
}

.small {
  font-size: 12px;
}
</style>
