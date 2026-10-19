<script setup lang="ts">
/** 装配 BOM：Excel 导入物料 + 按工序关联（标准件可被多工序复用，带数量）。
 *  绑定单位为工序：工序变化时物料随之变化，优化合并成工位后由工位聚合，最终汇入 SOP。 */
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import lb, { type CutPiece, type Process, type StationCutPieceItem } from '@/api/lineBalance'

const props = defineProps<{ styleId: number }>()

const pieces = ref<CutPiece[]>([])
const processes = ref<Process[]>([])
const activeProcessId = ref<number | null>(null)
// 当前工序绑定：物料 id → 数量
const boundQty = ref<Record<number, number>>({})
const importReplace = ref(false)
const importing = ref(false)
const saving = ref(false)

/** 列别名 → 字段。表头自动识别，全部转小写后比对。 */
const COLUMN_ALIASES: Record<keyof ImportRow, string[]> = {
  pieceCode: ['材料编号', '物料编号', '编号', '料号', 'code', 'piececode'],
  pieceName: ['材料名称', '物料名称', '名称', 'name', 'piecename'],
  material: ['材质', '材料', 'material'],
  spec: ['规格', '材料规格', '型号', 'spec', 'specification'],
}

type ImportRow = {
  pieceCode: string
  pieceName: string | null
  material: string | null
  spec: string | null
}

async function loadPieces() {
  const data = await lb.listCutpieces(props.styleId)
  pieces.value = data.list || []
}

async function loadProcesses() {
  const data = await lb.listProcesses(props.styleId)
  processes.value = data.list || []
  if (processes.value.length && activeProcessId.value == null) {
    selectProcess(processes.value[0].id)
  }
}

async function selectProcess(id: number) {
  activeProcessId.value = id
  const res = await lb.getProcessMaterials(id)
  const map: Record<number, number> = {}
  for (const c of res.materials || []) map[c.id] = c.quantity ?? 1
  boundQty.value = map
}

function isBound(p: CutPiece): boolean {
  return p.id in boundQty.value
}

/** 把当前工序的物料绑定持久化（选中/取消/改数量后自动调用）。 */
async function persistBinding() {
  if (activeProcessId.value == null) return
  saving.value = true
  try {
    const items: StationCutPieceItem[] = Object.entries(boundQty.value).map(
      ([id, qty]) => ({ cutPieceId: Number(id), quantity: qty }),
    )
    await lb.bindProcessMaterials(activeProcessId.value, items)
    await loadPieces()
  } catch (e: any) {
    ElMessage.error(e?.message || '物料关联保存失败')
  } finally {
    saving.value = false
  }
}

function toggleBind(p: CutPiece) {
  if (p.id in boundQty.value) {
    const m = { ...boundQty.value }
    delete m[p.id]
    boundQty.value = m
  } else {
    boundQty.value = { ...boundQty.value, [p.id]: 1 }
  }
  persistBinding()
}

function setQty(id: number, v: number | undefined) {
  if (!(id in boundQty.value)) return
  boundQty.value = { ...boundQty.value, [id]: Math.max(1, Number(v) || 1) }
  persistBinding()
}

function detectColumns(headers: string[]): Record<keyof ImportRow, number> | null {
  const norm = headers.map((h) => String(h ?? '').trim().toLowerCase())
  const idx = {} as Record<keyof ImportRow, number>
  let matched = 0
  for (const field of Object.keys(COLUMN_ALIASES) as (keyof ImportRow)[]) {
    const found = norm.findIndex((h) => h && COLUMN_ALIASES[field].includes(h))
    idx[field] = found
    if (found >= 0) matched++
  }
  // 至少识别到「材料编号」才认为这是带表头的数据
  return matched >= 1 && idx.pieceCode >= 0 ? idx : null
}

function cell(row: any[], i: number): string {
  if (i < 0) return ''
  const v = row[i]
  return v === null || v === undefined ? '' : String(v).trim()
}

function buildRows(rows: any[][]): ImportRow[] {
  if (!rows.length) return []
  const map = detectColumns(rows[0].map((v) => String(v ?? '')))
  const dataRows = map ? rows.slice(1) : rows
  const col: Record<keyof ImportRow, number> = map ?? {
    pieceCode: 0, pieceName: 1, material: 2, spec: 3,
  }
  const out: ImportRow[] = []
  for (const r of dataRows) {
    const pieceCode = cell(r, col.pieceCode)
    if (!pieceCode) continue
    out.push({
      pieceCode,
      pieceName: cell(r, col.pieceName) || null,
      material: cell(r, col.material) || null,
      spec: cell(r, col.spec) || null,
    })
  }
  return out
}

async function onFileChange(file: UploadFile) {
  const raw = file.raw
  if (!raw) return
  importing.value = true
  try {
    const ExcelJS = await import('exceljs')
    const workbook = new ExcelJS.Workbook()
    await workbook.xlsx.load(await raw.arrayBuffer())
    const sheet = workbook.worksheets[0]
    if (!sheet) { ElMessage.warning('Excel 文件中没有工作表'); return }

    const rows: any[][] = []
    sheet.eachRow((row) => {
      const values = Array.isArray(row.values) ? row.values.slice(1) : []
      if (values.some((v) => v !== null && v !== undefined && String(v).trim() !== '')) rows.push(values)
    })

    const parsed = buildRows(rows)
    if (!parsed.length) { ElMessage.warning('未解析到有效物料行，请检查文件内容'); return }

    const res = await lb.importCutpieces(props.styleId, parsed, importReplace.value)
    ElMessage.success(`已导入 ${res.count} 个物料`)
    await loadPieces()
  } catch (e: any) {
    ElMessage.error(e?.message || 'Excel 导入失败')
  } finally {
    importing.value = false
  }
}

async function downloadSample() {
  const ExcelJS = await import('exceljs')
  const workbook = new ExcelJS.Workbook()
  const sheet = workbook.addWorksheet('物料清单')
  sheet.addRow(['材料编号', '材料名称', '材质', '规格'])
  const sample: string[][] = [
    ['M12-NUT', '六角螺母', '金属', 'M12'],
    ['M12-BOLT', '六角螺栓', '金属', 'M12x40'],
    ['BRKT-01', '支架', '金属', '冲压件'],
    ['SEAL-A', '密封圈', '橡胶', 'Φ60'],
  ]
  sample.forEach((r) => sheet.addRow(r))
  ;[14, 18, 10, 14].forEach((w, i) => { sheet.getColumn(i + 1).width = w })
  sheet.getRow(1).font = { bold: true }

  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '物料导入示例.xlsx'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

watch(() => props.styleId, () => {
  activeProcessId.value = null
  loadProcesses()
  loadPieces()
})

onMounted(async () => {
  await loadPieces()
  await loadProcesses()
})
defineExpose({ reload: async () => { await loadPieces(); await loadProcesses() } })
</script>

<template>
  <div>
    <div style="display:flex;gap:8px;margin-bottom:12px;align-items:center;flex-wrap:wrap">
      <el-upload :auto-upload="false" :show-file-list="false" accept=".xlsx,.xls" :on-change="onFileChange">
        <el-button type="primary" :loading="importing">导入 Excel</el-button>
      </el-upload>
      <el-button @click="downloadSample">下载示例 Excel</el-button>
      <el-checkbox v-model="importReplace">替换现有物料</el-checkbox>
      <el-button @click="loadPieces">刷新</el-button>
      <span style="margin-left:auto;align-self:center;color:#64748b">共 {{ pieces.length }} 项物料</span>
    </div>

    <el-alert type="info" :closable="false" style="margin-bottom:12px">
      上传 Excel 自动识别表头（<b>材料编号 / 材料名称 / 材质 / 规格</b>，列顺序任意）。
      材料编号款内唯一；标准件（螺母/螺栓等）可被多个工序复用。物料绑定到工序，
      工序变化时物料随之变化，优化合并成工位后汇入 SOP。点「下载示例 Excel」获取模板。
    </el-alert>

    <div style="display:flex;gap:16px">
      <div style="width:220px;flex:none">
        <div style="font-weight:600;margin-bottom:6px;color:#334155">工序</div>
        <div style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;max-height:460px;overflow-y:auto">
          <div v-for="p in processes" :key="p.id"
            @click="selectProcess(p.id)"
            :style="{ padding:'8px 12px', cursor:'pointer', fontSize:'13px', borderBottom:'1px solid #f1f5f9',
                      background: activeProcessId === p.id ? '#eff6ff' : '#fff',
                      color: activeProcessId === p.id ? '#2563eb' : '#475569', fontWeight: activeProcessId === p.id ? 600 : 400 }">
            <span style="color:#94a3b8;margin-right:4px">{{ p.originalCode }}</span>{{ p.processName }}
          </div>
          <div v-if="!processes.length" style="padding:16px;text-align:center;color:#cbd5e1;font-size:13px">
            请先在「工序录入」录入工序
          </div>
        </div>
      </div>

      <div style="flex:1;min-width:0">
        <div style="display:flex;align-items:center;margin-bottom:6px">
          <span style="font-weight:600;color:#334155">物料清单（BOM）</span>
          <span v-if="activeProcessId != null" style="margin-left:auto;color:#64748b;font-size:13px">
            已关联 {{ Object.keys(boundQty).length }} 项
            <el-tag v-if="saving" type="info" size="small" effect="plain" style="margin-left:6px">保存中…</el-tag>
            <el-tag v-else type="success" size="small" effect="plain" style="margin-left:6px">勾选即自动保存</el-tag>
          </span>
        </div>
        <el-table :data="pieces" border size="small" max-height="420">
          <el-table-column v-if="activeProcessId != null" width="50" align="center" label="选">
            <template #default="{ row }">
              <el-checkbox :model-value="isBound(row)" @change="toggleBind(row)" />
            </template>
          </el-table-column>
          <el-table-column prop="pieceCode" label="材料编号" width="110" />
          <el-table-column prop="pieceName" label="材料名称" min-width="120">
            <template #default="{ row }">{{ row.pieceName || '-' }}</template>
          </el-table-column>
          <el-table-column prop="material" label="材质" width="90">
            <template #default="{ row }">{{ row.material || '-' }}</template>
          </el-table-column>
          <el-table-column prop="spec" label="规格" width="110">
            <template #default="{ row }">{{ row.spec || '-' }}</template>
          </el-table-column>
          <el-table-column v-if="activeProcessId != null" label="数量" width="110" align="center">
            <template #default="{ row }">
              <el-input-number v-if="isBound(row)" :model-value="boundQty[row.id]"
                :min="1" size="small" controls-position="right" style="width:92px"
                @update:model-value="(v: number | undefined) => setQty(row.id, v)" />
              <span v-else style="color:#cbd5e1">—</span>
            </template>
          </el-table-column>
          <el-table-column label="复用" width="90" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.used" type="primary" size="small">已用</el-tag>
              <el-tag v-else type="info" size="small">未用</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>
