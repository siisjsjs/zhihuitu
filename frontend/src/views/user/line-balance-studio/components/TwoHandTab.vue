<script setup lang="ts">
/** 流程优化方式2·双手作业优化（标准工时分析）：
 *  选工序 → 上传作业视频 → 边回放边「切分」动作要素 → 拖动时间轴微调起止 →
 *  在工时表里标动素/类别/评定/宽放，自动算标准工时 → 持久化到该工序 two_hand_data，最终汇入 SOP。 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import lb, { type Process } from '@/api/lineBalance'

const props = defineProps<{ styleId: number }>()

type Category = 'value-added' | 'non-value-added' | 'preparation' | 'incidental'
interface Segment {
  id: string
  index: number
  startTime: number
  endTime: number
  description: string
  therblig: string
  category: Category
  amplitude: string
  rating: number
  allowance: number
}

const THERBLIGS = [
  { code: '', name: '（未指定）' },
  { code: 'TE', name: '伸手 TE' },
  { code: 'G', name: '抓取 G' },
  { code: 'TL', name: '移物 TL' },
  { code: 'P', name: '定位 P' },
  { code: 'A', name: '装配 A' },
  { code: 'RL', name: '释放 RL' },
  { code: 'DA', name: '拆卸 DA' },
  { code: 'H', name: '持住 H' },
]

const CATEGORIES: { value: Category; label: string; color: string }[] = [
  { value: 'value-added', label: '有效作业', color: '#22c55e' },
  { value: 'non-value-added', label: '无效作业', color: '#ef4444' },
  { value: 'preparation', label: '准备作业', color: '#3b82f6' },
  { value: 'incidental', label: '附带作业', color: '#f97316' },
]
function catColor(c: Category): string {
  return CATEGORIES.find((x) => x.value === c)?.color || '#94a3b8'
}

// —— 工序 ——
const processes = ref<Process[]>([])
const activeId = ref<number | null>(null)
const saving = ref(false)

// —— 视频 ——
const videoEl = ref<HTMLVideoElement | null>(null)
const videoUrl = ref('')          // 绑定到 <video> 的地址（本地预览或服务器地址）
const serverUrl = ref('')         // 持久化用的服务器地址
const filename = ref('')
const duration = ref(0)
const curTime = ref(0)
const isPlaying = ref(false)
const playbackRate = ref(1)
const uploading = ref(false)

// —— 切分要素 ——
const segments = ref<Segment[]>([])

// —— 时间轴拖拽 ——
const timelineEl = ref<HTMLDivElement | null>(null)
const draggingId = ref<string | null>(null)
const dragType = ref<'start' | 'end' | null>(null)

function fmt(t: number): string {
  if (t == null || !isFinite(t)) return '0.000'
  return t.toFixed(3)
}
function stdTime(s: Segment): number {
  const observed = Math.max(0, s.endTime - s.startTime)
  return observed * (s.rating || 1) * (1 + (s.allowance || 0))
}
const totalStd = computed(() => segments.value.reduce((acc, s) => acc + stdTime(s), 0))

async function loadProcesses() {
  const data = await lb.listProcesses(props.styleId)
  processes.value = data.list || []
  if (processes.value.length && activeId.value == null) {
    selectProcess(processes.value[0].id)
  }
}

async function selectProcess(id: number) {
  activeId.value = id
  resetVideoState()
  const res = await lb.getTwoHand(id)
  const d = res.data || {}
  segments.value = Array.isArray(d.segments) ? d.segments.map(normalizeSeg) : []
  serverUrl.value = d.videoUrl || ''
  videoUrl.value = d.videoUrl || ''
  filename.value = d.videoFilename || ''
  duration.value = Number(d.duration) || 0
}

function normalizeSeg(s: any, i: number): Segment {
  return {
    id: s.id || crypto.randomUUID(),
    index: i + 1,
    startTime: Number(s.startTime) || 0,
    endTime: Number(s.endTime) || 0,
    description: s.description ?? '新动作',
    therblig: s.therblig ?? '',
    category: (s.category as Category) ?? 'value-added',
    amplitude: s.amplitude ?? '',
    rating: s.rating != null ? Number(s.rating) : 1,
    allowance: s.allowance != null ? Number(s.allowance) : 0.1,
  }
}

function resetVideoState() {
  if (videoUrl.value.startsWith('blob:')) URL.revokeObjectURL(videoUrl.value)
  videoUrl.value = ''
  serverUrl.value = ''
  filename.value = ''
  duration.value = 0
  curTime.value = 0
  isPlaying.value = false
}
// —— 上传视频 ——
async function onFileChange(file: UploadFile) {
  const raw = file.raw
  if (!raw) return
  uploading.value = true
  try {
    if (videoUrl.value.startsWith('blob:')) URL.revokeObjectURL(videoUrl.value)
    videoUrl.value = URL.createObjectURL(raw)   // 先本地预览，秒开
    const res = await lb.uploadVideo(props.styleId, raw)
    serverUrl.value = res.url
    filename.value = res.filename
    if (res.duration) duration.value = res.duration
    ElMessage.success('视频已上传，可回放并切分动作要素')
  } catch (e: any) {
    ElMessage.error(e?.message || '视频上传失败')
    videoUrl.value = ''
  } finally {
    uploading.value = false
  }
}

function onLoadedMeta() {
  const d = videoEl.value?.duration
  if (d && isFinite(d)) duration.value = d
}
function onTimeUpdate() { curTime.value = videoEl.value?.currentTime ?? 0 }

function togglePlay() {
  const v = videoEl.value
  if (!v) return
  if (isPlaying.value) v.pause()
  else v.play()
  isPlaying.value = !isPlaying.value
}
function setRate(r: number) {
  playbackRate.value = r
  if (videoEl.value) videoEl.value.playbackRate = r
}

// —— 切分：在「上一段终点 → 当前时刻」之间新建一个动作要素 ——
function cut() {
  const v = videoEl.value
  if (!v) { ElMessage.warning('请先上传视频'); return }
  const now = v.currentTime
  const lastEnd = segments.value.length
    ? Math.max(...segments.value.map((s) => s.endTime))
    : 0
  if (now <= lastEnd + 0.1) { ElMessage.warning('当前时刻需晚于上一要素终点'); return }
  segments.value.push({
    id: crypto.randomUUID(),
    index: segments.value.length + 1,
    startTime: lastEnd,
    endTime: now,
    description: '新动作',
    therblig: '',
    category: 'value-added',
    amplitude: '',
    rating: 1,
    allowance: 0.1,
  })
  persist()
}

function reindex() {
  segments.value.forEach((s, i) => { s.index = i + 1 })
}
function delSegment(id: string) {
  segments.value = segments.value.filter((s) => s.id !== id)
  reindex()
  persist()
}

// —— 时间轴拖拽起止 ——
function startDrag(e: MouseEvent, id: string, type: 'start' | 'end') {
  e.stopPropagation()
  draggingId.value = id
  dragType.value = type
  if (videoEl.value) { videoEl.value.pause(); isPlaying.value = false }
}
function onTimelineClick(e: MouseEvent) {
  if (draggingId.value || !timelineEl.value || duration.value <= 0) return
  const rect = timelineEl.value.getBoundingClientRect()
  const t = ((e.clientX - rect.left) / rect.width) * duration.value
  if (videoEl.value) videoEl.value.currentTime = Math.max(0, Math.min(t, duration.value))
}
function onGlobalMove(e: MouseEvent) {
  if (!draggingId.value || !dragType.value || !timelineEl.value || duration.value <= 0) return
  const rect = timelineEl.value.getBoundingClientRect()
  const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width))
  const t = (x / rect.width) * duration.value
  const seg = segments.value.find((s) => s.id === draggingId.value)
  if (!seg) return
  if (dragType.value === 'start') seg.startTime = Math.min(t, seg.endTime - 0.1)
  else seg.endTime = Math.max(t, seg.startTime + 0.1)
  if (videoEl.value) videoEl.value.currentTime = t
}
function onGlobalUp() {
  if (draggingId.value) persist()
  draggingId.value = null
  dragType.value = null
}

function onKeyDown(e: KeyboardEvent) {
  const tgt = e.target as HTMLElement
  if (tgt && (tgt.tagName === 'INPUT' || tgt.tagName === 'TEXTAREA' || tgt.tagName === 'SELECT')) return
  if (e.code === 'Space') { e.preventDefault(); togglePlay() }
  else if (e.code === 'KeyC') { e.preventDefault(); cut() }
}

// —— 持久化到工序 two_hand_data ——
let saveTimer: number | null = null
function persist() {
  if (activeId.value == null) return
  if (saveTimer !== null) clearTimeout(saveTimer)
  saveTimer = window.setTimeout(doSave, 600)   // 防抖：拖拽/编辑频繁时合并保存
}
async function doSave() {
  if (activeId.value == null) return
  saving.value = true
  try {
    await lb.saveTwoHand(activeId.value, {
      kind: 'standard-time',
      videoUrl: serverUrl.value || null,
      videoFilename: filename.value || null,
      duration: duration.value || null,
      totalStd: Number(totalStd.value.toFixed(3)),
      segments: segments.value.map((s) => ({
        index: s.index,
        startTime: s.startTime,
        endTime: s.endTime,
        description: s.description,
        therblig: s.therblig,
        category: s.category,
        amplitude: s.amplitude,
        rating: s.rating,
        allowance: s.allowance,
        stdTime: Number(stdTime(s).toFixed(3)),
      })),
    })
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

watch(() => props.styleId, () => { activeId.value = null; loadProcesses() })
onMounted(() => {
  loadProcesses()
  window.addEventListener('mousemove', onGlobalMove)
  window.addEventListener('mouseup', onGlobalUp)
  window.addEventListener('keydown', onKeyDown)
})
onUnmounted(() => {
  if (videoUrl.value.startsWith('blob:')) URL.revokeObjectURL(videoUrl.value)
  window.removeEventListener('mousemove', onGlobalMove)
  window.removeEventListener('mouseup', onGlobalUp)
  window.removeEventListener('keydown', onKeyDown)
})
defineExpose({ reload: loadProcesses })
</script>

<template>
  <div>
    <el-alert type="info" :closable="false" style="margin-bottom:12px">
      选择工序 → 上传作业视频，边回放边按 <b>切分(C)</b> 把动作拆成要素 → 拖动时间轴微调每段起止 →
      在工时表里标动素 / 类别 / 评定系数 / 宽放率，系统自动算<b>标准工时</b>。数据按工序保存，最终汇入 SOP。
    </el-alert>

    <div style="display:flex;gap:14px">
      <!-- 工序列表 -->
      <div style="width:190px;flex:none">
        <div style="font-weight:600;margin-bottom:6px;color:#334155">工序</div>
        <div style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;max-height:560px;overflow-y:auto">
          <div v-for="p in processes" :key="p.id" @click="selectProcess(p.id)"
            :style="{ padding:'8px 12px', cursor:'pointer', fontSize:'13px', borderBottom:'1px solid #f1f5f9',
                      background: activeId === p.id ? '#eff6ff' : '#fff',
                      color: activeId === p.id ? '#2563eb' : '#475569', fontWeight: activeId === p.id ? 600 : 400 }">
            <span style="color:#94a3b8;margin-right:4px">{{ p.originalCode }}</span>{{ p.processName }}
            <el-tag v-if="p.twoHandData" type="success" size="small" effect="plain" style="margin-left:4px">已分析</el-tag>
          </div>
          <div v-if="!processes.length" style="padding:16px;text-align:center;color:#cbd5e1;font-size:13px">
            请先在「工序录入」录入工序
          </div>
        </div>
      </div>

      <!-- 分析区 -->
      <div style="flex:1;min-width:0" v-if="activeId != null">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <el-upload :auto-upload="false" :show-file-list="false" accept="video/*" :on-change="onFileChange">
            <el-button type="primary" size="small" :loading="uploading">上传视频</el-button>
          </el-upload>
          <span style="margin-left:auto;color:#64748b;font-size:13px">
            标准工时合计 <b style="color:#d97706">{{ totalStd.toFixed(3) }}s</b>
            <el-tag v-if="saving" type="info" size="small" effect="plain" style="margin-left:6px">保存中…</el-tag>
            <el-tag v-else type="success" size="small" effect="plain" style="margin-left:6px">自动保存</el-tag>
          </span>
        </div>

        <div v-if="!videoUrl" style="border:1px dashed #cbd5e1;border-radius:8px;padding:40px;text-align:center;color:#94a3b8">
          上传该工序的作业视频后开始切分动作要素
        </div>

        <template v-else>
          <!-- 播放器 -->
          <div style="position:relative;background:#000;border-radius:8px;overflow:hidden;max-height:300px">
            <video ref="videoEl" :src="videoUrl" style="width:100%;max-height:300px;display:block"
              @loadedmetadata="onLoadedMeta" @timeupdate="onTimeUpdate"
              @ended="isPlaying = false" @click="togglePlay" />
            <div style="position:absolute;top:8px;left:8px;background:rgba(0,0,0,.5);color:#4ade80;
                        font-family:monospace;font-size:12px;padding:2px 6px;border-radius:4px">
              {{ fmt(curTime) }} / {{ fmt(duration) }}
            </div>
            <div style="position:absolute;top:8px;right:8px;display:flex;background:rgba(0,0,0,.5);border-radius:4px;overflow:hidden">
              <button v-for="r in [0.5, 1, 1.5, 2]" :key="r" @click="setRate(r)"
                :style="{ border:'none', cursor:'pointer', fontSize:'12px', padding:'2px 8px',
                          background: playbackRate === r ? '#2563eb' : 'transparent',
                          color: playbackRate === r ? '#fff' : '#cbd5e1' }">{{ r }}x</button>
            </div>
          </div>

          <!-- 播放控制 + 切分 -->
          <div style="display:flex;align-items:center;gap:10px;margin:8px 0">
            <el-button size="small" @click="togglePlay">{{ isPlaying ? '暂停' : '播放' }}（空格）</el-button>
            <el-button size="small" type="danger" @click="cut">切分动作 (C)</el-button>
            <span style="color:#94a3b8;font-size:12px">已切分 {{ segments.length }} 个要素</span>
          </div>

          <!-- 时间轴 -->
          <div ref="timelineEl" @click="onTimelineClick"
            style="position:relative;height:46px;background:#0f172a;border-radius:6px;overflow:hidden;cursor:crosshair;margin-bottom:12px">
            <div v-for="seg in segments" :key="seg.id"
              :style="{ position:'absolute', top:'8px', height:'30px',
                        left: ((seg.startTime / (duration||1)) * 100) + '%',
                        width: (((seg.endTime - seg.startTime) / (duration||1)) * 100) + '%',
                        background: catColor(seg.category), borderRadius:'3px',
                        display:'flex', alignItems:'center', justifyContent:'center',
                        color:'#fff', fontSize:'11px', overflow:'hidden' }">
              <span style="pointer-events:none">{{ seg.index }}</span>
              <div @mousedown="(e: MouseEvent) => startDrag(e, seg.id, 'start')"
                style="position:absolute;left:0;top:0;bottom:0;width:6px;cursor:w-resize;background:rgba(255,255,255,.4)" />
              <div @mousedown="(e: MouseEvent) => startDrag(e, seg.id, 'end')"
                style="position:absolute;right:0;top:0;bottom:0;width:6px;cursor:e-resize;background:rgba(255,255,255,.4)" />
            </div>
            <div :style="{ position:'absolute', top:0, bottom:0, width:'2px', background:'#eab308', pointerEvents:'none',
                           left: ((curTime / (duration||1)) * 100) + '%' }" />
          </div>

          <!-- 工时表 -->
          <el-table :data="segments" border size="small" max-height="320" empty-text="按「切分动作 (C)」开始拆分要素">
            <el-table-column prop="index" label="#" width="44" align="center" />
            <el-table-column label="要素名称" min-width="130">
              <template #default="{ row }">
                <el-input v-model="row.description" size="small" @change="persist" />
              </template>
            </el-table-column>
            <el-table-column label="动素" width="92">
              <template #default="{ row }">
                <el-select v-model="row.therblig" size="small" @change="persist">
                  <el-option v-for="t in THERBLIGS" :key="t.code" :label="t.name" :value="t.code" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="类别" width="110">
              <template #default="{ row }">
                <el-select v-model="row.category" size="small" @change="persist">
                  <el-option v-for="c in CATEGORIES" :key="c.value" :label="c.label" :value="c.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="幅度" width="80">
              <template #default="{ row }">
                <el-input v-model="row.amplitude" size="small" placeholder="-" @change="persist" />
              </template>
            </el-table-column>
            <el-table-column label="实测(s)" width="80" align="right">
              <template #default="{ row }">{{ (row.endTime - row.startTime).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="评定" width="84" align="center">
              <template #default="{ row }">
                <el-input-number v-model="row.rating" :min="0" :step="0.05" size="small"
                  controls-position="right" style="width:74px" @change="persist" />
              </template>
            </el-table-column>
            <el-table-column label="宽放" width="84" align="center">
              <template #default="{ row }">
                <el-input-number v-model="row.allowance" :min="0" :step="0.01" size="small"
                  controls-position="right" style="width:74px" @change="persist" />
              </template>
            </el-table-column>
            <el-table-column label="标准(s)" width="84" align="right">
              <template #default="{ row }">
                <b style="color:#d97706">{{ stdTime(row).toFixed(2) }}</b>
              </template>
            </el-table-column>
            <el-table-column width="50" align="center">
              <template #default="{ row }">
                <el-button link type="danger" size="small" @click="delSegment(row.id)">删</el-button>
              </template>
            </el-table-column>
          </el-table>
        </template>
      </div>
      <div v-else style="flex:1;display:flex;align-items:center;justify-content:center;color:#94a3b8">
        请选择一道工序开始双手作业 / 标准工时分析
      </div>
    </div>
  </div>
</template>

