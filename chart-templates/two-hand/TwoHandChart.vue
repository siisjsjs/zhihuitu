<template>
  <div class="two-hand-container" :class="{ 'preview-mode': mode === 'preview' }">
    <div class="left-panel" v-if="mode !== 'preview'">
      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
            <el-button link type="primary" @click="loadExample">加载示例</el-button>
          </div>
        </template>
        <el-form :model="headerInfo" label-width="70px" size="small">
          <el-form-item label="工站名称">
            <el-input v-model="headerInfo.stationName" placeholder="工站名称" />
          </el-form-item>
          <el-row :gutter="10">
            <el-col :span="12">
              <el-form-item label="改善现场">
                <el-select v-model="headerInfo.improvement" style="width: 100%">
                  <el-option label="现行" value="现行" />
                  <el-option label="改善" value="改善" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="作业方式">
                <el-input v-model="headerInfo.method" placeholder="作业方式" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="10">
            <el-col :span="12">
              <el-form-item label="开始状态">
                <el-input v-model="headerInfo.startState" placeholder="开始状态" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="结束状态">
                <el-input v-model="headerInfo.endState" placeholder="结束状态" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="10">
            <el-col :span="12">
              <el-form-item label="研究者">
                <el-input v-model="headerInfo.researcher" placeholder="研究者" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="日期">
                <el-date-picker v-model="headerInfo.date" type="date" placeholder="选择日期" style="width: 100%" value-format="YYYY-MM-DD" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </el-card>

      <el-card class="steps-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>作业步骤 ({{ steps.length }})</span>
            <div>
              <el-button link type="primary" @click="addStep">新增步骤</el-button>
              <el-button link type="danger" @click="deleteLastStep">删除末行</el-button>
            </div>
          </div>
        </template>
        <div class="table-container">
          <el-table :data="steps" size="small" border style="width: 100%" max-height="400">
            <el-table-column type="index" label="序" width="40" align="center" />
            <el-table-column label="左手说明" min-width="120">
              <template #default="{ row }">
                <el-input v-model="row.leftDesc" size="small" placeholder="左手描述" />
              </template>
            </el-table-column>
            <el-table-column label="左手符号" width="100">
              <template #default="{ row }">
                <el-select v-model="row.leftSymbol" size="small" placeholder="类型">
                  <el-option label="○ 操作" value="operation" />
                  <el-option label="⇨ 搬运" value="transport" />
                  <el-option label="D 等待" value="delay" />
                  <el-option label="▽ 持握" value="hold" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="右手符号" width="100">
              <template #default="{ row }">
                <el-select v-model="row.rightSymbol" size="small" placeholder="类型">
                  <el-option label="○ 操作" value="operation" />
                  <el-option label="⇨ 搬运" value="transport" />
                  <el-option label="D 等待" value="delay" />
                  <el-option label="▽ 持握" value="hold" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="右手说明" min-width="120">
              <template #default="{ row }">
                <el-input v-model="row.rightDesc" size="small" placeholder="右手描述" />
              </template>
            </el-table-column>
            <el-table-column label="" width="50" align="center">
              <template #default="{ $index }">
                <el-button link type="danger" :icon="Delete" @click="removeStep($index)" />
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>

      <div class="save-slot-wrapper" v-if="$slots['save-button']">
        <slot name="save-button" />
      </div>
    </div>

    <div class="right-panel">
      <div class="chart-container" ref="chartContainerRef">
        <div class="chart-scroll export-target" ref="exportTargetRef">
          <div class="flow-chart-paper" ref="paperRef">
            <div class="flow-main-title">双手作业分析图</div>

            <div class="flow-top-section">
              <table class="flow-info-grid">
                <tbody>
                  <tr>
                    <td class="k">工站名称</td>
                    <td class="v" colspan="3">{{ headerInfo.stationName || '—' }}</td>
                    <td class="k">改善现场</td>
                    <td class="v">{{ headerInfo.improvement || '—' }}</td>
                  </tr>
                  <tr>
                    <td class="k">开始状态</td>
                    <td class="v" colspan="3">{{ headerInfo.startState || '—' }}</td>
                    <td class="k">结束状态</td>
                    <td class="v">{{ headerInfo.endState || '—' }}</td>
                  </tr>
                  <tr>
                    <td class="k">研究者</td>
                    <td class="v">{{ headerInfo.researcher || '—' }}</td>
                    <td class="k">日期</td>
                    <td class="v">{{ headerInfo.date || '—' }}</td>
                    <td class="k">作业方式</td>
                    <td class="v">{{ headerInfo.method || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- 双手作业主表（含圆点和连线） -->
            <div class="process-chart-wrapper" ref="processWrapperRef">
              <table class="process-table">
                <thead>
                  <tr>
                    <th rowspan="2" class="col-desc">左手</th>
                    <th colspan="4" class="symbols-group-header">符号</th>
                    <th colspan="4" class="symbols-group-header">符号</th>
                    <th rowspan="2" class="col-desc">右手</th>
                  </tr>
                  <tr>
                    <th class="col-sym">○</th>
                    <th class="col-sym">⇨</th>
                    <th class="col-sym">D</th>
                    <th class="col-sym">▽</th>
                    <th class="col-sym">○</th>
                    <th class="col-sym">⇨</th>
                    <th class="col-sym">D</th>
                    <th class="col-sym">▽</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(step, i) in steps" :key="i" class="data-row">
                    <td class="col-desc left-desc">{{ step.leftDesc || '—' }}</td>
                    <td v-for="(sym, j) in symbolKeys" :key="'l-'+j"
                        class="col-sym"
                        :class="{ 'active-sym': step.leftSymbol === sym }"
                        :data-side="'left'" :data-row="i" :data-col="j">
                    </td>
                    <td v-for="(sym, j) in symbolKeys" :key="'r-'+j"
                        class="col-sym"
                        :class="{ 'active-sym': step.rightSymbol === sym }"
                        :data-side="'right'" :data-row="i" :data-col="j">
                    </td>
                    <td class="col-desc right-desc">{{ step.rightDesc || '—' }}</td>
                  </tr>
                </tbody>
              </table>
              <!-- 圆点 -->
              <div v-for="(dot, i) in dotPositions" :key="'dot-'+i"
                   class="dot-marker"
                   :style="{ left: dot.x + 'px', top: dot.y + 'px' }"></div>
              <!-- 连线 -->
              <div v-for="(line, i) in lineSegments" :key="'line-'+i"
                   class="line-segment"
                   :style="getLineStyle(line)"></div>
            </div>

            <!-- 统计表 -->
            <div class="stats-section">
              <table class="stats-table">
                <thead>
                  <tr>
                    <th class="st-label">统计内容</th>
                    <th class="st-sym">符号</th>
                    <th class="st-val">左手</th>
                    <th class="st-val">右手</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(sym, idx) in symbolKeys" :key="sym">
                    <td v-if="idx === 0" :rowspan="symbolKeys.length" class="st-label">次数</td>
                    <td class="st-sym">{{ symbolDisplay[sym] }}</td>
                    <td class="st-val">{{ stats.left[sym] }}</td>
                    <td class="st-val">{{ stats.right[sym] }}</td>
                  </tr>
                  <tr class="total-row">
                    <td class="st-label">合计</td>
                    <td class="st-sym"></td>
                    <td class="st-val">{{ leftTotal }}</td>
                    <td class="st-val">{{ rightTotal }}</td>
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
import { ref, computed, reactive, nextTick, onMounted, onBeforeUnmount, watch } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ExcelJS from 'exceljs'
import html2canvas from 'html2canvas'

const props = defineProps({
  data: { type: Object, default: null },
  mode: { type: String, default: 'edit' }
})
const emit = defineEmits(['update:data'])

const symbolKeys = ['operation', 'transport', 'delay', 'hold']
const symbolDisplay = { operation: '○', transport: '⇨', delay: 'D', hold: '▽' }

const oldSymbolMap = { operation: 'operation', transport: 'transport', inspect: 'hold', wait: 'delay', hold: 'hold', delay: 'delay' }
function migrateSymbol(sym) {
  return oldSymbolMap[sym] || 'operation'
}

function migrateSteps(rawSteps) {
  if (!rawSteps?.length) return null
  return rawSteps.map(s => ({
    leftDesc: s.leftDesc || '',
    leftSymbol: migrateSymbol(s.leftSymbol),
    rightSymbol: migrateSymbol(s.rightSymbol),
    rightDesc: s.rightDesc || ''
  }))
}

const defaultHeader = {
  stationName: '', improvement: '现行', startState: '', endState: '',
  researcher: '', date: new Date().toISOString().split('T')[0], method: ''
}

const defaultSteps = [{ leftDesc: '', leftSymbol: 'operation', rightSymbol: 'operation', rightDesc: '' }]

const headerInfo = ref({ ...defaultHeader, ...(props.data?.headerInfo || {}) })
const steps = ref(migrateSteps(props.data?.steps) || defaultSteps.map(s => ({ ...s })))

function emitData() {
  const meta = {}
  const src = props.data
  if (src && typeof src === 'object') {
    if (src._style != null) meta._style = src._style
    if (src._componentFile != null) meta._componentFile = src._componentFile
  }
  emit('update:data', {
    ...meta,
    headerInfo: { ...headerInfo.value },
    steps: steps.value.map(s => ({ ...s }))
  })
}

watch([headerInfo, steps], emitData, { deep: true })

const chartContainerRef = ref(null)
const exportTargetRef = ref(null)
const paperRef = ref(null)
const processWrapperRef = ref(null)

const stats = computed(() => {
  const left = { operation: 0, transport: 0, delay: 0, hold: 0 }
  const right = { operation: 0, transport: 0, delay: 0, hold: 0 }
  steps.value.forEach(s => {
    if (left[s.leftSymbol] !== undefined) left[s.leftSymbol]++
    if (right[s.rightSymbol] !== undefined) right[s.rightSymbol]++
  })
  return { left, right }
})

const leftTotal = computed(() => symbolKeys.reduce((sum, k) => sum + stats.value.left[k], 0))
const rightTotal = computed(() => symbolKeys.reduce((sum, k) => sum + stats.value.right[k], 0))

// ─── 圆点和连线定位 ───
const dotPositions = ref([])
const lineSegments = ref([])

function recalcOverlay() {
  nextTick(() => {
    const wrapper = processWrapperRef.value
    if (!wrapper) return

    const wrapperRect = wrapper.getBoundingClientRect()
    const dots = []
    const leftDots = []
    const rightDots = []

    for (let i = 0; i < steps.value.length; i++) {
      const step = steps.value[i]
      const leftIdx = symbolKeys.indexOf(step.leftSymbol)
      const rightIdx = symbolKeys.indexOf(step.rightSymbol)

      if (leftIdx >= 0) {
        const cell = wrapper.querySelector(`td[data-side="left"][data-row="${i}"][data-col="${leftIdx}"]`)
        if (cell) {
          const r = cell.getBoundingClientRect()
          const pos = { x: r.left - wrapperRect.left + r.width / 2 + wrapper.scrollLeft, y: r.top - wrapperRect.top + r.height / 2 + wrapper.scrollTop }
          dots.push(pos)
          leftDots.push(pos)
        } else { leftDots.push(null) }
      } else { leftDots.push(null) }

      if (rightIdx >= 0) {
        const cell = wrapper.querySelector(`td[data-side="right"][data-row="${i}"][data-col="${rightIdx}"]`)
        if (cell) {
          const r = cell.getBoundingClientRect()
          const pos = { x: r.left - wrapperRect.left + r.width / 2 + wrapper.scrollLeft, y: r.top - wrapperRect.top + r.height / 2 + wrapper.scrollTop }
          dots.push(pos)
          rightDots.push(pos)
        } else { rightDots.push(null) }
      } else { rightDots.push(null) }
    }

    const lines = []
    for (let i = 0; i < leftDots.length - 1; i++) {
      if (leftDots[i] && leftDots[i + 1]) lines.push({ x1: leftDots[i].x, y1: leftDots[i].y, x2: leftDots[i + 1].x, y2: leftDots[i + 1].y })
    }
    for (let i = 0; i < rightDots.length - 1; i++) {
      if (rightDots[i] && rightDots[i + 1]) lines.push({ x1: rightDots[i].x, y1: rightDots[i].y, x2: rightDots[i + 1].x, y2: rightDots[i + 1].y })
    }

    dotPositions.value = dots
    lineSegments.value = lines
  })
}

function getLineStyle(line) {
  const dx = line.x2 - line.x1
  const dy = line.y2 - line.y1
  const length = Math.sqrt(dx * dx + dy * dy)
  const angle = Math.atan2(dy, dx) * 180 / Math.PI
  return {
    left: line.x1 + 'px',
    top: line.y1 + 'px',
    width: length + 'px',
    transform: `rotate(${angle}deg)`
  }
}

let resizeObserver = null
onMounted(() => {
  recalcOverlay()
  emitData()
  if (processWrapperRef.value) {
    resizeObserver = new ResizeObserver(recalcOverlay)
    resizeObserver.observe(processWrapperRef.value)
  }
})
onBeforeUnmount(() => { resizeObserver?.disconnect() })
watch(steps, recalcOverlay, { deep: true })

// ─── 步骤操作 ───
const addStep = () => { steps.value.push({ leftDesc: '', leftSymbol: 'operation', rightSymbol: 'operation', rightDesc: '' }) }
const removeStep = (i) => { steps.value.splice(i, 1) }
const deleteLastStep = () => { if (steps.value.length > 0) steps.value.pop() }

const loadExample = () => {
  headerInfo.value = {
    stationName: '变速箱装配工站', improvement: '改善',
    startState: '零件在料架上', endState: '变速箱装配完成',
    researcher: '李工', date: '2024-06-15', method: '手工装配'
  }
  steps.value = [
    { leftDesc: '等待', leftSymbol: 'delay', rightSymbol: 'transport', rightDesc: '取变速箱组' },
    { leftDesc: '协助固定变速箱组', leftSymbol: 'operation', rightSymbol: 'operation', rightDesc: '固定变速箱组' },
    { leftDesc: '等待', leftSymbol: 'delay', rightSymbol: 'transport', rightDesc: '取最终轴齿轮' },
    { leftDesc: '协助安装最终轴齿轮', leftSymbol: 'operation', rightSymbol: 'operation', rightDesc: '安装最终轴齿轮' },
    { leftDesc: '取垫片', leftSymbol: 'transport', rightSymbol: 'transport', rightDesc: '取齿轮油加注设备' },
    { leftDesc: '协助安装垫片', leftSymbol: 'operation', rightSymbol: 'operation', rightDesc: '加注齿轮油并安装垫片' },
    { leftDesc: '等待', leftSymbol: 'delay', rightSymbol: 'transport', rightDesc: '取变速箱垫片' },
    { leftDesc: '协助安装变速箱垫片', leftSymbol: 'operation', rightSymbol: 'operation', rightDesc: '安装变速箱垫片' },
    { leftDesc: '取缘面螺栓 1 号并定位', leftSymbol: 'operation', rightSymbol: 'operation', rightDesc: '锁付缘面螺栓 1 号' },
    { leftDesc: '取缘面螺栓 2 号并定位', leftSymbol: 'operation', rightSymbol: 'operation', rightDesc: '锁付缘面螺栓 2 号' },
    { leftDesc: '取缘面螺栓 3 号并定位', leftSymbol: 'operation', rightSymbol: 'operation', rightDesc: '锁付缘面螺栓 3 号' },
    { leftDesc: '取缘面螺栓 4 号并定位', leftSymbol: 'operation', rightSymbol: 'operation', rightDesc: '锁付缘面螺栓 4 号' }
  ]
}

// ─── 导出图片 ───
const exportImage = async () => {
  try {
    const target = paperRef.value || exportTargetRef.value
    if (!target) { ElMessage.warning('无法导出图片'); return }
    await nextTick()
    const canvas = await html2canvas(target, {
      useCORS: true, scale: 2, backgroundColor: '#fff', logging: false,
      onclone: (doc, cloned) => {
        const style = doc.createElement('style')
        style.textContent = '* { font-family: "Microsoft YaHei","PingFang SC","Hiragino Sans GB","SimSun",sans-serif !important; }'
        doc.head.appendChild(style)
        cloned.querySelectorAll('.process-chart-wrapper').forEach(w => { w.style.overflow = 'visible' })
      }
    })
    const link = document.createElement('a')
    link.href = canvas.toDataURL('image/png')
    link.download = `双手作业分析_${headerInfo.value.stationName || '未命名'}.png`
    link.click()
    ElMessage.success('图片导出成功')
  } catch (e) { ElMessage.error('图片导出失败：' + (e?.message || String(e))) }
}

// ─── Excel 连线图片生成（参考流程程序图） ───
function buildExcelLineImage(stepsData, side, colWidthsPx, rowHeightsPx) {
  try {
    const symbolIndexMap = { operation: 0, transport: 1, delay: 2, hold: 3 }
    const widths = colWidthsPx.length === 4 ? colWidthsPx : [54, 54, 54, 54]
    const heights = rowHeightsPx.length === stepsData.length ? rowHeightsPx : stepsData.map(() => 34)
    const totalW = widths.reduce((s, n) => s + n, 0)
    const totalH = heights.reduce((s, n) => s + n, 0)
    const scale = 2
    const canvas = document.createElement('canvas')
    canvas.width = totalW * scale
    canvas.height = totalH * scale
    const ctx = canvas.getContext('2d')
    if (!ctx) return null

    ctx.scale(scale, scale)
    ctx.clearRect(0, 0, totalW, totalH)

    const colStart = [0]
    for (let i = 0; i < widths.length - 1; i++) colStart.push(colStart[i] + widths[i])
    const rowStart = [0]
    for (let i = 0; i < heights.length - 1; i++) rowStart.push(rowStart[i] + heights[i])

    const symKey = side === 'left' ? 'leftSymbol' : 'rightSymbol'
    const points = stepsData.map((step, i) => {
      const c = symbolIndexMap[step[symKey]] ?? 0
      return { x: colStart[c] + widths[c] / 2, y: rowStart[i] + heights[i] / 2 }
    })
    if (points.length < 2) return null

    ctx.strokeStyle = '#333'
    ctx.lineWidth = 1.5
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.beginPath()
    ctx.moveTo(points[0].x, points[0].y)
    for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y)
    ctx.stroke()

    ctx.fillStyle = '#333'
    points.forEach(p => {
      ctx.beginPath()
      ctx.arc(p.x, p.y, 3.5, 0, Math.PI * 2)
      ctx.fill()
    })

    return { base64: canvas.toDataURL('image/png'), width: totalW, height: totalH }
  } catch { return null }
}

// ─── 导出 Excel ───
const exportExcel = async () => {
  try {
    const workbook = new ExcelJS.Workbook()
    const sheet = workbook.addWorksheet('双手作业分析图')

    sheet.columns = [
      { width: 22 },
      { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 },
      { width: 7 }, { width: 7 }, { width: 7 }, { width: 7 },
      { width: 22 }
    ]

    const thin = { style: 'thin', color: { argb: 'FF777777' } }
    const allBorder = { top: thin, left: thin, right: thin, bottom: thin }
    const center = { vertical: 'middle', horizontal: 'center', wrapText: true }
    const headerFill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE8E8E8' } }
    const cjkFont = { name: '宋体', size: 11 }
    const cjkBold = { name: '宋体', size: 11, bold: true }
    const titleFont = { name: '宋体', size: 16, bold: true }
    const symFont = { name: '宋体', size: 11, bold: true }
    const setCell = (r, c, val, font, fill, align) => {
      const cell = sheet.getCell(r, c)
      cell.value = val
      if (font) cell.font = font
      if (fill) cell.fill = fill
      cell.alignment = align || center
    }

    // 标题
    sheet.mergeCells('A1:J1')
    setCell(1, 1, '双手作业分析图', titleFont)
    sheet.getRow(1).height = 34

    // 表头 Row 2-3
    sheet.mergeCells(2, 1, 3, 1)
    setCell(2, 1, '左手', cjkBold, headerFill)
    sheet.mergeCells(2, 2, 2, 5)
    setCell(2, 2, '符号', cjkBold, headerFill)
    sheet.mergeCells(2, 6, 2, 9)
    setCell(2, 6, '符号', cjkBold, headerFill)
    sheet.mergeCells(2, 10, 3, 10)
    setCell(2, 10, '右手', cjkBold, headerFill)
    const symHeaders = ['○', '⇨', 'D', '▽', '○', '⇨', 'D', '▽']
    symHeaders.forEach((h, i) => setCell(3, i + 2, h, symFont, headerFill))
    for (let r = 2; r <= 3; r++) {
      sheet.getRow(r).height = 24
      for (let c = 1; c <= 10; c++) {
        const cell = sheet.getCell(r, c)
        if (!cell.font) cell.font = cjkBold
        if (!cell.fill) cell.fill = headerFill
        cell.alignment = center
      }
    }

    // 数据行（符号列留空，由连线图片覆盖）
    const dataStart = 4
    const ROW_H = 26
    steps.value.forEach((step, idx) => {
      const r = dataStart + idx
      setCell(r, 1, step.leftDesc || '—', cjkFont, null, { vertical: 'middle', horizontal: 'center', wrapText: true })
      setCell(r, 10, step.rightDesc || '—', cjkFont, null, { vertical: 'middle', horizontal: 'center', wrapText: true })
      sheet.getRow(r).height = ROW_H
      for (let c = 1; c <= 10; c++) {
        if (!sheet.getCell(r, c).font) sheet.getCell(r, c).font = cjkFont
        if (!sheet.getCell(r, c).alignment) sheet.getCell(r, c).alignment = center
      }
    })

    // 左侧连线+圆点图片叠加到 B-E 列（col index 1-4）
    if (steps.value.length >= 2) {
      const symColWidthsPx = [2, 3, 4, 5].map(ci => {
        const w = sheet.getColumn(ci).width || 7
        return Math.round(w * 7 + 5)
      })
      const rowHeightsPx = steps.value.map((_, idx) => {
        const h = sheet.getRow(dataStart + idx).height || ROW_H
        return Math.round(h * 96 / 72)
      })

      const leftImg = buildExcelLineImage(steps.value, 'left', symColWidthsPx, rowHeightsPx)
      if (leftImg) {
        const id = workbook.addImage({ base64: leftImg.base64, extension: 'png' })
        sheet.addImage(id, { tl: { col: 1, row: dataStart - 1 }, br: { col: 5, row: dataStart - 1 + steps.value.length }, editAs: 'oneCell' })
      }

      const rightImg = buildExcelLineImage(steps.value, 'right', symColWidthsPx, rowHeightsPx)
      if (rightImg) {
        const id = workbook.addImage({ base64: rightImg.base64, extension: 'png' })
        sheet.addImage(id, { tl: { col: 5, row: dataStart - 1 }, br: { col: 9, row: dataStart - 1 + steps.value.length }, editAs: 'oneCell' })
      }
    }

    const lastDataRow = dataStart + Math.max(steps.value.length, 1) - 1
    const statsStart = lastDataRow + 1

    // 统计表（跨满 10 列，与主表对齐）
    // 表头: 统计内容(A-B) | 符号(C-D) | 左手(E-G) | 右手(H-J)
    sheet.mergeCells(statsStart, 1, statsStart, 2)
    setCell(statsStart, 1, '统计内容', cjkBold, headerFill)
    sheet.mergeCells(statsStart, 3, statsStart, 4)
    setCell(statsStart, 3, '符号', cjkBold, headerFill)
    sheet.mergeCells(statsStart, 5, statsStart, 7)
    setCell(statsStart, 5, '左手', cjkBold, headerFill)
    sheet.mergeCells(statsStart, 8, statsStart, 10)
    setCell(statsStart, 8, '右手', cjkBold, headerFill)
    sheet.getRow(statsStart).height = 24
    for (let c = 1; c <= 10; c++) {
      const cell = sheet.getCell(statsStart, c)
      if (!cell.font) cell.font = cjkBold
      if (!cell.fill) cell.fill = headerFill
      cell.alignment = center
    }

    // 数据行: 次数(A-B rowspan4) | 符号(C-D) | 左手(E-G) | 右手(H-J)
    const symRow = statsStart + 1
    sheet.mergeCells(symRow, 1, symRow + 3, 2)
    setCell(symRow, 1, '次数', cjkBold)
    symbolKeys.forEach((sym, idx) => {
      const r = symRow + idx
      sheet.mergeCells(r, 3, r, 4)
      setCell(r, 3, symbolDisplay[sym], symFont)
      sheet.mergeCells(r, 5, r, 7)
      setCell(r, 5, stats.value.left[sym], cjkFont)
      sheet.mergeCells(r, 8, r, 10)
      setCell(r, 8, stats.value.right[sym], cjkFont)
      sheet.getRow(r).height = 22
    })

    // 合计行: 合计(A-B) | 空(C-D) | 左手合计(E-G) | 右手合计(H-J)
    const totalRow = symRow + 4
    sheet.mergeCells(totalRow, 1, totalRow, 2)
    setCell(totalRow, 1, '合计', cjkBold)
    sheet.mergeCells(totalRow, 3, totalRow, 4)
    setCell(totalRow, 3, '', cjkFont)
    sheet.mergeCells(totalRow, 5, totalRow, 7)
    setCell(totalRow, 5, leftTotal.value, cjkBold)
    sheet.mergeCells(totalRow, 8, totalRow, 10)
    setCell(totalRow, 8, rightTotal.value, cjkBold)
    sheet.getRow(totalRow).height = 24

    // 全表边框（主表 + 统计表都跨 10 列）
    for (let r = 1; r <= totalRow; r++) {
      for (let c = 1; c <= 10; c++) {
        sheet.getCell(r, c).border = allBorder
        if (!sheet.getCell(r, c).alignment) sheet.getCell(r, c).alignment = center
      }
    }

    const buffer = await workbook.xlsx.writeBuffer()
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `双手作业分析_${headerInfo.value.stationName || '导出'}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('Excel 导出成功')
  } catch (e) { ElMessage.error('Excel 导出失败：' + (e?.message || String(e))) }
}

defineExpose({ exportImage, exportExcel, exportTargetRef })
</script>

<style scoped lang="scss">
.two-hand-container {
  display: flex;
  height: 100%;
  gap: 16px;
  overflow: hidden;
}
.two-hand-container.preview-mode {
  .right-panel { flex: 1; width: 100%; }
}

.left-panel {
  width: 420px;
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
  min-width: 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  padding: 16px;
  overflow: hidden;
}

.info-card, .steps-card {
  :deep(.el-card__header) { padding: 10px 15px; border-bottom: 1px solid #f0f2f5; }
  :deep(.el-card__body) { padding: 10px; }
}
.card-header {
  display: flex; justify-content: space-between; align-items: center;
  font-weight: bold; font-size: 14px;
}

.save-slot-wrapper {
  padding: 12px 0 4px;
  display: flex; justify-content: center; flex-shrink: 0;
}

.chart-container {
  flex: 1; overflow: auto; background: #f8fafc;
  display: flex; justify-content: center; padding: 20px; border-radius: 4px;
}
.chart-scroll {
  background: white; box-shadow: 0 2px 12px 0 rgba(0,0,0,.1); height: max-content;
}
.export-target {
  padding: 0; min-width: 0; display: inline-block; background: #fff;
}
.flow-chart-paper {
  background: #fff; border: 1px solid #777;
}
.flow-main-title {
  font-size: 16px; font-weight: 600; text-align: center;
  padding: 14px 0 10px; border-bottom: 1px solid #777; color: #333;
}

/* 顶部基本信息 */
.flow-top-section { border-bottom: 1px solid #777; }
.flow-info-grid {
  width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13px;
  td { border: 1px solid #999; padding: 5px 8px; text-align: center; vertical-align: middle; color: #333; }
  tr:first-child td { border-top: none; }
  tr:last-child td { border-bottom: none; }
  td:first-child { border-left: none; }
  td:last-child { border-right: none; }
  .k { font-weight: 600; background: #f5f5f5; white-space: nowrap; width: 72px; }
}

/* 双手作业主表 */
.process-chart-wrapper {
  position: relative;
  overflow: visible;
}
.process-table {
  width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13px;
  th, td { border: 1px solid #777; padding: 4px 6px; text-align: center; vertical-align: middle; }
  th { font-weight: 600; background: #e8e8e8; color: #333; font-size: 13px; }
  .symbols-group-header { font-size: 14px; letter-spacing: 2px; }
  .col-desc { min-width: 120px; font-size: 13px; }
  .col-sym { width: 40px; }
  thead .col-sym { font-size: 18px; }
  .left-desc { text-align: center; }
  .right-desc { text-align: center; }
  thead tr { height: 32px; }
  tbody .data-row { height: 36px; }
  tr > *:first-child { border-left: none; }
  tr > *:last-child { border-right: none; }
  thead tr:first-child th { border-top: none; }
}

/* 圆点 */
.dot-marker {
  position: absolute;
  width: 10px; height: 10px;
  border-radius: 50%;
  background: #333;
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 2;
}

/* 连线 */
.line-segment {
  position: absolute;
  height: 2px;
  background: #333;
  transform-origin: 0 50%;
  pointer-events: none;
  z-index: 1;
}

/* 统计对比表 */
.stats-section { border-top: none; }
.stats-table {
  width: 100%; border-collapse: collapse; table-layout: auto; font-size: 13px;
  th, td { border: 1px solid #777; padding: 4px 8px; text-align: center; vertical-align: middle; }
  th { font-weight: 600; background: #e8e8e8; color: #333; font-size: 12px; }
  .st-label { font-weight: 600; width: 72px; }
  .st-sym { width: 48px; font-weight: 600; font-size: 18px; }
  .st-val { min-width: 48px; }
  .st-group { letter-spacing: 1px; }
  .total-row td { font-weight: 600; background: #fafafa; }
  tr > *:first-child { border-left: none; }
  tr > *:last-child { border-right: none; }
  thead tr:first-child th { border-top: none; }
  tbody tr:last-child td { border-bottom: none; }
}

:deep(.el-table .cell) { padding: 0 4px; }
</style>
