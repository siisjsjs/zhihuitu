<template>
  <div class="therblig-chart-container" :class="{ 'preview-mode': mode === 'preview' }">
    <div class="left-panel" v-if="mode !== 'preview'">
      <!-- 步骤输入表格 -->
      <el-card class="steps-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>动素明细 ({{ steps.length }})</span>
            <div>
              <el-button link type="primary" @click="loadExample">加载示例</el-button>
              <el-button link type="primary" @click="addStep">新增步骤</el-button>
              <el-button link type="danger" @click="clearSteps">清空</el-button>
            </div>
          </div>
        </template>
        <div class="table-container">
          <el-table :data="steps" size="small" border style="width: 100%" max-height="600">
            <el-table-column type="index" label="序" width="40" align="center" />
            <el-table-column label="要素作业" min-width="120">
              <template #default="{ row }">
                <el-input v-model="row.elementWork" size="small" placeholder="要素作业" />
              </template>
            </el-table-column>
            <el-table-column label="左手动作" min-width="130">
              <template #default="{ row }">
                <el-input v-model="row.leftAction" size="small" placeholder="左手动作" />
              </template>
            </el-table-column>
            <el-table-column label="左手动素" width="140">
              <template #default="{ row }">
                <el-select v-model="row.leftTherblig" placeholder="选择动素" size="small" style="width: 120px" clearable>
                  <el-option v-for="t in THERBLIGS" :key="t.id" :value="t.id" :label="t.name">
                    <div style="display: flex; align-items: center; gap: 8px;">
                      <span v-html="t.svg" :style="{ color: t.color }"></span>
                      <span>{{ t.name }}</span>
                    </div>
                  </el-option>
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="眼动素" width="140">
              <template #default="{ row }">
                <el-select v-model="row.eyeTherblig" placeholder="选择动素" size="small" style="width: 120px" clearable>
                  <el-option v-for="t in THERBLIGS" :key="t.id" :value="t.id" :label="t.name">
                    <div style="display: flex; align-items: center; gap: 8px;">
                      <span v-html="t.svg" :style="{ color: t.color }"></span>
                      <span>{{ t.name }}</span>
                    </div>
                  </el-option>
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="右手动素" width="140">
              <template #default="{ row }">
                <el-select v-model="row.rightTherblig" placeholder="选择动素" size="small" style="width: 120px" clearable>
                  <el-option v-for="t in THERBLIGS" :key="t.id" :value="t.id" :label="t.name">
                    <div style="display: flex; align-items: center; gap: 8px;">
                      <span v-html="t.svg" :style="{ color: t.color }"></span>
                      <span>{{ t.name }}</span>
                    </div>
                  </el-option>
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="右手动作" min-width="130">
              <template #default="{ row }">
                <el-input v-model="row.rightAction" size="small" placeholder="右手动作" />
              </template>
            </el-table-column>
            <el-table-column label="改善点" min-width="100">
              <template #default="{ row }">
                <el-input v-model="row.improvement" size="small" placeholder="改善点" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="50" align="center">
              <template #default="{ $index }">
                <el-button link type="danger" :icon="Delete" @click="removeStep($index)" />
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>

      <!-- 由父组件注入的"保存图表"按钮 -->
      <div class="save-slot-wrapper" v-if="$slots['save-button']">
        <slot name="save-button" />
      </div>
    </div>

    <div class="right-panel">

      <!-- 动素分析图预览 -->
      <div class="chart-container" ref="chartContainerRef">
        <div class="chart-scroll export-target" ref="exportTargetRef">
          <div class="therblig-chart-paper">
            <div class="chart-main-title">动素分析图</div>

            <!-- 主数据表 -->
            <table class="therblig-main-table">
              <thead>
                <tr>
                  <th rowspan="2" class="col-seq">序号</th>
                  <th rowspan="2" class="col-work">要素作业</th>
                  <th rowspan="2" class="col-action">左手动作</th>
                  <th colspan="3" class="col-symbol-group">动素记号</th>
                  <th rowspan="2" class="col-action">右手动作</th>
                  <th rowspan="2" class="col-improve">改善点</th>
                </tr>
                <tr class="sub-header">
                  <th class="col-symbol">左手</th>
                  <th class="col-symbol">眼</th>
                  <th class="col-symbol">右手</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(step, index) in steps" :key="index">
                  <td class="col-seq">{{ index + 1 }}</td>
                  <td v-if="shouldRenderWork(index)" :rowspan="getWorkRowspan(index)" class="col-work">{{ step.elementWork || '' }}</td>
                  <td class="col-action">{{ step.leftAction || '' }}</td>
                  <td class="col-symbol">
                    <span
                      v-if="getTherblig(step.leftTherblig)"
                      class="therblig-cell"
                      :style="{ color: getTherblig(step.leftTherblig).color }"
                    >
                      <span v-html="getTherblig(step.leftTherblig).svg"></span>
                      <span class="therblig-name">{{ getTherblig(step.leftTherblig).name }}</span>
                    </span>
                  </td>
                  <td class="col-symbol">
                    <span
                      v-if="getTherblig(step.eyeTherblig)"
                      class="therblig-cell"
                      :style="{ color: getTherblig(step.eyeTherblig).color }"
                    >
                      <span v-html="getTherblig(step.eyeTherblig).svg"></span>
                      <span class="therblig-name">{{ getTherblig(step.eyeTherblig).name }}</span>
                    </span>
                  </td>
                  <td class="col-symbol">
                    <span
                      v-if="getTherblig(step.rightTherblig)"
                      class="therblig-cell"
                      :style="{ color: getTherblig(step.rightTherblig).color }"
                    >
                      <span v-html="getTherblig(step.rightTherblig).svg"></span>
                      <span class="therblig-name">{{ getTherblig(step.rightTherblig).name }}</span>
                    </span>
                  </td>
                  <td class="col-action">{{ step.rightAction || '' }}</td>
                  <td class="col-improve">{{ step.improvement || '' }}</td>
                </tr>
              </tbody>
            </table>

            <!-- 统计汇总表 -->
            <div class="stats-section">
              <div class="stats-title">动素统计汇总</div>
              <table class="therblig-stats-table">
                <thead>
                  <tr>
                    <th>动素类别</th>
                    <th>左手</th>
                    <th>眼</th>
                    <th>右手</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td class="class-label">
                      <span class="class-dot" style="background: #22c55e;"></span>
                      第一类（有效动素）
                    </td>
                    <td>{{ stats.left[1] }}</td>
                    <td>{{ stats.eye[1] }}</td>
                    <td>{{ stats.right[1] }}</td>
                  </tr>
                  <tr>
                    <td class="class-label">
                      <span class="class-dot" style="background: #f59e0b;"></span>
                      第二类（辅助动素）
                    </td>
                    <td>{{ stats.left[2] }}</td>
                    <td>{{ stats.eye[2] }}</td>
                    <td>{{ stats.right[2] }}</td>
                  </tr>
                  <tr>
                    <td class="class-label">
                      <span class="class-dot" style="background: #ef4444;"></span>
                      第三类（无效动素）
                    </td>
                    <td>{{ stats.left[3] }}</td>
                    <td>{{ stats.eye[3] }}</td>
                    <td>{{ stats.right[3] }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Delete, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ExcelJS from 'exceljs'
import html2canvas from 'html2canvas'

const props = defineProps({
  data: { type: Object, default: null },
  mode: { type: String, default: 'edit' }
})
const emit = defineEmits(['update:data'])

// 18 standard therbligs with SVG symbols
const THERBLIGS = [
  // Class 1 - Effective (有效动素)
  { id: 'TE', name: '伸手', classNum: 1, color: '#22c55e',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><path d="M6 8 Q16 28 26 8" fill="none" stroke="currentColor" stroke-width="2.5"/></svg>' },
  { id: 'G', name: '握取', classNum: 1, color: '#22c55e',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><path d="M6 26 L6 12 Q6 2 16 2 Q26 2 26 12 L26 26" fill="none" stroke="currentColor" stroke-width="2.5"/></svg>' },
  { id: 'TL', name: '移物', classNum: 1, color: '#22c55e',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><path d="M4 8 Q16 32 28 8" fill="none" stroke="currentColor" stroke-width="2.5"/><circle cx="16" cy="17" r="3" fill="none" stroke="currentColor" stroke-width="2"/></svg>' },
  { id: 'P', name: '定位', classNum: 1, color: '#22c55e',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><circle cx="14" cy="11" r="8" fill="none" stroke="currentColor" stroke-width="2.5"/><path d="M22 11 L22 24 Q22 30 10 30" fill="none" stroke="currentColor" stroke-width="2.5"/></svg>' },
  { id: 'DA', name: '拆卸', classNum: 1, color: '#22c55e',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><line x1="6" y1="16" x2="26" y2="16" stroke="currentColor" stroke-width="2.5"/><line x1="13" y1="9" x2="11" y2="23" stroke="currentColor" stroke-width="2.5"/><line x1="21" y1="9" x2="19" y2="23" stroke="currentColor" stroke-width="2.5"/></svg>' },
  { id: 'U', name: '使用', classNum: 1, color: '#22c55e',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><path d="M8 6 L8 20 Q8 28 16 28 Q24 28 24 20 L24 6" fill="none" stroke="currentColor" stroke-width="2.5"/></svg>' },
  { id: 'A', name: '装配', classNum: 1, color: '#22c55e',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><line x1="6" y1="12" x2="26" y2="12" stroke="currentColor" stroke-width="2.5"/><line x1="6" y1="20" x2="26" y2="20" stroke="currentColor" stroke-width="2.5"/><line x1="12" y1="6" x2="12" y2="26" stroke="currentColor" stroke-width="2.5"/><line x1="20" y1="6" x2="20" y2="26" stroke="currentColor" stroke-width="2.5"/></svg>' },
  { id: 'RL', name: '放开', classNum: 1, color: '#22c55e',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><path d="M4 24 Q16 0 28 24" fill="none" stroke="currentColor" stroke-width="2.5"/><circle cx="16" cy="15" r="3" fill="none" stroke="currentColor" stroke-width="2"/></svg>' },

  // Class 2 - Auxiliary (辅助动素)
  { id: 'I', name: '检查', classNum: 1, color: '#22c55e',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><ellipse cx="16" cy="16" rx="8" ry="11" fill="none" stroke="currentColor" stroke-width="2.5"/></svg>' },
  { id: 'Sh', name: '寻找', classNum: 2, color: '#f59e0b',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><path d="M4 18 Q16 6 28 18" fill="none" stroke="currentColor" stroke-width="2"/><path d="M4 18 Q16 30 28 18" fill="none" stroke="currentColor" stroke-width="2"/><path d="M22 13 Q17 18 22 23" fill="none" stroke="currentColor" stroke-width="2"/></svg>' },
  { id: 'F', name: '发现', classNum: 2, color: '#f59e0b',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><ellipse cx="16" cy="16" rx="12" ry="8" fill="none" stroke="currentColor" stroke-width="2"/><ellipse cx="16" cy="16" rx="6" ry="8" fill="none" stroke="currentColor" stroke-width="2"/></svg>' },
  { id: 'St', name: '选择', classNum: 2, color: '#f59e0b',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><line x1="4" y1="16" x2="26" y2="16" stroke="currentColor" stroke-width="2.5"/><polyline points="20,10 26,16 20,22" fill="none" stroke="currentColor" stroke-width="2.5"/></svg>' },
  { id: 'Pn', name: '思考', classNum: 2, color: '#f59e0b',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><circle cx="14" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M9 7 L9 28 L24 28" fill="none" stroke="currentColor" stroke-width="2"/><path d="M17 10 L20 13 L11 20 L9 16" fill="none" stroke="currentColor" stroke-width="2"/></svg>' },
  { id: 'PP', name: '预定位', classNum: 2, color: '#f59e0b',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><circle cx="16" cy="9" r="4.5" fill="none" stroke="currentColor" stroke-width="2.5"/><circle cx="16" cy="22" r="6.5" fill="none" stroke="currentColor" stroke-width="2.5"/></svg>' },

  // Class 3 - Non-productive (无效动素)
  { id: 'H', name: '持住', classNum: 3, color: '#ef4444',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><path d="M6 26 L6 14 Q6 4 16 4 Q26 4 26 14 L26 26" fill="none" stroke="currentColor" stroke-width="2.5"/><line x1="2" y1="26" x2="30" y2="26" stroke="currentColor" stroke-width="2.5"/></svg>' },
  { id: 'AD', name: '可避免延迟', classNum: 3, color: '#ef4444',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><path d="M8 6 L8 22 L21 22" fill="none" stroke="currentColor" stroke-width="2.5"/><circle cx="24" cy="22" r="3" fill="none" stroke="currentColor" stroke-width="2"/></svg>' },
  { id: 'UD', name: '不可避免延迟', classNum: 3, color: '#ef4444',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><circle cx="26" cy="16" r="3" fill="none" stroke="currentColor" stroke-width="2"/><path d="M28 14 L14 4 L4 14 L6 16" fill="none" stroke="currentColor" stroke-width="2.5"/></svg>' },
  { id: 'R', name: '休息', classNum: 3, color: '#ef4444',
    svg: '<svg viewBox="0 0 32 32" width="24" height="24"><ellipse cx="12" cy="8" rx="7" ry="5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 13 L12 18 L24 18 L24 28" fill="none" stroke="currentColor" stroke-width="2.5"/></svg>' },
]

// Helper to look up a therblig by id
const getTherblig = (id) => {
  if (!id) return null
  return THERBLIGS.find(t => t.id === id) || null
}

// Data model
const defaultStep = {
  elementWork: '',
  leftAction: '',
  leftTherblig: '',
  eyeTherblig: '',
  rightTherblig: '',
  rightAction: '',
  improvement: '',
}

const steps = ref(
  props.data?.steps?.length
    ? props.data.steps.map(s => ({ ...defaultStep, ...s }))
    : [{ ...defaultStep }]
)

const chartContainerRef = ref(null)
const exportTargetRef = ref(null)

function emitData() {
  emit('update:data', { steps: steps.value.map(s => ({ ...s })) })
}

watch(steps, emitData, { deep: true })

// Statistics
const stats = computed(() => {
  const result = { left: {1:0, 2:0, 3:0}, eye: {1:0, 2:0, 3:0}, right: {1:0, 2:0, 3:0} }
  steps.value.forEach(s => {
    const lt = THERBLIGS.find(t => t.id === s.leftTherblig)
    const et = THERBLIGS.find(t => t.id === s.eyeTherblig)
    const rt = THERBLIGS.find(t => t.id === s.rightTherblig)
    if (lt) result.left[lt.classNum]++
    if (et) result.eye[et.classNum]++
    if (rt) result.right[rt.classNum]++
  })
  return result
})

// 要素作业 auto-merge
const workMerge = computed(() => {
  const groups = []
  let i = 0
  while (i < steps.value.length) {
    const s = steps.value[i]
    let span = 1
    if (s.elementWork) {
      while (i + span < steps.value.length) {
        if (steps.value[i + span].elementWork === s.elementWork) span++
        else break
      }
    }
    groups.push({ start: i, span })
    i += span
  }
  return groups
})
const shouldRenderWork = (idx) => workMerge.value.some(g => g.start === idx)
const getWorkRowspan = (idx) => workMerge.value.find(g => g.start === idx)?.span || 1

// Methods
const addStep = () => {
  steps.value.push({
    elementWork: '',
    leftAction: '',
    leftTherblig: '',
    eyeTherblig: '',
    rightTherblig: '',
    rightAction: '',
    improvement: '',
  })
}

const removeStep = (index) => {
  steps.value.splice(index, 1)
}

const clearSteps = () => {
  steps.value = []
}

const loadExample = () => {
  steps.value = [
    { elementWork: '组装登高平台', leftAction: '定位装配体', leftTherblig: 'P', eyeTherblig: '', rightTherblig: 'P', rightAction: '定位短螺栓', improvement: '' },
    { elementWork: '', leftAction: '伸手向装配体', leftTherblig: 'TE', eyeTherblig: '', rightTherblig: 'TE', rightAction: '伸手向短螺栓', improvement: '' },
    { elementWork: '', leftAction: '握取装配体', leftTherblig: 'G', eyeTherblig: '', rightTherblig: 'G', rightAction: '握取短螺栓', improvement: '' },
    { elementWork: '', leftAction: '移物装配体', leftTherblig: 'TL', eyeTherblig: '', rightTherblig: 'TL', rightAction: '移物短螺栓', improvement: '' },
    { elementWork: '', leftAction: '等待（持握装配体）', leftTherblig: 'H', eyeTherblig: '', rightTherblig: 'A', rightAction: '将短螺栓装配入短三孔折板', improvement: '' },
  ]
}

// Helper: convert SVG to base64 PNG for Excel
const svgToBase64 = (svgStr, color) => {
  return new Promise((resolve) => {
    let colored = svgStr.replace(/currentColor/g, color)
    if (!colored.includes('xmlns')) {
      colored = colored.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')
    }
    const blob = new Blob([colored], { type: 'image/svg+xml' })
    const url = URL.createObjectURL(blob)
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = 48
      canvas.height = 48
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0, 48, 48)
      URL.revokeObjectURL(url)
      resolve(canvas.toDataURL('image/png').split(',')[1])
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      resolve(null)
    }
    img.src = url
  })
}

// Export Excel
const exportExcel = async () => {
  try {
    const workbook = new ExcelJS.Workbook()
    const sheet = workbook.addWorksheet('动素分析')

    sheet.columns = [
      { width: 8 },   // A 序号
      { width: 16 },  // B 要素作业
      { width: 20 },  // C 左手动作
      { width: 12 },  // D 左手动素
      { width: 12 },  // E 眼动素
      { width: 12 },  // F 右手动素
      { width: 20 },  // G 右手动作
      { width: 14 },  // H 改善点
    ]

    const thin = { style: 'thin', color: { argb: 'FF777777' } }
    const allBorder = { top: thin, left: thin, right: thin, bottom: thin }
    const center = { vertical: 'middle', horizontal: 'center' }

    // Title
    sheet.mergeCells('A1:H1')
    sheet.getCell('A1').value = '动素分析图'
    sheet.getCell('A1').alignment = center
    sheet.getCell('A1').font = { bold: true, size: 14 }
    sheet.getRow(1).height = 30

    // Table headers (two rows)
    sheet.mergeCells('A2:A3')
    sheet.mergeCells('B2:B3')
    sheet.mergeCells('C2:C3')
    sheet.mergeCells('D2:F2')
    sheet.mergeCells('G2:G3')
    sheet.mergeCells('H2:H3')
    sheet.getCell('A2').value = '序号'
    sheet.getCell('B2').value = '要素作业'
    sheet.getCell('C2').value = '左手动作'
    sheet.getCell('D2').value = '动素记号'
    sheet.getCell('G2').value = '右手动作'
    sheet.getCell('H2').value = '改善点'
    sheet.getCell('D3').value = '左手'
    sheet.getCell('E3').value = '眼'
    sheet.getCell('F3').value = '右手'
    sheet.getRow(2).height = 24
    sheet.getRow(3).height = 24

    // Header styling
    for (let r = 2; r <= 3; r++) {
      for (let c = 1; c <= 8; c++) {
        const cell = sheet.getCell(r, c)
        cell.font = { bold: true }
        cell.alignment = center
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE8E8E8' } }
      }
    }

    // Color map for therblig classes
    const classBgColors = { 1: 'FFDCFCE7', 2: 'FFFEF3C7', 3: 'FFFEE2E2' }
    const classFontColors = { 1: 'FF16A34A', 2: 'FFD97706', 3: 'FFDC2626' }

    // Pre-render therblig icons
    const iconCache = new Map()
    const getIconBase64 = async (t) => {
      if (!t) return null
      if (iconCache.has(t.id)) return iconCache.get(t.id)
      const base64 = await svgToBase64(t.svg, t.color)
      iconCache.set(t.id, base64)
      return base64
    }

    // Data rows
    const startRow = 4
    for (let idx = 0; idx < steps.value.length; idx++) {
      const step = steps.value[idx]
      const r = startRow + idx
      sheet.getCell(`A${r}`).value = idx + 1
      sheet.getCell(`B${r}`).value = step.elementWork || ''
      sheet.getCell(`C${r}`).value = step.leftAction || ''
      const lt = getTherblig(step.leftTherblig)
      const et = getTherblig(step.eyeTherblig)
      const rt = getTherblig(step.rightTherblig)

      // Helper to add icon image + colored background to a cell
      const addTherbligIcon = async (t, colIndex, cellRef) => {
        if (!t) return
        const base64 = await getIconBase64(t)
        if (base64) {
          const imageId = workbook.addImage({ base64, extension: 'png' })
          sheet.addImage(imageId, {
            tl: { col: colIndex + 0.15, row: r - 1 + 0.08 },
            ext: { width: 22, height: 22 }
          })
        }
        sheet.getCell(cellRef).value = t.name
        sheet.getCell(cellRef).font = { bold: true, color: { argb: classFontColors[t.classNum] }, size: 8 }
        sheet.getCell(cellRef).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: classBgColors[t.classNum] } }
      }

      await addTherbligIcon(lt, 3, `D${r}`)  // col D = index 3
      await addTherbligIcon(et, 4, `E${r}`)  // col E = index 4
      await addTherbligIcon(rt, 5, `F${r}`)  // col F = index 5

      sheet.getCell(`G${r}`).value = step.rightAction || ''
      sheet.getCell(`H${r}`).value = step.improvement || ''
      sheet.getRow(r).height = 28
    }

    const lastDataRow = startRow + Math.max(steps.value.length, 1) - 1

    // Merge elementWork cells
    for (const g of workMerge.value) {
      if (g.span > 1) {
        const s = startRow + g.start
        const e = s + g.span - 1
        sheet.mergeCells(`B${s}:B${e}`)
      }
    }

    // Stats section
    const statsStartRow = lastDataRow + 1
    sheet.mergeCells(`A${statsStartRow}:H${statsStartRow}`)
    sheet.getCell(`A${statsStartRow}`).value = '动素统计汇总'
    sheet.getCell(`A${statsStartRow}`).font = { bold: true, size: 12 }
    sheet.getCell(`A${statsStartRow}`).alignment = center
    sheet.getRow(statsStartRow).height = 26

    const statsHeaderRow = statsStartRow + 1
    sheet.getCell(statsHeaderRow, 1).value = '动素类别'
    sheet.mergeCells(statsHeaderRow, 1, statsHeaderRow, 5)
    sheet.getCell(statsHeaderRow, 6).value = '左手'
    sheet.getCell(statsHeaderRow, 7).value = '眼'
    sheet.getCell(statsHeaderRow, 8).value = '右手'
    for (let c = 1; c <= 8; c++) {
      const cell = sheet.getCell(statsHeaderRow, c)
      cell.font = { bold: true }
      cell.alignment = center
      cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE8E8E8' } }
    }

    const classNames = [
      '第一类（有效动素）',
      '第二类（辅助动素）',
      '第三类（无效动素）'
    ]
    const classColors = ['FF22C55E', 'FFF59E0B', 'FFEF4444']
    classNames.forEach((name, idx) => {
      const r = statsHeaderRow + 1 + idx
      sheet.getCell(r, 1).value = name
      sheet.mergeCells(r, 1, r, 5)
      sheet.getCell(r, 6).value = stats.value.left[idx + 1]
      sheet.getCell(r, 7).value = stats.value.eye[idx + 1]
      sheet.getCell(r, 8).value = stats.value.right[idx + 1]
      sheet.getCell(r, 1).font = { color: { argb: classColors[idx] }, bold: true }
      sheet.getRow(r).height = 24
    })

    const totalLastRow = statsHeaderRow + 3

    // Borders for all cells
    for (let r = 1; r <= totalLastRow; r++) {
      for (let c = 1; c <= 8; c++) {
        const cell = sheet.getCell(r, c)
        cell.border = allBorder
        if (!cell.alignment) cell.alignment = center
      }
    }

    const buffer = await workbook.xlsx.writeBuffer()
    const blob = new Blob([buffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = '动素分析图.xlsx'
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('Excel 导出成功')
  } catch (e) {
    ElMessage.error('Excel 导出失败：' + (e?.message || String(e)))
  }
}

const exportImage = async () => {
  try {
    const target = exportTargetRef.value
    if (!target) { ElMessage.warning('无法导出图片'); return }
    const canvas = await html2canvas(target, { useCORS: true, scale: 2, backgroundColor: '#fff', logging: false })
    const link = document.createElement('a')
    link.href = canvas.toDataURL('image/png')
    link.download = '动素分析图.png'
    link.click()
    ElMessage.success('图片导出成功')
  } catch (e) {
    ElMessage.error('图片导出失败：' + (e?.message || String(e)))
  }
}

onMounted(() => {
  emitData()
})

defineExpose({ exportExcel, exportImage, exportTargetRef })
</script>

<style scoped lang="scss">
.therblig-chart-container {
  display: flex;
  height: 100%;
  gap: 16px;
  overflow: hidden;
}

.therblig-chart-container.preview-mode {
  .right-panel {
    flex: 1;
    width: 100%;
  }
}

.save-slot-wrapper {
  padding: 12px 0 4px;
  display: flex;
  justify-content: center;
  flex-shrink: 0;
}

.left-panel {
  width: 450px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex-shrink: 0;
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

.steps-card {
  :deep(.el-card__header) {
    padding: 10px 15px;
    border-bottom: 1px solid #f0f2f5;
  }
  :deep(.el-card__body) {
    padding: 10px;
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  font-size: 14px;
}

.action-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
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
}

.chart-scroll {
  background: white;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  height: max-content;
}

.export-target {
  padding: 0;
  min-width: 0;
  display: inline-block;
  background: #fff;
}

.therblig-chart-paper {
  background: #fff;
  border: 1px solid #777;
  min-width: 700px;
}

.chart-main-title {
  font-size: 16px;
  font-weight: 600;
  text-align: center;
  padding: 16px 0 12px;
  border-bottom: 1px solid #777;
  color: #333;
}

/* Main data table */
.therblig-main-table {
  width: 100%;
  border-collapse: collapse;
  border: none;
  table-layout: fixed;
  font-size: 13px;

  th, td {
    border: 1px solid #777;
    padding: 4px 6px;
    text-align: center;
    vertical-align: middle;
  }

  thead th {
    font-weight: 600;
    background: #e8e8e8;
    color: #333;
    padding: 5px 6px;
    font-size: 12px;
  }

  .sub-header th {
    font-weight: 500;
    font-size: 11px;
    padding: 4px 6px;
  }

  .col-seq {
    width: 50px;
  }

  .col-work {
    width: 120px;
  }

  .col-action {
    text-align: center;
    width: 140px;
  }

  .col-symbol-group {
    width: 180px;
  }

  .col-symbol {
    width: 80px;
  }

  .therblig-cell {
    display: inline-flex;
    align-items: center;
    gap: 2px;
  }

  .therblig-name {
    font-size: 11px;
    font-weight: 600;
  }

  .col-improve {
    text-align: center;
    width: 100px;
  }

  tbody tr {
    height: 36px;
  }

  tr > *:first-child {
    border-left: none;
  }
  tr > *:last-child {
    border-right: none;
  }
  thead tr:first-child th {
    border-top: none;
  }
}

/* Stats section */
.stats-section {
  border-top: 2px solid #777;
}

.stats-title {
  font-weight: 600;
  font-size: 14px;
  text-align: center;
  padding: 10px 0 8px;
  color: #333;
  border-bottom: 1px solid #777;
}

.therblig-stats-table {
  width: 100%;
  border-collapse: collapse;
  border: none;
  font-size: 13px;

  th, td {
    border: 1px solid #777;
    padding: 8px 12px;
    text-align: center;
    vertical-align: middle;
  }

  th {
    font-weight: 600;
    background: #e8e8e8;
    color: #333;
  }

  th:first-child,
  td:first-child {
    border-left: none;
  }

  th:last-child,
  td:last-child {
    border-right: none;
  }

  thead tr:first-child th {
    border-top: none;
  }

  tbody tr:last-child td {
    border-bottom: none;
  }

  .class-label {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    font-weight: 500;
  }

  .class-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }
}

/* Hide extra padding in el-table cells */
:deep(.el-table .cell) {
  padding: 0 4px;
}
</style>
