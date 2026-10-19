<script setup lang="ts">
import { ref, watch, onMounted, shallowRef, onUnmounted, nextTick, computed } from 'vue'
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router'
import request from '@/api/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'

const router = useRouter()
const route = useRoute()
const chartId = ref(route.params.chartId || '')
const chart = ref<any>(null)
const engine = ref('')
const activeTab = ref('data')
const dirty = ref(false)
const loaded = ref(false)

// ECharts
const chartRef = ref<HTMLDivElement>()
let chartInstance: any = null

// Chart config
const ct = ref('bar')
const titleTxt = ref('图表标题')
const showTitle = ref(true)
const showLegend = ref(true)
const showGrid = ref(true)
const showLabels = ref(false)
const themeIdx = ref(0)
const data = ref<any[]>([{ cat: 'Q1', v1: 280, v2: 180 }, { cat: 'Q2', v1: 420, v2: 260 }, { cat: 'Q3', v1: 350, v2: 310 }, { cat: 'Q4', v1: 510, v2: 380 }])

const themes = [['#3b82f6','#8b5cf6','#f59e0b','#10b981'],['#0ea5e9','#f43f5e','#a855f7','#14b8a6'],['#6366f1','#ec4899','#f97316','#06b6d4'],['#1d4ed8','#7c3aed','#dc2626','#059669']]

// vue-component engine
const DynamicComponent = shallowRef<any>(null)
const compData = ref<any>(null)
const compRef = ref<any>(null)

// style selection
const selectedStyle = ref<string | null>(null)
const templateStyles = ref<any[]>([])
const componentModules = import.meta.glob('../../../../../chart-templates/**/*.vue')

// matplotlib engine
const previewImage = ref('')
const summaryData = ref<Record<string, any> | null>(null)
const templateConfig = ref<any>(null)
const formParams = ref<Record<string, any>>({})
const generating = ref(false)
const excelFileNames = ref<Record<string, string>>({})
let debounceTimer: ReturnType<typeof setTimeout> | null = null

const CHART_META_KEYS = ['_style', '_componentFile'] as const
const IMAGE_EXPORT_HIDDEN_TEMPLATE_IDS = new Set([
  'process-flow',
  'man-machine',
  'therblig',
  'joint-operation',
  'two-hand',
])

const hideImageExport = computed(() => IMAGE_EXPORT_HIDDEN_TEMPLATE_IDS.has(chart.value?.templateId))
const excelExample = computed(() => templateConfig.value?.config?.excelExample || null)

function mergePersistedChartMeta(payload: Record<string, any>, prev: Record<string, any> | null | undefined) {
  const out = { ...payload }
  const base = prev || {}
  for (const k of CHART_META_KEYS) {
    if (base[k] !== undefined && out[k] === undefined) (out as any)[k] = base[k]
  }
  return out
}

async function loadVueComponentByFile(componentFile?: string | null, templateId?: string) {
  const keys = Object.keys(componentModules)
  let compKey: string | undefined
  if (componentFile) {
    compKey = keys.find(k => k.endsWith('/' + componentFile))
  }
  if (!compKey && templateId) {
    compKey = keys.find(k => k.includes(`/${templateId}/`))
  }
  if (compKey) {
    const mod = await componentModules[compKey]()
    DynamicComponent.value = (mod as any).default
  }
}

async function selectStyleInEditor(styleId: string) {
  selectedStyle.value = styleId
  const style = templateStyles.value.find(s => s.id === styleId)
  if (style?.component) {
    if (!compData.value) compData.value = chart.value?.chartData ? { ...chart.value.chartData } : {}
    compData.value._style = styleId
    compData.value._componentFile = style.component
    await loadVueComponentByFile(style.component)
  }
  await nextTick()
  loaded.value = true
}

function updateChart() {
  if (!chartRef.value) return
  if (!chartInstance) chartInstance = echarts.init(chartRef.value)

  const colors = themes[themeIdx.value]
  const tp = ct.value === 'pie' ? 'pie' : ct.value

  const option: any = {
    title: { show: showTitle.value, text: titleTxt.value, left: 'center', textStyle: { fontSize: 18, fontWeight: 600 } },
    tooltip: { trigger: tp === 'pie' ? 'item' : 'axis' },
    legend: { show: showLegend.value, bottom: 0 },
    grid: { show: showGrid.value, left: 40, right: 20, bottom: 50, top: 60 },
    xAxis: tp === 'pie' ? undefined : { type: 'category', data: data.value.map(d => d.cat), axisLabel: { fontSize: 12 } },
    yAxis: tp === 'pie' ? undefined : { type: 'value', splitLine: { show: showGrid.value } },
    series: tp === 'pie' ? [{
      type: 'pie', radius: '60%', data: data.value.map(d => ({ name: d.cat, value: d.v1 })),
      label: { show: showLabels.value, formatter: '{b}: {c}' },
      itemStyle: { borderRadius: 4 }
    }] : [
      { type: tp, name: '系列1', data: data.value.map(d => d.v1), itemStyle: { color: colors[0] }, smooth: true, areaStyle: tp === 'line' ? { color: colors[0] + '22' } : undefined },
      { type: tp, name: '系列2', data: data.value.map(d => d.v2), itemStyle: { color: colors[1] }, smooth: true, areaStyle: tp === 'line' ? { color: colors[1] + '22' } : undefined },
    ]
  }
  chartInstance.setOption(option)
}

function resizeChart() {
  chartInstance?.resize()
}

onMounted(async () => {
  if (!chartId.value) return

  const c = await request.get(`/charts/${chartId.value}`)
  chart.value = c
  engine.value = c.engine

  if (c.engine === 'drawio') {
    router.replace(`/drawio-editor/${chartId.value}`)
    return
  }

  if (c.engine === 'vue-component') {
    try {
      const tpl = await request.get(`/templates/${c.templateId}`)
      const styles = tpl.config?.styles || []
      templateStyles.value = styles

      const savedComponentFile = c.chartData?._componentFile
      const savedStyle = c.chartData?._style

      if (savedComponentFile) {
        selectedStyle.value = savedStyle || 'unknown'
        compData.value = c.chartData || {}
        await loadVueComponentByFile(savedComponentFile)
      } else if (styles.length > 0) {
        const fallbackStyle = styles.find((s: any) => s.id === savedStyle) || styles[0]
        selectedStyle.value = fallbackStyle?.id || null
        compData.value = {
          ...(c.chartData || {}),
          ...(fallbackStyle?.id ? { _style: fallbackStyle.id } : {}),
          ...(fallbackStyle?.component ? { _componentFile: fallbackStyle.component } : {}),
        }
        await loadVueComponentByFile(fallbackStyle?.component)
      } else {
        compData.value = c.chartData || {}
        await loadVueComponentByFile(null, c.templateId)
      }
    } catch {
      // fallback
    }
  } else if (c.engine === 'matplotlib') {
    previewImage.value = c.chartData?.image_base64 || ''
    if (c.chartData?.params) {
      formParams.value = JSON.parse(JSON.stringify(c.chartData.params))
    }
    try {
      const tpl = await request.get(`/templates/${c.templateId}`)
      templateConfig.value = tpl
      const schema = tpl.config?.paramSchema || {}
      for (const [key, field] of Object.entries<any>(schema)) {
        if (formParams.value[key] === undefined) {
          if (Object.prototype.hasOwnProperty.call(field, 'default')) {
            formParams.value[key] = JSON.parse(JSON.stringify(field.default))
          } else if (
            isFieldType(field, 'string-list')
            || isFieldType(field, 'number-list')
            || isFieldType(field, 'matrix')
            || isFieldType(field, 'hidden')
          ) {
            formParams.value[key] = []
          } else {
            formParams.value[key] = ''
          }
        }
      }
      normalizeAllMatrixParams()
    } catch {}
    if (Object.keys(formParams.value).length) {
      try {
        const initResult = await request.post('/charts/generate', { templateId: c.templateId, params: formParams.value })
        previewImage.value = initResult.image_base64
        summaryData.value = initResult.summary || null
      } catch {}
    }
  } else {
    updateChart()
  }

  await nextTick()
  loaded.value = true
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  chartInstance?.dispose()
  if (debounceTimer) clearTimeout(debounceTimer)
})

// dirty tracking
watch(compData, () => { if (loaded.value) dirty.value = true }, { deep: true })
watch(formParams, () => {
  if (!loaded.value) return
  dirty.value = true
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => regenerateMatplotlib(), 800)
}, { deep: true })

async function saveChart(silent = false) {
  if (!chart.value?.id) return
  if (debounceTimer) { clearTimeout(debounceTimer); debounceTimer = null }
  if (generating.value) await new Promise<void>(r => { const check = () => { if (!generating.value) r(); else setTimeout(check, 100) }; check() })
  let chartData = compData.value || chart.value.chartData
  if (engine.value === 'vue-component' && chartData && typeof chartData === 'object') {
    chartData = mergePersistedChartMeta(chartData, chart.value?.chartData)
  }
  if (engine.value === 'matplotlib') {
    chartData = { params: formParams.value, image_base64: previewImage.value }
  }
  await request.put(`/charts/${chart.value.id}`, {
    title: chart.value.title,
    chartData
  }, { _silent: silent } as any)
  dirty.value = false
  if (!silent) ElMessage.success('已保存')
}

function onCompDataUpdate(d: any) {
  compData.value = mergePersistedChartMeta(d, compData.value || chart.value?.chartData)
}

async function exportImage() {
  // 优先使用 vue-component 模板自带的 exportImage:保证组件特有的 overlay(如流程图红色连线)
  // 以及宽表/内嵌图片等细节能够被正确捕获,避免通用 html2canvas 路径漏内容。
  if (DynamicComponent.value && typeof compRef.value?.exportImage === 'function') {
    return compRef.value.exportImage()
  }

  const link = document.createElement('a')
  if (previewImage.value) {
    link.href = previewImage.value
  } else if (DynamicComponent.value) {
    // fallback:组件未实现 exportImage 时的兜底路径
    const rawTarget = compRef.value?.exportTargetRef
    const target = rawTarget?.value ?? rawTarget
    if (target) {
      const { default: html2canvas } = await import('html2canvas')
      const canvas = await html2canvas(target, { useCORS: true, scale: 2, backgroundColor: '#fff' })
      link.href = canvas.toDataURL('image/png')
    }
  } else if (chartRef.value) {
    const canvas = chartRef.value.querySelector('canvas')
    link.href = canvas?.toDataURL('image/png') || ''
  }
  if (!link.href) { ElMessage.warning('无法导出图片'); return }
  link.download = `${chart.value?.title || '图表'}.png`
  link.click()
}

function exportExcel() {
  compRef.value?.exportExcel?.()
}

function exportCode() {
  const optionJson = JSON.stringify(chartInstance?.getOption() || {}, null, 2)
  const code = `<!DOCTYPE html><html><head><script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"><\/script></head><body><div id="chart" style="width:800px;height:500px"></div><script>var chart=echarts.init(document.getElementById('chart'));chart.setOption(${optionJson});<\/script></body></html>`
  const blob = new Blob([code], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `${chart.value?.title || '图表'}.html`; a.click()
  URL.revokeObjectURL(url)
}

async function regenerateMatplotlib() {
  if (!chart.value?.templateId || generating.value) return
  generating.value = true
  try {
    normalizeAllMatrixParams()
    const result = await request.post('/charts/generate', {
      templateId: chart.value.templateId,
      params: formParams.value
    })
    previewImage.value = result.image_base64
    summaryData.value = result.summary || null
  } catch {
    // silent on auto-regenerate
  }
  generating.value = false
}

function addListItem(key: string, type?: string) {
  if (!formParams.value[key]) formParams.value[key] = []
  formParams.value[key].push(type === 'number-list' ? 0 : '')
}

function removeListItem(key: string, idx: number) {
  formParams.value[key].splice(idx, 1)
}

function isFieldType(fieldConfig: any, type: string): boolean {
  return String(fieldConfig?.type || '').trim().toLowerCase() === type
}

function getMatrixRows(fieldConfig: any): string[] {
  const src = fieldConfig.rowsFrom
  if (!src) return []
  const v = formParams.value[src]
  return Array.isArray(v) ? v.filter((s: any) => String(s).trim()) : []
}

function getMatrixCols(fieldConfig: any): string[] {
  const src = fieldConfig.colsFrom
  if (!src) return []
  const v = formParams.value[src]
  return Array.isArray(v) ? v.filter((s: any) => String(s).trim()) : []
}

function getMatrixCell(key: string, ri: number, ci: number): number {
  const m = formParams.value[key]
  if (!Array.isArray(m) || !Array.isArray(m[ri])) return 0
  return typeof m[ri][ci] === 'number' ? m[ri][ci] : 0
}

function setMatrixCell(key: string, ri: number, ci: number, val: number | undefined) {
  if (!Array.isArray(formParams.value[key])) formParams.value[key] = []
  const m = formParams.value[key] as number[][]
  while (m.length <= ri) m.push([])
  while (m[ri].length <= ci) m[ri].push(0)
  m[ri][ci] = val ?? 0
}

function normalizeMatrixParam(key: string, fieldConfig: any) {
  const rows = getMatrixRows(fieldConfig)
  const cols = getMatrixCols(fieldConfig)
  const rowCount = rows.length
  const colCount = cols.length
  if (!rowCount || !colCount) return

  const raw = formParams.value[key]
  if (
    Array.isArray(raw)
    && raw.length === rowCount
    && raw.length > 0
    && Array.isArray((raw as any[])[0])
    && raw.every(r => Array.isArray(r) && r.length === colCount)
  ) {
    formParams.value[key] = (raw as any[][]).map((row: any[]) => row.map(v => Number(v) || 0))
    return
  }

  const parsed = parseMatrixValue(formParams.value[key], rowCount, colCount)
  const normalized = Array.from({ length: rowCount }, (_, ri) =>
    Array.from({ length: colCount }, (_, ci) => parsed[ri]?.[ci] ?? 0)
  )
  formParams.value[key] = normalized
}

function normalizeAllMatrixParams() {
  const schema = templateConfig.value?.config?.paramSchema || {}
  for (const [key, field] of Object.entries<any>(schema)) {
    if (isFieldType(field, 'matrix')) normalizeMatrixParam(key, field)
  }
}

async function handleExcelUpload(event: Event, fieldConfig: any, key: string) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  try {
    const ExcelJS = await import('exceljs')
    const workbook = new ExcelJS.Workbook()
    await workbook.xlsx.load(await file.arrayBuffer())
    const sheet = workbook.worksheets[0]
    if (!sheet) {
      ElMessage.warning('Excel 文件中没有工作表')
      return
    }

    const rows: any[][] = []
    sheet.eachRow(row => {
      const values = Array.isArray(row.values) ? row.values.slice(1) : []
      if (values.some(v => v !== null && v !== undefined && String(v).trim() !== '')) rows.push(values)
    })
    if (rows.length < 2) {
      ElMessage.warning('Excel 至少需要表头和一行数据')
      return
    }

    const headers = rows[0].map(v => String(v ?? '').trim())
    const mappings = Array.isArray(fieldConfig.mappings) ? fieldConfig.mappings : []
    let matrixImported = false
    for (const mapping of mappings) {
      const target = mapping.target
      const mode = String(mapping.mode || '').trim().toLowerCase()
      if (mode === 'matrix') {
        matrixImported = true
        const stationHeader = String(mapping.stationColumn || mapping.rowKeyColumn || '气象站').trim()
        const monthHeaders: string[] = Array.isArray(mapping.monthColumns)
          ? mapping.monthColumns.map((h: string) => String(h).trim())
          : []
        const stationCol = Math.max(0, headers.indexOf(stationHeader) >= 0 ? headers.indexOf(stationHeader) : Number(mapping.stationIndex ?? 0))
        const colIdxs = monthHeaders.map(h => Math.max(0, headers.indexOf(h) >= 0 ? headers.indexOf(h) : -1)).filter(i => i >= 0)

        let useIdxs = colIdxs
        if (!useIdxs.length) {
          const startCol = Number(mapping.valueStartColumn ?? stationCol + 1)
          const count = Number(mapping.monthCount ?? Math.max(0, headers.length - startCol))
          useIdxs = Array.from({ length: Math.min(count, Math.max(0, headers.length - startCol)) }, (_, k) => startCol + k)
        }

        const rowNames: string[] = []
        const body: number[][] = []
        for (const row of rows.slice(1)) {
          const station = String(row[stationCol] ?? '').trim()
          if (!station) continue
          rowNames.push(station)
          const nums = useIdxs.map(ci => Number(row[ci])).filter(value => Number.isFinite(value))
          if (nums.length !== useIdxs.length) continue
          body.push(nums)
        }

        if (rowNames.length === 0 || body.length !== rowNames.length) {
          ElMessage.warning('未识别到热力图矩阵数据，请确认表头包含气象站与各月份列')
          continue
        }

        formParams.value[mapping.rowsTarget || 'row_labels'] = rowNames
        formParams.value[mapping.colsTarget || 'column_labels'] = useIdxs.map(i => String(headers[i] ?? '').trim()).filter(Boolean)
        formParams.value[target] = body
        continue
      }

      const column = String(mapping.column || '').trim()
      const fallbackIndex = Number(mapping.index ?? 0)
      const columnIndex = Math.max(0, headers.indexOf(column) >= 0 ? headers.indexOf(column) : fallbackIndex)
      formParams.value[target] = rows
        .slice(1)
        .map(row => Number(row[columnIndex]))
        .filter(value => Number.isFinite(value))
    }

    // 整块矩阵已在上面写好，勿再 normalize，避免色阶/数值错乱
    if (!matrixImported) {
      normalizeAllMatrixParams()
    }

    excelFileNames.value[key] = file.name
    ElMessage.success(`已导入 ${file.name}`)
  } catch (e: any) {
    ElMessage.error(e.message || 'Excel 导入失败')
  }
}

async function downloadExcelExample() {
  const config = excelExample.value
  if (!config) return

  const ExcelJS = await import('exceljs')
  const workbook = new ExcelJS.Workbook()
  const sheet = workbook.addWorksheet(config.sheetName || '示例数据')
  const columns = Array.isArray(config.columns) ? config.columns : []
  sheet.addRow(columns)
  ;(config.rows || []).forEach((row: any[]) => sheet.addRow(row))
  const colCount = columns.length || Math.max(...(config.rows || []).map((r: any[]) => r.length), 0)
  for (let i = 1; i <= colCount; i++) {
    sheet.getColumn(i).width = i === 1 ? 14 : 11
  }

  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = config.fileName || `${chart.value?.title || '图表'}_Excel示例.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function parseMatrixValue(value: any, rowCount: number, colCount: number): number[][] {
  if (Array.isArray(value)) {
    if (Array.isArray(value[0])) {
      if (value.length === rowCount && value.every((r: any[]) => Array.isArray(r) && r.length === colCount)) {
        return value.map((row: any[]) => row.map(v => Number(v) || 0))
      }
      return value.map((row: any[]) => row.map(v => Number(v) || 0))
    }
    const nums = value.map(v => Number(v) || 0)
    return chunkNumbers(nums, rowCount, colCount)
  }

  if (typeof value !== 'string' || !value.trim()) return []
  const text = value.trim()
  const rowTexts = text.includes('\n')
    ? text.split('\n')
    : text.includes(';')
      ? text.split(';')
      : []

  if (rowTexts.length) {
    return rowTexts
      .map(row => row.replace(/，/g, ',').split(',').map(v => Number(v.trim()) || 0))
      .filter(row => row.length)
  }

  const nums = text.replace(/，/g, ',').split(',').map(v => Number(v.trim()) || 0)
  return chunkNumbers(nums, rowCount, colCount)
}

function chunkNumbers(nums: number[], rowCount: number, colCount: number): number[][] {
  return Array.from({ length: rowCount }, (_, ri) =>
    Array.from({ length: colCount }, (_, ci) => nums[ri * colCount + ci] ?? 0)
  )
}

onBeforeRouteLeave(async () => {
  if (!dirty.value) return true
  try {
    await ElMessageBox.confirm('有未保存的修改，是否保存？', '提示', {
      confirmButtonText: '保存并退出',
      cancelButtonText: '不保存',
      distinguishCancelAndClose: true,
      type: 'warning',
    })
  } catch (action) {
    if (action === 'cancel') return true
    return false
  }
  try {
    await saveChart(true)
  } catch {
    // save failed, still allow navigation
  }
  return true
})
</script>

<template>
  <div style="height: 100vh; display: flex; flex-direction: column; background: #f8fafc">
    <!-- Top Bar -->
    <header style="height: 52px; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; background: #fff; border-bottom: 1px solid #e2e8f0; flex-shrink: 0">
      <div style="display: flex; align-items: center; gap: 12px">
        <el-button text @click="router.push('/my-charts')">←</el-button>
        <span style="font-weight: 700; font-size: 15px; color: #1e293b">图表编辑器</span>
        <el-tag size="small" type="primary">编辑中</el-tag>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button size="small" @click="() => saveChart()">💾 保存</el-button>
        <el-button v-if="engine === 'matplotlib' && excelExample" size="small" plain type="success" @click="downloadExcelExample">📥 Excel 示例</el-button>
        <el-button v-if="!hideImageExport" size="small" @click="exportImage">🖼️ 导出图片</el-button>
        <el-button v-if="DynamicComponent" size="small" @click="exportExcel">📊 导出 Excel</el-button>
        <el-button v-if="!DynamicComponent && !previewImage" size="small" @click="exportCode">📄 导出代码</el-button>
      </div>
    </header>

    <!-- Style Picker Overlay -->
    <div v-if="templateStyles.length > 0 && !selectedStyle" class="style-picker-overlay">
      <div class="style-picker-card">
        <h2 class="style-picker-title">选择图表风格</h2>
        <p class="style-picker-desc">该图表尚未关联风格，请选择一种风格以加载正确的编辑组件</p>
        <div class="style-picker-grid">
          <div v-for="s in templateStyles" :key="s.id" class="style-option" @click="selectStyleInEditor(s.id)">
            <div v-if="s.previewImage" class="style-option-preview">
              <img :src="s.previewImage" :alt="s.name" />
            </div>
            <div class="style-option-name">{{ s.name }}</div>
            <div class="style-option-desc">{{ s.description }}</div>
            <el-button type="primary" size="small" style="margin-top: 12px">选择此风格</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Editor Content -->
    <div style="flex: 1; display: flex; overflow: hidden">

      <!-- Config Panel (for matplotlib param editor) -->
      <div v-if="previewImage && templateConfig?.config?.paramSchema" :style="{ width: '400px', background: '#fff', borderRight: '1px solid #e2e8f0', overflow: 'auto', flexShrink: 0, padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }">
        <div style="font-size: 14px; font-weight: 600; color: #1e293b">参数设置</div>
        <div v-for="(fieldConfig, key) in templateConfig.config.paramSchema" v-show="!isFieldType(fieldConfig, 'hidden') && fieldConfig.showMatrixTable !== false" :key="key">
          <label style="font-size: 13px; font-weight: 600; color: #475569; margin-bottom: 6px; display: block">{{ fieldConfig.label || key }}</label>
          <div v-if="isFieldType(fieldConfig, 'excel')">
            <div style="border: 1px dashed #cbd5e1; border-radius: 8px; padding: 14px; background: #f8fafc">
              <div style="font-size: 12px; color: #64748b; line-height: 1.6; margin-bottom: 10px">{{ fieldConfig.help || '上传 Excel 文件后会自动读取指定列数据。' }}</div>
              <input
                :id="`excel-editor-${String(key)}`"
                type="file"
                accept=".xlsx"
                style="display: none"
                @change="handleExcelUpload($event, fieldConfig, key as string)"
              />
              <label :for="`excel-editor-${String(key)}`" style="display: inline-flex; align-items: center; justify-content: center; height: 32px; padding: 0 12px; border-radius: 6px; background: #1a56db; color: #fff; font-size: 13px; cursor: pointer">上传 Excel</label>
              <div v-if="excelFileNames[key as string]" style="margin-top: 8px; font-size: 12px; color: #16a34a">已导入：{{ excelFileNames[key as string] }}</div>
            </div>
          </div>
          <div v-else-if="isFieldType(fieldConfig, 'string-list')">
            <div v-for="(_, idx) in (formParams[key] || [])" :key="idx" style="display: flex; gap: 6px; margin-bottom: 6px">
              <el-input v-model="formParams[key][idx]" :placeholder="`${fieldConfig.label || key} ${Number(idx) + 1}`" size="small" />
              <el-button text type="danger" size="small" @click="removeListItem(key as string, Number(idx))">✕</el-button>
            </div>
            <el-button text size="small" @click="addListItem(key as string)">+ 添加</el-button>
          </div>
          <div v-else-if="isFieldType(fieldConfig, 'number-list')">
            <div v-for="(_, idx) in (formParams[key] || [])" :key="idx" style="display: flex; gap: 6px; margin-bottom: 6px">
              <el-input-number v-model="formParams[key][idx]" size="small" style="flex: 1" />
              <el-button text type="danger" size="small" @click="removeListItem(key as string, Number(idx))">✕</el-button>
            </div>
            <el-button text size="small" @click="addListItem(key as string, 'number-list')">+ 添加</el-button>
          </div>
          <div v-else-if="isFieldType(fieldConfig, 'matrix')">
            <div style="overflow-x: auto">
              <table v-if="getMatrixRows(fieldConfig).length && getMatrixCols(fieldConfig).length" style="width: 100%; border-collapse: collapse; font-size: 12px; border: 1px solid #e2e8f0; border-radius: 6px">
                <thead>
                  <tr style="background: #f8fafc">
                    <th style="padding: 6px 8px; font-weight: 500; color: #94a3b8; text-align: left; border: 1px solid #e2e8f0; min-width: 60px"></th>
                    <th v-for="col in getMatrixCols(fieldConfig)" :key="col" style="padding: 6px 8px; font-weight: 600; color: #475569; text-align: center; border: 1px solid #e2e8f0; min-width: 56px">{{ col }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in getMatrixRows(fieldConfig)" :key="ri">
                    <td style="padding: 4px 8px; font-weight: 600; color: #475569; background: #f8fafc; border: 1px solid #e2e8f0; white-space: nowrap">{{ row }}</td>
                    <td v-for="(_, ci) in getMatrixCols(fieldConfig)" :key="ci" style="padding: 2px; border: 1px solid #e2e8f0">
                      <el-input-number
                        :model-value="getMatrixCell(key as string, ri, ci)"
                        @update:model-value="setMatrixCell(key as string, ri, ci, $event)"
                        size="small" :min="0" :controls="false"
                        style="width: 100%"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-else style="font-size: 12px; color: #94a3b8; padding: 8px 0">请先填写上方的行列名称</div>
            </div>
          </div>
          <el-input-number v-else-if="isFieldType(fieldConfig, 'number')" v-model="formParams[key]" :placeholder="fieldConfig.placeholder || ''" style="width: 100%" />
          <el-input v-else-if="isFieldType(fieldConfig, 'text') || isFieldType(fieldConfig, 'textarea')" type="textarea" v-model="formParams[key]" :rows="4" :placeholder="fieldConfig.placeholder || `请输入${fieldConfig.label || key}`" />
          <el-input v-else v-model="formParams[key]" :placeholder="fieldConfig.placeholder || `请输入${fieldConfig.label || key}`" />
        </div>
        <div v-if="generating" style="margin-top: auto; text-align: center; color: #94a3b8; font-size: 13px">生成中...</div>
      </div>

      <!-- Config Panel (for ECharts/data editor) -->
      <div v-if="!DynamicComponent && !previewImage" style="width: 300px; background: #fff; border-right: 1px solid #e2e8f0; overflow: auto; flex-shrink: 0">
        <div style="padding: 12px 16px 0; border-bottom: 1px solid #f1f5f9">
          <el-radio-group v-model="activeTab" size="small">
            <el-radio-button value="data">数据</el-radio-button>
            <el-radio-button value="style">样式</el-radio-button>
            <el-radio-button value="advanced">高级</el-radio-button>
          </el-radio-group>
        </div>
        <div style="padding: 16px">
          <!-- Data Tab -->
          <div v-if="activeTab === 'data'">
            <div style="font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; margin-bottom: 10px">图表类型</div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 16px">
              <button v-for="c in [{k:'bar',l:'柱状'},{k:'line',l:'折线'},{k:'pie',l:'饼图'},{k:'radar',l:'雷达'}]" :key="c.k"
                @click="ct = c.k; updateChart()"
                :style="{ padding: '8px 4px', borderRadius: 6, fontSize: 10, border: '1px solid', cursor: 'pointer', background: ct === c.k ? '#eff6ff' : 'transparent', color: ct === c.k ? '#2563eb' : '#94a3b8', borderColor: ct === c.k ? '#bfdbfe' : 'transparent', fontFamily: 'inherit', fontWeight: 500 }">{{ c.l }}</button>
            </div>
            <div style="font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; margin-bottom: 10px">数据表格</div>
            <div style="border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden">
              <table style="width: 100%; border-collapse: collapse; font-size: 12px">
                <thead><tr style="background: #f8fafc">
                  <th style="padding: 6px; font-weight: 500; color: #94a3b8; text-align: left; border-bottom: 1px solid #e2e8f0">类别</th>
                  <th style="padding: 6px; font-weight: 500; color: #94a3b8; text-align: left; border-bottom: 1px solid #e2e8f0">系列1</th>
                  <th style="padding: 6px; font-weight: 500; color: #94a3b8; text-align: left; border-bottom: 1px solid #e2e8f0">系列2</th>
                </tr></thead>
                <tbody>
                  <tr v-for="(r, i) in data" :key="i">
                    <td style="padding: 3px"><el-input v-model="r.cat" size="small" /></td>
                    <td style="padding: 3px"><el-input-number v-model="r.v1" size="small" :min="0" style="width: 100%" /></td>
                    <td style="padding: 3px"><el-input-number v-model="r.v2" size="small" :min="0" style="width: 100%" /></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <el-button text size="small" style="margin-top: 4px" @click="data.push({cat:`项${data.length+1}`,v1:0,v2:0})">+ 添加行</el-button>
            <el-button text size="small" style="margin-top: 4px" @click="updateChart()">↻ 刷新预览</el-button>
          </div>

          <!-- Style Tab -->
          <div v-if="activeTab === 'style'">
            <div style="font-size: 12px; font-weight: 600; color: #64748b; margin-bottom: 10px">标题</div>
            <el-input v-model="titleTxt" placeholder="图表标题" size="small" style="margin-bottom: 8px" @input="updateChart" />
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px">
              <span style="font-size: 13px; color: #475569">显示标题</span>
              <el-switch v-model="showTitle" @change="updateChart" />
            </div>
            <div style="font-size: 12px; font-weight: 600; color: #64748b; margin-bottom: 10px; margin-top: 12px">图例与网格</div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px">
              <span style="font-size: 13px; color: #475569">显示图例</span>
              <el-switch v-model="showLegend" @change="updateChart" />
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px">
              <span style="font-size: 13px; color: #475569">显示网格线</span>
              <el-switch v-model="showGrid" @change="updateChart" />
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px">
              <span style="font-size: 13px; color: #475569">显示数据标签</span>
              <el-switch v-model="showLabels" @change="updateChart" />
            </div>
            <div style="font-size: 12px; font-weight: 600; color: #64748b; margin-bottom: 10px; margin-top: 12px">颜色主题</div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px">
              <div v-for="(t, i) in themes" :key="i" @click="themeIdx = i; updateChart()"
                :style="{ width: '100%', aspectRatio: '1', borderRadius: 8, cursor: 'pointer', border: themeIdx === i ? '2px solid #2563eb' : '2px solid #e2e8f0', background: `linear-gradient(135deg,${t[0]},${t[1]})` }" />
            </div>
          </div>

          <!-- Advanced Tab -->
          <div v-if="activeTab === 'advanced'">
            <div style="font-size: 12px; font-weight: 600; color: #64748b; margin-bottom: 10px">ECharts 配置代码</div>
            <pre style="background: #0f172a; border-radius: 8px; padding: 16px; font-size: 12px; color: #93c5fd; line-height: 1.8; overflow: auto; max-height: 400px">
              <code>// ECharts option 配置</code>
            </pre>
            <p style="font-size: 12px; color: #94a3b8; margin-top: 8px">高级用户可直接编辑配置代码</p>
          </div>
        </div>
      </div>

      <!-- Preview Area -->
      <div style="flex: 1; padding: 24px; display: flex; align-items: center; justify-content: center; overflow: auto">
        <!-- Vue Component -->
        <div v-if="DynamicComponent" style="width: 100%; height: 100%; overflow: auto">
          <DynamicComponent ref="compRef" :data="compData" @update:data="onCompDataUpdate" />
        </div>

        <!-- Matplotlib image -->
        <div v-else-if="previewImage" style="background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 24px">
          <img :src="previewImage" style="max-width: 100%; max-height: 80vh" alt="chart" />
        </div>

        <!-- ECharts canvas -->
        <div v-else ref="chartRef" style="width: 100%; height: 100%; background: #fff; border-radius: 12px; border: 1px solid #e2e8f0" />

        <div v-if="!chartId && !DynamicComponent && !previewImage" style="text-align: center; color: #94a3b8">
          <p>请先创建一个图表</p>
        </div>
      </div>

      <!-- Right: Analysis Results (matplotlib) -->
      <div v-if="summaryData && Object.keys(summaryData).length" style="width: 300px; background: #fff; border-left: 1px solid #e2e8f0; overflow: auto; padding: 24px; flex-shrink: 0; display: flex; flex-direction: column; gap: 12px">
        <div style="font-size: 15px; font-weight: 700; color: #1e293b">分析结果</div>
        <div style="display: flex; flex-direction: column; gap: 0">
          <div v-for="(val, key) in summaryData" :key="key" style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f1f5f9; font-size: 13px">
            <span style="color: #64748b">{{ key }}</span>
            <span style="color: #0f172a; font-weight: 600">{{ val }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.style-picker-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
}
.style-picker-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px 48px;
  max-width: 920px;
  width: 90%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  text-align: center;
}
.style-picker-title {
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 8px;
}
.style-picker-desc {
  font-size: 14px;
  color: #94a3b8;
  margin: 0 0 28px;
}
.style-picker-grid {
  display: flex;
  gap: 20px;
  justify-content: center;
}
.style-option {
  flex: 1;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 24px 16px;
  cursor: pointer;
  transition: all 0.2s;
}
.style-option:hover {
  border-color: #409eff;
  background: #f0f7ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
}
.style-option-name {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
}
.style-option-desc {
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}
.style-option-preview {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 12px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}
.style-option-preview img {
  width: 100%;
  height: auto;
  max-height: 200px;
  object-fit: contain;
  display: block;
}
</style>
