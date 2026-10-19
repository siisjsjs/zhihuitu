<script setup lang="ts">
/** SOP：工位装配信息补录（实时自动保存）+ 单工位 Excel 导出 + 批量 Excel（进度轮询）。
 *  合并工序名（累加）可在此直接编辑，保存后回流到树状图与 SOP。 */
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import lb, { type Station, type Plan, type EquipmentItem } from '@/api/lineBalance'
import { resolveApiStaticUrl } from '@/utils/apiStatic'

const props = defineProps<{ plan: Plan | null; styleId: number }>()

const stations = ref<Station[]>([])
const activeId = ref<number | null>(null)
const form = ref<Partial<Station>>({})
const equipment = ref<EquipmentItem[]>([])
// 工序名称（单行；多道工序合并时以「 + 」连接），编辑后回流到树状图与 SOP
const mergeNamesText = ref('')
// 操作说明各段：与「设备及工具」一致的逐行编辑（每行一个输入框，可增删）
const lines = reactive<Record<string, string[]>>({
  check: [], main: [], notes: [], selfCheck: [], tech: [],
})
// 段配置：key 对应 lines / 对应后端字段
const SECTIONS = [
  { key: 'check', field: 'checkSteps', label: '检查工序', placeholder: '开工前需检查的项目，每行一条' },
  { key: 'main', field: 'mainSteps', label: '本工序作业', placeholder: '本工位作业内容，每行一步（留空则自动用合并工序名占位）' },
  { key: 'notes', field: 'notes', label: '注意事项', placeholder: '作业注意事项，每行一条' },
  { key: 'selfCheck', field: 'selfCheck', label: '自检', placeholder: '完工自检项目，每行一条' },
  { key: 'tech', field: 'techReq', label: '技术要求', placeholder: '技术 / 品质要求，每行一条' },
] as const

function strToLines(s: string | null | undefined): string[] {
  if (!s) return []
  return String(s).replace(/\r\n/g, '\n').replace(/\r/g, '\n')
    .split('\n').map((x) => x.trim()).filter(Boolean)
}
function addLine(key: string) { lines[key].push('') }
function removeLine(key: string, i: number) { lines[key].splice(i, 1) }
const saving = ref(false)
const saveHint = ref('')
// 流程优化可跳过：未选用方案时用基础方案（每工序一工位，不合并）
const localPlan = ref<Plan | null>(null)
const baselineLoading = ref(false)
// 自动保存：选中工位/初始化加载期间不触发，避免空表覆盖
let loadingStation = false
let autoSaveTimer: number | null = null

function activePlan(): Plan | null { return props.plan ?? localPlan.value }

async function genBaseline() {
  baselineLoading.value = true
  try {
    const p = await lb.saveBaseline(props.styleId)
    localPlan.value = p
    ElMessage.success('已生成基础方案（每工序一工位）')
    await loadStations()
  } catch { /* */ } finally {
    baselineLoading.value = false
  }
}

const batchRunning = ref(false)
const batchProgress = ref('')
const batchUrl = ref('')
let timer: number | null = null

function clearTimer() { if (timer !== null) { clearInterval(timer); timer = null } }
function clearAutoSave() { if (autoSaveTimer !== null) { clearTimeout(autoSaveTimer); autoSaveTimer = null } }

async function loadStations() {
  const plan = activePlan()
  if (!plan) { stations.value = []; return }
  const data = await lb.planStations(plan.id)
  stations.value = data.stations || []
  if (stations.value.length) selectStation(stations.value[0].id)
}

function detailToText(detail: any[] | null | undefined): string {
  if (!Array.isArray(detail)) return ''
  return detail
    .map((d: any) => (typeof d === 'string' ? d : d?.name || d?.processName || d?.genCode || d?.originalCode || ''))
    .filter(Boolean)
    .join(' + ')
}

async function selectStation(id: number) {
  clearAutoSave()
  loadingStation = true
  activeId.value = id
  const st = await lb.getStation(id)
  form.value = {
    workerCount: st.workerCount ?? null,
    workType: st.workType ?? '',
    processSeq: st.processSeq ?? null,
    approver: st.approver ?? '',
    reviewer: st.reviewer ?? '',
    department: st.department ?? '',
    ownerName: st.ownerName ?? '',
    fileNo: st.fileNo ?? '',
    version: st.version ?? '',
  }
  lines.check = strToLines(st.checkSteps)
  lines.main = strToLines(st.mainSteps)
  lines.notes = strToLines(st.notes)
  lines.selfCheck = strToLines(st.selfCheck)
  lines.tech = strToLines(st.techReq)
  mergeNamesText.value = detailToText(st.processDetail)
  equipment.value = Array.isArray(st.equipment) ? st.equipment.map((e) => ({ ...e })) : []
  // 让本次赋值不触发自动保存
  setTimeout(() => { loadingStation = false }, 0)
}

function addEquip() { equipment.value.push({ name: '', model: '', condition: '' }) }
function removeEquip(i: number) { equipment.value.splice(i, 1) }

async function persistInfo(silent = false) {
  if (activeId.value == null) return
  saving.value = true
  try {
    const processDetail = mergeNamesText.value
      .split(/\s*\+\s*|[，,\n]/)
      .map((s) => s.trim())
      .filter(Boolean)
    const sectionPayload: Record<string, string> = {}
    for (const sec of SECTIONS) {
      sectionPayload[sec.field] = lines[sec.key].map((s) => s.trim()).filter(Boolean).join('\n')
    }
    await lb.updateStationInfo(activeId.value, {
      ...form.value,
      ...sectionPayload,
      processDetail,
      equipment: equipment.value.filter((e) => e.name || e.model || e.condition),
    })
    // 同步侧栏人数显示
    const cur = stations.value.find((s) => s.id === activeId.value)
    if (cur && form.value.workerCount != null) cur.workerCount = form.value.workerCount
    saveHint.value = '已自动保存 ' + new Date().toLocaleTimeString()
    if (!silent) ElMessage.success('工位信息已保存')
  } catch { /* */ } finally {
    saving.value = false
  }
}

function scheduleAutoSave() {
  if (loadingStation || activeId.value == null) return
  saveHint.value = '编辑中…'
  clearAutoSave()
  autoSaveTimer = window.setTimeout(() => persistInfo(true), 800)
}

watch([form, equipment, mergeNamesText, lines], scheduleAutoSave, { deep: true })

async function genXlsx() {
  if (activeId.value == null) return
  try {
    // 导出前先确保最新编辑已落库
    clearAutoSave()
    await persistInfo(true)
    const res = await lb.generateSingleXlsx(activeId.value)
    window.open(resolveApiStaticUrl(res.url), '_blank')
    ElMessage.success('Excel SOP 已生成')
  } catch { /* */ }
}

async function startBatch() {
  const plan = activePlan()
  if (!plan) return
  batchRunning.value = true
  batchProgress.value = '提交任务...'
  batchUrl.value = ''
  try {
    const { taskId } = await lb.batchSop(plan.id, { fmt: 'xlsx' })
    pollBatch(taskId)
  } catch {
    batchRunning.value = false
  }
}

function pollBatch(taskId: string) {
  clearTimer()
  timer = window.setInterval(async () => {
    try {
      const task = await lb.getSopTask(taskId)
      batchProgress.value = task.progress || task.status
      if (task.status === 'done') {
        clearTimer()
        batchRunning.value = false
        batchUrl.value = resolveApiStaticUrl(task.result?.url || '')
        ElMessage.success('批量 SOP 生成完成')
      } else if (task.status === 'error') {
        clearTimer()
        batchRunning.value = false
        ElMessage.error(task.error || '生成失败')
      }
    } catch {
      clearTimer()
      batchRunning.value = false
    }
  }, 1000)
}

watch(() => props.plan?.id, () => { activeId.value = null; localPlan.value = null; loadStations() })
watch(() => props.styleId, () => { activeId.value = null; localPlan.value = null; loadStations() })
onMounted(loadStations)
onUnmounted(() => { clearTimer(); clearAutoSave() })
defineExpose({ reload: loadStations })
</script>

<template>
  <div>
    <div v-if="!activePlan()">
      <el-alert type="info" :closable="false" style="margin-bottom:12px">
        流程优化可跳过。未选用优化方案时，可直接生成「基础方案」——每道工序对应一个工位（不做合并），
        之后照常补录工位信息并导出 SOP。若需要更高平衡率，请回到「流程优化」选用方案。
      </el-alert>
      <el-button type="primary" :loading="baselineLoading" @click="genBaseline">
        生成基础方案并开始 SOP
      </el-button>
    </div>

    <template v-else>
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;padding:10px;background:#f8fafc;border-radius:8px">
        <span style="font-weight:600;color:#334155">批量导出：</span>
        <el-button type="primary" size="small" :loading="batchRunning" @click="startBatch">全部工位导出 Excel（多 Sheet）</el-button>
        <span v-if="batchRunning" style="color:#2563eb;font-size:13px">{{ batchProgress }}</span>
        <el-link v-if="batchUrl" type="success" :href="batchUrl" target="_blank" style="margin-left:8px">下载结果 ↓</el-link>
      </div>

      <div style="display:flex;gap:16px">
        <div style="width:200px;flex:none">
          <div style="font-weight:600;margin-bottom:6px;color:#334155">工位</div>
          <div style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden">
            <div v-for="s in stations" :key="s.id" @click="selectStation(s.id)"
              :style="{ padding:'8px 12px', cursor:'pointer', fontSize:'13px', borderBottom:'1px solid #f1f5f9',
                        background: activeId === s.id ? '#eff6ff' : '#fff',
                        color: activeId === s.id ? '#2563eb' : '#475569', fontWeight: activeId === s.id ? 600 : 400 }">
              {{ s.stationCode }} · {{ s.workerCount }}人
            </div>
          </div>
        </div>

        <div style="flex:1;min-width:0" v-if="activeId != null">
          <el-form label-width="90px" label-position="top">
            <el-form-item label="工序名称">
              <el-input v-model="mergeNamesText" placeholder="如：车架合装 + 水罐安装" />
            </el-form-item>
            <div style="display:flex;gap:12px">
              <el-form-item label="工序排号" style="width:120px;flex:none">
                <el-input-number v-model="form.processSeq" :min="1" :step="1" controls-position="right" placeholder="如 2" style="width:100%" />
              </el-form-item>
              <el-form-item label="本工位人数" style="width:120px;flex:none">
                <el-input-number v-model="form.workerCount" :min="1" :step="1" controls-position="right" style="width:100%" />
              </el-form-item>
              <el-form-item label="作业类型" style="flex:1">
                <el-input v-model="form.workType" placeholder="如 装配 / 检测" />
              </el-form-item>
            </div>

            <el-form-item v-for="sec in SECTIONS" :key="sec.key" :label="sec.label">
              <div style="width:100%">
                <div v-for="(_, i) in lines[sec.key]" :key="i"
                  style="display:flex;gap:8px;margin-bottom:6px;align-items:center">
                  <span style="color:#94a3b8;font-size:12px;width:20px;text-align:right">{{ i + 1 }}.</span>
                  <el-input v-model="lines[sec.key][i]" :placeholder="sec.placeholder" style="flex:1" />
                  <el-button text type="danger" @click="removeLine(sec.key, i)">删除</el-button>
                </div>
                <el-button size="small" @click="addLine(sec.key)">+ 添加一行</el-button>
              </div>
            </el-form-item>

            <el-form-item label="设备及工具">
              <div style="width:100%">
                <div v-for="(e, i) in equipment" :key="i"
                  style="display:flex;gap:8px;margin-bottom:6px">
                  <el-input v-model="e.name" placeholder="设备/工装名称" style="flex:1" />
                  <el-input v-model="e.model" placeholder="型号" style="width:140px" />
                  <el-input v-model="e.condition" placeholder="设定条件" style="width:140px" />
                  <el-button text type="danger" @click="removeEquip(i)">删除</el-button>
                </div>
                <el-button size="small" @click="addEquip">+ 添加设备</el-button>
              </div>
            </el-form-item>

            <div style="display:flex;gap:12px">
              <el-form-item label="核准" style="flex:1">
                <el-input v-model="form.approver" placeholder="核准人" />
              </el-form-item>
              <el-form-item label="审核" style="flex:1">
                <el-input v-model="form.reviewer" placeholder="审核人" />
              </el-form-item>
              <el-form-item label="部门" style="flex:1">
                <el-input v-model="form.department" placeholder="部门" />
              </el-form-item>
              <el-form-item label="负责人" style="flex:1">
                <el-input v-model="form.ownerName" placeholder="负责人" />
              </el-form-item>
            </div>
            <div style="display:flex;gap:12px">
              <el-form-item label="文件编号" style="flex:1">
                <el-input v-model="form.fileNo" placeholder="文件编号" />
              </el-form-item>
              <el-form-item label="版本号" style="width:120px;flex:none">
                <el-input v-model="form.version" placeholder="如 A" />
              </el-form-item>
            </div>
          </el-form>
          <div style="display:flex;gap:8px;align-items:center">
            <el-button type="primary" plain @click="genXlsx">导出 Excel</el-button>
            <span style="color:#94a3b8;font-size:12px">{{ saveHint || '修改后自动保存' }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
