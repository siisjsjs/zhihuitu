<script setup lang="ts">
/** 产线平衡 / SOP 工作台：款式选择 → 工序 → 编码 → 寻优 → 裁片 → SOP。 */
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useLineBalanceStore } from '@/stores/lineBalance'
import lb, { type Style, type Plan } from '@/api/lineBalance'
import ProcessTab from './components/ProcessTab.vue'
import EncodeTab from './components/EncodeTab.vue'
import OptimizeTab from './components/OptimizeTab.vue'
import CutPieceTab from './components/CutPieceTab.vue'
import SopTab from './components/SopTab.vue'

const store = useLineBalanceStore()
const styles = ref<Style[]>([])
const activeTab = ref('process')
const createVisible = ref(false)
const newStyle = ref<Partial<Style>>({ styleCode: '', name: '', taktTime: undefined })

const encodeRef = ref<{ reload: () => void } | null>(null)
const optimizeRef = ref<{ reload: () => void } | null>(null)
const cutpieceRef = ref<{ reload: () => void } | null>(null)

/** 切到「编码 / 裁片 / 优化」页时刷新，确保工序录入的改动实时反映。 */
function onTabChange(name: string | number) {
  if (name === 'encode') encodeRef.value?.reload()
  else if (name === 'optimize') optimizeRef.value?.reload()
  else if (name === 'cutpiece') cutpieceRef.value?.reload()
}

async function loadStyles() {
  const data = await lb.listStyles({ page: 1, pageSize: 100 })
  styles.value = data.list || []
}

function pickStyle(s: Style) {
  store.setStyle(s)
  activeTab.value = 'process'
}

async function createStyle() {
  if (!newStyle.value.styleCode || !newStyle.value.name) {
    ElMessage.warning('请填写款号和名称'); return
  }
  try {
    const s = await lb.createStyle(newStyle.value)
    ElMessage.success('款式已创建')
    createVisible.value = false
    newStyle.value = { styleCode: '', name: '', taktTime: undefined }
    await loadStyles()
    pickStyle(s)
  } catch { /* */ }
}

async function delStyle(s: Style) {
  await ElMessageBox.confirm(`删除款式 ${s.styleCode}（含工序）？`, '确认', { type: 'warning' })
  await lb.deleteStyle(s.id)
  if (store.currentStyle?.id === s.id) store.reset()
  await loadStyles()
}

function onPlanSaved(plan: Plan) {
  store.selectPlan(plan)
  ElMessage.success(`已选用方案：${plan.name}`)
}

onMounted(loadStyles)
</script>

<template>
  <div style="display:flex;height:calc(100vh - 56px)">
    <!-- 左侧款式列表 -->
    <aside style="width:240px;flex:none;border-right:1px solid #e2e8f0;background:#fff;display:flex;flex-direction:column">
      <div style="padding:14px 16px;border-bottom:1px solid #f1f5f9;display:flex;align-items:center">
        <span style="font-weight:700;color:#0f172a">款式</span>
        <el-button type="primary" size="small" style="margin-left:auto" @click="createVisible = true">新建</el-button>
      </div>
      <div style="flex:1;overflow-y:auto">
        <div v-for="s in styles" :key="s.id" @click="pickStyle(s)"
          :style="{ padding:'12px 16px', cursor:'pointer', borderBottom:'1px solid #f8fafc',
                    background: store.currentStyle?.id === s.id ? '#eff6ff' : '#fff' }">
          <div style="display:flex;align-items:center">
            <span :style="{ fontWeight:600, fontSize:'14px', color: store.currentStyle?.id === s.id ? '#2563eb' : '#1e293b' }">{{ s.styleCode }}</span>
            <el-button link type="danger" size="small" style="margin-left:auto" @click.stop="delStyle(s)">删</el-button>
          </div>
          <div style="font-size:12px;color:#94a3b8;margin-top:2px">{{ s.name }}</div>
        </div>
        <div v-if="!styles.length" style="padding:24px;text-align:center;color:#cbd5e1;font-size:13px">暂无款式</div>
      </div>
    </aside>

    <!-- 右侧工作区 -->
    <main style="flex:1;min-width:0;display:flex;flex-direction:column;overflow:hidden">
      <div v-if="!store.currentStyle" style="flex:1;display:flex;align-items:center;justify-content:center;color:#94a3b8">
        请选择或新建一个款式开始
      </div>
      <template v-else>
        <div style="padding:14px 20px;border-bottom:1px solid #e2e8f0;background:#fff;display:flex;align-items:center;gap:12px">
          <h2 style="margin:0;font-size:18px;color:#0f172a">{{ store.currentStyle.name }}</h2>
          <el-tag effect="plain">{{ store.currentStyle.styleCode }}</el-tag>
          <el-tag v-if="store.currentPlan" type="success">方案：{{ store.currentPlan.name }}</el-tag>
        </div>

        <div style="flex:1;overflow-y:auto;padding:16px 20px">
          <el-tabs v-model="activeTab" @tab-change="onTabChange">
            <el-tab-pane label="1·工序录入" name="process">
              <ProcessTab :style-id="store.currentStyle.id" />
            </el-tab-pane>
            <el-tab-pane label="2·工序编码" name="encode">
              <EncodeTab ref="encodeRef" :style-id="store.currentStyle.id" />
            </el-tab-pane>
            <el-tab-pane label="3·裁片关联" name="cutpiece">
              <CutPieceTab ref="cutpieceRef" :style-id="store.currentStyle.id" />
            </el-tab-pane>
            <el-tab-pane label="4·流程优化（可跳过）" name="optimize">
              <OptimizeTab ref="optimizeRef" :style-id="store.currentStyle.id" @plan-saved="onPlanSaved" />
            </el-tab-pane>
            <el-tab-pane label="5·SOP 生成" name="sop">
              <SopTab :plan="store.currentPlan" :style-id="store.currentStyle.id" />
            </el-tab-pane>
          </el-tabs>
        </div>
      </template>
    </main>

    <el-dialog v-model="createVisible" title="新建款式" width="460px">
      <el-form label-width="80px">
        <el-form-item label="款号"><el-input v-model="newStyle.styleCode" placeholder="如 7700" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="newStyle.name" placeholder="如 男式短袖衬衫" /></el-form-item>
        <el-form-item label="目标节拍">
          <el-input-number v-model="newStyle.taktTime" :min="0" :step="1" controls-position="right" placeholder="可选(s)" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="createStyle">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>
