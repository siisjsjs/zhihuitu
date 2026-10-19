<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import request from '@/api/request'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const chartId = route.params.chartId as string
const chart = ref<any>(null)
const iframeRef = ref<HTMLIFrameElement>()
const saving = ref(false)
const loading = ref(true)
const currentXml = ref('')
const savedXml = ref('')
const dirty = ref(false)

const DRAWIO_URL = 'https://embed.diagrams.net/?embed=1&proto=json&spin=1&libraries=1'

const EMPTY_DRAWIO =
  '<mxfile host="embed.diagrams.net"><diagram id="empty" name="Page-1"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel></diagram></mxfile>'

function handleMessage(evt: MessageEvent) {
  if (!iframeRef.value || evt.source !== iframeRef.value.contentWindow) return
  let msg: any
  try {
    msg = JSON.parse(evt.data)
  } catch {
    return
  }

  const targetOrigin = evt.origin && evt.origin !== 'null' ? evt.origin : 'https://embed.diagrams.net'

  if (msg.event === 'init') {
    loading.value = false
    const xml = chart.value?.chartData?.xml || ''
    savedXml.value = xml || EMPTY_DRAWIO
    currentXml.value = savedXml.value
    iframeRef.value!.contentWindow!.postMessage(
      JSON.stringify({
        action: 'load',
        xml: savedXml.value,
        autosave: 1,
      }),
      targetOrigin
    )
  } else if (msg.event === 'save') {
    currentXml.value = msg.xml
    doSave(msg.xml)
  } else if (msg.event === 'autosave') {
    currentXml.value = msg.xml
    dirty.value = currentXml.value !== savedXml.value
  } else if (msg.event === 'export') {
    downloadExport(msg.data, msg.format)
  } else if (msg.event === 'exit') {
    handleExit()
  }
}

async function doSave(xml?: string) {
  saving.value = true
  const toSave = xml || currentXml.value
  try {
    await request.put(`/charts/${chartId}`, { chartData: { xml: toSave } })
    savedXml.value = toSave
    dirty.value = false
    ElMessage.success('已保存')
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  }
  saving.value = false
}

function triggerSave() {
  doSave(currentXml.value)
}

function triggerExport(format: string) {
  iframeRef.value?.contentWindow?.postMessage(JSON.stringify({ action: 'export', format, background: '#FFFFFF', scale: 4, border: 0, crop: true }), '*')
}

function downloadExport(data: string, format: string) {
  const a = document.createElement('a')
  a.download = `chart_${chartId}.${format === 'xmlsvg' ? 'svg' : format}`
  a.href = data
  a.click()
}

async function handleExit() {
  if (dirty.value) {
    try {
      await ElMessageBox.confirm('你有未保存的修改，是否保存后再离开？', '提示', {
        confirmButtonText: '保存并离开',
        cancelButtonText: '不保存',
        distinguishCancelAndClose: true,
        type: 'warning',
      })
      await doSave()
      router.push('/my-charts')
    } catch (action) {
      if (action === 'cancel') {
        router.push('/my-charts')
      }
    }
  } else {
    router.push('/my-charts')
  }
}

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (dirty.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onBeforeRouteLeave(async (_to, _from, next) => {
  if (!dirty.value) {
    next()
    return
  }
  try {
    await ElMessageBox.confirm('你有未保存的修改，是否保存后再离开？', '提示', {
      confirmButtonText: '保存并离开',
      cancelButtonText: '不保存',
      distinguishCancelAndClose: true,
      type: 'warning',
    })
    await doSave()
    next()
  } catch (action) {
    if (action === 'cancel') {
      next()
    } else {
      next(false)
    }
  }
})

onMounted(async () => {
  try {
    chart.value = await request.get(`/charts/${chartId}`)
  } catch (e: any) {
    ElMessage.error('加载图表失败')
    router.push('/my-charts')
    return
  }
  window.addEventListener('message', handleMessage)
  window.addEventListener('beforeunload', onBeforeUnload)
})

onUnmounted(() => {
  window.removeEventListener('message', handleMessage)
  window.removeEventListener('beforeunload', onBeforeUnload)
})
</script>

<template>
  <div style="display: flex; flex-direction: column; height: 100vh; background: #f8fafc">
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 0 20px; height: 52px; background: #fff; border-bottom: 1px solid #e2e8f0; flex-shrink: 0">
      <div style="display: flex; align-items: center; gap: 12px">
        <button @click="handleExit" style="display: flex; align-items: center; gap: 6px; padding: 6px 12px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; color: #475569; font-family: inherit">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
          返回
        </button>
        <span style="font-size: 15px; font-weight: 600; color: #1e293b">{{ chart?.title || 'Draw.io 编辑器' }}</span>
        <span v-if="dirty" style="font-size: 12px; color: #f59e0b; margin-left: 4px">未保存</span>
      </div>
      <div style="display: flex; gap: 8px">
        <button @click="triggerSave" :disabled="saving" style="padding: 6px 16px; border-radius: 6px; background: #2563eb; color: #fff; border: none; cursor: pointer; font-size: 13px; font-family: inherit">
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <button @click="triggerExport('png')" style="padding: 6px 12px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; color: #475569; font-family: inherit">导出图片</button>
        <button @click="triggerExport('xmlsvg')" style="padding: 6px 12px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; color: #475569; font-family: inherit">导出 SVG</button>
      </div>
    </div>
    <div v-if="loading" style="flex: 1; display: flex; align-items: center; justify-content: center; color: #94a3b8; font-size: 15px">
      Draw.io 加载中...
    </div>
    <iframe ref="iframeRef" :src="DRAWIO_URL" style="flex: 1; border: none; width: 100%" />
  </div>
</template>
