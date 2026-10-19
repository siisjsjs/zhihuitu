<template>
  <div class="man-machine-container" :class="{ 'preview-mode': mode === 'preview' }">
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
            <el-input v-model="headerInfo.worker" placeholder="操作者姓名" />
          </el-form-item>
          <el-row :gutter="10">
            <el-col :span="12">
              <el-form-item label="日期">
                <el-date-picker v-model="headerInfo.date" type="date" placeholder="选择日期" style="width: 100%" value-format="YYYY-MM-DD" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="研究者">
                <el-input v-model="headerInfo.analyst" placeholder="研究者" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </el-card>

      <!-- 机器管理 -->
      <el-card class="machines-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>机器列 ({{ machines.length }})</span>
            <div>
              <el-button link type="primary" @click="addMachine">新增机器</el-button>
              <el-button link type="danger" @click="removeLastMachine" :disabled="machines.length <= 1">删除末列</el-button>
            </div>
          </div>
        </template>
        <div class="machines-list">
          <div v-for="(m, idx) in machines" :key="m.id" class="machine-item">
            <span class="col-index">{{ idx + 1 }}.</span>
            <el-input v-model="m.name" size="small" placeholder="机器名称" />
          </div>
        </div>
      </el-card>

      <!-- 作业步骤 -->
      <el-card class="steps-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>作业步骤 ({{ rows.length }})</span>
            <div>
              <el-button link type="primary" @click="addRow">新增步骤</el-button>
              <el-button link type="danger" @click="clearRows">清空</el-button>
            </div>
          </div>
        </template>
        <div class="steps-scroll">
          <table class="edit-table">
            <thead>
              <tr>
                <th class="th-seq">序</th>
                <th class="th-time">时间</th>
                <th class="th-desc">人-描述</th>
                <th class="th-state">状态</th>
                <th v-for="m in machines" :key="m.id" class="th-desc">{{ m.name }}-描述</th>
                <th v-for="m in machines" :key="'s'+m.id" class="th-state">状态</th>
                <th class="th-op">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rIdx) in rows" :key="rIdx">
                <td class="td-seq">{{ rIdx + 1 }}</td>
                <td>
                  <el-input-number v-model="row.time" size="small" :min="0" :step="1" :controls="false" style="width:60px" />
                </td>
                <td>
                  <el-input v-model="row.workerDesc" size="small" placeholder="人活动" />
                </td>
                <td>
                  <el-select v-model="row.workerState" size="small" style="width:70px">
                    <el-option label="工作" value="work" />
                    <el-option label="空闲" value="idle" />
                  </el-select>
                </td>
                <td v-for="m in machines" :key="m.id">
                  <el-input v-model="getCell(row, m.id).desc" size="small" placeholder="机器活动" />
                </td>
                <td v-for="m in machines" :key="'s'+m.id">
                  <el-select v-model="getCell(row, m.id).state" size="small" style="width:70px">
                    <el-option label="工作" value="work" />
                    <el-option label="空闲" value="idle" />
                  </el-select>
                </td>
                <td>
                  <el-button link type="danger" :icon="Delete" @click="removeRow(rIdx)" />
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

      <div class="chart-container" ref="chartContainerRef">
        <div class="chart-scroll export-target" ref="exportTargetRef">
          <div class="man-machine-paper">
            <!-- 全部合为一个连续表 -->
            <table class="unified-table">
              <colgroup>
                <col style="width: 60px" />
                <col />
                <col style="width: 40px" />
                <template v-for="m in machines" :key="'cg'+m.id">
                  <col />
                  <col style="width: 40px" />
                </template>
              </colgroup>
              <!-- 标题 -->
              <tr class="title-row">
                <td :colspan="totalCols">人机作业分析图</td>
              </tr>
              <!-- 信息区 -->
              <tr>
                <td class="label-cell">作业名称</td>
                <td :colspan="totalCols - 1">{{ headerInfo.taskName }}</td>
              </tr>
              <tr>
                <td class="label-cell">操作者</td>
                <td>{{ headerInfo.worker }}</td>
                <td class="label-cell">机器</td>
                <td :colspan="Math.max(1, totalCols - 3)">{{ machines.map(m => m.name).join('、') }}</td>
              </tr>
              <tr>
                <td class="label-cell">日期</td>
                <td>{{ headerInfo.date }}</td>
                <td class="label-cell">研究者</td>
                <td :colspan="Math.max(1, totalCols - 3)">{{ headerInfo.analyst }}</td>
              </tr>
              <!-- 表头 -->
              <tr class="thead-row">
                <th class="col-time" rowspan="2">时间</th>
                <th colspan="2">{{ headerInfo.worker || '操作者' }}</th>
                <th v-for="m in machines" :key="m.id" colspan="2">{{ m.name }}</th>
              </tr>
              <tr class="sub-header">
                <th>描述</th>
                <th class="col-bar">状态</th>
                <template v-for="m in machines" :key="m.id">
                  <th>描述</th>
                  <th class="col-bar">状态</th>
                </template>
              </tr>
              <!-- 数据 -->
              <tr v-for="(row, idx) in rows" :key="idx" class="data-row">
                <td class="col-time">{{ cumulativeTime(idx) }}</td>
                <td v-if="shouldRenderWorker(idx)" :rowspan="getWorkerSpan(idx)" class="td-desc">
                  {{ row.workerDesc }}
                </td>
                <td v-if="shouldRenderWorker(idx)" :rowspan="getWorkerSpan(idx)"
                    :class="['td-bar', row.workerState === 'work' ? 'bar-work' : 'bar-idle']"
                    :style="{ height: getWorkerMergedTime(idx) * barScale + 'px' }">
                </td>
                <template v-for="m in machines" :key="m.id">
                  <td v-if="shouldRenderMachine(idx, m.id)" :rowspan="getMachineSpan(idx, m.id)" class="td-desc">
                    {{ getCell(row, m.id).desc }}
                  </td>
                  <td v-if="shouldRenderMachine(idx, m.id)" :rowspan="getMachineSpan(idx, m.id)"
                      :class="['td-bar', getCell(row, m.id).state === 'work' ? 'bar-work' : 'bar-idle']"
                      :style="{ height: getMachineMergedTime(idx, m.id) * barScale + 'px' }">
                  </td>
                </template>
              </tr>
              <!-- 统计汇总 -->
              <tr class="stats-header-row">
                <td :colspan="totalCols" class="stats-title-cell">统计汇总</td>
              </tr>
              <tr class="stats-col-header">
                <th>项目</th>
                <th>周程/s</th>
                <th>工作时间/s</th>
                <th>空闲时间/s</th>
                <th :colspan="Math.max(1, totalCols - 4)">利用率/%</th>
              </tr>
              <tr>
                <td class="label-cell">{{ headerInfo.worker || '操作者' }}</td>
                <td>{{ statsData.cycle }}</td>
                <td>{{ statsData.workerWork }}</td>
                <td>{{ statsData.workerIdle }}</td>
                <td :colspan="Math.max(1, totalCols - 4)"
                    :class="statsData.workerEff >= 80 ? 'eff-good' : 'eff-bad'">{{ statsData.workerEff }}%</td>
              </tr>
              <tr v-for="m in machines" :key="'stat'+m.id">
                <td class="label-cell">{{ m.name }}</td>
                <td>{{ statsData.cycle }}</td>
                <td>{{ statsData.machines[m.id]?.work ?? 0 }}</td>
                <td>{{ statsData.machines[m.id]?.idle ?? 0 }}</td>
                <td :colspan="Math.max(1, totalCols - 4)"
                    :class="(statsData.machines[m.id]?.eff ?? 0) >= 80 ? 'eff-good' : 'eff-bad'">{{ statsData.machines[m.id]?.eff ?? 0 }}%</td>
              </tr>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Download } from '@element-plus/icons-vue'
import ExcelJS from 'exceljs'
import html2canvas from 'html2canvas'

const props = defineProps({
  data: { type: Object, default: null },
  mode: { type: String, default: 'edit' }
})
const emit = defineEmits(['update:data'])

const chartContainerRef = ref(null)
const exportTargetRef = ref(null)
const barScale = 3
const totalCols = computed(() => 1 + 2 + machines.value.length * 2)

const defaultHeader = {
  taskName: '',
  worker: '',
  date: new Date().toISOString().split('T')[0],
  analyst: ''
}

const headerInfo = ref({ ...defaultHeader, ...(props.data?.headerInfo || {}) })

let machineCounter = 0
const makeMachineId = () => `m${++machineCounter}`

const initMachines = () => {
  if (props.data?.machines?.length) {
    const ms = props.data.machines.map(m => ({ ...m }))
    const maxId = ms.reduce((max, m) => {
      const num = parseInt(m.id?.replace('m', '') || '0')
      return num > max ? num : max
    }, 0)
    machineCounter = maxId
    return ms
  }
  return [{ id: makeMachineId(), name: '机器1' }]
}

const machines = ref(initMachines())

const makeEmptyCells = () => {
  const cells = {}
  machines.value.forEach(m => { cells[m.id] = { desc: '', state: 'idle' } })
  return cells
}

const initRows = () => {
  if (props.data?.rows?.length) {
    return props.data.rows.map(r => ({ ...r, cells: { ...r.cells } }))
  }
  return [{ time: 0, workerDesc: '', workerState: 'work', cells: makeEmptyCells() }]
}

const rows = ref(initRows())

function emitData() {
  emit('update:data', {
    headerInfo: { ...headerInfo.value },
    machines: machines.value.map(m => ({ ...m })),
    rows: rows.value.map(r => ({ ...r, cells: { ...r.cells } }))
  })
}

watch([headerInfo, machines, rows], emitData, { deep: true })

const getCell = (row, machineId) => {
  if (!row.cells[machineId]) row.cells[machineId] = { desc: '', state: 'idle' }
  return row.cells[machineId]
}

const addMachine = () => {
  const m = { id: makeMachineId(), name: `机器${machines.value.length + 1}` }
  machines.value.push(m)
  rows.value.forEach(r => { r.cells[m.id] = { desc: '', state: 'idle' } })
}

const removeLastMachine = () => {
  if (machines.value.length <= 1) return
  const removed = machines.value.pop()
  rows.value.forEach(r => { delete r.cells[removed.id] })
}

const addRow = () => {
  rows.value.push({ time: 0, workerDesc: '', workerState: 'work', cells: makeEmptyCells() })
}
const removeRow = (idx) => { rows.value.splice(idx, 1) }
const clearRows = () => { rows.value = [] }

// 累计时间
const cumulativeTime = (idx) => {
  let t = 0
  for (let i = 0; i <= idx; i++) t += rows.value[i].time
  return t
}

// 合并：人描述（含空描述）
const workerMerge = computed(() => {
  const groups = []; let i = 0
  while (i < rows.value.length) {
    const s = rows.value[i]; let span = 1
    while (i + span < rows.value.length) {
      const n = rows.value[i + span]
      if (n.workerDesc === s.workerDesc && n.workerState === s.workerState) span++
      else break
    }
    groups.push({ start: i, span }); i += span
  }
  return groups
})
const shouldRenderWorker = (idx) => workerMerge.value.some(g => g.start === idx)
const getWorkerSpan = (idx) => workerMerge.value.find(g => g.start === idx)?.span || 1
const getWorkerMergedTime = (idx) => {
  const g = workerMerge.value.find(g => g.start === idx)
  if (!g) return rows.value[idx].time
  let t = 0
  for (let i = g.start; i < g.start + g.span; i++) t += rows.value[i].time
  return t
}

// 合并：每台机器描述（含空描述）
const machineMerges = computed(() => {
  const result = {}
  machines.value.forEach(m => {
    const groups = []; let i = 0
    while (i < rows.value.length) {
      const cell = getCell(rows.value[i], m.id); let span = 1
      while (i + span < rows.value.length) {
        const nc = getCell(rows.value[i + span], m.id)
        if (nc.desc === cell.desc && nc.state === cell.state) span++
        else break
      }
      groups.push({ start: i, span }); i += span
    }
    result[m.id] = groups
  })
  return result
})
const shouldRenderMachine = (idx, machineId) => (machineMerges.value[machineId] || []).some(g => g.start === idx)
const getMachineSpan = (idx, machineId) => (machineMerges.value[machineId] || []).find(g => g.start === idx)?.span || 1
const getMachineMergedTime = (idx, machineId) => {
  const groups = machineMerges.value[machineId] || []
  const g = groups.find(g => g.start === idx)
  if (!g) return rows.value[idx].time
  let t = 0
  for (let i = g.start; i < g.start + g.span; i++) t += rows.value[i].time
  return t
}

// 统计
const statsData = computed(() => {
  let cycle = 0, workerWork = 0
  const mWork = {}
  machines.value.forEach(m => { mWork[m.id] = 0 })
  rows.value.forEach(r => {
    cycle += r.time
    if (r.workerState === 'work') workerWork += r.time
    machines.value.forEach(m => {
      if (getCell(r, m.id).state === 'work') mWork[m.id] += r.time
    })
  })
  const ms = {}
  machines.value.forEach(m => {
    const w = mWork[m.id]
    ms[m.id] = { work: w, idle: cycle - w, eff: cycle > 0 ? +((w / cycle) * 100).toFixed(1) : 0 }
  })
  return {
    cycle,
    workerWork,
    workerIdle: cycle - workerWork,
    workerEff: cycle > 0 ? +((workerWork / cycle) * 100).toFixed(1) : 0,
    machines: ms
  }
})

const loadExample = () => {
  machineCounter = 2
  headerInfo.value = { taskName: '钻床钻孔作业', worker: '操作工A', date: '2024-03-20', analyst: '张工' }
  machines.value = [
    { id: 'm1', name: '立式钻床' },
    { id: 'm2', name: '攻丝机' }
  ]
  rows.value = [
    { time: 15, workerDesc: '取工件、装夹到钻床', workerState: 'work',
      cells: { m1: { desc: '空闲', state: 'idle' }, m2: { desc: '自动攻丝', state: 'work' } } },
    { time: 2, workerDesc: '开动钻床', workerState: 'work',
      cells: { m1: { desc: '空闲', state: 'idle' }, m2: { desc: '自动攻丝', state: 'work' } } },
    { time: 30, workerDesc: '空闲（等待钻孔）', workerState: 'idle',
      cells: { m1: { desc: '钻孔加工', state: 'work' }, m2: { desc: '空闲', state: 'idle' } } },
    { time: 10, workerDesc: '停机、卸工件', workerState: 'work',
      cells: { m1: { desc: '空闲', state: 'idle' }, m2: { desc: '空闲', state: 'idle' } } },
    { time: 8, workerDesc: '检验、放置', workerState: 'work',
      cells: { m1: { desc: '空闲', state: 'idle' }, m2: { desc: '空闲', state: 'idle' } } },
  ]
}

// 导出Excel
const exportExcel = async () => {
  try {
    const workbook = new ExcelJS.Workbook()
    const sheet = workbook.addWorksheet('人机作业分析')
    const mCount = machines.value.length
    const totalCols = 1 + 2 + mCount * 2 // time + worker(desc+bar) + machines(desc+bar each)
    const colWidths = [10, 22, 8]
    machines.value.forEach(() => { colWidths.push(22, 8) })
    sheet.columns = colWidths.map(w => ({ width: w }))

    const thin = { style: 'thin', color: { argb: 'FF777777' } }
    const allBorder = { top: thin, left: thin, right: thin, bottom: thin }
    const center = { vertical: 'middle', horizontal: 'center', wrapText: true }

    // 标题
    sheet.mergeCells(1, 1, 1, totalCols)
    sheet.getCell('A1').value = '人机作业分析图'
    sheet.getCell('A1').alignment = center
    sheet.getCell('A1').font = { bold: true, size: 14 }
    sheet.getRow(1).height = 30

    // 信息
    const labelFill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF1F5F9' } }
    // Row 2: 作业名称
    sheet.getCell(2, 1).value = '作业名称'
    sheet.getCell(2, 1).font = { bold: true }
    sheet.getCell(2, 1).fill = labelFill
    if (totalCols > 2) sheet.mergeCells(2, 2, 2, totalCols)
    sheet.getCell(2, 2).value = headerInfo.value.taskName
    // Row 3: 操作者 + 机器
    sheet.getCell(3, 1).value = '操作者'
    sheet.getCell(3, 1).font = { bold: true }
    sheet.getCell(3, 1).fill = labelFill
    sheet.getCell(3, 2).value = headerInfo.value.worker
    sheet.getCell(3, 3).value = '机器'
    sheet.getCell(3, 3).font = { bold: true }
    sheet.getCell(3, 3).fill = labelFill
    if (totalCols > 4) sheet.mergeCells(3, 4, 3, totalCols)
    sheet.getCell(3, 4).value = machines.value.map(m => m.name).join('、')
    // Row 4: 日期 + 研究者
    sheet.getCell(4, 1).value = '日期'
    sheet.getCell(4, 1).font = { bold: true }
    sheet.getCell(4, 1).fill = labelFill
    sheet.getCell(4, 2).value = headerInfo.value.date
    sheet.getCell(4, 3).value = '研究者'
    sheet.getCell(4, 3).font = { bold: true }
    sheet.getCell(4, 3).fill = labelFill
    if (totalCols > 4) sheet.mergeCells(4, 4, 4, totalCols)
    sheet.getCell(4, 4).value = headerInfo.value.analyst
    for (let r = 2; r <= 4; r++) {
      for (let c = 1; c <= totalCols; c++) {
        sheet.getCell(r, c).alignment = center
      }
    }

    // 表头
    sheet.mergeCells(5, 1, 6, 1) // 时间
    sheet.getCell(5, 1).value = '时间'
    sheet.mergeCells(5, 2, 5, 3) // 操作者
    sheet.getCell(5, 2).value = headerInfo.value.worker || '操作者'
    sheet.getCell(6, 2).value = '描述'
    sheet.getCell(6, 3).value = '状态'
    machines.value.forEach((m, mi) => {
      const base = 4 + mi * 2
      sheet.mergeCells(5, base, 5, base + 1)
      sheet.getCell(5, base).value = m.name
      sheet.getCell(6, base).value = '描述'
      sheet.getCell(6, base + 1).value = '状态'
    })
    for (let r = 5; r <= 6; r++) {
      for (let c = 1; c <= totalCols; c++) {
        const cell = sheet.getCell(r, c)
        cell.font = { bold: true }
        cell.alignment = center
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE8E8E8' } }
      }
    }

    // 数据
    const startRow = 7
    rows.value.forEach((row, idx) => {
      const r = startRow + idx
      sheet.getCell(r, 1).value = cumulativeTime(idx)
      sheet.getCell(r, 2).value = row.workerDesc
      // 状态列：只填充颜色，不写数字
      const wFill = row.workerState === 'work' ? 'FFA0A0A0' : 'FFFFFFFF'
      sheet.getCell(r, 3).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: wFill } }
      machines.value.forEach((m, mi) => {
        const base = 4 + mi * 2
        const cell = getCell(row, m.id)
        sheet.getCell(r, base).value = cell.desc
        const mFill = cell.state === 'work' ? 'FFA0A0A0' : 'FFFFFFFF'
        sheet.getCell(r, base + 1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: mFill } }
      })
      sheet.getRow(r).height = 22
      for (let c = 1; c <= totalCols; c++) sheet.getCell(r, c).alignment = center
    })

    const lastDataRow = startRow + Math.max(rows.value.length, 1) - 1

    // 合并描述列
    for (const g of workerMerge.value) {
      if (g.span > 1) {
        const s = startRow + g.start, e = s + g.span - 1
        sheet.mergeCells(s, 2, e, 2)
      }
    }
    machines.value.forEach((m, mi) => {
      const col = 4 + mi * 2
      const groups = machineMerges.value[m.id] || []
      for (const g of groups) {
        if (g.span > 1) {
          const s = startRow + g.start, e = s + g.span - 1
          sheet.mergeCells(s, col, e, col)
        }
      }
    })

    // 合并状态列（连续相同状态合并）
    const mergeStateCol = (colIdx, getState) => {
      let i = 0
      while (i < rows.value.length) {
        const state = getState(i); let span = 1
        while (i + span < rows.value.length && getState(i + span) === state) span++
        if (span > 1) {
          const s = startRow + i, e = s + span - 1
          sheet.mergeCells(s, colIdx, e, colIdx)
        }
        i += span
      }
    }
    mergeStateCol(3, (i) => rows.value[i].workerState)
    machines.value.forEach((m, mi) => {
      mergeStateCol(5 + mi * 2, (i) => getCell(rows.value[i], m.id).state)
    })

    // 统计
    const sr = lastDataRow + 1
    sheet.mergeCells(sr, 1, sr, totalCols)
    sheet.getCell(sr, 1).value = '统计汇总'
    sheet.getCell(sr, 1).font = { bold: true, size: 12 }
    sheet.getCell(sr, 1).alignment = center

    const hr = sr + 1
    const heads = ['项目', '周程/s', '工作时间/s', '空闲时间/s', '利用率/%']
    heads.forEach((h, i) => {
      sheet.getCell(hr, i + 1).value = h
      sheet.getCell(hr, i + 1).font = { bold: true }
      sheet.getCell(hr, i + 1).alignment = center
      sheet.getCell(hr, i + 1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE8E8E8' } }
    })
    if (totalCols > 5) sheet.mergeCells(hr, 5, hr, totalCols)

    const ss = statsData.value
    const writeRow = (row, label, work, idle, eff) => {
      sheet.getCell(row, 1).value = label
      sheet.getCell(row, 1).font = { bold: true }
      sheet.getCell(row, 2).value = ss.cycle
      sheet.getCell(row, 3).value = work
      sheet.getCell(row, 4).value = idle
      sheet.getCell(row, 5).value = `${eff}%`
      sheet.getCell(row, 5).font = { bold: true, color: { argb: eff >= 80 ? 'FF16A34A' : 'FFDC2626' } }
      for (let c = 1; c <= Math.max(5, totalCols); c++) sheet.getCell(row, c).alignment = center
      if (totalCols > 5) sheet.mergeCells(row, 5, row, totalCols)
    }
    writeRow(hr + 1, headerInfo.value.worker || '操作者', ss.workerWork, ss.workerIdle, ss.workerEff)
    machines.value.forEach((m, mi) => {
      const md = ss.machines[m.id]
      writeRow(hr + 2 + mi, m.name, md?.work ?? 0, md?.idle ?? 0, md?.eff ?? 0)
    })

    const totalLastRow = hr + 1 + machines.value.length
    for (let r = 1; r <= totalLastRow; r++) {
      for (let c = 1; c <= totalCols; c++) {
        const cell = sheet.getCell(r, c)
        cell.border = allBorder
        if (!cell.alignment) cell.alignment = center
      }
    }

    const buffer = await workbook.xlsx.writeBuffer()
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `人机作业分析_${headerInfo.value.taskName || '导出'}.xlsx`
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
    link.download = `人机作业分析_${headerInfo.value.taskName || '导出'}.png`
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
.man-machine-container {
  display: flex;
  height: 100%;
  gap: 16px;
  overflow: hidden;
}

.man-machine-container.preview-mode {
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
  width: 520px;
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
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.machines-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.machine-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.col-index {
  font-weight: 600;
  color: #666;
  width: 20px;
  flex-shrink: 0;
}

.steps-scroll {
  overflow-x: auto;
}
.edit-table {
  border-collapse: collapse;
  font-size: 12px;
  width: 100%;
  th, td {
    border: 1px solid #ddd;
    padding: 4px 6px;
    text-align: center;
    white-space: nowrap;
  }
  th {
    background: #f5f5f5;
    font-weight: 600;
    font-size: 11px;
  }
  .th-seq { width: 30px; }
  .th-time { width: 60px; }
  .th-state { width: 70px; }
  .th-desc { min-width: 100px; }
  .th-op { width: 40px; }
  .td-seq { color: #999; }
}

.action-bar {
  display: flex;
  gap: 8px;
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

.man-machine-paper {
  background: #fff;
  padding: 32px 28px;
  min-width: 500px;
  font-size: 13px;
  color: #333;
}

.unified-table {
  width: 100%;
  border-collapse: collapse;

  th, td {
    border: 1px solid #999;
    padding: 4px 8px;
    text-align: center;
    font-size: 13px;
    vertical-align: middle;
  }

  .title-row td {
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 10px;
  }

  .label-cell {
    background: #f1f5f9;
    font-weight: 600;
    width: 80px;
  }

  .thead-row th {
    background: #e8e8e8;
    font-weight: 700;
    padding: 6px 8px;
  }

  .sub-header th {
    font-weight: 600;
    font-size: 12px;
    background: #f0f0f0;
    padding: 4px 6px;
  }

  .col-time {
    width: 50px;
    padding: 4px;
    font-size: 12px;
  }

  .col-bar {
    width: 30px;
  }

  .td-desc {
    text-align: left;
    padding: 4px 8px;
    min-width: 100px;
  }

  .td-bar {
    padding: 0;
    min-height: 10px;
  }

  .bar-work {
    background: #a0a0a0;
  }

  .bar-idle {
    background: #fff;
  }

  .data-row td {
    vertical-align: middle;
  }

  .stats-title-cell {
    font-weight: 700;
    font-size: 14px;
    background: #f8fafc;
    padding: 6px 10px;
  }

  .stats-col-header th {
    background: #e8e8e8;
    font-weight: 700;
    padding: 6px 10px;
  }

  .stats-header-row td {
    font-weight: 700;
    font-size: 14px;
    background: #f8fafc;
    padding: 6px 10px;
  }

  .eff-good {
    color: #16a34a;
    font-weight: 700;
  }

  .eff-bad {
    color: #dc2626;
    font-weight: 700;
  }
}
</style>
