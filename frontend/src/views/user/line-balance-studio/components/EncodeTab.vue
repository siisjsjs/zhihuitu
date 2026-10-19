<script setup lang="ts">
/** 工序编码：实时根据当前工序生成点分编码 + DAG 校验（仅查环 / 缺失上游）+ 编码树 + 确认落库。
 *  工序录入改动后切到本页会自动重算，无需手动点「生成编码」。 */
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import lb, { type EncodePreview, type ProcessTree as ProcessTreeData } from '@/api/lineBalance'
import ProcessTree from './ProcessTree.vue'

const props = defineProps<{ styleId: number }>()
const emit = defineEmits<{ (e: 'confirmed'): void }>()

const preview = ref<EncodePreview | null>(null)
const tree = ref<ProcessTreeData | null>(null)
const loading = ref(false)
const confirming = ref(false)

const terminals = computed<string[]>(() => {
  const p = preview.value
  if (!p) return []
  if (p.terminals && p.terminals.length) return p.terminals
  return p.terminal ? [p.terminal] : []
})

async function runEncode(silent = false) {
  loading.value = true
  try {
    const [p, t] = await Promise.all([
      lb.encode(props.styleId),
      lb.processTree(props.styleId),
    ])
    preview.value = p
    tree.value = t
    if (!p.ok && !silent) ElMessage.warning('编码校验未通过：存在环路或上游编码缺失')
  } catch { /* */ } finally {
    loading.value = false
  }
}

async function confirm() {
  if (!preview.value?.ok) { ElMessage.warning('校验未通过，无法确认'); return }
  confirming.value = true
  try {
    const res = await lb.confirmEncode(props.styleId)
    ElMessage.success(`编码已确认（结束点 ${res.terminal}）`)
    emit('confirmed')
  } catch { /* */ } finally {
    confirming.value = false
  }
}

watch(() => props.styleId, () => runEncode(true))
onMounted(() => runEncode(true))
defineExpose({ reload: () => runEncode(true) })
</script>

<template>
  <div>
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
      <el-button :loading="loading" @click="runEncode(false)">刷新编码</el-button>
      <el-button type="success" @click="confirm" :loading="confirming" :disabled="!preview?.ok">确认编码</el-button>
      <el-tag v-if="preview" :type="preview.ok ? 'success' : 'danger'" style="margin-left:8px">
        {{ preview.ok ? `校验通过 · 结束点 ${terminals.join(' / ') || '-'}` : '校验未通过' }}
      </el-tag>
      <span style="color:#94a3b8;font-size:12px">编码随工序录入实时更新</span>
    </div>

    <el-alert
      v-if="preview?.ok"
      type="info"
      :closable="false"
      style="margin-bottom:12px"
      title="支持 DAG 工艺关系：允许分叉（一上游对多下游）、汇合（多上游对一下游）与多个结束点。仅在出现环路或上游编码不存在时报错。"
    />

    <el-alert v-if="preview && !preview.ok" type="error" :closable="false" style="margin-bottom:12px">
      <ul style="margin:0;padding-left:18px">
        <li v-for="(e, i) in preview.errors" :key="i">{{ e }}</li>
      </ul>
    </el-alert>

    <div v-if="tree" style="margin-bottom:16px">
      <div style="font-weight:600;margin-bottom:6px;color:#334155">编码树</div>
      <ProcessTree :nodes="tree.nodes" :edges="tree.edges" />
    </div>

    <el-table v-if="preview" :data="preview.processes" border size="small" max-height="360">
      <el-table-column label="工序编码" width="130">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.genCode || row.originalCode || '-' }}</el-tag>
          <span v-if="row.genCode && row.originalCode && row.genCode !== row.originalCode"
            style="color:#94a3b8;font-size:11px;margin-left:4px">（原 {{ row.originalCode }}）</span>
        </template>
      </el-table-column>
      <el-table-column prop="genUpstream" label="编码上游" width="130">
        <template #default="{ row }">{{ row.genUpstream || '-' }}</template>
      </el-table-column>
      <el-table-column prop="processName" label="名称" min-width="140" />
      <el-table-column prop="sam" label="SAM(s)" width="90" />
      <el-table-column label="负荷占比" width="100">
        <template #default="{ row }">{{ row.loadRatio ?? '-' }}%</template>
      </el-table-column>
      <el-table-column label="分段标记" width="110">
        <template #default="{ row }">
          <el-tag v-if="row.isBottleneck" type="danger" size="small">瓶颈保护</el-tag>
          <el-tag v-else-if="row.segmentReason" type="warning" size="small">{{ row.segmentReason }}</el-tag>
          <span v-else style="color:#cbd5e1">-</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
