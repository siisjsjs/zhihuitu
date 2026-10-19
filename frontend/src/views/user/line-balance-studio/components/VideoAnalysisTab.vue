<script setup lang="ts">
/** 视频分析录入工序：上传视频 → 播放打点切分 → 每段=一道工序（段时长→SAM，名称手填）→ 生成工序。
 *  「打点」按当前播放时间从上一个分段点切出一段，最符合「看到一道工序结束就点一下」的习惯。 */
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import lb from '@/api/lineBalance'

const props = defineProps<{ styleId: number }>()
const emit = defineEmits<{ (e: 'generated'): void }>()

interface Seg { start: number; end: number; name: string }

const videoEl = ref<HTMLVideoElement | null>(null)
const videoUrl = ref('')          // 本地 objectURL，用于即时播放
const filename = ref('')          // 服务端文件名，用于切片
const duration = ref(0)
const curTime = ref(0)
const uploading = ref(false)
const generating = ref(false)
const replace = ref(false)
const segments = ref<Seg[]>([])

function fmt(t: number): string {
  if (!t && t !== 0) return '-'
  const m = Math.floor(t / 60)
  const s = (t % 60).toFixed(1).padStart(4, '0')
  return `${m}:${s}`
}

const lastEnd = () => (segments.value.length ? segments.value[segments.value.length - 1].end : 0)

async function onFileChange(file: UploadFile) {
  const raw = file.raw
  if (!raw) return
  uploading.value = true
  try {
    if (videoUrl.value) URL.revokeObjectURL(videoUrl.value)
    videoUrl.value = URL.createObjectURL(raw)
    segments.value = []
    const res = await lb.uploadVideo(props.styleId, raw)
    filename.value = res.filename
    if (res.duration) duration.value = res.duration
    ElMessage.success('视频已上传，可开始打点切分')
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

function onTimeUpdate() {
  curTime.value = videoEl.value?.currentTime ?? 0
}

/** 在当前时间打点：从上一段结束处切出一段。 */
function mark() {
  const t = Math.round((videoEl.value?.currentTime ?? 0) * 10) / 10
  const start = lastEnd()
  if (t <= start) {
    ElMessage.warning(`打点时间需大于上一分段点 ${fmt(start)}`)
    return
  }
  segments.value.push({ start, end: t, name: '' })
}

/** 用剩余时长补最后一段（到视频结尾）。 */
function fillRest() {
  const start = lastEnd()
  if (duration.value - start < 0.1) { ElMessage.info('已到视频结尾'); return }
  segments.value.push({ start, end: Math.round(duration.value * 10) / 10, name: '' })
}

function undo() {
  segments.value.pop()
}

function clearAll() {
  segments.value = []
}

function delSeg(i: number) {
  segments.value.splice(i, 1)
}

function seek(t: number) {
  if (videoEl.value) { videoEl.value.currentTime = t; videoEl.value.pause() }
}

async function preview(seg: Seg) {
  if (!filename.value) return
  try {
    const res = await lb.clipVideo(filename.value, seg.start, seg.end)
    window.open(res.url, '_blank')
  } catch (e: any) {
    ElMessage.error(e?.message || '切片失败')
  }
}

async function generate() {
  if (!segments.value.length) { ElMessage.warning('请先打点切分出工序'); return }
  generating.value = true
  try {
    const rows = segments.value.map((s, i) => {
      const code = String((i + 1) * 10)
      return {
        originalCode: code,
        originalUpstream: i > 0 ? String(i * 10) : null,
        processName: s.name.trim() || `工序${i + 1}`,
        sam: Math.round((s.end - s.start) * 10) / 10,
        machineType: null,
        workerMachine: null,
      }
    })
    const res = await lb.addProcesses(props.styleId, rows, replace.value)
    ElMessage.success(`已生成 ${res.count} 道工序`)
    emit('generated')
  } catch (e: any) {
    ElMessage.error(e?.message || '生成工序失败')
  } finally {
    generating.value = false
  }
}
</script>

<template>
  <div>
    <el-alert type="info" :closable="false" style="margin-bottom:12px">
      上传作业视频 → 播放到每道工序<b>结束</b>的瞬间点「打点切分」→ 每段自动成为一道工序（段时长即 SAM）→ 填工序名称 → 点「生成工序」。
      生成后流程与 Excel 导入完全一致（编码 / 寻优 / SOP 不变）。
    </el-alert>

    <div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap">
      <el-upload :auto-upload="false" :show-file-list="false" accept="video/*" :on-change="onFileChange">
        <el-button type="primary" :loading="uploading">上传视频</el-button>
      </el-upload>
      <el-checkbox v-model="replace">替换现有工序</el-checkbox>
      <span style="margin-left:auto;color:#64748b">已切分 {{ segments.length }} 段</span>
    </div>

    <div v-if="videoUrl" style="display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap">
      <div style="flex:1;min-width:320px">
        <video
          ref="videoEl" :src="videoUrl" controls
          style="width:100%;max-height:360px;background:#000;border-radius:8px"
          @loadedmetadata="onLoadedMeta" @timeupdate="onTimeUpdate"
        />
        <div style="display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap">
          <el-tag type="info" effect="plain">当前 {{ fmt(curTime) }}</el-tag>
          <el-tag effect="plain">上一分段点 {{ fmt(lastEnd()) }}</el-tag>
          <el-tag effect="plain">总时长 {{ fmt(duration) }}</el-tag>
          <el-button type="primary" @click="mark">打点切分</el-button>
          <el-button @click="fillRest">补到结尾</el-button>
          <el-button @click="undo" :disabled="!segments.length">撤销上一段</el-button>
          <el-button type="danger" link @click="clearAll" :disabled="!segments.length">清空</el-button>
        </div>
      </div>

      <div style="flex:1;min-width:360px">
        <el-table :data="segments" border size="small" empty-text="还没有分段，播放后点「打点切分」">
          <el-table-column type="index" label="#" width="48" />
          <el-table-column label="区间" width="150">
            <template #default="{ row }">
              <el-link type="primary" @click="seek(row.start)">{{ fmt(row.start) }}</el-link>
              <span style="color:#cbd5e1"> → </span>
              <el-link type="primary" @click="seek(row.end)">{{ fmt(row.end) }}</el-link>
            </template>
          </el-table-column>
          <el-table-column label="SAM(s)" width="80">
            <template #default="{ row }">{{ Math.round((row.end - row.start) * 10) / 10 }}</template>
          </el-table-column>
          <el-table-column label="工序名称" min-width="140">
            <template #default="{ row }"><el-input v-model="row.name" size="small" placeholder="必填" /></template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center">
            <template #default="{ row, $index }">
              <el-button link size="small" @click="preview(row)">预览</el-button>
              <el-button link type="danger" size="small" @click="delSeg($index)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-button type="success" style="margin-top:10px" :loading="generating" @click="generate">生成工序</el-button>
      </div>
    </div>

    <el-empty v-else description="请先上传视频" :image-size="80" />
  </div>
</template>

