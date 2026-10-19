<script setup lang="ts">
import { ref, onMounted, shallowRef, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import request from '@/api/request'
import { ElMessage } from 'element-plus'
import { coerceOperationProcessPayload } from '../../../../../chart-templates/operation-process/buildMxGraphXml'
import { coerceGanttPayload } from '../../../../../chart-templates/gantt/buildMxGraphXml'
import { coerceRoadmapPayload } from '../../../../../chart-templates/tech-roadmap/buildMxGraphXml'
import { coerceVsmPayload } from '../../../../../chart-templates/value-stream/buildMxGraphXml'

function extractFirstJSONObjectString(text: string): string | null {
  const start = text.indexOf('{')
  if (start === -1) return null
  let depth = 0
  let inStr = false
  let esc = false
  for (let i = start; i < text.length; i++) {
    const c = text[i]
    if (esc) {
      esc = false
      continue
    }
    if (c === '\\' && inStr) {
      esc = true
      continue
    }
    if (c === '"') {
      inStr = !inStr
      continue
    }
    if (!inStr) {
      if (c === '{') depth++
      else if (c === '}') {
        depth--
        if (depth === 0) return text.slice(start, i + 1)
      }
    }
  }
  return null
}

/** 与后端逻辑类似：兜底解析模型回复中的 JSON（含 ```json 围栏） */
function extractChartDictFromReply(reply: string): Record<string, unknown> | null {
  const fenced = reply.match(/```(?:json)?\s*([\s\S]*?)\s*```/i)
  const blobs = fenced ? [fenced[1].trim(), reply] : [reply]
  for (const blob of blobs) {
    const slice = extractFirstJSONObjectString(blob)
    if (!slice) continue
    try {
      const o = JSON.parse(slice)
      if (o && typeof o === 'object' && !Array.isArray(o)) return o as Record<string, unknown>
    } catch {
      /* continue */
    }
  }
  return null
}

const router = useRouter()
const route = useRoute()
const template = ref<any>(null)
const engine = ref('')
const messages = ref<{ role: string; content: string }[]>([])
const inputText = ref('')
const loading = ref(false)
const hasChart = ref(false)
const previewImage = ref('')
const summaryData = ref<Record<string, any> | null>(null)
const chartDataRef = ref<any>(null)
const componentKey = ref(0) // 触发组件重挂

const DynamicComponent = shallowRef<any>(null)

const suggestions = ref<string[]>([])

const selectedStyle = ref<string | null>(null)
const templateStyles = ref<any[]>([])

const exampleDialogVisible = ref(false)
const exampleData = computed(() => template.value?.config?.example || null)

const componentModules = import.meta.glob('../../../../../chart-templates/**/*.vue')

function initConversation(data: any, drawioLike: boolean) {
  messages.value = [{ role: 'assistant', content: `你好！我是智绘图 AI 助手。请描述你想要的${data.name}，我来帮你生成。` }]
  if (data.id === 'gantt') {
    suggestions.value = [
      `生成一张完整的${data.name}（含多个阶段和任务）`,
      '按示例生成 12 个月项目里程碑',
      '生成一个 6 个月的软件开发甘特图',
    ]
  } else if (data.id === 'tech-roadmap') {
    suggestions.value = [
      `生成一张完整的${data.name}（含多个阶段和节点）`,
      '按示例生成研究技术路线图',
      '生成一个软件系统的技术路线图',
    ]
  } else if (data.id === 'value-stream') {
    suggestions.value = [
      `生成一张完整的${data.name}（含工序、库存、信息流与改善点）`,
      '按示例生成某装配线当前状态价值流程图',
      '生成一个 4 工序的精益生产价值流程图',
    ]
  } else if (drawioLike) {
    suggestions.value = [
      `生成一张完整的${data.name}（含主干步骤与汇总表）`,
      '按示例说明生成（附图同款分支汇入）',
      '只生成主干加工与检验步骤',
    ]
  } else {
    suggestions.value = [`帮我画一个${data.name}`, '修改颜色方案', '加上数据标签']
  }
}

function getSelectedTemplateStyle() {
  if (!templateStyles.value.length) return null
  return templateStyles.value.find(s => s.id === selectedStyle.value) || templateStyles.value[0]
}

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
    }
  } catch (e) {
    console.warn('加载模板组件失败:', e)
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

  const drawioLike =
    data.engine === 'drawio' ||
    !!data.config?.dataEntryComponent ||
    data.id === 'operation-process'

  if (drawioLike) {
    engine.value = 'drawio'
    if (data.config?.dataEntryComponent) {
      await loadVueComponent(data.config.dataEntryComponent as string)
    } else {
      await loadVueComponent('OperationProcessForm.vue')
    }
  } else {
    engine.value = data.engine
    if (data.engine === 'vue-component') {
      const styles = data.config?.styles || []
      templateStyles.value = styles
      if (styles.length > 0) {
        initConversation(data, drawioLike)
        return
      }
      await loadVueComponent()
    }
  }

  initConversation(data, drawioLike)
})

async function sendMessage() {
  if (!inputText.value.trim() || loading.value) return
  const userMsg = inputText.value
  messages.value.push({ role: 'user', content: userMsg })
  inputText.value = ''
  loading.value = true

  try {
    const chatPayload: any = {
      templateId: route.params.templateId,
      messages: messages.value.map(m => ({ role: m.role, content: m.content }))
    }
    if (selectedStyle.value) chatPayload.style = selectedStyle.value
    const result = await request.post('/ai/chat', chatPayload)

    messages.value.push({ role: 'assistant', content: result.reply })

    if (engine.value === 'drawio') {
      let raw = result.chartData as Record<string, unknown> | undefined
      if (!raw && typeof result.reply === 'string') raw = extractChartDictFromReply(result.reply) ?? undefined
      if (raw && typeof raw === 'object') {
        try {
          const tid = template.value?.id || route.params.templateId
          chartDataRef.value = tid === 'gantt'
            ? coerceGanttPayload(raw as any)
            : tid === 'tech-roadmap'
              ? coerceRoadmapPayload(raw as any)
              : tid === 'value-stream'
                ? coerceVsmPayload(raw as any)
                : coerceOperationProcessPayload(raw as any)
          componentKey.value++
          hasChart.value = true
        } catch (e) {
          console.warn('coerce payload failed:', e)
        }
      }
    } else if (result.finished) {
      if (engine.value === 'vue-component' && result.chartData) {
        chartDataRef.value = result.chartData
        componentKey.value++
        hasChart.value = true
      } else if (engine.value === 'matplotlib' && result.chartData) {
        const actualParams = result.chartData.params ?? result.chartData
        const genResult = await request.post('/charts/generate', {
          templateId: route.params.templateId,
          params: actualParams
        })
        previewImage.value = genResult.image_base64
        summaryData.value = genResult.summary || null
        chartDataRef.value = { params: actualParams, image_base64: genResult.image_base64 }
        hasChart.value = true
      }
    }
  } catch (e: any) {
    ElMessage.error(e.message || 'AI 对话失败')
    messages.value.push({ role: 'assistant', content: '抱歉，我遇到了一些问题，请稍后再试。' })
  }
  loading.value = false
}

async function confirmAndSave() {
  if (engine.value === 'drawio') {
    const raw = chartDataRef.value as Record<string, any> | null
    if (!raw) {
      ElMessage.warning('请等待 AI 生成完整数据')
      return
    }
    try {
      const tid = template.value?.id || route.params.templateId
      let xml: string
      if (tid === 'gantt') {
        const { buildGanttMxGraphXml, coerceGanttPayload: coerce } = await import(
          '../../../../../chart-templates/gantt/buildMxGraphXml'
        )
        xml = buildGanttMxGraphXml(coerce(raw))
      } else if (tid === 'tech-roadmap') {
        const { buildRoadmapMxGraphXml, coerceRoadmapPayload: coerce } = await import(
          '../../../../../chart-templates/tech-roadmap/buildMxGraphXml'
        )
        xml = buildRoadmapMxGraphXml(coerce(raw))
      } else if (tid === 'value-stream') {
        const { buildValueStreamMxGraphXml, coerceVsmPayload: coerce } = await import(
          '../../../../../chart-templates/value-stream/buildMxGraphXml'
        )
        xml = buildValueStreamMxGraphXml(coerce(raw))
      } else {
        const { buildOperationProcessMxGraphXml } = await import(
          '../../../../../chart-templates/operation-process/buildMxGraphXml'
        )
        xml = buildOperationProcessMxGraphXml(coerceOperationProcessPayload(raw))
      }
      const result = await request.post('/charts', {
        title: template.value?.name || '图表',
        templateId: route.params.templateId,
        chartData: { xml },
      })
      ElMessage.success('已保存，正在打开 Draw.io…')
      router.push(`/drawio-editor/${result.id}`)
    } catch (e: any) {
      console.error('生成 Draw.io XML 失败:', e)
      ElMessage.error(e.message || '生成失败，请检查数据')
    }
    return
  }

  const chartData = { ...(chartDataRef.value || {}) }
  if (engine.value === 'vue-component') {
    const style = getSelectedTemplateStyle()
    if (style?.id) chartData._style = style.id
    if (style?.component) chartData._componentFile = style.component
  }
  const result = await request.post('/charts', {
    title: template.value?.name || '图表',
    templateId: route.params.templateId,
    chartData
  })
  ElMessage.success('图表已保存')
  router.push(`/chart-editor/${result.id}`)
}

function onChartDataUpdate(data: any) {
  chartDataRef.value = data
}

function loadExampleData() {
  const ex = exampleData.value
  if (!ex?.aiPrompt) {
    ElMessage.warning('该模板暂无示例 prompt')
    return
  }
  inputText.value = ex.aiPrompt
  exampleDialogVisible.value = false
  ElMessage.success('示例已填入对话框,点击发送即可')
}
</script>

<template>
  <div style="min-height: 100vh; background: #f8fafc; display: flex; flex-direction: column">
    <!-- Top Nav -->
    <header style="height: 56px; display: flex; align-items: center; gap: 10px; padding: 0 24px; background: #fff; border-bottom: 1px solid #e2e8f0; flex-shrink: 0">
      <el-button text @click="router.push(`/mode-select/${route.params.templateId}`)">← 返回</el-button>
      <span style="font-weight: 600; color: #0f172a">AI 对话 · {{ template?.name || '加载中...' }}</span>
      <div style="margin-left: auto">
        <el-button v-if="exampleData" type="primary" plain size="small" @click="exampleDialogVisible = true">📘 示例</el-button>
      </div>
    </header>

    <!-- Style Picker Overlay -->
    <div v-if="templateStyles.length > 0 && !selectedStyle" class="style-picker-overlay">
      <div class="style-picker-card">
        <h2 class="style-picker-title">{{ template?.name }} · 选择风格</h2>
        <p class="style-picker-desc">请选择一种图表风格，选定后将加载对应的 AI 对话模式</p>
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
      <!-- Left: Chat -->
      <div style="width: 440px; background: #fff; border-right: 1px solid #e2e8f0; display: flex; flex-direction: column; flex-shrink: 0">
        <!-- Messages -->
        <div ref="chatRef" style="flex: 1; overflow: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px">
          <div v-for="(m, i) in messages" :key="i" style="display: flex; justify-content: m.role === 'user' ? 'flex-end' : 'flex-start'">
            <div v-if="m.role !== 'user'" style="width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0; background: linear-gradient(135deg, #2563eb, #8b5cf6); display: flex; align-items: center; justify-content: center; margin-right: 10px; margin-top: 2px; font-size: 16px">🤖</div>
            <div :style="{
              maxWidth: '80%', padding: '10px 14px', borderRadius: 12, fontSize: 14, lineHeight: 1.7,
              ...(m.role === 'user'
                ? { background: '#2563eb', color: '#fff', borderBottomRightRadius: 4 }
                : { background: '#f1f5f9', color: '#334155', borderBottomLeftRadius: 4 })
            }">{{ m.content }}</div>
          </div>
          <div v-if="loading" style="display: flex; align-items: center; gap: 10px">
            <div style="width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, #2563eb, #8b5cf6); display: flex; align-items: center; justify-content: center; font-size: 16px">🤖</div>
            <div style="padding: 10px 14px; background: #f1f5f9; border-radius: 12px; display: flex; gap: 4px">
              <div v-for="i in 3" :key="i" style="width: 6px; height: 6px; border-radius: 50%; background: #94a3b8; animation: blink 1.2s infinite" :style="{ animationDelay: `${(i - 1) * 0.2}s` }"> </div>
            </div>
          </div>
        </div>

        <!-- Input -->
        <div style="padding: 16px; border-top: 1px solid #e2e8f0; display: flex; gap: 8px">
          <el-input v-model="inputText" placeholder="描述你想要的图表效果..." :disabled="loading" @keyup.enter="sendMessage" />
          <el-button type="primary" :disabled="!inputText.trim() || loading" @click="sendMessage">发送</el-button>
        </div>

        <!-- Suggestions -->
        <div style="padding: 0 16px 12px; display: flex; gap: 6px; flex-wrap: wrap">
          <button v-for="s in suggestions" :key="s" @click="inputText = s"
            style="padding: 4px 10px; font-size: 12px; border-radius: 100px; border: 1px solid #e2e8f0; background: #f8fafc; color: #64748b; cursor: pointer; font-family: inherit">{{ s }}</button>
        </div>

        <!-- Confirm button -->
        <div v-if="hasChart" style="padding: 12px 16px; border-top: 1px solid #e2e8f0">
          <el-button type="primary" size="large" style="width: 100%" @click="confirmAndSave">✅ 确认生成，进入编辑</el-button>
        </div>
      </div>

      <!-- Center: Preview（工艺程序图等与流程程序图一致：自上而下铺满可滚动） -->
      <div style="flex: 1; padding: 16px; display: flex; flex-direction: column; align-items: stretch; justify-content: flex-start; overflow: hidden; min-width: 0">
        <template v-if="hasChart">
          <div v-if="engine === 'drawio' && DynamicComponent" style="flex: 1; min-height: 0; width: 100%; display: flex; overflow: auto">
            <DynamicComponent :key="componentKey" :data="chartDataRef" mode="preview" @update:data="onChartDataUpdate" />
          </div>
          <div v-else-if="engine === 'vue-component' && DynamicComponent" style="flex: 1; min-height: 0; width: 100%; display: flex; overflow: auto">
            <DynamicComponent :key="componentKey" :data="chartDataRef" mode="preview" @update:data="onChartDataUpdate" />
          </div>
          <div v-else-if="previewImage" style="background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 24px; display: flex; align-items: center; justify-content: center; max-width: 100%">
            <img :src="previewImage" style="max-width: 100%; max-height: 75vh; object-fit: contain" alt="chart preview" />
          </div>
        </template>
        <div v-else style="text-align: center; color: #cbd5e1; margin: auto">
          <div style="font-size: 80px; margin-bottom: 16px; animation: float 3s ease-in-out infinite">📊</div>
          <p style="font-size: 15px; color: #94a3b8">在左侧对话框描述你的需求<br/>AI 将为你生成图表预览</p>
        </div>
      </div>

      <!-- Right: Analysis Results -->
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

    <!-- 示例 Dialog -->
    <el-dialog v-model="exampleDialogVisible" :title="`${template?.name || ''} · 使用示例`" width="600px">
      <div v-if="exampleData">
        <p style="line-height: 1.7; color: #475569; margin-bottom: 12px">{{ exampleData.description }}</p>
        <div style="font-size: 13px; color: #64748b; margin-bottom: 6px">示例提问:</div>
        <div style="background: #f8fafc; border-radius: 8px; padding: 12px; font-size: 13px; color: #334155; line-height: 1.7">{{ exampleData.aiPrompt }}</div>
      </div>
      <template #footer>
        <el-button @click="exampleDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="loadExampleData">填入对话框</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
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
