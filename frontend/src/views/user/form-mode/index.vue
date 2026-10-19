<script setup lang="ts">
import { ref, onMounted, computed, shallowRef } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import request from '@/api/request'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const template = ref<any>(null)
const engine = ref('')
const previewImage = ref('')
const summaryData = ref<Record<string, any> | null>(null)
const loading = ref(false)

// style selection for templates that have styles
const selectedStyle = ref<string | null>(null)
const templateStyles = ref<any[]>([])

// vue-component engine: dynamic component
const DynamicComponent = shallowRef<any>(null)

// matplotlib engine: dynamic form params
const formParams = ref<Record<string, any>>({})
const excelFileNames = ref<Record<string, string>>({})

// For ProcessFlow.vue integration
const chartDataRef = ref<any>(null)
const componentKey = ref(0) // 触发组件重挂(加载示例 / AI 回填时用)

// 示例 dialog
const exampleDialogVisible = ref(false)
const exampleData = computed(() => template.value?.config?.example || null)
const excelExample = computed(() => template.value?.config?.excelExample || null)

const componentModules = import.meta.glob('../../../../../chart-templates/**/*.vue')

async function loadVueComponent(componentFile?: string) {
  try {
    const keys = Object.keys(componentModules)
    let compKey: string | undefined
    if (componentFile) {
      compKey = keys.find(k => k.endsWith('/' + componentFile))
    }
    if (!compKey) {
      compKey = keys.find(k => k.includes(`/${template.value.id}/`))
    }
    if (compKey) {
      const mod = await componentModules[compKey]()
      DynamicComponent.value = (mod as any).default
      chartDataRef.value = {}
    } else {
      ElMessage.warning('未找到模板组件')
    }
  } catch {
    ElMessage.warning('无法加载组件')
  }
}

async function selectStyle(styleId: string) {
  selectedStyle.value = styleId
  const style = templateStyles.value.find(s => s.id === styleId)
  if (style?.component) {
    await loadVueComponent(style.component)
  }
}

onMounted(async () => {
  const data = await request.get(`/templates/${route.params.templateId}`)
  template.value = data
  engine.value = data.engine

  // 工艺程序图：即使 DB 里 engine 未同步为 drawio，只要有 dataEntryComponent 就走 Draw.io 表单链路
  if (data.config?.dataEntryComponent) {
    engine.value = 'drawio'
    await loadVueComponent(data.config.dataEntryComponent as string)
    chartDataRef.value = chartDataRef.value || {}
    return
  }
  if (data.id === 'operation-process') {
    engine.value = 'drawio'
    await loadVueComponent('OperationProcessForm.vue')
    chartDataRef.value = chartDataRef.value || {}
    return
  }

  if (data.engine === 'drawio') {
    router.replace(`/mode-select/${route.params.templateId}`)
    return
  }

  if (data.engine === 'vue-component') {
    const styles = data.config?.styles || []
    templateStyles.value = styles
    if (styles.length > 0) {
      return
    }
    await loadVueComponent()
  } else if (data.engine === 'matplotlib') {
    const schema = data.config?.paramSchema || {}
    const defaults: Record<string, any> = {}
    for (const [key, field] of Object.entries<any>(schema)) {
      if (Object.prototype.hasOwnProperty.call(field, 'default')) defaults[key] = JSON.parse(JSON.stringify(field.default))
      else if (isFieldType(field, 'string-list') || isFieldType(field, 'number-list') || isFieldType(field, 'matrix') || isFieldType(field, 'hidden')) defaults[key] = []
      else defaults[key] = ''
    }
    formParams.value = defaults
  }
})

async function generateMatplotlib() {
  loading.value = true
  try {
    normalizeAllMatrixParams()
    const result = await request.post('/charts/generate', {
      templateId: route.params.templateId,
      params: formParams.value
    })
    previewImage.value = result.image_base64
    summaryData.value = result.summary || null
  } catch (e: any) {
    ElMessage.error(e.message || '生成失败')
  }
  loading.value = false
}

async function saveChart() {
  let chartData: any = {}
  if (engine.value === 'vue-component') {
    chartData = chartDataRef.value || {}
    if (selectedStyle.value) {
      const style = templateStyles.value.find(s => s.id === selectedStyle.value)
      chartData._style = selectedStyle.value
      if (style?.component) chartData._componentFile = style.component
    }
    const result = await request.post('/charts', {
      title: template.value?.name || '图表',
      templateId: route.params.templateId,
      chartData,
    })
    ElMessage.success('图表已保存')
    router.push(`/chart-editor/${result.id}`)
    return
  }

  if (engine.value === 'drawio') {
    const raw = chartDataRef.value as Record<string, any> | null
    const tid = template.value?.id || route.params.templateId
    if (tid === 'gantt') {
      if (!raw?.phases?.length) {
        ElMessage.warning('请至少添加一个阶段')
        return
      }
    } else if (tid === 'tech-roadmap') {
      if (!raw?.stages?.length) {
        ElMessage.warning('请至少添加一个阶段')
        return
      }
    } else if (tid === 'value-stream') {
      if (!raw?.processes?.length) {
        ElMessage.warning('请至少添加一个工序')
        return
      }
    } else {
      if (!raw?.mainSteps?.length) {
        ElMessage.warning('请至少填写一条主干步骤')
        return
      }
    }
    loading.value = true
    try {
      let xml: string
      if (tid === 'gantt') {
        const { buildGanttMxGraphXml, coerceGanttPayload } = await import(
          '../../../../../chart-templates/gantt/buildMxGraphXml'
        )
        xml = buildGanttMxGraphXml(coerceGanttPayload(raw as any))
      } else if (tid === 'tech-roadmap') {
        const { buildRoadmapMxGraphXml, coerceRoadmapPayload } = await import(
          '../../../../../chart-templates/tech-roadmap/buildMxGraphXml'
        )
        xml = buildRoadmapMxGraphXml(coerceRoadmapPayload(raw as any))
      } else if (tid === 'value-stream') {
        const { buildValueStreamMxGraphXml, coerceVsmPayload } = await import(
          '../../../../../chart-templates/value-stream/buildMxGraphXml'
        )
        xml = buildValueStreamMxGraphXml(coerceVsmPayload(raw as any))
      } else {
        const { buildOperationProcessMxGraphXml, coerceOperationProcessPayload } = await import(
          '../../../../../chart-templates/operation-process/buildMxGraphXml'
        )
        xml = buildOperationProcessMxGraphXml(coerceOperationProcessPayload(raw as any))
      }
      const result = await request.post('/charts', {
        title: template.value?.name || '图表',
        templateId: route.params.templateId,
        chartData: { xml },
      })
      ElMessage.success('已生成画布，正在打开 Draw.io…')
      router.push(`/drawio-editor/${result.id}`)
    } catch (e: any) {
      ElMessage.error(e.message || '生成失败')
    }
    loading.value = false
    return
  }

  chartData = { params: formParams.value, image_base64: previewImage.value }
  const result = await request.post('/charts', {
    title: template.value?.name || '图表',
    templateId: route.params.templateId,
    chartData,
  })
  ElMessage.success('图表已保存')
  router.push(`/chart-editor/${result.id}`)
}

function onDataUpdate(data: any) {
  chartDataRef.value = data
}

function loadExampleData() {
  const ex = exampleData.value
  if (!ex?.data) {
    ElMessage.warning('该模板暂无示例数据')
    return
  }
  if (engine.value === 'vue-component' || engine.value === 'drawio') {
    chartDataRef.value = JSON.parse(JSON.stringify(ex.data))
    componentKey.value++
  } else if (engine.value === 'matplotlib') {
    formParams.value = JSON.parse(JSON.stringify(ex.data))
    normalizeAllMatrixParams()
  }
  exampleDialogVisible.value = false
  ElMessage.success('示例数据已加载')
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
      formParams.value[target] = rows.slice(1)
        .map(row => Number(row[columnIndex]))
        .filter(value => Number.isFinite(value))
    }

    // 整块矩阵（Excel mode=matrix）已在上面写成正确二维数组，勿再 normalize（否则会按错误维度重排数值）
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
  a.download = config.fileName || `${template.value?.name || '图表'}_Excel示例.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
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
  return typeof m[ri][ci] === 'number' ? m[ri][ci] : Number(m[ri][ci]) || 0
}

function setMatrixCell(key: string, ri: number, ci: number, val: number | undefined) {
  if (!Array.isArray(formParams.value[key])) formParams.value[key] = []
  const m = formParams.value[key] as number[][]
  while (m.length <= ri) m.push([])
  while (m[ri].length <= ci) m[ri].push(0)
  m[ri][ci] = val ?? 0
}

function normalizeAllMatrixParams() {
  const schema = template.value?.config?.paramSchema || {}
  for (const [key, field] of Object.entries<any>(schema)) {
    if (isFieldType(field, 'matrix')) normalizeMatrixParam(key, field)
  }
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
  formParams.value[key] = Array.from({ length: rowCount }, (_, ri) =>
    Array.from({ length: colCount }, (_, ci) => parsed[ri]?.[ci] ?? 0)
  )
}

function parseMatrixValue(value: any, rowCount: number, colCount: number): number[][] {
  if (Array.isArray(value)) {
    if (Array.isArray(value[0])) {
      if (value.length === rowCount && value.every((r: any[]) => Array.isArray(r) && r.length === colCount)) {
        return value.map((row: any[]) => row.map(v => Number(v) || 0))
      }
      return value.map((row: any[]) => row.map(v => Number(v) || 0))
    }
    return chunkNumbers(value.map(v => Number(v) || 0), rowCount, colCount)
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

  return chunkNumbers(text.replace(/，/g, ',').split(',').map(v => Number(v.trim()) || 0), rowCount, colCount)
}

function chunkNumbers(nums: number[], rowCount: number, colCount: number): number[][] {
  return Array.from({ length: rowCount }, (_, ri) =>
    Array.from({ length: colCount }, (_, ci) => nums[ri * colCount + ci] ?? 0)
  )
}
</script>

<template>
  <div style="min-height: 100vh; background: #f8fafc; display: flex; flex-direction: column">
    <!-- Top Nav -->
    <header style="height: 56px; display: flex; align-items: center; gap: 10px; padding: 0 24px; background: #fff; border-bottom: 1px solid #e2e8f0; flex-shrink: 0">
      <el-button text @click="router.push(`/mode-select/${route.params.templateId}`)">← 返回</el-button>
      <span style="font-weight: 600; color: #0f172a">表单模式 · {{ template?.name || '加载中...' }}</span>
      <div style="margin-left: auto">
        <el-button v-if="excelExample" type="success" plain size="small" @click="downloadExcelExample">📥 Excel 示例</el-button>
        <el-button v-if="exampleData" type="primary" plain size="small" @click="exampleDialogVisible = true">📘 示例</el-button>
      </div>
    </header>

    <!-- Style Picker Overlay -->
    <div v-if="templateStyles.length > 0 && !selectedStyle" class="style-picker-overlay">
      <div class="style-picker-card">
        <h2 class="style-picker-title">{{ template?.name }} · 选择风格</h2>
        <p class="style-picker-desc">请选择一种图表风格，选定后将加载对应的编辑界面</p>
        <div class="style-picker-grid">
          <div v-for="s in templateStyles" :key="s.id" class="style-option" @click="selectStyle(s.id)">
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

    <div style="flex: 1; display: flex; overflow: hidden">
      <!-- Vue-component engine: 组件内置双面板,保存按钮通过 slot 注入到表单下方 -->
      <template v-if="(engine === 'vue-component' || engine === 'drawio') && DynamicComponent">
        <div style="flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; padding: 16px">
          <DynamicComponent :key="componentKey" :data="chartDataRef" @update:data="onDataUpdate">
            <template #save-button>
              <el-button type="primary" size="large" :loading="loading" @click="saveChart">保存图表</el-button>
            </template>
          </DynamicComponent>
        </div>
      </template>

      <!-- Matplotlib engine: 左表单 + 右预览,保存按钮在预览图下方 -->
      <template v-else-if="engine === 'matplotlib'">
        <div :style="{ width: '400px', background: '#fff', borderRight: '1px solid #e2e8f0', overflow: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', flexShrink: 0 }">
          <div v-for="(fieldConfig, key) in (template?.config?.paramSchema || {})" v-show="!isFieldType(fieldConfig, 'hidden') && fieldConfig.showMatrixTable !== false" :key="key">
            <label style="font-size: 13px; font-weight: 600; color: #475569; margin-bottom: 8px; display: block">{{ fieldConfig.label || key }}</label>

            <div v-if="isFieldType(fieldConfig, 'excel')">
              <div style="border: 1px dashed #cbd5e1; border-radius: 8px; padding: 14px; background: #f8fafc">
                <div style="font-size: 12px; color: #64748b; line-height: 1.6; margin-bottom: 10px">{{ fieldConfig.help || '上传 Excel 文件后会自动读取指定列数据。' }}</div>
                <input
                  :id="`excel-${String(key)}`"
                  type="file"
                  accept=".xlsx"
                  style="display: none"
                  @change="handleExcelUpload($event, fieldConfig, key as string)"
                />
                <label :for="`excel-${String(key)}`" style="display: inline-flex; align-items: center; justify-content: center; height: 32px; padding: 0 12px; border-radius: 6px; background: #1a56db; color: #fff; font-size: 13px; cursor: pointer">上传 Excel</label>
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
              <div style="font-size: 12px; color: #94a3b8; margin-bottom: 8px">行是工序，列是元素；没有该元素的工序填 0。</div>
              <div style="overflow-x: auto">
                <table v-if="getMatrixRows(fieldConfig).length && getMatrixCols(fieldConfig).length" style="width: 100%; border-collapse: collapse; font-size: 12px; border: 1px solid #e2e8f0; border-radius: 6px">
                  <thead>
                    <tr style="background: #f8fafc">
                      <th style="padding: 6px 8px; font-weight: 500; color: #94a3b8; text-align: left; border: 1px solid #e2e8f0; min-width: 72px">工序/元素</th>
                      <th v-for="col in getMatrixCols(fieldConfig)" :key="col" style="padding: 6px 8px; font-weight: 600; color: #475569; text-align: center; border: 1px solid #e2e8f0; min-width: 72px">{{ col }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, ri) in getMatrixRows(fieldConfig)" :key="ri">
                      <td style="padding: 4px 8px; font-weight: 600; color: #475569; background: #f8fafc; border: 1px solid #e2e8f0; white-space: nowrap">{{ row }}</td>
                      <td v-for="(_, ci) in getMatrixCols(fieldConfig)" :key="ci" style="padding: 2px; border: 1px solid #e2e8f0">
                        <el-input-number
                          :model-value="getMatrixCell(key as string, ri, ci)"
                          @update:model-value="setMatrixCell(key as string, ri, ci, $event)"
                          size="small"
                          :min="0"
                          :controls="false"
                          style="width: 100%"
                        />
                      </td>
                    </tr>
                  </tbody>
                </table>
                <div v-else style="font-size: 12px; color: #94a3b8; padding: 8px 0">请先填写上方的工序名称和元素名称</div>
              </div>
            </div>

            <el-input-number v-else-if="isFieldType(fieldConfig, 'number')" v-model="formParams[key]" :placeholder="fieldConfig.placeholder || ''" style="width: 100%" />

            <el-input v-else-if="isFieldType(fieldConfig, 'text') || isFieldType(fieldConfig, 'textarea')" type="textarea" v-model="formParams[key]" :rows="4" :placeholder="fieldConfig.placeholder || `请输入${fieldConfig.label || key}`" />

            <el-input v-else v-model="formParams[key]" :placeholder="fieldConfig.placeholder || `请输入${fieldConfig.label || key}`" />
          </div>

          <div style="margin-top: auto; display: flex; gap: 8px">
            <el-button type="primary" :loading="loading" @click="generateMatplotlib" style="flex: 1">生成图表</el-button>
          </div>
        </div>

        <div style="flex: 1; padding: 32px; display: flex; align-items: center; justify-content: center; overflow: auto">
          <div v-if="previewImage" style="text-align: center">
            <div style="background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 24px; display: inline-block">
              <img :src="previewImage" style="max-width: 100%; max-height: 75vh" alt="chart preview" />
            </div>
            <div style="margin-top: 16px">
              <el-button type="primary" size="large" @click="saveChart">保存图表</el-button>
            </div>
          </div>
          <div v-else style="text-align: center; color: #cbd5e1">
            <div style="font-size: 64px; margin-bottom: 16px">📊</div>
            <p style="font-size: 15px; color: #94a3b8">在左侧填写数据<br/>图表预览将显示在这里</p>
          </div>
        </div>

        <div v-if="summaryData && Object.keys(summaryData).length" style="width: 300px; background: #fff; border-left: 1px solid #e2e8f0; overflow: auto; padding: 24px; flex-shrink: 0; display: flex; flex-direction: column; gap: 12px">
          <div style="font-size: 15px; font-weight: 700; color: #1e293b">分析结果</div>
          <div style="display: flex; flex-direction: column; gap: 0">
            <div v-for="(val, key) in summaryData" :key="key" style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f1f5f9; font-size: 13px">
              <span style="color: #64748b">{{ key }}</span>
              <span style="color: #0f172a; font-weight: 600">{{ val }}</span>
            </div>
          </div>
        </div>
      </template>

      <template v-else>
        <div style="flex: 1; display: flex; align-items: center; justify-content: center">
          <p style="color: #94a3b8">加载模板信息中...</p>
        </div>
      </template>
    </div>

    <!-- 示例 Dialog -->
    <el-dialog v-model="exampleDialogVisible" :title="`${template?.name || ''} · 使用示例`" width="600px">
      <div v-if="exampleData">
        <p style="line-height: 1.7; color: #475569; margin-bottom: 16px">{{ exampleData.description }}</p>
        <div style="background: #f8fafc; border-radius: 8px; padding: 12px; font-size: 12px; color: #64748b; max-height: 240px; overflow: auto">
          <pre style="margin: 0; white-space: pre-wrap; word-break: break-all">{{ JSON.stringify(exampleData.data, null, 2) }}</pre>
        </div>
      </div>
      <template #footer>
        <el-button @click="exampleDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="loadExampleData">加载示例数据到表单</el-button>
      </template>
    </el-dialog>
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
