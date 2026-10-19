<template>
  <div class="process-flow-container" :class="{ 'preview-mode': mode === 'preview' }">
    <div class="left-panel" v-if="mode !== 'preview'">
      <!-- 顶部信息表单 -->
      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
            <el-button link type="primary" @click="loadExample">加载示例</el-button>
          </div>
        </template>
        <el-form :model="headerInfo" label-width="70px" size="small">
          <el-form-item label="工作名称">
            <el-input v-model="headerInfo.workName" placeholder="工作名称" />
          </el-form-item>
          <el-row :gutter="10">
            <el-col :span="12">
              <el-form-item label="开始">
                <el-input v-model="headerInfo.start" placeholder="开始" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="结束">
                <el-input v-model="headerInfo.end" placeholder="结束" />
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
              <el-form-item label="审阅者">
                <el-input v-model="headerInfo.reviewer" placeholder="审阅者" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="日期">
            <el-date-picker v-model="headerInfo.date" type="date" placeholder="选择日期" style="width: 100%" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="版本">
            <el-input v-model="headerInfo.version" placeholder="版本" />
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 步骤输入表格 -->
      <el-card class="steps-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>工序明细 ({{ steps.length }})</span>
            <div>
              <el-button link type="primary" @click="addStep">新增步骤</el-button>
              <el-button link type="danger" @click="clearSteps">清空</el-button>
            </div>
          </div>
        </template>
        <div class="table-container">
          <el-table :data="steps" size="small" border style="width: 100%" max-height="420">
            <el-table-column type="index" label="序" width="40" align="center" />
            <el-table-column label="工作说明" min-width="140">
              <template #default="{ row }">
                <el-input v-model="row.content" size="small" placeholder="工作描述" />
              </template>
            </el-table-column>
            <el-table-column label="时间/s" width="75">
              <template #default="{ row }">
                <el-input-number v-model="row.time" size="small" :min="0" :controls="false" style="width: 100%" />
              </template>
            </el-table-column>
            <el-table-column label="距离/m" width="75">
              <template #default="{ row }">
                <el-input-number v-model="row.distance" size="small" :min="0" :controls="false" style="width: 100%" />
              </template>
            </el-table-column>
            <el-table-column label="工序类型" width="95">
              <template #default="{ row }">
                <el-select v-model="row.symbol" size="small" placeholder="类型">
                  <el-option label="〇 操作" value="processing" />
                  <el-option label="□ 检查" value="inspection" />
                  <el-option label="→ 搬运" value="transport" />
                  <el-option label="D 等待" value="waiting" />
                  <el-option label="▽ 储存" value="storage" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="备注" width="90">
              <template #default="{ row }">
                <el-input v-model="row.remarks" size="small" placeholder="备注" />
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

      <!-- 由父组件注入的"保存图表"按钮(贴在表单下方,与鱼骨图体感一致) -->
      <div class="save-slot-wrapper" v-if="$slots['save-button']">
        <slot name="save-button" />
      </div>
    </div>

    <div class="right-panel">
      <div class="action-bar" v-if="mode !== 'preview'">
        <el-button type="primary" :icon="Download" @click="exportExcel">导出 Excel</el-button>
        <el-button style="display: none" :icon="Download" @click="exportImage">导出图片</el-button>
      </div>

      <!-- 流程程序图预览（与模板格式一致，用于导出） -->
      <div class="chart-container" ref="chartContainerRef">
        <div class="chart-scroll export-target" ref="exportTargetRef">
          <div class="flow-chart-paper">
            <div class="flow-main-title">流程程序图</div>
            <!-- 顶部：基本信息 + 统计表（合并为一个总表） -->
            <div class="flow-top-section">
              <table class="flow-head-table">
                <tbody>
                  <tr>
                    <td class="head-left">
                      <table class="flow-info-grid">
                        <tbody>
                          <tr>
                            <td class="k">工作名称</td>
                            <td class="v">{{ headerInfo.workName || '—' }}</td>
                          </tr>
                          <tr>
                            <td class="k">开始</td>
                            <td class="v">{{ headerInfo.start || '—' }}</td>
                          </tr>
                          <tr>
                            <td class="k">结束</td>
                            <td class="v">{{ headerInfo.end || '—' }}</td>
                          </tr>
                          <tr>
                            <td class="k">研究者</td>
                            <td class="v">{{ headerInfo.researcher || '—' }}</td>
                          </tr>
                          <tr>
                            <td class="k">审阅者</td>
                            <td class="v">{{ headerInfo.reviewer || '—' }}</td>
                          </tr>
                          <tr>
                            <td class="k">日期</td>
                            <td class="v">{{ headerInfo.date || '—' }}</td>
                          </tr>
                          <tr>
                            <td class="k">版本</td>
                            <td class="v">{{ headerInfo.version || '—' }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </td>
                    <td class="head-right">
                      <table class="flow-stats-table">
                        <thead>
                          <tr>
                            <th colspan="4" class="stats-merged-title">统计表</th>
                          </tr>
                          <tr>
                            <th>项别</th>
                            <th>次数</th>
                            <th>时间/s</th>
                            <th>距离/m</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td>操作O</td>
                            <td>{{ stats.counts.processing }}</td>
                            <td>{{ statsByType.processing.time }}</td>
                            <td>{{ statsByType.processing.distance }}</td>
                          </tr>
                          <tr>
                            <td>检查口</td>
                            <td>{{ stats.counts.inspection }}</td>
                            <td>{{ statsByType.inspection.time }}</td>
                            <td>{{ statsByType.inspection.distance }}</td>
                          </tr>
                          <tr>
                            <td>搬运→</td>
                            <td>{{ stats.counts.transport }}</td>
                            <td>{{ statsByType.transport.time }}</td>
                            <td>{{ statsByType.transport.distance }}</td>
                          </tr>
                          <tr>
                            <td>等待 D</td>
                            <td>{{ stats.counts.waiting }}</td>
                            <td>{{ statsByType.waiting.time }}</td>
                            <td>{{ statsByType.waiting.distance }}</td>
                          </tr>
                          <tr>
                            <td>储存▽</td>
                            <td>{{ stats.counts.storage }}</td>
                            <td>{{ statsByType.storage.time }}</td>
                            <td>{{ statsByType.storage.distance }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- 工序系列主表（表头双层划格 + 工序系列内连线） -->
            <div class="flow-process-wrapper" ref="processTableRef">
              <table class="flow-process-table">
                <thead>
                  <tr>
                    <th rowspan="2" class="col-desc">工作说明</th>
                    <th rowspan="2" class="col-num">时间/s</th>
                    <th rowspan="2" class="col-num">距离/m</th>
                    <th colspan="5" class="col-series">工序系列</th>
                    <th rowspan="2" class="col-remark">备注</th>
                  </tr>
                  <tr class="sub-header">
                    <th class="col-sym-h">操作</th>
                    <th class="col-sym-h">检查</th>
                    <th class="col-sym-h">搬运</th>
                    <th class="col-sym-h">等待</th>
                    <th class="col-sym-h">储存</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(step, index) in steps" :key="index">
                    <td class="col-desc">{{ step.content || '—' }}</td>
                    <td class="col-num">{{ step.time ?? '—' }}</td>
                    <td class="col-num">{{ step.distance ?? '—' }}</td>
                    <td class="col-sym">{{ step.symbol === 'processing' ? '〇' : '' }}</td>
                    <td class="col-sym">
                      <span class="sym-inspection">{{ step.symbol === 'inspection' ? '□' : '' }}</span>
                    </td>
                    <td class="col-sym">
                      <span class="sym-transport">{{ step.symbol === 'transport' ? '→' : '' }}</span>
                    </td>
                    <td class="col-sym">{{ step.symbol === 'waiting' ? 'D' : '' }}</td>
                    <td class="col-sym">{{ step.symbol === 'storage' ? '▽' : '' }}</td>
                    <td class="col-remark">{{ step.remarks || '—' }}</td>
                  </tr>
                </tbody>
              </table>
              <!-- 工序系列内的符号连线（覆盖在五列符号上） -->
              <div class="flow-line-overlay" :style="lineOverlayStyle">
                <svg class="flow-line-svg" :viewBox="processLineViewBox" preserveAspectRatio="none">
                  <path :d="processLinePath" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="butt" stroke-linejoin="miter" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount, watch } from 'vue'
import { Delete, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ExcelJS from 'exceljs'
import html2canvas from 'html2canvas'

const props = defineProps({
  data: { type: Object, default: null },
  mode: { type: String, default: 'edit' } // 'edit' | 'preview'
})
const emit = defineEmits(['update:data'])

const defaultHeader = {
  workName: '',
  start: '',
  end: '',
  researcher: '',
  reviewer: '',
  date: new Date().toISOString().split('T')[0],
  version: ''
}

const defaultSteps = [
  { content: '原料储存', distance: 0, time: 0, symbol: 'storage', remarks: '' },
  { content: '搬运至切割机', distance: 20, time: 300, symbol: 'transport', remarks: '' },
  { content: '切割下料', distance: 0, time: 900, symbol: 'processing', remarks: '' }
]

const headerInfo = ref({ ...defaultHeader, ...(props.data?.headerInfo || {}) })
const steps = ref(
  props.data?.steps?.length ? props.data.steps.map(s => ({ ...s })) : defaultSteps.map(s => ({ ...s }))
)

function emitData() {
  emit('update:data', { headerInfo: { ...headerInfo.value }, steps: steps.value.map(s => ({ ...s })) })
}

watch([headerInfo, steps], emitData, { deep: true })

// 注:不在此处 watch props.data。父组件需要重新注入数据时,应使用 :key 强制重挂组件,
// 避免 props.data 与 emit 形成循环。组件初始化时已通过上面的 ref 默认值合并 props.data。

const chartContainerRef = ref(null)
const exportTargetRef = ref(null)
const processTableRef = ref(null)
const lineLayout = ref({ top: 0, left: 0, width: 280, height: 0 })
const linePoints = ref([])

const symbolColIndexMap = { processing: 3, inspection: 4, transport: 5, waiting: 6, storage: 7 }

const refreshLineGeometry = async () => {
  await nextTick()
  const wrapper = processTableRef.value
  if (!wrapper) return
  const table = wrapper.querySelector('.flow-process-table')
  const thead = table?.querySelector('thead')
  const tbody = table?.querySelector('tbody')
  const rows = table ? Array.from(table.querySelectorAll('tbody tr')) : []
  if (!table || !thead || !tbody || rows.length === 0) {
    linePoints.value = []
    lineLayout.value = { top: 0, left: 0, width: 280, height: 0 }
    return
  }

  const wrapperRect = wrapper.getBoundingClientRect()
  const tbodyRect = tbody.getBoundingClientRect()
  const sampleRow = rows[0]
  const firstSymCell = sampleRow?.cells?.[3]
  const lastSymCell = sampleRow?.cells?.[7]
  if (!firstSymCell || !lastSymCell) return

  const firstRect = firstSymCell.getBoundingClientRect()
  const lastRect = lastSymCell.getBoundingClientRect()
  const left = firstRect.left - wrapperRect.left
  const right = lastRect.right - wrapperRect.left
  const top = tbodyRect.top - wrapperRect.top
  const height = tbodyRect.height

  lineLayout.value = {
    top,
    left,
    width: Math.max(0, right - left),
    height: Math.max(0, height)
  }

  const pts = []
  rows.forEach((row, i) => {
    const step = steps.value[i]
    if (!step) return
    const colIndex = symbolColIndexMap[step.symbol] ?? 3
    const cell = row.cells?.[colIndex]
    if (!cell) return
    const rect = cell.getBoundingClientRect()
    pts.push({
      x: rect.left - wrapperRect.left - left + rect.width / 2,
      y: rect.top - wrapperRect.top - top + rect.height / 2
    })
  })
  linePoints.value = pts
}

const lineOverlayStyle = computed(() => ({
  top: `${lineLayout.value.top}px`,
  left: `${lineLayout.value.left}px`,
  width: `${lineLayout.value.width}px`,
  height: `${lineLayout.value.height}px`
}))

const processLineViewBox = computed(() => {
  const w = Math.max(1, lineLayout.value.width)
  const h = Math.max(1, lineLayout.value.height)
  return `0 0 ${w} ${h}`
})

// 工序系列内直线连线路径（不转折，从单元格中心到中心）
const processLinePath = computed(() => {
  if (linePoints.value.length < 2) return ''
  let path = `M${linePoints.value[0].x},${linePoints.value[0].y}`
  for (let i = 1; i < linePoints.value.length; i++) {
    path += ` L${linePoints.value[i].x},${linePoints.value[i].y}`
  }
  return path
})

// 统计计算
const stats = computed(() => {
  const result = {
    totalDistance: 0,
    totalTime: 0,
    counts: { processing: 0, transport: 0, inspection: 0, waiting: 0, storage: 0 }
  }
  steps.value.forEach(step => {
    result.totalDistance += (step.distance || 0)
    result.totalTime += (step.time || 0)
    if (step.symbol && result.counts[step.symbol] !== undefined) {
      result.counts[step.symbol]++
    }
  })
  return result
})

// 按工序类型统计时间、距离
const statsByType = computed(() => {
  const types = ['processing', 'inspection', 'transport', 'waiting', 'storage']
  const result = {}
  types.forEach(t => {
    result[t] = { time: 0, distance: 0 }
  })
  steps.value.forEach(step => {
    if (step.symbol && result[step.symbol]) {
      result[step.symbol].time += (step.time || 0)
      result[step.symbol].distance += (step.distance || 0)
    }
  })
  return result
})

// 方法
const addStep = () => {
  steps.value.push({ content: '', distance: 0, time: 0, symbol: 'processing', remarks: '' })
}

const removeStep = (index) => {
  steps.value.splice(index, 1)
}

const clearSteps = () => {
  steps.value = []
}

const loadExample = () => {
  headerInfo.value = {
    workName: '零件加工流程',
    start: '08:00',
    end: '12:00',
    researcher: '张三',
    reviewer: '李四',
    date: '2024-03-20',
    version: 'A'
  }
  steps.value = [
    { content: '原料储存', distance: 0, time: 0, symbol: 'storage', remarks: '' },
    { content: '搬运至切割机', distance: 20, time: 300, symbol: 'transport', remarks: '' },
    { content: '等待切割', distance: 0, time: 600, symbol: 'waiting', remarks: '' },
    { content: '切割下料', distance: 0, time: 900, symbol: 'processing', remarks: '' },
    { content: '尺寸检查', distance: 0, time: 120, symbol: 'inspection', remarks: '' },
    { content: '搬运至钻床', distance: 15, time: 240, symbol: 'transport', remarks: '' },
    { content: '钻孔', distance: 0, time: 480, symbol: 'processing', remarks: '' },
    { content: '去毛刺', distance: 0, time: 300, symbol: 'processing', remarks: '' },
    { content: '最终检查', distance: 0, time: 180, symbol: 'inspection', remarks: '' },
    { content: '搬运至成品库', distance: 30, time: 360, symbol: 'transport', remarks: '' },
    { content: '成品储存', distance: 0, time: 0, symbol: 'storage', remarks: '' }
  ]
}


const exportExcel = async () => {
  try {
    const workbook = new ExcelJS.Workbook()
    const sheet = workbook.addWorksheet('流程程序图')

    sheet.columns = [
      { width: 24 }, // A 工作说明
      { width: 10 }, // B 时间
      { width: 10 }, // C 距离
      { width: 8 },  // D 操作
      { width: 8 },  // E 检查
      { width: 8 },  // F 搬运
      { width: 8 },  // G 等待
      { width: 8 },  // H 储存
      { width: 14 }  // I 备注
    ]

    const thin = { style: 'thin', color: { argb: 'FF777777' } }
    const allBorder = { top: thin, left: thin, right: thin, bottom: thin }
    const center = { vertical: 'middle', horizontal: 'center', wrapText: true }
    const labelFill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF5F5F5' } }
    const headerFill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE8E8E8' } }

    // Row 1: 标题
    sheet.mergeCells('A1:I1')
    sheet.getCell('A1').value = '流程程序图'
    sheet.getCell('A1').alignment = center
    sheet.getCell('A1').font = { bold: true, size: 14 }
    sheet.getRow(1).height = 30

    // Row 2~8: 左侧基本信息(A:E) + 右侧统计表(F:I)
    const infoRows = [
      ['工作名称', headerInfo.value.workName || '—'],
      ['开始', headerInfo.value.start || '—'],
      ['结束', headerInfo.value.end || '—'],
      ['研究者', headerInfo.value.researcher || '—'],
      ['审阅者', headerInfo.value.reviewer || '—'],
      ['日期', headerInfo.value.date || '—'],
      ['版本', headerInfo.value.version || '—']
    ]

    infoRows.forEach((row, idx) => {
      const r = 2 + idx
      sheet.getCell(r, 1).value = row[0]
      sheet.getCell(r, 1).font = { bold: true }
      sheet.getCell(r, 1).fill = labelFill
      sheet.mergeCells(r, 2, r, 5)
      sheet.getCell(r, 2).value = row[1]
      sheet.getRow(r).height = 26
    })

    // 右侧统计表 F2:I8
    sheet.mergeCells('F2:I2')
    sheet.getCell('F2').value = '统计表'
    sheet.getCell('F2').font = { bold: true, size: 12 }
    sheet.getCell('F2').alignment = center
    sheet.getCell('F2').fill = headerFill

    ;['项别', '次数', '时间/s', '距离/m'].forEach((h, i) => {
      sheet.getCell(3, 6 + i).value = h
      sheet.getCell(3, 6 + i).font = { bold: true }
      sheet.getCell(3, 6 + i).alignment = center
      sheet.getCell(3, 6 + i).fill = headerFill
    })

    const statsData = [
      ['操作 〇', stats.value.counts.processing, statsByType.value.processing.time, statsByType.value.processing.distance],
      ['检查 □', stats.value.counts.inspection, statsByType.value.inspection.time, statsByType.value.inspection.distance],
      ['搬运 →', stats.value.counts.transport, statsByType.value.transport.time, statsByType.value.transport.distance],
      ['等待 D', stats.value.counts.waiting, statsByType.value.waiting.time, statsByType.value.waiting.distance],
      ['储存 ▽', stats.value.counts.storage, statsByType.value.storage.time, statsByType.value.storage.distance]
    ]

    statsData.forEach((row, idx) => {
      const r = 4 + idx
      row.forEach((v, i) => {
        sheet.getCell(r, 6 + i).value = v
        sheet.getCell(r, 6 + i).alignment = center
      })
      sheet.getRow(r).height = 26
    })

    // Row 9~10: 工序表头（两层）
    sheet.mergeCells('A9:A10')
    sheet.mergeCells('B9:B10')
    sheet.mergeCells('C9:C10')
    sheet.mergeCells('D9:H9')
    sheet.mergeCells('I9:I10')
    sheet.getCell('A9').value = '工作说明'
    sheet.getCell('B9').value = '时间/s'
    sheet.getCell('C9').value = '距离/m'
    sheet.getCell('D9').value = '工序系列'
    sheet.getCell('I9').value = '备注'
    ;['操作', '检查', '搬运', '等待', '储存'].forEach((h, i) => {
      sheet.getCell(10, 4 + i).value = h
    })
    sheet.getRow(9).height = 24
    sheet.getRow(10).height = 24

    // Row 11+: 工序数据
    const startRow = 11
    const symbolMap = { processing: 'D', inspection: 'E', transport: 'F', waiting: 'G', storage: 'H' }
    const symbolChars = { processing: '〇', inspection: '□', transport: '→', waiting: 'D', storage: '▽' }

    steps.value.forEach((step, idx) => {
      const r = startRow + idx
      sheet.getCell(`A${r}`).value = step.content || '—'
      sheet.getCell(`B${r}`).value = step.time ?? 0
      sheet.getCell(`C${r}`).value = step.distance ?? 0
      sheet.getCell(`D${r}`).value = step.symbol === 'processing' ? '〇' : ''
      sheet.getCell(`E${r}`).value = step.symbol === 'inspection' ? '□' : ''
      sheet.getCell(`F${r}`).value = step.symbol === 'transport' ? '→' : ''
      sheet.getCell(`G${r}`).value = step.symbol === 'waiting' ? 'D' : ''
      sheet.getCell(`H${r}`).value = step.symbol === 'storage' ? '▽' : ''
      sheet.getCell(`I${r}`).value = step.remarks || '—'
      sheet.getRow(r).height = 24
    })

    const lastRow = startRow + Math.max(steps.value.length, 1) - 1

    // 工序系列红色连线（叠加透明 PNG 到 D~H 列区域）
    if (steps.value.length >= 2) {
      const symbolColWidthsPx = [4, 5, 6, 7, 8].map((colIndex) => {
        const w = sheet.getColumn(colIndex).width || 8
        return Math.round(w * 7 + 5)
      })
      const rowHeightsPx = steps.value.map((_, idx) => {
        const h = sheet.getRow(startRow + idx).height || 20
        return Math.round(h * 96 / 72)
      })

      const lineImage = buildExcelLineImage(steps.value, symbolColWidthsPx, rowHeightsPx)
      if (lineImage) {
        const imageId = workbook.addImage({
          base64: lineImage.base64,
          extension: 'png'
        })
        sheet.addImage(imageId, {
          tl: { col: 3, row: startRow - 1 },
          br: { col: 8, row: startRow - 1 + steps.value.length },
          editAs: 'oneCell'
        })
      }
    }

    // 全表边框 + 对齐 + 表头填色
    for (let r = 1; r <= lastRow; r++) {
      for (let c = 1; c <= 9; c++) {
        const cell = sheet.getCell(r, c)
        cell.border = allBorder
        if (!cell.alignment) cell.alignment = center
        else cell.alignment = { ...cell.alignment, ...center }
      }
    }
    for (let r = 9; r <= 10; r++) {
      for (let c = 1; c <= 9; c++) {
        sheet.getCell(r, c).font = { bold: true }
        sheet.getCell(r, c).fill = headerFill
      }
    }

    const buffer = await workbook.xlsx.writeBuffer()
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `流程程序图_${headerInfo.value.workName || '导出'}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('Excel 导出成功')
  } catch (e) {
    ElMessage.error('Excel 导出失败：' + (e?.message || String(e)))
  }
}

const buildExcelLineImage = (rows, colWidthsPx, rowHeightsPx) => {
  try {
    const symbolIndexMap = { processing: 0, inspection: 1, transport: 2, waiting: 3, storage: 4 }
    const widths = (colWidthsPx && colWidthsPx.length === 5) ? colWidthsPx : [61, 61, 61, 61, 61]
    const heights = (rowHeightsPx && rowHeightsPx.length === rows.length) ? rowHeightsPx : rows.map(() => 32)
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
    ctx.strokeStyle = '#ef4444'
    ctx.lineWidth = 2
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'

    const colStart = [0]
    for (let i = 0; i < widths.length - 1; i++) colStart.push(colStart[i] + widths[i])
    const rowStart = [0]
    for (let i = 0; i < heights.length - 1; i++) rowStart.push(rowStart[i] + heights[i])

    const points = rows.map((r, i) => {
      const c = symbolIndexMap[r.symbol] ?? 0
      return {
        x: colStart[c] + widths[c] / 2,
        y: rowStart[i] + heights[i] / 2
      }
    })
    if (points.length < 2) return null

    ctx.beginPath()
    ctx.moveTo(points[0].x, points[0].y)
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(points[i].x, points[i].y)
    }
    ctx.stroke()

    return {
      base64: canvas.toDataURL('image/png'),
      width: totalW,
      height: totalH
    }
  } catch {
    return null
  }
}

const exportImage = async () => {
  try {
    const target = exportTargetRef.value
    const wrapper = processTableRef.value
    if (!target || !wrapper) { ElMessage.warning('无法导出图片'); return }

    await refreshLineGeometry()
    await nextTick()

    let lineDataUrl = null
    let oW = 0, oH = 0

    const table = wrapper.querySelector('.flow-process-table')
    const tbody = table?.querySelector('tbody')
    const tbodyRows = table ? Array.from(table.querySelectorAll('tbody tr')) : []

    if (tbodyRows.length >= 2 && tbody) {
      const firstRow = tbodyRows[0]
      const firstSymCell = firstRow.cells?.[3]
      const lastSymCell = firstRow.cells?.[7]

      if (firstSymCell && lastSymCell) {
        const firstRect = firstSymCell.getBoundingClientRect()
        const lastRect = lastSymCell.getBoundingClientRect()
        const tbodyRect = tbody.getBoundingClientRect()

        oW = lastRect.right - firstRect.left
        oH = tbodyRect.height

        const pts = []
        tbodyRows.forEach((row, i) => {
          const step = steps.value[i]
          if (!step) return
          const colIndex = symbolColIndexMap[step.symbol] ?? 3
          const cell = row.cells?.[colIndex]
          if (!cell) return
          const r = cell.getBoundingClientRect()
          pts.push({
            x: r.left - firstRect.left + r.width / 2,
            y: r.top - tbodyRect.top + r.height / 2
          })
        })

        if (pts.length >= 2) {
          const c = document.createElement('canvas')
          c.width = oW * 2
          c.height = oH * 2
          const ctx = c.getContext('2d')
          ctx.scale(2, 2)
          ctx.strokeStyle = '#ef4444'
          ctx.lineWidth = 2
          ctx.lineCap = 'round'
          ctx.lineJoin = 'round'
          ctx.beginPath()
          ctx.moveTo(pts[0].x, pts[0].y)
          for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y)
          ctx.stroke()
          lineDataUrl = c.toDataURL('image/png')
        }
      }
    }

    const capturedOW = oW, capturedOH = oH, capturedUrl = lineDataUrl
    const scale = 2
    const canvas = await html2canvas(target, {
      useCORS: true,
      scale,
      backgroundColor: '#fff',
      logging: false,
      onclone: (_doc, clonedTarget) => {
        const clonedSvg = clonedTarget.querySelector('.flow-line-svg')
        if (clonedSvg) clonedSvg.remove()

        if (capturedUrl) {
          const clonedOverlay = clonedTarget.querySelector('.flow-line-overlay')
          if (clonedOverlay) {
            const img = _doc.createElement('img')
            img.src = capturedUrl
            img.style.width = capturedOW + 'px'
            img.style.height = capturedOH + 'px'
            img.style.position = 'absolute'
            img.style.top = '0'
            img.style.left = '0'
            img.style.pointerEvents = 'none'
            clonedOverlay.appendChild(img)
          }
        }
      }
    })

    const link = document.createElement('a')
    link.href = canvas.toDataURL('image/png')
    link.download = `流程程序图_${headerInfo.value.workName || '导出'}.png`
    link.click()
    ElMessage.success('图片导出成功')
  } catch (e) {
    ElMessage.error('图片导出失败：' + (e?.message || String(e)))
  }
}

watch(steps, () => {
  refreshLineGeometry()
}, { deep: true })

onMounted(() => {
  // 初始 emit 一次,确保父组件即使用户未改动任何字段、直接保存,也能拿到默认数据
  emitData()
  refreshLineGeometry()
  window.addEventListener('resize', refreshLineGeometry)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', refreshLineGeometry)
})

defineExpose({ exportExcel, exportImage, exportTargetRef })
</script>

<style scoped lang="scss">
.process-flow-container {
  display: flex;
  height: 100%;
  gap: 16px;
  overflow: hidden;
}

.process-flow-container.preview-mode {
  /* AI 对话右侧预览模式:只显示右侧图表 */
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
  width: 420px; /* 左侧较窄 */
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
  min-width: 0; /* 防止flex子项溢出 */
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  padding: 16px;
  overflow: hidden;
}

.info-card, .steps-card {
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
  gap: 8px;
  flex-shrink: 0;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.stats-info {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
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

.flow-chart-paper {
  background: #fff;
  border: 1px solid #777;
}

.flow-main-title {
  font-size: 16px;
  font-weight: 600;
  text-align: center;
  padding: 16px 0 12px;
  border-bottom: 1px solid #777;
  color: #333;
}

/* 顶部：基本信息 + 统计表 */
.flow-top-section {
  padding: 0;
  border-bottom: none;
}

.flow-head-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  border: none;
  td {
    border: none;
    vertical-align: top;
    padding: 0;
  }
  .head-left {
    width: 62%;
    border-right: 1px solid #777;
  }
  .head-right {
    width: 38%;
    padding: 0;
  }
}

.flow-info-grid {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 13px;
  border: none;
  height: 100%;
  tr {
    height: 42px;
  }
  td {
    border: 1px solid #777;
    padding: 6px 8px;
    line-height: 1.4;
    color: #333;
    text-align: center;
    vertical-align: middle;
  }
  tr:first-child td {
    border-top: none;
  }
  tr:last-child td {
    border-bottom: none;
  }
  td:first-child {
    border-left: none;
  }
  td:last-child {
    border-right: none;
  }
  .k {
    width: 96px;
    font-weight: 600;
    background: #f5f5f5;
  }
  .v {
    text-align: center;
  }
}

.flow-stats-table {
  width: 100%;
  border-collapse: collapse;
  border: none;
  font-size: 13px;
  tr {
    height: 42px;
  }
  th, td {
    border: 1px solid #777;
    padding: 8px 12px;
    text-align: center;
    vertical-align: middle;
  }
  tr:first-child th {
    border-top: none;
  }
  tbody tr:last-child td {
    border-bottom: none;
  }
  th:first-child,
  td:first-child {
    border-left: none;
  }
  th:last-child,
  td:last-child {
    border-right: none;
  }
  th {
    font-weight: 600;
    background: #e8e8e8;
    text-align: center;
    color: #333;
  }
  .stats-merged-title {
    font-size: 14px;
    font-weight: 600;
    padding: 8px 0;
  }
}

.flow-series-title {
  font-weight: 600;
  font-size: 14px;
  padding: 12px 20px 8px;
  color: #333;
}

/* 工序系列主表 */
.flow-process-wrapper {
  position: relative;
  overflow: hidden;
}

.flow-process-table {
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
  .col-sym-h {
    width: 56px;
  }
  .col-desc {
    text-align: center;
    width: 180px;
  }
  .col-num {
    width: 60px;
  }
  .col-series {
    width: 280px;
  }
  .col-sym {
    width: 56px;
    font-size: 15px;
  }
  .col-remark {
    text-align: center;
    width: 100px;
    max-width: 100px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  tbody tr {
    height: 36px;
  }
  /* 与外层总边框共享边线，避免左右下叠线加粗 */
  tr > *:first-child {
    border-left: none;
  }
  tr > *:last-child {
    border-right: none;
  }
  tbody tr:last-child td {
    border-bottom: none;
  }
}

.sym-transport,
.sym-inspection {
  display: inline-block;
  font-size: 24px;
  line-height: 1;
  font-weight: 400;
}

/* 工序系列内连线覆盖层（绘在符号上方） */
.flow-line-overlay {
  position: absolute;
  pointer-events: none;
  z-index: 2;
}

.flow-line-svg {
  width: 100%;
  height: 100%;
  display: block;
}

/* 隐藏表格表头多余padding */
:deep(.el-table .cell) {
  padding: 0 4px;
}
</style>