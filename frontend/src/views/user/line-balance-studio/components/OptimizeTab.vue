<script setup lang="ts">
/** 流程优化（可跳过）：先展示当前编码树（含物料）+ 生产线平衡图，
 *  再由用户选择优化方式：①平衡寻优（自动合并工位）②双手作业优化（逐工序动作分析）。 */
import { ref, computed, onMounted, watch } from 'vue'
import lb, { type EncodePreview, type ProcessTree as ProcessTreeData, type Plan, type TreeNode, type TreeEdge } from '@/api/lineBalance'
import { useLineBalanceStore } from '@/stores/lineBalance'
import { useUserStore } from '@/stores/user'
import ProcessTree from './ProcessTree.vue'
import BalanceSearch from './BalanceSearch.vue'
import TwoHandTab from './TwoHandTab.vue'

const props = defineProps<{ styleId: number }>()
const emit = defineEmits<{ (e: 'planSaved', plan: Plan): void }>()

// 双手作业优化尚未完善，仅管理员可见；普通用户只用「平衡寻优」。
const isAdmin = computed(() => useUserStore().userInfo?.role === 'admin')

const store = useLineBalanceStore()
const preview = ref<EncodePreview | null>(null)
const tree = ref<ProcessTreeData | null>(null)
// 优化后工位树（有方案时优先展示）；null=展示原始编码树
const optimizedTree = ref<{ nodes: TreeNode[]; edges: TreeEdge[] } | null>(null)
const treePlanName = ref('')
const chartImg = ref('')
const chartLoading = ref(false)
const chartIsOptimized = ref(false)
const chartPlanName = ref('')
const loading = ref(false)
// null=方式选择页；'balance'=平衡寻优；'twohand'=双手作业优化
const method = ref<'balance' | 'twohand' | null>(null)
// 请求令牌：切换款式时自增，丢弃旧款式迟到的异步结果，避免把旧数据写回界面。
let loadToken = 0

/** 清空本款展示状态，避免切换款式时残留上一款的树/平衡图。 */
function resetOverview() {
  preview.value = null
  tree.value = null
  optimizedTree.value = null
  treePlanName.value = ''
  chartImg.value = ''
  chartIsOptimized.value = false
  chartPlanName.value = ''
}

async function loadOverview() {
  const token = ++loadToken
  resetOverview()
  loading.value = true
  try {
    const sid = props.styleId
    const [p, t] = await Promise.all([
      lb.encode(sid),
      lb.processTree(sid),
    ])
    if (token !== loadToken) return  // 已切到别的款式，丢弃本次结果
    preview.value = p
    tree.value = t
    await loadChart(p, token)
  } catch { /* */ } finally {
    if (token === loadToken) loading.value = false
  }
}

/** 概览平衡图：优先画「已选用/最近方案」的优化后工位图，无方案时退回原始工序图。 */
async function loadChart(p: EncodePreview, token: number) {
  chartLoading.value = true
  try {
    const plan = await pickPlan()
    if (token !== loadToken) return
    if (plan) {
      const { stations } = await lb.planStations(plan.id)
      if (token !== loadToken) return
      const valid = (stations || []).filter((s) => Number(s.stationTakt) > 0)
      if (valid.length) {
        buildStationTree(valid, plan.name)
        const res = await lb.generateBalanceChart({
          title: `生产线平衡图（优化后·${plan.name}）`,
          station_names: valid.map((s) => s.stationCode),
          station_times: valid.map((s) => Number(s.stationTakt) || 0),
        })
        if (token !== loadToken) return
        chartImg.value = res.image_base64 || ''
        chartIsOptimized.value = true
        chartPlanName.value = plan.name
        return
      }
    }
    // 无方案：画原始工序图，编码树退回原始
    optimizedTree.value = null
    treePlanName.value = ''
    chartIsOptimized.value = false
    chartPlanName.value = ''
    const procs = p?.processes || []
    if (!procs.length) { chartImg.value = ''; return }
    const res = await lb.generateBalanceChart({
      title: '生产线平衡图（优化前）',
      station_names: procs.map((x) => x.genCode || x.originalCode || x.processName),
      station_times: procs.map((x) => Number(x.sam) || 0),
    })
    if (token !== loadToken) return
    // 后端 image_base64 已带 data:image/png;base64, 前缀，直接使用即可
    chartImg.value = res.image_base64 || ''
  } catch {
    chartImg.value = ''
  } finally {
    chartLoading.value = false
  }
}

/** 选用于绘图的方案：已选用方案优先，否则取该款最近一个方案。 */
async function pickPlan(): Promise<Plan | null> {
  const cur = store.currentPlan
  if (cur && (cur as any).id) return cur
  try {
    const { plan } = await lb.selectedPlan(props.styleId)
    if (plan) return plan
    const { list } = await lb.listPlans(props.styleId)
    if (!list || !list.length) return null
    // 列表按时间倒序，取最新的非基线方案；都为基线则取第一个
    return list.find((p) => !(p.params && p.params.baseline)) || list[0]
  } catch {
    return null
  }
}

/** 把方案工位列表转成「工位树」：每个工位一个节点，节点内列出归并的工序明细，
 *  按 upstream/downstream 链路连边，让编码树同步反映优化后的工位划分。
 *  processDetail 为合并工序名字符串数组（累加后的工序名）。 */
function buildStationTree(stations: any[], planName: string) {
  const nodes: TreeNode[] = stations.map((s) => {
    const details = Array.isArray(s.processDetail) ? s.processDetail : []
    const names = details
      .map((d: any) => (typeof d === 'string' ? d : d?.processName || d?.genCode || d?.originalCode || ''))
      .filter(Boolean)
    return {
      id: String(s.stationCode),
      genCode: s.stationCode,
      name: names.length ? names.join('、') : s.stationCode,
      sam: Number(s.stationTakt) || 0,
      loadRatio: null,
      isBottleneck: false,
      segmentReason: null,
    }
  })
  const codes = new Set(nodes.map((n) => n.id))
  const edges: TreeEdge[] = []
  stations.forEach((s) => {
    const up = s.upstreamStation
    if (up && codes.has(String(up))) edges.push({ source: String(up), target: String(s.stationCode) })
  })
  optimizedTree.value = { nodes, edges }
  treePlanName.value = planName
}

function pick(m: 'balance' | 'twohand') {
  method.value = m
}
function back() {
  method.value = null
  loadOverview()
}

function onPlanSaved(plan: Plan) {
  emit('planSaved', plan)
}

watch(() => props.styleId, () => { method.value = null; loadOverview() })
onMounted(loadOverview)
defineExpose({ reload: () => { if (method.value === null) loadOverview() } })
</script>

<template>
  <div>
    <!-- 概览页：编码树 + 平衡图 + 方式选择 -->
    <template v-if="method === null">
      <el-alert type="info" :closable="false" style="margin-bottom:12px">
        这一步<b>可跳过</b>，直接到 SOP 也能出图（按基础方案：每工序一工位）。
        如需提升平衡率或细化动作，选择下面任一优化方式。
      </el-alert>

      <div v-if="preview && !preview.ok" style="margin-bottom:12px">
        <el-alert type="warning" :closable="false">
          当前编码未通过校验，建议先到「工序编码」修正后再优化。
        </el-alert>
      </div>

      <div v-if="optimizedTree || tree" style="margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:6px;color:#334155;display:flex;align-items:center;gap:8px">
          <template v-if="optimizedTree">
            工位树
            <el-tag type="success" size="small">优化后 · {{ treePlanName }}</el-tag>
          </template>
          <template v-else>
            当前编码树（节点含已关联物料）
            <el-tag size="small" type="info" effect="plain">优化前现状</el-tag>
          </template>
        </div>
        <ProcessTree
          v-if="optimizedTree"
          :nodes="optimizedTree.nodes"
          :edges="optimizedTree.edges"
        />
        <ProcessTree v-else-if="tree" :nodes="tree.nodes" :edges="tree.edges" />
      </div>

      <div style="margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:6px;color:#334155;display:flex;align-items:center;gap:8px">
          生产线平衡图
          <el-tag v-if="chartIsOptimized" type="success" size="small">优化后 · {{ chartPlanName }}</el-tag>
          <el-tag v-else size="small" type="info" effect="plain">优化前现状</el-tag>
        </div>
        <div v-loading="chartLoading" style="border:1px solid #e2e8f0;border-radius:8px;background:#fff;padding:8px;text-align:center;min-height:120px">
          <img v-if="chartImg" :src="chartImg" style="max-width:100%" />
          <div v-else style="color:#cbd5e1;padding:24px">暂无可绘制的工序时间数据</div>
        </div>
      </div>

      <div style="font-weight:600;margin:12px 0 8px;color:#334155">选择优化方式</div>
      <div style="display:flex;gap:16px;flex-wrap:wrap">
        <div @click="pick('balance')"
          style="flex:1;min-width:280px;border:1px solid #e2e8f0;border-radius:10px;padding:18px;cursor:pointer;transition:.15s"
          onmouseover="this.style.borderColor='#2563eb'" onmouseout="this.style.borderColor='#e2e8f0'">
          <div style="font-size:16px;font-weight:700;color:#0f172a;margin-bottom:6px">① 平衡寻优</div>
          <div style="color:#64748b;font-size:13px;line-height:1.6">
            按工艺流向自动合并工序、最小化工位数并最大化平衡率，生成可选用的方案。
          </div>
          <el-button type="primary" plain size="small" style="margin-top:12px">选用 →</el-button>
        </div>

        <div @click="pick('twohand')" v-if="isAdmin"
          style="flex:1;min-width:280px;border:1px solid #e2e8f0;border-radius:10px;padding:18px;cursor:pointer;transition:.15s"
          onmouseover="this.style.borderColor='#2563eb'" onmouseout="this.style.borderColor='#e2e8f0'">
          <div style="font-size:16px;font-weight:700;color:#0f172a;margin-bottom:6px">② 双手作业优化</div>
          <div style="color:#64748b;font-size:13px;line-height:1.6">
            逐工序回放作业视频、切片对照，填写双手作业分析图，细化单工序动作改善。
          </div>
          <el-button type="primary" plain size="small" style="margin-top:12px">选用 →</el-button>
        </div>
      </div>
    </template>

    <!-- 方式1：平衡寻优 -->
    <template v-else-if="method === 'balance'">
      <el-button link type="primary" style="margin-bottom:8px" @click="back">← 返回优化方式</el-button>
      <BalanceSearch :style-id="styleId" @plan-saved="onPlanSaved" />
    </template>

    <!-- 方式2：双手作业优化 -->
    <template v-else>
      <el-button link type="primary" style="margin-bottom:8px" @click="back">← 返回优化方式</el-button>
      <TwoHandTab :style-id="styleId" />
    </template>
  </div>
</template>
