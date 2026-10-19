<template>
  <div class="two-hand-container" :class="{ 'preview-mode': mode === 'preview' }">
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
          <el-form-item label="时间单位">
            <el-select v-model="headerInfo.timeUnit" style="width: 100%">
              <el-option label="秒 (s)" value="s" />
              <el-option label="分 (min)" value="min" />
              <el-option label="TMU" value="TMU" />
            </el-select>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 布局图上传 -->
      <el-card class="image-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>双手布局图</span>
            <el-button link type="primary" @click="triggerImageUpload">{{ layoutImage ? '更换图片' : '上传图片' }}</el-button>
          </div>
        </template>
        <div class="image-upload-area" @click="triggerImageUpload">
          <img v-if="layoutImage" :src="layoutImage" class="upload-preview-img" alt="布局图" />
          <div v-else class="upload-placeholder">
            <el-icon :size="24" color="#ccc"><Picture /></el-icon>
            <span>点击上传双手布局图</span>
          </div>
        </div>
        <input ref="imageInputRef" type="file" accept="image/*" style="display:none" @change="onImageUpload" />
      </el-card>

      <!-- 步骤输入表格 -->
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
          <el-table :data="steps" size="small" border style="width: 100%" max-height="420">
            <el-table-column type="index" label="序" width="40" align="center" />
            <el-table-column label="左手说明" min-width="120">
              <template #default="{ row }">
                <el-input v-model="row.leftDesc" size="small" placeholder="左手描述" />
              </template>
            </el-table-column>
            <el-table-column label="左手符号" width="100">
              <template #default="{ row }">
                <el-select v-model="row.leftSymbol" size="small" placeholder="类型">
                  <el-option label="〇 操作" value="operation" />
                  <el-option label="→ 移动" value="transport" />
                  <el-option label="□ 检验" value="inspect" />
                  <el-option label="D 等待" value="wait" />
                  <el-option label="▽ 持握" value="hold" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="70">
              <template #default="{ row }">
                <el-input-number v-model="row.time" size="small" :min="0" :controls="false" style="width: 100%" />
              </template>
            </el-table-column>
            <el-table-column label="右手符号" width="100">
              <template #default="{ row }">
                <el-select v-model="row.rightSymbol" size="small" placeholder="类型">
                  <el-option label="▽ 持握" value="hold" />
                  <el-option label="D 等待" value="wait" />
                  <el-option label="□ 检验" value="inspect" />
                  <el-option label="→ 移动" value="transport" />
                  <el-option label="〇 操作" value="operation" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="右手说明" min-width="120">
              <template #default="{ row }">
                <el-input v-model="row.rightDesc" size="small" placeholder="右手描述" />
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
      <!-- 双手作业分析图预览 -->
      <div class="chart-container" ref="chartContainerRef">
        <div class="chart-scroll export-target" ref="exportTargetRef">
          <div class="flow-chart-paper" ref="paperRef">
            <div class="flow-main-title">双手作业分析图</div>

            <!-- 顶部基本信息 + 布局图 -->
            <div class="flow-top-section">
              <div class="header-flex">
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
                    <tr>
                      <td class="k">时间单位</td>
                      <td class="v" colspan="5">{{ headerInfo.timeUnit || 's' }}</td>
                    </tr>
                  </tbody>
                </table>
                <div class="layout-image-area">
                  <img v-if="layoutImage" :src="layoutImage" class="layout-img" alt="双手布局图" />
                  <div v-else class="layout-placeholder">
                    <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="#bbb" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5" fill="#bbb" stroke="none"/><path d="M21 15l-5-5L5 21"/></svg>
                    <span>双手布局图</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 双手作业主表 -->
            <div class="flow-process-wrapper">
              <table class="flow-process-table">
                <thead>
                  <tr>
                    <th colspan="7" class="side-header left-side-header">左 手</th>
                    <th rowspan="2" class="col-time">时间</th>
                    <th colspan="7" class="side-header right-side-header">右 手</th>
                  </tr>
                  <tr>
                    <th class="col-order">单元顺序</th>
                    <th class="col-desc">作业单元说明</th>
                    <th class="col-sym"><svg class="sym-icon" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="#333" stroke-width="2"/></svg></th>
                    <th class="col-sym"><svg class="sym-icon" viewBox="0 0 24 24"><path d="M3 12h14M13 7l5 5-5 5" fill="none" stroke="#333" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></th>
                    <th class="col-sym"><svg class="sym-icon" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" fill="none" stroke="#333" stroke-width="2"/></svg></th>
                    <th class="col-sym"><svg class="sym-icon" viewBox="0 0 24 24"><path d="M5 4h8a8 8 0 0 1 0 16H5V4z" fill="none" stroke="#333" stroke-width="2"/></svg></th>
                    <th class="col-sym"><svg class="sym-icon" viewBox="0 0 24 24"><polygon points="2,3 22,3 12,21" fill="none" stroke="#333" stroke-width="2"/></svg></th>
                    <th class="col-sym"><svg class="sym-icon" viewBox="0 0 24 24"><polygon points="2,3 22,3 12,21" fill="none" stroke="#333" stroke-width="2"/></svg></th>
                    <th class="col-sym"><svg class="sym-icon" viewBox="0 0 24 24"><path d="M5 4h8a8 8 0 0 1 0 16H5V4z" fill="none" stroke="#333" stroke-width="2"/></svg></th>
                    <th class="col-sym"><svg class="sym-icon" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" fill="none" stroke="#333" stroke-width="2"/></svg></th>
                    <th class="col-sym"><svg class="sym-icon" viewBox="0 0 24 24"><path d="M3 12h14M13 7l5 5-5 5" fill="none" stroke="#333" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></th>
                    <th class="col-sym"><svg class="sym-icon" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="#333" stroke-width="2"/></svg></th>
                    <th class="col-desc">作业单元说明</th>
                    <th class="col-order">单元顺序</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(step, index) in steps" :key="index">
                    <template v-if="shouldRenderLeft(index)">
                      <td class="col-order" :rowspan="getLeftRowspan(index)">{{ index + 1 }}</td>
                      <td class="col-desc" :rowspan="getLeftRowspan(index)">{{ step.leftDesc || '—' }}</td>
                      <td class="col-sym" :rowspan="getLeftRowspan(index)"><svg v-if="step.leftSymbol === 'operation'" class="sym-icon" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="#333" stroke-width="2"/></svg></td>
                      <td class="col-sym" :rowspan="getLeftRowspan(index)"><svg v-if="step.leftSymbol === 'transport'" class="sym-icon" viewBox="0 0 24 24"><path d="M3 12h14M13 7l5 5-5 5" fill="none" stroke="#333" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></td>
                      <td class="col-sym" :rowspan="getLeftRowspan(index)"><svg v-if="step.leftSymbol === 'inspect'" class="sym-icon" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" fill="none" stroke="#333" stroke-width="2"/></svg></td>
                      <td class="col-sym" :rowspan="getLeftRowspan(index)"><svg v-if="step.leftSymbol === 'wait'" class="sym-icon" viewBox="0 0 24 24"><path d="M5 4h8a8 8 0 0 1 0 16H5V4z" fill="none" stroke="#333" stroke-width="2"/></svg></td>
                      <td class="col-sym" :rowspan="getLeftRowspan(index)"><svg v-if="step.leftSymbol === 'hold'" class="sym-icon" viewBox="0 0 24 24"><polygon points="2,3 22,3 12,21" fill="none" stroke="#333" stroke-width="2"/></svg></td>
                    </template>
                    <td class="col-time">{{ step.time ?? 0 }}</td>
                    <template v-if="shouldRenderRight(index)">
                      <td class="col-sym" :rowspan="getRightRowspan(index)"><svg v-if="step.rightSymbol === 'hold'" class="sym-icon" viewBox="0 0 24 24"><polygon points="2,3 22,3 12,21" fill="none" stroke="#333" stroke-width="2"/></svg></td>
                      <td class="col-sym" :rowspan="getRightRowspan(index)"><svg v-if="step.rightSymbol === 'wait'" class="sym-icon" viewBox="0 0 24 24"><path d="M5 4h8a8 8 0 0 1 0 16H5V4z" fill="none" stroke="#333" stroke-width="2"/></svg></td>
                      <td class="col-sym" :rowspan="getRightRowspan(index)"><svg v-if="step.rightSymbol === 'inspect'" class="sym-icon" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" fill="none" stroke="#333" stroke-width="2"/></svg></td>
                      <td class="col-sym" :rowspan="getRightRowspan(index)"><svg v-if="step.rightSymbol === 'transport'" class="sym-icon" viewBox="0 0 24 24"><path d="M3 12h14M13 7l5 5-5 5" fill="none" stroke="#333" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></td>
                      <td class="col-sym" :rowspan="getRightRowspan(index)"><svg v-if="step.rightSymbol === 'operation'" class="sym-icon" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="#333" stroke-width="2"/></svg></td>
                      <td class="col-desc" :rowspan="getRightRowspan(index)">{{ step.rightDesc || '—' }}</td>
                      <td class="col-order" :rowspan="getRightRowspan(index)">{{ index + 1 }}</td>
                    </template>
                  </tr>
                </tbody>
                <tfoot>
                  <tr class="summary-row">
                    <td class="col-order">合计</td>
                    <td class="col-desc"></td>
                    <td class="col-sym">{{ leftStats.operation }}</td>
                    <td class="col-sym">{{ leftStats.transport }}</td>
                    <td class="col-sym">{{ leftStats.inspect }}</td>
                    <td class="col-sym">{{ leftStats.wait }}</td>
                    <td class="col-sym">{{ leftStats.hold }}</td>
                    <td class="col-time">{{ totalTime }}</td>
                    <td class="col-sym">{{ rightStats.hold }}</td>
                    <td class="col-sym">{{ rightStats.wait }}</td>
                    <td class="col-sym">{{ rightStats.inspect }}</td>
                    <td class="col-sym">{{ rightStats.transport }}</td>
                    <td class="col-sym">{{ rightStats.operation }}</td>
                    <td class="col-desc"></td>
                    <td class="col-order">合计</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { Delete, Picture } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ExcelJS from 'exceljs'
import html2canvas from 'html2canvas'

const props = defineProps({
  data: { type: Object, default: null },
  mode: { type: String, default: 'edit' } // 'edit' | 'preview'
})
const emit = defineEmits(['update:data'])

const defaultHeader = {
  stationName: '',
  improvement: '现行',
  startState: '',
  endState: '',
  researcher: '',
  date: new Date().toISOString().split('T')[0],
  method: '',
  timeUnit: 's'
}

const defaultSteps = [
  {
    leftDesc: '',
    leftSymbol: 'operation',
    time: 0,
    rightSymbol: 'operation',
    rightDesc: ''
  }
]

// 数据状态(支持 props.data 初始化)
const headerInfo = ref({ ...defaultHeader, ...(props.data?.headerInfo || {}) })
const steps = ref(
  props.data?.steps?.length ? props.data.steps.map(s => ({ ...s })) : defaultSteps.map(s => ({ ...s }))
)
const layoutImage = ref(props.data?.layoutImage || '')

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
    steps: steps.value.map(s => ({ ...s })),
    layoutImage: layoutImage.value
  })
}

watch([headerInfo, steps, layoutImage], emitData, { deep: true })

// 注:不在此处 watch props.data。父组件需要重新注入数据时,应使用 :key 强制重挂组件。

const chartContainerRef = ref(null)
const exportTargetRef = ref(null)
const paperRef = ref(null)
const imageInputRef = ref(null)

const triggerImageUpload = () => {
  imageInputRef.value?.click()
}

const onImageUpload = (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    layoutImage.value = ev.target.result
  }
  reader.readAsDataURL(file)
  e.target.value = ''
}

// 符号映射
const symbolCharMap = {
  operation: '〇',
  transport: '→',
  inspect: '□',
  wait: 'D',
  hold: '▽'
}

// 统计计算
const leftStats = computed(() => {
  const counts = { operation: 0, transport: 0, inspect: 0, wait: 0, hold: 0 }
  steps.value.forEach(step => {
    if (step.leftSymbol && counts[step.leftSymbol] !== undefined) {
      counts[step.leftSymbol]++
    }
  })
  return counts
})

const rightStats = computed(() => {
  const counts = { operation: 0, transport: 0, inspect: 0, wait: 0, hold: 0 }
  steps.value.forEach(step => {
    if (step.rightSymbol && counts[step.rightSymbol] !== undefined) {
      counts[step.rightSymbol]++
    }
  })
  return counts
})

const totalTime = computed(() => steps.value.reduce((sum, s) => sum + (s.time ?? 0), 0))

// 自动合并逻辑（左侧和右侧独立合并）
const leftMerge = computed(() => {
  const groups = []
  let i = 0
  while (i < steps.value.length) {
    const s = steps.value[i]
    let span = 1
    if (s.leftDesc) {
      while (i + span < steps.value.length) {
        const next = steps.value[i + span]
        if (next.leftDesc === s.leftDesc && next.leftSymbol === s.leftSymbol) span++
        else break
      }
    }
    groups.push({ start: i, span })
    i += span
  }
  return groups
})

const rightMerge = computed(() => {
  const groups = []
  let i = 0
  while (i < steps.value.length) {
    const s = steps.value[i]
    let span = 1
    if (s.rightDesc) {
      while (i + span < steps.value.length) {
        const next = steps.value[i + span]
        if (next.rightDesc === s.rightDesc && next.rightSymbol === s.rightSymbol) span++
        else break
      }
    }
    groups.push({ start: i, span })
    i += span
  }
  return groups
})

const shouldRenderLeft = (idx) => leftMerge.value.some(g => g.start === idx)
const getLeftRowspan = (idx) => leftMerge.value.find(g => g.start === idx)?.span || 1
const shouldRenderRight = (idx) => rightMerge.value.some(g => g.start === idx)
const getRightRowspan = (idx) => rightMerge.value.find(g => g.start === idx)?.span || 1

// 方法
const addStep = () => {
  steps.value.push({
    leftDesc: '',
    leftSymbol: 'operation',
    time: 0,
    rightSymbol: 'operation',
    rightDesc: ''
  })
}

const removeStep = (index) => {
  steps.value.splice(index, 1)
}

const deleteLastStep = () => {
  if (steps.value.length > 0) {
    steps.value.pop()
  }
}

const loadExample = () => {
  headerInfo.value = {
    stationName: '臂部组装工站',
    improvement: '现行',
    startState: '零件在料盒中',
    endState: '组装完成放入成品区',
    researcher: '张三',
    date: '2024-03-20',
    method: '手工装配',
    timeUnit: 's'
  }
  steps.value = [
    { leftDesc: '移至组合体', leftSymbol: 'transport', time: 0, rightSymbol: 'transport', rightDesc: '移至短螺栓' },
    { leftDesc: '空闲（持握组合体）', leftSymbol: 'hold', time: 0, rightSymbol: 'operation', rightDesc: '将短螺栓塞入短三孔折板' },
    { leftDesc: '移至短三孔折板', leftSymbol: 'transport', time: 0, rightSymbol: 'transport', rightDesc: '拿取螺母' },
    { leftDesc: '空闲（持握短三孔折板）', leftSymbol: 'hold', time: 0, rightSymbol: 'operation', rightDesc: '用螺母拧紧短螺栓' },
    { leftDesc: '移至组合好的臂', leftSymbol: 'transport', time: 0, rightSymbol: 'transport', rightDesc: '移至堵头' },
    { leftDesc: '空闲（持握臂）', leftSymbol: 'hold', time: 0, rightSymbol: 'operation', rightDesc: '用堵头将L板和三孔连接片组合' },
    { leftDesc: '移至组合好的臂', leftSymbol: 'transport', time: 0, rightSymbol: 'transport', rightDesc: '移至卡头' },
    { leftDesc: '空闲（持握臂）', leftSymbol: 'hold', time: 0, rightSymbol: 'operation', rightDesc: '将卡头塞进堵头' }
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
      onclone: (doc) => {
        const style = doc.createElement('style')
        style.textContent = '* { font-family: "Microsoft YaHei","PingFang SC","Hiragino Sans GB","SimSun",sans-serif !important; }'
        doc.head.appendChild(style)
      }
    })
    const link = document.createElement('a')
    link.href = canvas.toDataURL('image/png')
    link.download = `双手作业分析_经典_${headerInfo.value.stationName || '未命名'}.png`
    link.click()
    ElMessage.success('图片导出成功')
  } catch (e) { ElMessage.error('图片导出失败：' + (e?.message || String(e))) }
}

// ─── 导出 Excel（经典15列布局） ───
const exportExcel = async () => {
  try {
    const workbook = new ExcelJS.Workbook()
    const sheet = workbook.addWorksheet('双手作业分析图')
    sheet.columns = [
      { width: 8 }, { width: 18 },
      { width: 5 }, { width: 5 }, { width: 5 }, { width: 5 }, { width: 5 },
      { width: 7 },
      { width: 5 }, { width: 5 }, { width: 5 }, { width: 5 }, { width: 5 },
      { width: 18 }, { width: 8 }
    ]
    const thin = { style: 'thin', color: { argb: 'FF777777' } }
    const allBorder = { top: thin, left: thin, right: thin, bottom: thin }
    const center = { vertical: 'middle', horizontal: 'center', wrapText: true }
    const headerFill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE8E8E8' } }
    const cjkFont = { name: '宋体', size: 10 }
    const cjkBold = { name: '宋体', size: 10, bold: true }
    const titleFont = { name: '宋体', size: 16, bold: true }
    const symFont = { name: '宋体', size: 10, bold: true }
    const setCell = (r, c, val, font, fill, align) => {
      const cell = sheet.getCell(r, c)
      cell.value = val
      if (font) cell.font = font
      if (fill) cell.fill = fill
      cell.alignment = align || center
    }
    sheet.mergeCells('A1:O1')
    setCell(1, 1, '双手作业分析图', titleFont)
    sheet.getRow(1).height = 34

    const infoStart = 2
    const hi = headerInfo.value
    const infoRows = [
      [['工站名称',2,1],[ hi.stationName||'—',4,0],['改善现场',2,1],[hi.improvement||'—',2,0],['时间单位',2,1],[hi.timeUnit||'s',1,0]],
      [['开始状态',2,1],[ hi.startState||'—',4,0],['结束状态',2,1],[hi.endState||'—',7,0]],
      [['研究者',2,1],[ hi.researcher||'—',2,0],['日期',2,1],[hi.date||'—',2,0],['作业方式',2,1],[hi.method||'—',5,0]]
    ]
    infoRows.forEach((row, ri) => {
      const r = infoStart + ri
      let col = 1
      row.forEach(([text, span, isK]) => {
        if (span > 1) sheet.mergeCells(r, col, r, col + span - 1)
        setCell(r, col, text, isK ? cjkBold : cjkFont, isK ? headerFill : null)
        col += span
      })
      sheet.getRow(r).height = 22
    })

    const hdr1 = infoStart + infoRows.length
    const hdr2 = hdr1 + 1
    sheet.mergeCells(hdr1, 1, hdr1, 7); setCell(hdr1, 1, '左 手', cjkBold, headerFill)
    sheet.mergeCells(hdr1, 8, hdr2, 8); setCell(hdr1, 8, '时间', cjkBold, headerFill)
    sheet.mergeCells(hdr1, 9, hdr1, 15); setCell(hdr1, 9, '右 手', cjkBold, headerFill)
    setCell(hdr2, 1, '单元顺序', cjkBold, headerFill)
    setCell(hdr2, 2, '作业单元说明', cjkBold, headerFill)
    ;['〇','→','□','D','▽'].forEach((h,i) => setCell(hdr2, 3+i, h, symFont, headerFill))
    ;['▽','D','□','→','〇'].forEach((h,i) => setCell(hdr2, 9+i, h, symFont, headerFill))
    setCell(hdr2, 14, '作业单元说明', cjkBold, headerFill)
    setCell(hdr2, 15, '单元顺序', cjkBold, headerFill)
    sheet.getRow(hdr1).height = 24; sheet.getRow(hdr2).height = 24

    const lMap = { operation:3, transport:4, inspect:5, wait:6, hold:7 }
    const rMap = { hold:9, wait:10, inspect:11, transport:12, operation:13 }
    const ds = hdr2 + 1
    const RH = 26
    steps.value.forEach((s, i) => {
      const r = ds + i
      setCell(r, 1, i+1, cjkFont)
      setCell(r, 2, s.leftDesc||'—', cjkFont)
      if (s.leftSymbol && lMap[s.leftSymbol]) setCell(r, lMap[s.leftSymbol], '●', symFont)
      setCell(r, 8, s.time??0, cjkFont)
      if (s.rightSymbol && rMap[s.rightSymbol]) setCell(r, rMap[s.rightSymbol], '●', symFont)
      setCell(r, 14, s.rightDesc||'—', cjkFont)
      setCell(r, 15, i+1, cjkFont)
      sheet.getRow(r).height = RH
    })
    const ldr = ds + Math.max(steps.value.length,1) - 1
    const sr = ldr + 1
    setCell(sr,1,'合计',cjkBold); setCell(sr,2,'',cjkFont)
    setCell(sr,3,leftStats.value.operation,cjkBold)
    setCell(sr,4,leftStats.value.transport,cjkBold)
    setCell(sr,5,leftStats.value.inspect,cjkBold)
    setCell(sr,6,leftStats.value.wait,cjkBold)
    setCell(sr,7,leftStats.value.hold,cjkBold)
    setCell(sr,8,totalTime.value,cjkBold)
    setCell(sr,9,rightStats.value.hold,cjkBold)
    setCell(sr,10,rightStats.value.wait,cjkBold)
    setCell(sr,11,rightStats.value.inspect,cjkBold)
    setCell(sr,12,rightStats.value.transport,cjkBold)
    setCell(sr,13,rightStats.value.operation,cjkBold)
    setCell(sr,14,'',cjkFont); setCell(sr,15,'合计',cjkBold)
    sheet.getRow(sr).height = 26
    for (let r=1;r<=sr;r++) for (let c=1;c<=15;c++) {
      sheet.getCell(r,c).border = allBorder
      if (!sheet.getCell(r,c).alignment) sheet.getCell(r,c).alignment = center
    }
    const buffer = await workbook.xlsx.writeBuffer()
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `双手作业分析_经典_${headerInfo.value.stationName || '导出'}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('Excel 导出成功')
  } catch (e) { ElMessage.error('Excel 导出失败：' + (e?.message || String(e))) }
}

onMounted(() => {
  // 初始 emit 一次,确保父组件即使用户未改动任何字段、直接保存,也能拿到默认数据
  emitData()
})

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
  gap: 10px;
  min-width: 0;
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
  display: none; /* 已移除 Excel 导出按钮 */
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

/* 左侧面板图片上传卡 */
.image-card {
  :deep(.el-card__header) {
    padding: 10px 15px;
    border-bottom: 1px solid #f0f2f5;
  }
  :deep(.el-card__body) {
    padding: 10px;
  }
}

.image-upload-area {
  width: 100%;
  min-height: 100px;
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #fafafa;
  &:hover {
    border-color: #409eff;
    background: #f5f7fa;
  }
}

.upload-preview-img {
  width: 100%;
  max-height: 160px;
  object-fit: contain;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: #bbb;
  font-size: 12px;
}

/* 顶部信息区 */
.flow-top-section {
  padding: 0;
  border-bottom: none;
}

.header-flex {
  display: flex;
  border-bottom: 1px solid #777;
  height: 180px;
}

.flow-info-grid {
  flex: 0 0 55%;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 13px;
  border: none;
  tr {
    height: 36px;
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
  td:first-child {
    border-left: none;
  }
  tr:last-child td {
    border-bottom: none;
  }
  .k {
    width: 80px;
    font-weight: 600;
    background: #f5f5f5;
    white-space: nowrap;
  }
  .v {
    text-align: center;
  }
}

/* 布局图区域 (预览表头右侧) */
.layout-image-area {
  flex: 0 0 45%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f8f8;
  border-left: 1px solid #777;
  overflow: hidden;
  height: 100%;
}

.layout-img {
  width: 100%;
  height: 100%;
  object-fit: fill;
}

.layout-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: #bbb;
  font-size: 11px;
  text-align: center;
  line-height: 1.4;
}

/* 双手作业主表 */
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
  .side-header {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 2px;
  }
  .left-side-header {
    background: #e8e8e8;
  }
  .right-side-header {
    background: #e8e8e8;
  }
  .col-order {
    width: 52px;
    font-size: 12px;
  }
  .col-desc {
    text-align: center;
    min-width: 100px;
  }
  .col-sym {
    width: 32px;
    font-size: 14px;
  }

  .sym-icon {
    width: 20px;
    height: 20px;
    display: block;
    margin: 0 auto;
  }
  .col-time {
    width: 50px;
    font-size: 12px;
  }
  tbody tr {
    height: 32px;
  }
  tfoot tr {
    height: 32px;
  }
  .summary-row {
    td {
      font-weight: 600;
      background: #fafafa;
    }
  }
  /* 与外层总边框共享边线 */
  tr > *:first-child {
    border-left: none;
  }
  tr > *:last-child {
    border-right: none;
  }
  tfoot tr:last-child td {
    border-bottom: none;
  }
}

/* 隐藏表格表头多余padding */
:deep(.el-table .cell) {
  padding: 0 4px;
}
</style>
