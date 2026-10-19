<template>
  <div class="joint-op-container" :class="{ 'preview-mode': mode === 'preview' }">
    <div class="left-panel" v-if="mode !== 'preview'">
      <!-- 基本信息 -->
      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
            <el-button link type="primary" @click="loadExample">加载示例</el-button>
          </div>
        </template>
        <el-form :model="headerInfo" label-width="70px" size="small">
          <el-form-item label="作业名称">
            <el-input v-model="headerInfo.taskName" placeholder="作业名称" />
          </el-form-item>
          <el-form-item label="操作者">
            <el-input v-model="headerInfo.operator" placeholder="操作者" />
          </el-form-item>
          <el-row :gutter="10">
            <el-col :span="12">
              <el-form-item label="日期">
                <el-date-picker v-model="headerInfo.date" type="date" placeholder="选择日期" style="width: 100%" value-format="YYYY-MM-DD" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="地点">
                <el-input v-model="headerInfo.location" placeholder="作业地点" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="备注">
            <el-input v-model="headerInfo.remarks" placeholder="备注" />
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 列（操作者）管理 -->
      <el-card class="columns-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>操作者列 ({{ columns.length }})</span>
            <div>
              <el-button link type="primary" @click="addColumn">新增列</el-button>
              <el-button link type="danger" @click="removeLastColumn" :disabled="columns.length <= 1">删除末列</el-button>
            </div>
          </div>
        </template>
        <div class="columns-list">
          <div v-for="(col, idx) in columns" :key="col.id" class="column-item">
            <span class="col-index">{{ idx + 1 }}.</span>
            <el-input v-model="col.name" size="small" placeholder="操作者名称" />
          </div>
        </div>
      </el-card>

      <!-- 时间行编辑 -->
      <el-card class="rows-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>时间行明细 ({{ timeRows.length }})</span>
            <div>
              <el-button link type="primary" @click="addTimeRow">新增行</el-button>
              <el-button link type="danger" @click="removeLastRow" :disabled="timeRows.length <= 1">删除末行</el-button>
              <el-button link type="danger" @click="clearRows">清空</el-button>
            </div>
          </div>
        </template>
        <div class="rows-table-container">
          <table class="rows-edit-table">
            <thead>
              <tr>
                <th class="th-time">时间/s</th>
                <th v-for="col in columns" :key="col.id" class="th-col">{{ col.name }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rIdx) in timeRows" :key="rIdx">
                <td class="td-time">
                  <el-input-number v-model="row.time" size="small" :min="0" :step="0.5" :controls="false" style="width: 100%" />
                </td>
                <td v-for="col in columns" :key="col.id" class="td-cell">
                  <el-input v-model="getCell(row, col.id).desc" size="small" placeholder="描述" />
                  <div class="cell-meta">
                    <el-input-number v-model="getCell(row, col.id).duration" size="small" :min="0" :step="0.5" :controls="false" style="width: 60px" />
                    <el-switch v-model="getCell(row, col.id).isWork" size="small" active-text="工" inactive-text="闲" inline-prompt />
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </el-card>

      <!-- 由父组件注入的"保存图表"按钮 -->
      <div class="save-slot-wrapper" v-if="$slots['save-button']">
        <slot name="save-button" />
      </div>
    </div>

    <div class="right-panel">

      <!-- 联合作业分析图预览 -->
      <div class="chart-container" ref="chartContainerRef">
        <div class="chart-scroll export-target" ref="exportTargetRef">
          <div class="joint-chart-paper">
            <div class="chart-main-title">联合作业分析图</div>

            <!-- 头部信息 -->
            <div class="chart-header-section">
              <table class="chart-info-table">
                <tbody>
                  <tr>
                    <td class="k">作业名称</td>
                    <td class="v" colspan="3">{{ headerInfo.taskName || '—' }}</td>
                    <td class="k">操作者</td>
                    <td class="v">{{ headerInfo.operator || '—' }}</td>
                  </tr>
                  <tr>
                    <td class="k">日期</td>
                    <td class="v">{{ headerInfo.date || '—' }}</td>
                    <td class="k">作业地点</td>
                    <td class="v">{{ headerInfo.location || '—' }}</td>
                    <td class="k">备注</td>
                    <td class="v">{{ headerInfo.remarks || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- 作业分析主表 -->
            <table class="chart-main-table">
              <thead>
                <tr>
                  <th class="col-time" rowspan="2">时间/s</th>
                  <template v-for="col in columns" :key="col.id">
                    <th colspan="2" class="col-operator-header">{{ col.name }}</th>
                  </template>
                </tr>
                <tr>
                  <template v-for="col in columns" :key="col.id + '-sub'">
                    <th class="col-sub-desc">描述</th>
                    <th class="col-sub-bar">时间</th>
                  </template>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, rIdx) in timeRows" :key="rIdx">
                  <td class="col-time">{{ row.time }}</td>
                  <template v-for="col in columns" :key="col.id">
                    <template v-if="shouldRenderCell(rIdx, col.id)">
                      <td class="td-desc" :rowspan="getCellRowspan(rIdx, col.id)">
                        {{ getCell(row, col.id).desc || '—' }}
                      </td>
                      <td class="td-bar" :rowspan="getCellRowspan(rIdx, col.id)"
                          :class="getCell(row, col.id).isWork ? 'bar-work' : 'bar-idle'"></td>
                    </template>
                  </template>
                </tr>
              </tbody>
            </table>

            <!-- 统计表 -->
            <div class="chart-stats-section">
              <div class="stats-title">统计汇总</div>
              <table class="chart-stats-table">
                <thead>
                  <tr>
                    <th>操作者</th>
                    <th>周程/s</th>
                    <th>工作时间/s</th>
                    <th>空闲时间/s</th>
                    <th>效率/%</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="col in columns" :key="col.id">
                    <td>{{ col.name }}</td>
                    <td>{{ stats[col.id]?.cycleTime ?? '—' }}</td>
                    <td class="stat-work">{{ stats[col.id]?.workTime ?? '—' }}</td>
                    <td class="stat-idle">{{ stats[col.id]?.idleTime ?? '—' }}</td>
                    <td class="stat-eff" :class="{ 'eff-high': Number(stats[col.id]?.efficiency) >= 80, 'eff-low': Number(stats[col.id]?.efficiency) < 50 }">
                      {{ stats[col.id]?.efficiency ?? '—' }}%
                    </td>
                  </tr>
                  <tr class="stats-summary-row">
                    <td><strong>平均</strong></td>
                    <td>{{ avgStats.cycleTime }}</td>
                    <td class="stat-work">{{ avgStats.workTime }}</td>
                    <td class="stat-idle">{{ avgStats.idleTime }}</td>
                    <td class="stat-eff">{{ avgStats.efficiency }}%</td>
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
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ExcelJS from 'exceljs'
import html2canvas from 'html2canvas'

const props = defineProps({
  data: { type: Object, default: null },
  mode: { type: String, default: 'edit' }
})
const emit = defineEmits(['update:data'])

// ===== 数据状态 =====
const defaultHeader = {
  taskName: '',
  operator: '',
  date: new Date().toISOString().split('T')[0],
  location: '',
  remarks: ''
}

const headerInfo = ref({ ...defaultHeader, ...(props.data?.headerInfo || {}) })

let colCounter = 0
const makeColId = () => `col${++colCounter}`

const initColumns = () => {
  if (props.data?.columns?.length) {
    const cols = props.data.columns.map(c => ({ ...c }))
    const maxId = cols.reduce((max, c) => {
      const num = parseInt(c.id?.replace('col', '') || '0')
      return num > max ? num : max
    }, 0)
    colCounter = maxId
    return cols
  }
  return [{ id: makeColId(), name: '操作者1' }]
}

const initTimeRows = () => {
  if (props.data?.timeRows?.length) {
    return props.data.timeRows.map(r => ({ ...r, cells: { ...r.cells } }))
  }
  return []
}

const columns = ref(initColumns())
const timeRows = ref(initTimeRows())

const chartContainerRef = ref(null)
const exportTargetRef = ref(null)

// ===== 辅助方法 =====
const getCell = (row, colId) => {
  if (!row.cells[colId]) {
    row.cells[colId] = { desc: '', duration: 0, isWork: false }
  }
  return row.cells[colId]
}

// ===== 预览合并计算 =====
// 相邻行中同一列 desc+isWork 相同的单元格自动合并
const mergeInfo = computed(() => {
  const info = {}
  columns.value.forEach(col => {
    const groups = []
    let i = 0
    while (i < timeRows.value.length) {
      const cell = getCell(timeRows.value[i], col.id)
      let span = 1
      if (cell.desc) {
        while (i + span < timeRows.value.length) {
          const next = getCell(timeRows.value[i + span], col.id)
          if (next.desc === cell.desc && next.isWork === cell.isWork) {
            span++
          } else {
            break
          }
        }
      }
      groups.push({ start: i, span })
      i += span
    }
    info[col.id] = groups
  })
  return info
})

const shouldRenderCell = (rIdx, colId) => {
  const groups = mergeInfo.value[colId]
  if (!groups) return true
  return groups.some(g => g.start === rIdx)
}

const getCellRowspan = (rIdx, colId) => {
  const groups = mergeInfo.value[colId]
  if (!groups) return 1
  const g = groups.find(g => g.start === rIdx)
  return g ? g.span : 1
}

// ===== 列管理 =====
const addColumn = () => {
  const newId = makeColId()
  columns.value.push({ id: newId, name: `操作者${columns.value.length + 1}` })
  // 为现有行添加该列的单元格
  timeRows.value.forEach(row => {
    row.cells[newId] = { desc: '', duration: 0, isWork: false }
  })
}

const removeLastColumn = () => {
  if (columns.value.length <= 1) return
  const removed = columns.value.pop()
  // 清理行数据
  timeRows.value.forEach(row => {
    delete row.cells[removed.id]
  })
}

// ===== 行管理 =====
const addTimeRow = () => {
  const lastTime = timeRows.value.length > 0 ? timeRows.value[timeRows.value.length - 1].time : 0
  const cells = {}
  columns.value.forEach(col => {
    cells[col.id] = { desc: '', duration: 0.5, isWork: false }
  })
  timeRows.value.push({ time: lastTime + 0.5, cells })
}

const removeLastRow = () => {
  if (timeRows.value.length <= 1) return
  timeRows.value.pop()
}

const clearRows = () => {
  timeRows.value = []
}

// ===== 统计 =====
const stats = computed(() => {
  const result = {}
  const maxTime = timeRows.value.length > 0 ? Math.max(...timeRows.value.map(r => r.time)) : 0
  columns.value.forEach(col => {
    let workTime = 0
    timeRows.value.forEach(row => {
      const cell = row.cells[col.id]
      if (cell && cell.isWork) {
        workTime += (cell.duration || 0)
      }
    })
    const cycleTime = maxTime
    const idleTime = Math.max(0, +(cycleTime - workTime).toFixed(2))
    const efficiency = cycleTime > 0 ? (workTime / cycleTime * 100).toFixed(1) : '0.0'
    result[col.id] = {
      name: col.name,
      cycleTime: +cycleTime.toFixed(2),
      workTime: +workTime.toFixed(2),
      idleTime,
      efficiency
    }
  })
  return result
})

const avgStats = computed(() => {
  const cols = columns.value
  if (cols.length === 0) return { cycleTime: 0, workTime: 0, idleTime: 0, efficiency: '0.0' }
  let totalWork = 0, totalIdle = 0, totalCycle = 0
  cols.forEach(col => {
    const s = stats.value[col.id]
    if (s) {
      totalCycle += s.cycleTime
      totalWork += s.workTime
      totalIdle += s.idleTime
    }
  })
  const n = cols.length
  return {
    cycleTime: +(totalCycle / n).toFixed(2),
    workTime: +(totalWork / n).toFixed(2),
    idleTime: +(totalIdle / n).toFixed(2),
    efficiency: totalCycle > 0 ? ((totalWork / totalCycle) * 100).toFixed(1) : '0.0'
  }
})

// ===== 加载示例 =====
const loadExample = () => {
  colCounter = 7

  headerInfo.value = {
    taskName: 'F1汽车轮胎更换',
    operator: '换胎团队',
    date: '2024-03-20',
    location: '维修站',
    remarks: 'F1赛事进站换胎流程分析'
  }

  columns.value = [
    { id: 'col1', name: '前千斤顶操作员' },
    { id: 'col2', name: '后千斤顶操作员' },
    { id: 'col3', name: '轮胎枪手' },
    { id: 'col4', name: '轮胎搬运工' },
    { id: 'col5', name: '稳定员' },
    { id: 'col6', name: '总协调员' },
    { id: 'col7', name: '其他辅助人员' },
  ]

  timeRows.value = [
    {
      time: 0.5,
      cells: {
        col1: { desc: '顶起前部', duration: 0.5, isWork: true },
        col2: { desc: '顶起后部', duration: 0.5, isWork: true },
        col3: { desc: '等待', duration: 0.5, isWork: false },
        col4: { desc: '等待', duration: 0.5, isWork: false },
        col5: { desc: '等待', duration: 0.5, isWork: false },
        col6: { desc: '确认停车位置', duration: 0.5, isWork: true },
        col7: { desc: '等待', duration: 0.5, isWork: false },
      }
    },
    {
      time: 1.0,
      cells: {
        col1: { desc: '保持顶升', duration: 0.5, isWork: true },
        col2: { desc: '保持顶升', duration: 0.5, isWork: true },
        col3: { desc: '拧松旧轮胎螺母', duration: 0.5, isWork: true },
        col4: { desc: '准备新轮胎', duration: 0.5, isWork: true },
        col5: { desc: '扶稳车身', duration: 0.5, isWork: true },
        col6: { desc: '协调指挥', duration: 0.5, isWork: true },
        col7: { desc: '等待', duration: 0.5, isWork: false },
      }
    },
    {
      time: 1.5,
      cells: {
        col1: { desc: '保持顶升', duration: 0.5, isWork: true },
        col2: { desc: '保持顶升', duration: 0.5, isWork: true },
        col3: { desc: '卸下旧轮胎', duration: 0.5, isWork: true },
        col4: { desc: '递送新轮胎', duration: 0.5, isWork: true },
        col5: { desc: '扶稳车身', duration: 0.5, isWork: true },
        col6: { desc: '协调指挥', duration: 0.5, isWork: true },
        col7: { desc: '清理旧轮胎', duration: 0.5, isWork: true },
      }
    },
    {
      time: 2.0,
      cells: {
        col1: { desc: '保持顶升', duration: 0.5, isWork: true },
        col2: { desc: '保持顶升', duration: 0.5, isWork: true },
        col3: { desc: '安装新轮胎', duration: 0.5, isWork: true },
        col4: { desc: '传递轮胎', duration: 0.5, isWork: true },
        col5: { desc: '扶稳车身', duration: 0.5, isWork: true },
        col6: { desc: '协调指挥', duration: 0.5, isWork: true },
        col7: { desc: '搬走旧轮胎', duration: 0.5, isWork: true },
      }
    },
    {
      time: 2.5,
      cells: {
        col1: { desc: '保持顶升', duration: 0.5, isWork: true },
        col2: { desc: '保持顶升', duration: 0.5, isWork: true },
        col3: { desc: '拧紧螺母', duration: 0.5, isWork: true },
        col4: { desc: '等待', duration: 0.5, isWork: false },
        col5: { desc: '扶稳车身', duration: 0.5, isWork: true },
        col6: { desc: '检查安装', duration: 0.5, isWork: true },
        col7: { desc: '等待', duration: 0.5, isWork: false },
      }
    },
    {
      time: 3.0,
      cells: {
        col1: { desc: '放下前部', duration: 0.5, isWork: true },
        col2: { desc: '放下后部', duration: 0.5, isWork: true },
        col3: { desc: '最终紧固', duration: 0.5, isWork: true },
        col4: { desc: '等待', duration: 0.5, isWork: false },
        col5: { desc: '等待', duration: 0.5, isWork: false },
        col6: { desc: '确认完成', duration: 0.5, isWork: true },
        col7: { desc: '等待', duration: 0.5, isWork: false },
      }
    },
    {
      time: 3.5,
      cells: {
        col1: { desc: '撤离千斤顶', duration: 0.5, isWork: true },
        col2: { desc: '撤离千斤顶', duration: 0.5, isWork: true },
        col3: { desc: '等待', duration: 0.5, isWork: false },
        col4: { desc: '等待', duration: 0.5, isWork: false },
        col5: { desc: '等待', duration: 0.5, isWork: false },
        col6: { desc: '发出放行信号', duration: 0.5, isWork: true },
        col7: { desc: '等待', duration: 0.5, isWork: false },
      }
    },
  ]
}

// ===== 数据同步 =====
function emitData() {
  emit('update:data', {
    headerInfo: { ...headerInfo.value },
    columns: columns.value.map(c => ({ ...c })),
    timeRows: timeRows.value.map(r => ({ ...r, cells: { ...r.cells } }))
  })
}

watch([headerInfo, columns, timeRows], emitData, { deep: true })

// ===== 导出Excel =====
const exportExcel = async () => {
  try {
    const workbook = new ExcelJS.Workbook()
    const sheet = workbook.addWorksheet('联合作业分析')

    const colCount = columns.value.length
    const totalCols = 1 + colCount * 2 // 时间列 + 每个操作者2列(描述+涂黑)

    // 设置列宽
    const colWidths = [{ width: 10 }] // 时间列
    columns.value.forEach(() => {
      colWidths.push({ width: 18 }) // 描述列
      colWidths.push({ width: 5 })  // 涂黑条列
    })
    sheet.columns = colWidths

    const thin = { style: 'thin', color: { argb: 'FF777777' } }
    const allBorder = { top: thin, left: thin, right: thin, bottom: thin }
    const center = { vertical: 'middle', horizontal: 'center', wrapText: true }

    let currentRow = 1

    // 标题
    sheet.mergeCells(currentRow, 1, currentRow, totalCols)
    const titleCell = sheet.getCell(currentRow, 1)
    titleCell.value = '联合作业分析图'
    titleCell.alignment = center
    titleCell.font = { bold: true, size: 14 }
    sheet.getRow(currentRow).height = 30
    currentRow++

    // 辅助：将 totalCols 分成 n 段，返回 [{s,e},...] (1-indexed, 含两端)
    const splitCols = (n) => {
      const segs = []
      for (let i = 0; i < n; i++) {
        const s = 1 + Math.floor(i * totalCols / n)
        const e = Math.floor((i + 1) * totalCols / n)
        segs.push({ s, e })
      }
      return segs
    }

    const labelFill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF5F5F5' } }

    // 头部信息行1: 作业名称(值) | 操作者(值)  — 分4段
    const h1 = splitCols(4)
    sheet.mergeCells(currentRow, h1[0].s, currentRow, h1[0].e)
    sheet.getCell(currentRow, h1[0].s).value = '作业名称'
    sheet.getCell(currentRow, h1[0].s).font = { bold: true }
    sheet.getCell(currentRow, h1[0].s).fill = labelFill
    sheet.getCell(currentRow, h1[0].s).alignment = center
    sheet.mergeCells(currentRow, h1[1].s, currentRow, h1[1].e)
    sheet.getCell(currentRow, h1[1].s).value = headerInfo.value.taskName || '—'
    sheet.getCell(currentRow, h1[1].s).alignment = center
    sheet.mergeCells(currentRow, h1[2].s, currentRow, h1[2].e)
    sheet.getCell(currentRow, h1[2].s).value = '操作者'
    sheet.getCell(currentRow, h1[2].s).font = { bold: true }
    sheet.getCell(currentRow, h1[2].s).fill = labelFill
    sheet.getCell(currentRow, h1[2].s).alignment = center
    sheet.mergeCells(currentRow, h1[3].s, currentRow, h1[3].e)
    sheet.getCell(currentRow, h1[3].s).value = headerInfo.value.operator || '—'
    sheet.getCell(currentRow, h1[3].s).alignment = center
    sheet.getRow(currentRow).height = 24
    currentRow++

    // 头部信息行2: 日期(值) | 地点(值) | 备注(值) — 分6段
    const h2 = splitCols(6)
    const infoKV = [
      { k: '日期', v: headerInfo.value.date || '—' },
      { k: '地点', v: headerInfo.value.location || '—' },
      { k: '备注', v: headerInfo.value.remarks || '—' }
    ]
    infoKV.forEach((item, i) => {
      const kSeg = h2[i * 2]
      const vSeg = h2[i * 2 + 1]
      sheet.mergeCells(currentRow, kSeg.s, currentRow, kSeg.e)
      sheet.getCell(currentRow, kSeg.s).value = item.k
      sheet.getCell(currentRow, kSeg.s).font = { bold: true }
      sheet.getCell(currentRow, kSeg.s).fill = labelFill
      sheet.getCell(currentRow, kSeg.s).alignment = center
      sheet.mergeCells(currentRow, vSeg.s, currentRow, vSeg.e)
      sheet.getCell(currentRow, vSeg.s).value = item.v
      sheet.getCell(currentRow, vSeg.s).alignment = center
    })
    sheet.getRow(currentRow).height = 24
    currentRow++

    // 数据表头 - 第一行：操作者名称（合并2列）
    sheet.getCell(currentRow, 1).value = '时间/s'
    sheet.getCell(currentRow, 1).font = { bold: true }
    sheet.getCell(currentRow, 1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE8E8E8' } }
    sheet.mergeCells(currentRow, 1, currentRow + 1, 1) // 时间列跨2行
    columns.value.forEach((col, idx) => {
      const startCol = 2 + idx * 2
      sheet.mergeCells(currentRow, startCol, currentRow, startCol + 1)
      const cell = sheet.getCell(currentRow, startCol)
      cell.value = col.name
      cell.font = { bold: true }
      cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE8E8E8' } }
      cell.alignment = center
    })
    sheet.getRow(currentRow).height = 26
    currentRow++

    // 数据表头 - 第二行：描述/时间 子列
    columns.value.forEach((col, idx) => {
      const startCol = 2 + idx * 2
      const descCell = sheet.getCell(currentRow, startCol)
      descCell.value = '描述'
      descCell.font = { bold: true, size: 10 }
      descCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF0F0F0' } }
      descCell.alignment = center
      const barCell = sheet.getCell(currentRow, startCol + 1)
      barCell.value = '时间'
      barCell.font = { bold: true, size: 10 }
      barCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF0F0F0' } }
      barCell.alignment = center
    })
    sheet.getRow(currentRow).height = 22
    currentRow++

    // 数据行
    const workFill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFA0A0A0' } }
    const idleFill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFFFFFF' } }

    const dataStartRow = currentRow
    timeRows.value.forEach(row => {
      sheet.getCell(currentRow, 1).value = row.time
      columns.value.forEach((col, idx) => {
        const cell = row.cells[col.id]
        const descCol = 2 + idx * 2
        const barCol = descCol + 1
        const descCell = sheet.getCell(currentRow, descCol)
        const barCell = sheet.getCell(currentRow, barCol)
        if (cell) {
          descCell.value = cell.desc || '—'
          barCell.value = ''
          barCell.fill = cell.isWork ? workFill : idleFill
        } else {
          descCell.value = '—'
          barCell.value = ''
          barCell.fill = idleFill
        }
      })
      sheet.getRow(currentRow).height = 28
      currentRow++
    })

    // 合并连续相同单元格（与前端预览一致）
    columns.value.forEach((col, idx) => {
      const descCol = 2 + idx * 2
      const barCol = descCol + 1
      let i = 0
      while (i < timeRows.value.length) {
        const cell = getCell(timeRows.value[i], col.id)
        let span = 1
        if (cell.desc) {
          while (i + span < timeRows.value.length) {
            const next = getCell(timeRows.value[i + span], col.id)
            if (next.desc === cell.desc && next.isWork === cell.isWork) {
              span++
            } else {
              break
            }
          }
        }
        if (span > 1) {
          const startR = dataStartRow + i
          const endR = dataStartRow + i + span - 1
          sheet.mergeCells(startR, descCol, endR, descCol)
          sheet.mergeCells(startR, barCol, endR, barCol)
          sheet.getCell(startR, descCol).alignment = { vertical: 'middle', horizontal: 'center', wrapText: true }
        }
        i += span
      }
    })

    // 统计表
    sheet.mergeCells(currentRow, 1, currentRow, totalCols)
    sheet.getCell(currentRow, 1).value = '统计汇总'
    sheet.getCell(currentRow, 1).font = { bold: true, size: 12 }
    sheet.getCell(currentRow, 1).alignment = center
    sheet.getRow(currentRow).height = 26
    currentRow++

    // 统计表头 — 按 totalCols 均分5列
    const statHeaders = ['操作者', '周程/s', '工作时间/s', '空闲时间/s', '效率/%']
    const statSegs = splitCols(5)

    const writeStatRow = (values, opts = {}) => {
      for (let i = 0; i < 5; i++) {
        const { s, e } = statSegs[i]
        if (e > s) sheet.mergeCells(currentRow, s, currentRow, e)
        const c = sheet.getCell(currentRow, s)
        c.value = values[i]
        c.alignment = center
        if (opts.bold) c.font = { bold: true }
        if (opts.fill) c.fill = opts.fill
      }
      sheet.getRow(currentRow).height = 24
      currentRow++
    }

    writeStatRow(statHeaders, { bold: true, fill: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE8E8E8' } } })

    // 统计数据
    const greenFont = { color: { argb: 'FF16A34A' } }
    const grayFont = { color: { argb: 'FF94A3B8' } }
    const redFont = { color: { argb: 'FFDC2626' }, bold: true }
    const greenBoldFont = { color: { argb: 'FF16A34A' }, bold: true }

    const writeColoredStatRow = (values, eff) => {
      for (let i = 0; i < 5; i++) {
        const { s, e } = statSegs[i]
        if (e > s) sheet.mergeCells(currentRow, s, currentRow, e)
        const c = sheet.getCell(currentRow, s)
        c.value = values[i]
        c.alignment = center
        // i=2 工作时间绿色, i=3 空闲时间灰色, i=4 效率按阈值
        if (i === 2) c.font = greenFont
        else if (i === 3) c.font = grayFont
        else if (i === 4) {
          const effNum = Number(eff)
          if (effNum >= 80) c.font = greenBoldFont
          else if (effNum < 50) c.font = redFont
          else c.font = { bold: true }
        }
      }
      sheet.getRow(currentRow).height = 24
      currentRow++
    }

    columns.value.forEach(col => {
      const s = stats.value[col.id]
      if (s) {
        writeColoredStatRow([s.name, s.cycleTime, s.workTime, s.idleTime, `${s.efficiency}%`], s.efficiency)
      }
    })

    // 平均行
    writeStatRow(
      ['平均', avgStats.value.cycleTime, avgStats.value.workTime, avgStats.value.idleTime, `${avgStats.value.efficiency}%`],
      { bold: true }
    )

    // 全局边框和对齐
    const lastRow = currentRow - 1
    for (let r = 1; r <= lastRow; r++) {
      for (let c = 1; c <= totalCols; c++) {
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
    link.download = `联合作业分析_${headerInfo.value.taskName || '未命名'}.xlsx`
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
    link.download = `联合作业分析_${headerInfo.value.taskName || '未命名'}.png`
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
.joint-op-container {
  display: flex;
  height: 100%;
  gap: 16px;
  overflow: hidden;
}

.joint-op-container.preview-mode {
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

.info-card, .columns-card, .rows-card {
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

/* 列管理 */
.columns-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.column-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.col-index {
  font-size: 12px;
  color: #999;
  width: 20px;
  text-align: right;
  flex-shrink: 0;
}

/* 行编辑表 */
.rows-table-container {
  overflow: auto;
  max-height: 400px;
}

.rows-edit-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;

  th, td {
    border: 1px solid #e2e8f0;
    padding: 4px 6px;
    text-align: center;
    vertical-align: middle;
  }

  th {
    background: #f5f7fa;
    font-weight: 600;
    font-size: 11px;
    position: sticky;
    top: 0;
    z-index: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 80px;
  }

  .th-time {
    width: 60px;
    min-width: 60px;
  }

  .th-col {
    min-width: 100px;
  }

  .td-time {
    width: 60px;
    min-width: 60px;
  }

  .td-cell {
    min-width: 100px;
  }
}

.cell-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 3px;
  justify-content: center;
}

/* 操作栏 */
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}

/* 预览区域 */
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

/* 联合作业分析图纸 */
.joint-chart-paper {
  background: #fff;
  border: 1px solid #777;
  min-width: 600px;
}

.chart-main-title {
  font-size: 16px;
  font-weight: 600;
  text-align: center;
  padding: 16px 0 12px;
  border-bottom: 1px solid #777;
  color: #333;
}

/* 头部信息表 */
.chart-header-section {
  border-bottom: 1px solid #777;
}

.chart-info-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  td {
    border: 1px solid #ccc;
    padding: 6px 10px;
    vertical-align: middle;
    text-align: center;
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
    font-weight: 600;
    background: #f5f5f5;
    white-space: nowrap;
    width: 70px;
  }

  .v {
    color: #333;
  }
}

/* 主数据表 */
.chart-main-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  table-layout: fixed;

  th, td {
    border: 1px solid #777;
    padding: 6px 8px;
    text-align: center;
    vertical-align: middle;
  }

  thead th {
    font-weight: 600;
    background: #e8e8e8;
    color: #333;
    font-size: 12px;
    padding: 8px 6px;
  }

  .col-time {
    width: 60px;
    font-weight: 500;
  }

  .col-operator-header {
    min-width: 120px;
  }

  .col-sub-desc {
    font-size: 11px;
    font-weight: 500;
    background: #f0f0f0;
  }

  .col-sub-bar {
    width: 28px;
    min-width: 28px;
    max-width: 28px;
    font-size: 11px;
    font-weight: 500;
    background: #f0f0f0;
  }

  .td-desc {
    font-size: 12px;
    line-height: 1.3;
    color: #333;
    text-align: left;
    padding: 6px 8px;
  }

  .td-bar {
    width: 28px;
    min-width: 28px;
    max-width: 28px;
    padding: 0;
  }

  .bar-work {
    background: #a0a0a0;
  }

  .bar-idle {
    background: #fff;
  }

  tbody tr {
    height: 40px;
  }

  tr > *:first-child {
    border-left: none;
  }

  tr > *:last-child {
    border-right: none;
  }

  tbody tr:last-child td {
    border-bottom: none;
  }

  thead tr:first-child th {
    border-top: none;
  }
}

/* 统计区域 */
.chart-stats-section {
  border-top: 2px solid #777;
}

.stats-title {
  font-size: 14px;
  font-weight: 600;
  text-align: center;
  padding: 10px 0 8px;
  color: #333;
  border-bottom: 1px solid #777;
}

.chart-stats-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  th, td {
    border: 1px solid #777;
    padding: 6px 10px;
    text-align: center;
    vertical-align: middle;
  }

  th {
    font-weight: 600;
    background: #e8e8e8;
    color: #333;
    font-size: 12px;
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

  .stat-work {
    color: #16a34a;
    font-weight: 500;
  }

  .stat-idle {
    color: #94a3b8;
  }

  .stat-eff {
    font-weight: 600;
  }

  .eff-high {
    color: #16a34a;
  }

  .eff-low {
    color: #dc2626;
  }

  .stats-summary-row {
    background: #fafafa;
    td {
      font-weight: 500;
    }
  }
}

/* 隐藏表格表头多余padding */
:deep(.el-table .cell) {
  padding: 0 4px;
}
</style>
