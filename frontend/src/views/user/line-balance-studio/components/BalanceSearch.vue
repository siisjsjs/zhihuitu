<script setup lang="ts">
/** 流程优化方式1·平衡寻优：一键自动寻优 → 工位结果 → 保存方案。
 *  已保存方案款式独立，原始方案置顶，其后是逐次优化的方案，便于对比。 */
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import lb, { type OptimizeResult, type Plan } from '@/api/lineBalance'

const props = defineProps<{ styleId: number }>()
const emit = defineEmits<{ (e: 'planSaved', plan: Plan): void }>()

const running = ref(false)
const progress = ref('')
const result = ref<OptimizeResult | null>(null)
const plans = ref<Plan[]>([])
const lastTaskId = ref('')
const chartImg = ref('')
const chartLoading = ref(false)
let timer: number | null = null

/** 优化结果变化时，用合并后的工位时间重绘平衡图（“优化后”对照）。 */
async function loadResultChart(r: OptimizeResult) {
  const stations = r?.stations || []
  if (stations.length < 2) { chartImg.value = ''; return }
  chartLoading.value = true
  try {
    const res = await lb.generateBalanceChart({
      title: '生产线平衡图（优化后）',
      station_names: stations.map((s) => s.stationCode || s.name),
      station_times: stations.map((s) => Number(s.time) || 0),
    })
    chartImg.value = res.image_base64 || ''
  } catch {
    chartImg.value = ''
  } finally {
    chartLoading.value = false
  }
}

watch(result, (r) => {
  if (r) loadResultChart(r)
  else chartImg.value = ''
})

function isBaseline(p: Plan): boolean {
  return !!(p.params && p.params.baseline)
}

function clearTimer() {
  if (timer !== null) { clearInterval(timer); timer = null }
}

async function loadPlans() {
  try {
    const data = await lb.listPlans(props.styleId)
    plans.value = data.list || []
  } catch { /* */ }
}

/** 确保本款存在「原始方案」基线（幂等，作为对比起点）。 */
async function ensureBaseline() {
  try {
    await lb.saveBaseline(props.styleId)
    await loadPlans()
  } catch { /* 无工序时后端会拒绝，忽略 */ }
}

async function startOptimize() {
  running.value = true
  progress.value = '提交任务...'
  result.value = null
  try {
    await ensureBaseline()
    const { taskId } = await lb.optimize(props.styleId)
    lastTaskId.value = taskId
    poll(taskId)
  } catch (e: any) {
    running.value = false
    ElMessage.error(e?.response?.data?.message || e?.message || '寻优提交失败')
  }
}

function poll(taskId: string) {
  clearTimer()
  timer = window.setInterval(async () => {
    try {
      const task = await lb.getOptimizeTask(taskId)
      progress.value = task.progress || task.status
      if (task.status === 'done') {
        clearTimer()
        running.value = false
        result.value = task.result
        ElMessage.success('寻优完成')
      } else if (task.status === 'error') {
        clearTimer()
        running.value = false
        ElMessage.error(task.error || '寻优失败')
      }
    } catch {
      clearTimer()
      running.value = false
    }
  }, 1000)
}

async function savePlan() {
  if (!lastTaskId.value || !result.value) return
  try {
    const plan = await lb.savePlan(props.styleId, lastTaskId.value)
    ElMessage.success(`方案已保存：${plan.name}`)
    await loadPlans()
    emit('planSaved', plan)
  } catch { /* */ }
}

function selectPlan(p: Plan) {
  emit('planSaved', p)
}

onMounted(loadPlans)
onUnmounted(clearTimer)
// 切换款式：清空上一款的寻优结果/图表/任务，重新拉取本款方案，确保款式间数据独立。
watch(() => props.styleId, () => {
  clearTimer()
  running.value = false
  progress.value = ''
  result.value = null
  lastTaskId.value = ''
  chartImg.value = ''
  loadPlans()
})
defineExpose({ reload: loadPlans })
</script>

<template>
  <div>
    <div style="display:flex;gap:12px;align-items:center;margin-bottom:12px;padding:10px;background:#f8fafc;border-radius:8px">
      <el-button type="primary" :loading="running" @click="startOptimize">一键自动寻优</el-button>
      <span style="color:#64748b;font-size:13px">按工艺流向自动合并工序、最小化工位数并最大化平衡率，无需手填目标产量/工时。</span>
    </div>

    <el-alert v-if="running" type="info" :closable="false" style="margin-bottom:12px">
      {{ progress }}
    </el-alert>

    <div v-if="result" style="margin-bottom:16px">
      <el-descriptions :column="3" border size="small" style="margin-bottom:10px">
        <el-descriptions-item label="平衡率">{{ (result.balanceRate * 100).toFixed(1) }}%</el-descriptions-item>
        <el-descriptions-item label="工位数">{{ result.stations.length }}</el-descriptions-item>
        <el-descriptions-item label="节拍(s)">{{ result.kpi.takt ?? '-' }}</el-descriptions-item>
      </el-descriptions>
      <el-tag v-if="result.timeoutReached" type="warning" style="margin-bottom:8px">达到时间上限，结果为近似最优</el-tag>

      <div v-loading="chartLoading" style="border:1px solid #e2e8f0;border-radius:8px;background:#fff;padding:8px;text-align:center;min-height:120px;margin-bottom:10px">
        <img v-if="chartImg" :src="chartImg" style="max-width:100%" />
        <div v-else style="color:#cbd5e1;padding:24px">优化后平衡图生成中…</div>
      </div>

      <el-table :data="result.stations" border size="small" max-height="320">
        <el-table-column prop="stationCode" label="工位" width="100" />
        <el-table-column prop="time" label="工时(s)" width="100" />
        <el-table-column label="合并工序" min-width="220">
          <template #default="{ row }">{{ (row.mergeNames || []).join(' + ') }}</template>
        </el-table-column>
      </el-table>

      <el-button type="success" style="margin-top:10px" @click="savePlan">保存为方案</el-button>
    </div>

    <div>
      <div style="font-weight:600;margin:8px 0;color:#334155">
        已保存方案 <span style="font-weight:400;color:#94a3b8;font-size:12px">（本款式独立 · 原始方案置顶，其后为逐次优化）</span>
      </div>
      <el-table :data="plans" border size="small" empty-text="暂无方案，点「一键自动寻优」开始">
        <el-table-column label="方案名" min-width="220">
          <template #default="{ row }">
            <el-tag v-if="isBaseline(row)" type="info" size="small" effect="plain" style="margin-right:6px">原始</el-tag>
            {{ row.name }}
          </template>
        </el-table-column>
        <el-table-column prop="takt" label="节拍(s)" width="90" />
        <el-table-column label="平衡率" width="90">
          <template #default="{ row }">{{ row.balanceRate != null ? (row.balanceRate * 100).toFixed(1) + '%' : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="selectPlan(row)">选用 →</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>
