<script setup lang="ts">
/** 工序录入：两种来源（导入 Excel / 视频分析）→ 行内编辑 + 删除。两条路最终都落到 addProcesses。 */
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import lb, { type Process } from '@/api/lineBalance'
import VideoAnalysisTab from './VideoAnalysisTab.vue'
import { useUserStore } from '@/stores/user'

const props = defineProps<{ styleId: number }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

// 视频分析尚未完善，仅管理员可见；普通用户只走「导入 Excel」。
const isAdmin = computed(() => useUserStore().userInfo?.role === 'admin')

const list = ref<Process[]>([])
const loading = ref(false)
const importing = ref(false)
const importReplace = ref(false)
const source = ref<'excel' | 'video'>('excel')

/** 列别名 → 字段。表头自动识别用，全部转小写后比对。 */
const COLUMN_ALIASES: Record<keyof ImportRow, string[]> = {
  originalCode: ['原始码', '工序码', '工序号', '编码', 'code', 'originalcode'],
  originalUpstream: ['上游码', '上游', '前序', '前置工序', 'upstream', 'originalupstream'],
  processName: ['工序名称', '名称', '工序', 'name', 'processname'],
  actualTime: ['实际时间', '实测时间', '观测时间', '实际工时', 'actual', 'actualtime'],
  relaxRate: ['放宽率', '宽放率', '宽放', 'relax', 'relaxrate', 'allowance'],
  ratingFactor: ['评定系数', '评比系数', '评定', 'rating', 'ratingfactor', 'rating系数'],
  sam: ['sam', 'sam(s)', '标准工时', '标准时间'],
  machineType: ['机器类型', '机器', '设备', 'machine', 'machinetype'],
  workerMachine: ['人机', '人机类型', 'worker', 'workermachine'],
}

type ImportRow = {
  originalCode: string
  originalUpstream: string | null
  processName: string
  actualTime: number | null
  relaxRate: number
  ratingFactor: number
  sam: number | null
  machineType: string | null
  workerMachine: string | null
}

async function load() {
  loading.value = true
  try {
    const data = await lb.listProcesses(props.styleId)
    list.value = data.list || []
  } finally {
    loading.value = false
  }
}

/** 根据表头文本匹配各字段所在列索引；无表头时返回 null（走位置兜底）。 */
function detectColumns(headers: string[]): Record<keyof ImportRow, number> | null {
  const norm = headers.map((h) => String(h ?? '').trim().toLowerCase())
  const idx = {} as Record<keyof ImportRow, number>
  let matched = 0
  for (const field of Object.keys(COLUMN_ALIASES) as (keyof ImportRow)[]) {
    const aliases = COLUMN_ALIASES[field]
    const found = norm.findIndex((h) => h && aliases.includes(h))
    idx[field] = found
    if (found >= 0) matched++
  }
  // 至少识别到「原始码 + SAM」才认为这是带表头的数据
  return matched >= 2 && idx.originalCode >= 0 ? idx : null
}

function cell(row: any[], i: number): string {
  if (i < 0) return ''
  const v = row[i]
  return v === null || v === undefined ? '' : String(v).trim()
}

function buildRows(rows: any[][]): ImportRow[] {
  if (!rows.length) return []
  const map = detectColumns(rows[0].map((v) => String(v ?? '')))
  // 有表头则跳过首行并按识别列取值；无表头按固定列序
  const dataRows = map ? rows.slice(1) : rows
  const col: Record<keyof ImportRow, number> = map ?? {
    originalCode: 0, originalUpstream: 1, processName: 2,
    actualTime: 3, relaxRate: 4, ratingFactor: 5, sam: 6,
    machineType: 7, workerMachine: 8,
  }
  const num = (r: any[], i: number): number | null => {
    const s = cell(r, i)
    if (s === '') return null
    const n = Number(s)
    return Number.isFinite(n) ? n : null
  }
  const out: ImportRow[] = []
  for (const r of dataRows) {
    const originalCode = cell(r, col.originalCode)
    if (!originalCode) continue
    out.push({
      originalCode,
      originalUpstream: cell(r, col.originalUpstream) || null,
      processName: cell(r, col.processName) || originalCode,
      actualTime: num(r, col.actualTime),
      relaxRate: num(r, col.relaxRate) ?? 0,
      ratingFactor: num(r, col.ratingFactor) ?? 1,
      sam: num(r, col.sam),
      machineType: cell(r, col.machineType) || null,
      workerMachine: cell(r, col.workerMachine) || null,
    })
  }
  return out
}

async function onFileChange(file: UploadFile) {
  const raw = file.raw
  if (!raw) return
  importing.value = true
  try {
    const ExcelJS = await import('exceljs')
    const workbook = new ExcelJS.Workbook()
    await workbook.xlsx.load(await raw.arrayBuffer())
    const sheet = workbook.worksheets[0]
    if (!sheet) { ElMessage.warning('Excel 文件中没有工作表'); return }

    const rows: any[][] = []
    sheet.eachRow((row) => {
      const values = Array.isArray(row.values) ? row.values.slice(1) : []
      if (values.some((v) => v !== null && v !== undefined && String(v).trim() !== '')) rows.push(values)
    })

    const parsed = buildRows(rows)
    if (!parsed.length) { ElMessage.warning('未解析到有效工序行，请检查文件内容'); return }

    const res = await lb.addProcesses(props.styleId, parsed, importReplace.value)
    ElMessage.success(`已导入 ${res.count} 道工序`)
    await load()
    emit('changed')
  } catch (e: any) {
    ElMessage.error(e?.message || 'Excel 导入失败')
  } finally {
    importing.value = false
  }
}

async function downloadSample() {
  const ExcelJS = await import('exceljs')
  const workbook = new ExcelJS.Workbook()
  const sheet = workbook.addWorksheet('工序清单')
  sheet.addRow(['原始码', '上游码', '工序名称', '实际时间', '放宽率', '评定系数', '机器类型', '人机'])
  // 实际时间(s) / 放宽率(0~1，如0.13=13%) / 评定系数(如1.05)；标准时间 = 实际×评定×(1+放宽)，由系统自动算
  const sample: (string | number)[][] = [
    ['10', '', '底盘上线', 30, 0.13, 1.0, '装配台', '人'],
    ['20', '10', '前车轮加工', 77.5, 0.13, 1.05, '装配台', '人'],
    ['30', '10', '后车轮加工', 75, 0.13, 1.0, '装配台', '人'],
    ['40', '20,30', '车架合装', 40, 0.1, 1.0, '装配台', '人'],
    ['50', '40', '水罐安装', 35, 0.15, 0.95, '吊装设备', '机'],
    ['60', '50', '整车检测', 28, 0.1, 1.0, '检测台', '人'],
  ]
  sample.forEach((r) => sheet.addRow(r))
  ;[12, 12, 16, 10, 8, 8, 12, 8].forEach((w, i) => { sheet.getColumn(i + 1).width = w })
  sheet.getRow(1).font = { bold: true }

  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '工序导入示例.xlsx'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function saveRow(row: Process) {
  try {
    await lb.updateProcess(row.id, {
      originalCode: row.originalCode,
      originalUpstream: row.originalUpstream,
      processName: row.processName,
      actualTime: row.actualTime,
      relaxRate: row.relaxRate,
      ratingFactor: row.ratingFactor,
      machineType: row.machineType,
      workerMachine: row.workerMachine,
      canMerge: row.canMerge,
    })
    ElMessage.success('已保存')
    emit('changed')
  } catch { /* */ }
}

/** 标准时间预览：实际×评定×(1+放宽)；无实际时间时回退已有 sam。 */
function previewSam(row: Process): number {
  if (row.actualTime != null) {
    const r = Number(row.actualTime) * Number(row.ratingFactor ?? 1) * (1 + Number(row.relaxRate ?? 0))
    return Math.round(r * 100) / 100
  }
  return row.sam ?? 0
}

async function delRow(row: Process) {
  await ElMessageBox.confirm(`删除工序 ${row.originalCode}？`, '确认', { type: 'warning' })
  await lb.deleteProcess(row.id)
  await load()
  emit('changed')
}

/** 视频分析生成工序后刷新列表并通知上层（同 Excel 导入）。 */
async function onVideoGenerated() {
  await load()
  emit('changed')
}

onMounted(load)
// 切换款式时工序面板不会卸载，需手动重载，避免显示上一个款式的工序。
watch(() => props.styleId, () => { source.value = 'excel'; load() })
defineExpose({ reload: load })
</script>

<template>
  <div>
    <el-radio-group v-model="source" style="margin-bottom:12px">
      <el-radio-button label="excel">导入 Excel</el-radio-button>
      <el-radio-button v-if="isAdmin" label="video">视频分析</el-radio-button>
    </el-radio-group>

    <template v-if="source === 'excel'">
      <div style="display:flex;gap:8px;margin-bottom:12px;align-items:center;flex-wrap:wrap">
        <el-upload :auto-upload="false" :show-file-list="false" accept=".xlsx,.xls" :on-change="onFileChange">
          <el-button type="primary" :loading="importing">导入 Excel</el-button>
        </el-upload>
        <el-button @click="downloadSample">下载示例 Excel</el-button>
        <el-checkbox v-model="importReplace">替换现有工序</el-checkbox>
        <el-button @click="load" :loading="loading">刷新</el-button>
        <span style="margin-left:auto;color:#64748b;align-self:center">共 {{ list.length }} 道工序</span>
      </div>

      <el-alert type="info" :closable="false" style="margin-bottom:12px">
        上传 Excel 自动识别表头（<b>原始码 / 上游码 / 工序名称 / 实际时间 / 放宽率 / 评定系数 / 机器类型 / 人机</b>，列顺序任意）。
        <b>标准时间 = 实际时间 × 评定系数 ×(1 + 放宽率)</b>，由系统自动计算，后续编码与平衡寻优均按标准时间。
        放宽率填 0~1（如 0.13 表示 13%），评定系数如 1.05。上游码为前序工序的原始码，支持 DAG：多个上游用逗号分隔（汇合），同一上游可被多道工序引用（分叉），首道工序留空。点「下载示例 Excel」获取模板。
      </el-alert>
    </template>

    <VideoAnalysisTab
      v-else :style-id="props.styleId" @generated="onVideoGenerated"
      style="margin-bottom:16px"
    />

    <el-table :data="list" border size="small" v-loading="loading" empty-text="暂无工序，导入 Excel 或用视频分析生成">
      <el-table-column label="原始码" width="100">
        <template #default="{ row }"><el-input v-model="row.originalCode" size="small" /></template>
      </el-table-column>
      <el-table-column label="上游码" width="120">
        <template #default="{ row }"><el-input v-model="row.originalUpstream" size="small" placeholder="逗号分隔" /></template>
      </el-table-column>
      <el-table-column label="工序名称" min-width="140">
        <template #default="{ row }"><el-input v-model="row.processName" size="small" /></template>
      </el-table-column>
      <el-table-column label="实际时间(s)" width="110">
        <template #default="{ row }"><el-input-number v-model="row.actualTime" :min="0" :step="0.1" size="small" controls-position="right" style="width:100px" /></template>
      </el-table-column>
      <el-table-column label="放宽率" width="100">
        <template #default="{ row }"><el-input-number v-model="row.relaxRate" :min="0" :max="1" :step="0.01" :precision="2" size="small" controls-position="right" style="width:90px" /></template>
      </el-table-column>
      <el-table-column label="评定系数" width="100">
        <template #default="{ row }"><el-input-number v-model="row.ratingFactor" :min="0" :step="0.01" :precision="2" size="small" controls-position="right" style="width:90px" /></template>
      </el-table-column>
      <el-table-column label="标准时间(s)" width="100" align="center">
        <template #default="{ row }"><span style="font-weight:600;color:#0f172a">{{ previewSam(row) }}</span></template>
      </el-table-column>
      <el-table-column label="机器类型" width="120">
        <template #default="{ row }"><el-input v-model="row.machineType" size="small" /></template>
      </el-table-column>
      <el-table-column label="可合并" width="70" align="center">
        <template #default="{ row }"><el-switch v-model="row.canMerge" size="small" /></template>
      </el-table-column>
      <el-table-column label="操作" width="120" align="center">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="saveRow(row)">保存</el-button>
          <el-button link type="danger" size="small" @click="delRow(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
