<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import type { UploadRequestOptions } from 'element-plus'
import request from '@/api/request'
import { resolveApiStaticUrl } from '@/utils/apiStatic'
import { renderMarkdown } from '@/utils/markdown'

const activeTab = ref('system')
const siteConfig = ref<any>({})
const aiConfigs = ref<any[]>([])
const aiDialogVisible = ref(false)
const aiForm = ref({ provider: 'anthropic', apiKey: '', baseUrl: '', model: 'claude-sonnet-4-20250514' })
const editingAiId = ref<number | null>(null)
const logs = ref<any[]>([])
const logTotal = ref(0)
const logPage = ref(1)

const announcements = ref<any[]>([])
const annDialogVisible = ref(false)
const annForm = ref({
  title: '',
  content: '',
  isActive: true,
  isHighlight: false,
  imageUrl: '' as string,
})
const editingAnnId = ref<number | null>(null)
const annContentRef = ref<any>(null)
const annPreview = ref(true)
const annContentHtml = computed(() => renderMarkdown(annForm.value.content))

function annTextarea(): HTMLTextAreaElement | null {
  const el = annContentRef.value?.$el || annContentRef.value
  return (el?.querySelector?.('textarea') as HTMLTextAreaElement) || null
}

// 在光标处包裹/插入 markdown 片段
function wrapSelection(before: string, after = before, placeholder = '文字') {
  const ta = annTextarea()
  const text = annForm.value.content
  if (!ta) {
    annForm.value.content = text + before + placeholder + after
    return
  }
  const start = ta.selectionStart
  const end = ta.selectionEnd
  const sel = text.slice(start, end) || placeholder
  annForm.value.content = text.slice(0, start) + before + sel + after + text.slice(end)
  requestAnimationFrame(() => {
    ta.focus()
    const pos = start + before.length
    ta.setSelectionRange(pos, pos + sel.length)
  })
}

// 行首插入（标题、列表）
function prefixLine(prefix: string, placeholder = '文字') {
  const ta = annTextarea()
  const text = annForm.value.content
  if (!ta) {
    annForm.value.content = text + (text && !text.endsWith('\n') ? '\n' : '') + prefix + placeholder
    return
  }
  const start = ta.selectionStart
  const lineStart = text.lastIndexOf('\n', start - 1) + 1
  annForm.value.content = text.slice(0, lineStart) + prefix + text.slice(lineStart)
  requestAnimationFrame(() => {
    ta.focus()
    const pos = start + prefix.length
    ta.setSelectionRange(pos, pos)
  })
}

function insertText(snippet: string) {
  const ta = annTextarea()
  const text = annForm.value.content
  if (!ta) {
    annForm.value.content = text + snippet
    return
  }
  const start = ta.selectionStart
  annForm.value.content = text.slice(0, start) + snippet + text.slice(start)
  requestAnimationFrame(() => {
    ta.focus()
    const pos = start + snippet.length
    ta.setSelectionRange(pos, pos)
  })
}

async function loadAnnouncements() {
  try {
    announcements.value = (await request.get('/admin/announcements')) || []
  } catch {
    announcements.value = []
  }
}

async function saveAnnouncement() {
  const hasText = !!(annForm.value.title?.trim() || annForm.value.content?.trim())
  const hasImg = !!annForm.value.imageUrl?.trim()
  if (!hasText && !hasImg) {
    ElMessage.warning('请填写标题、正文或上传配图')
    return
  }
  if (editingAnnId.value != null) {
    await request.put(`/admin/announcements/${editingAnnId.value}`, annForm.value)
  } else {
    await request.post('/admin/announcements', annForm.value)
  }
  annDialogVisible.value = false
  ElMessage.success('公告已保存')
  loadAnnouncements()
}

function editAnnouncement(row: any) {
  editingAnnId.value = row.id
  annForm.value = {
    title: row.title || '',
    content: row.content || '',
    isActive: row.isActive !== false,
    isHighlight: !!row.isHighlight,
    imageUrl: row.imageUrl || '',
  }
  annDialogVisible.value = true
}

function newAnnouncement() {
  editingAnnId.value = null
  annForm.value = { title: '', content: '', isActive: true, isHighlight: false, imageUrl: '' }
  annDialogVisible.value = true
}

async function handleAnnImageUpload(options: UploadRequestOptions) {
  const file = options.file as File
  const fd = new FormData()
  fd.append('file', file)
  const token = localStorage.getItem('token')
  try {
    const { data } = await axios.post<{ code: number; message?: string; data?: { url: string } }>(
      `${import.meta.env.VITE_API_BASE_URL}/admin/announcements/upload-image`,
      fd,
      { headers: { Authorization: token ? `Bearer ${token}` : '' } }
    )
    if (data.code !== 200) throw new Error(data.message || '上传失败')
    annForm.value.imageUrl = data.data!.url
    ElMessage.success('图片已上传')
    options.onSuccess(data)
  } catch (e: unknown) {
    const err = e instanceof Error ? e : new Error('上传失败')
    ElMessage.error(err.message)
    options.onError(err as any)
  }
}

// 上传图片并在正文光标处插入 markdown 图片语法
async function handleAnnInlineImageUpload(options: UploadRequestOptions) {
  const file = options.file as File
  const fd = new FormData()
  fd.append('file', file)
  const token = localStorage.getItem('token')
  try {
    const { data } = await axios.post<{ code: number; message?: string; data?: { url: string } }>(
      `${import.meta.env.VITE_API_BASE_URL}/admin/announcements/upload-image`,
      fd,
      { headers: { Authorization: token ? `Bearer ${token}` : '' } }
    )
    if (data.code !== 200) throw new Error(data.message || '上传失败')
    insertText(`\n![图片](${resolveApiStaticUrl(data.data!.url)})\n`)
    ElMessage.success('图片已插入正文')
    options.onSuccess(data)
  } catch (e: unknown) {
    const err = e instanceof Error ? e : new Error('上传失败')
    ElMessage.error(err.message)
    options.onError(err as any)
  }
}

async function removeAnnouncement(id: number) {
  try {
    await ElMessageBox.confirm('确定删除该公告？', '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await request.delete(`/admin/announcements/${id}`)
  ElMessage.success('已删除')
  loadAnnouncements()
}

async function loadConfig() {
  try {
    const data = await request.get('/admin/system-config')
    siteConfig.value = data || {}
  } catch {}
}

async function saveConfig() {
  await request.put('/admin/system-config', siteConfig.value)
  ElMessage.success('配置已保存')
}

async function loadAiConfigs() {
  try { aiConfigs.value = await request.get('/admin/ai-config') || [] } catch {}
}

async function saveAiConfig() {
  if (editingAiId.value) {
    await request.put(`/admin/ai-config/${editingAiId.value}`, aiForm.value)
  } else {
    await request.post('/admin/ai-config', aiForm.value)
  }
  aiDialogVisible.value = false
  loadAiConfigs()
}

function editAiConfig(cfg: any) {
  editingAiId.value = cfg.id
  aiForm.value = { provider: cfg.provider, apiKey: '', baseUrl: cfg.baseUrl || '', model: cfg.model }
  aiDialogVisible.value = true
}

function newAiConfig() {
  editingAiId.value = null
  aiForm.value = { provider: 'anthropic', apiKey: '', baseUrl: '', model: 'claude-sonnet-4-20250514' }
  aiDialogVisible.value = true
}

async function toggleAiConfig(id: number) {
  await request.post(`/admin/ai-config/${id}/toggle`)
  loadAiConfigs()
}

async function deleteAiConfig(id: number) {
  await request.delete(`/admin/ai-config/${id}`)
  loadAiConfigs()
}

async function loadLogs() {
  try {
    const data = await request.get('/admin/operation-logs', { params: { page: logPage.value, pageSize: 20 } })
    logs.value = data.list || []
    logTotal.value = data.total || 0
  } catch {}
}

// Import ElMessage
import { ElMessage, ElMessageBox } from 'element-plus'

onMounted(() => { loadConfig(); loadAiConfigs(); loadLogs(); loadAnnouncements() })
</script>

<template>
  <div style="padding: 28px">
    <div style="margin-bottom: 24px">
      <h1 style="font-size: 22px; font-weight: 700; color: #0f172a; margin: 0">系统配置</h1>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="站点设置" name="system">
        <el-card shadow="never" style="border: 1px solid #e2e8f0; max-width: 600px">
          <el-form :model="siteConfig" label-width="100px">
            <el-form-item label="站点名称"><el-input v-model="siteConfig.siteName" placeholder="智绘图" /></el-form-item>
            <el-form-item label="站点描述"><el-input v-model="siteConfig.siteDescription" type="textarea" :rows="3" /></el-form-item>
            <el-form-item><el-button type="primary" @click="saveConfig">保存配置</el-button></el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="AI 服务配置" name="ai">
        <div style="margin-bottom: 16px"><el-button type="primary" @click="newAiConfig">新增配置</el-button></div>
        <el-table :data="aiConfigs" style="max-width: 800px" stripe>
          <el-table-column prop="provider" label="提供商" width="100" />
          <el-table-column prop="model" label="模型" width="200" />
          <el-table-column prop="baseUrl" label="接口地址" min-width="200" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }"><el-tag :type="row.isEnabled ? 'success' : 'info'" size="small">{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button text size="small" @click="editAiConfig(row)">编辑</el-button>
              <el-button text size="small" @click="toggleAiConfig(row.id)">{{ row.isEnabled ? '停用' : '启用' }}</el-button>
              <el-button text size="small" type="danger" @click="deleteAiConfig(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="aiConfigs.length === 0" description="暂无 AI 配置" style="padding: 40px" />

        <el-dialog v-model="aiDialogVisible" :title="editingAiId ? '编辑 AI 配置' : '新增 AI 配置'" width="480px">
          <el-form :model="aiForm" label-width="100px">
            <el-form-item label="提供商"><el-select v-model="aiForm.provider"><el-option label="Anthropic (Claude)" value="anthropic" /><el-option label="OpenAI (GPT)" value="openai" /></el-select></el-form-item>
            <el-form-item label="API Key"><el-input v-model="aiForm.apiKey" type="password" show-password /></el-form-item>
            <el-form-item label="模型"><el-input v-model="aiForm.model" /></el-form-item>
            <el-form-item label="接口地址"><el-input v-model="aiForm.baseUrl" placeholder="可选，默认使用官方地址" /></el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="aiDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="saveAiConfig">保存</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <el-tab-pane label="公告管理" name="announcement">
        <div style="margin-bottom: 16px">
          <el-button type="primary" @click="newAnnouncement">发布公告</el-button>
          <span style="margin-left: 12px; font-size: 13px; color: #64748b">用户端仅展示一条启用中的公告（以最新创建为准）。每个浏览器会话首次进入会弹窗；管理员修改正文后，同一会话内也会再次弹出。</span>
        </div>
        <el-table :data="announcements" style="max-width: 960px" stripe>
          <el-table-column prop="title" label="标题" min-width="120" show-overflow-tooltip />
          <el-table-column label="配图" width="72">
            <template #default="{ row }">
              <img
                v-if="row.imageUrl"
                :src="resolveApiStaticUrl(row.imageUrl)"
                alt=""
                style="width: 48px; height: 48px; object-fit: cover; border-radius: 6px; border: 1px solid #e2e8f0"
              />
              <span v-else style="color: #94a3b8">—</span>
            </template>
          </el-table-column>
          <el-table-column label="标红" width="72">
            <template #default="{ row }">
              <el-tag v-if="row.isHighlight" type="danger" size="small">标红</el-tag>
              <span v-else style="color: #94a3b8">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="content" label="正文摘要" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ (row.content || '').slice(0, 80) }}{{ (row.content || '').length > 80 ? '…' : '' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="88">
            <template #default="{ row }">
              <el-tag :type="row.isActive ? 'success' : 'info'" size="small">{{ row.isActive ? '启用' : '停用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="168">
            <template #default="{ row }">{{ row.createdAt ? new Date(row.createdAt).toLocaleString() : '—' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button text size="small" type="primary" @click="editAnnouncement(row)">编辑</el-button>
              <el-button text size="small" type="danger" @click="removeAnnouncement(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="announcements.length === 0" description="暂无公告，点击上方发布公告" style="padding: 40px" />

        <el-dialog v-model="annDialogVisible" :title="editingAnnId != null ? '编辑公告' : '发布公告'" width="860px" destroy-on-close>
          <el-form :model="annForm" label-width="88px">
            <el-form-item label="标题">
              <el-input v-model="annForm.title" placeholder="可选；留空时用户端显示为「网站公告」" maxlength="200" show-word-limit />
            </el-form-item>
            <el-form-item label="正文">
              <div class="md-editor">
                <div class="md-toolbar">
                  <el-button-group>
                    <el-button size="small" @click="prefixLine('# ', '标题')">H1</el-button>
                    <el-button size="small" @click="prefixLine('## ', '标题')">H2</el-button>
                    <el-button size="small" @click="prefixLine('### ', '标题')">H3</el-button>
                  </el-button-group>
                  <el-button-group>
                    <el-button size="small" @click="wrapSelection('**')"><strong>B</strong></el-button>
                    <el-button size="small" @click="wrapSelection('*')"><em>I</em></el-button>
                    <el-button size="small" @click="wrapSelection('==')"><span style="color:#dc2626">标红</span></el-button>
                    <el-button size="small" @click="wrapSelection('`', '`', '代码')">代码</el-button>
                  </el-button-group>
                  <el-button-group>
                    <el-button size="small" @click="prefixLine('- ', '列表项')">• 列表</el-button>
                    <el-button size="small" @click="prefixLine('1. ', '列表项')">1. 列表</el-button>
                    <el-button size="small" @click="prefixLine('> ', '引用')">引用</el-button>
                    <el-button size="small" @click="insertText('\n---\n')">分割线</el-button>
                  </el-button-group>
                  <el-button-group>
                    <el-button size="small" @click="wrapSelection('[', '](https://)', '链接文字')">链接</el-button>
                    <el-upload
                      :show-file-list="false"
                      accept="image/jpeg,image/png,image/gif,image/webp"
                      :http-request="handleAnnInlineImageUpload"
                      style="display: inline-block"
                    >
                      <el-button size="small">插入图片</el-button>
                    </el-upload>
                  </el-button-group>
                  <div style="flex: 1" />
                  <el-button size="small" :type="annPreview ? 'primary' : 'default'" plain @click="annPreview = !annPreview">
                    {{ annPreview ? '预览中' : '显示预览' }}
                  </el-button>
                </div>
                <div class="md-panes" :class="{ 'no-preview': !annPreview }">
                  <el-input
                    ref="annContentRef"
                    v-model="annForm.content"
                    type="textarea"
                    :rows="12"
                    placeholder="支持 Markdown：# 标题、**加粗**、==标红==、- 列表、![图片](url)、[链接](url)。可与配图二选一或同时使用"
                    maxlength="5000"
                    show-word-limit
                    resize="none"
                  />
                  <div v-if="annPreview" class="md-preview markdown-body">
                    <div v-if="annForm.content.trim()" v-html="annContentHtml" />
                    <div v-else class="md-preview-empty">预览区 · 在左侧输入即可实时查看效果</div>
                  </div>
                </div>
              </div>
            </el-form-item>
            <el-form-item label="配图">
              <div style="display: flex; flex-direction: column; gap: 10px; align-items: flex-start">
                <el-upload
                  :show-file-list="false"
                  accept="image/jpeg,image/png,image/gif,image/webp"
                  :http-request="handleAnnImageUpload"
                >
                  <template #trigger>
                    <el-button type="primary" plain>上传图片</el-button>
                  </template>
                </el-upload>
                <div v-if="annForm.imageUrl" style="display: flex; align-items: flex-start; gap: 12px; flex-wrap: wrap">
                  <img
                    :src="resolveApiStaticUrl(annForm.imageUrl)"
                    alt="预览"
                    style="max-width: 280px; max-height: 180px; border-radius: 8px; border: 1px solid #e2e8f0; object-fit: contain; background: #f8fafc"
                  />
                  <el-button text type="danger" @click="annForm.imageUrl = ''">移除图片</el-button>
                </div>
                <span style="font-size: 12px; color: #94a3b8">支持 JPG / PNG / GIF / WebP，单张不超过 5MB</span>
              </div>
            </el-form-item>
            <el-form-item label="标红">
              <el-switch v-model="annForm.isHighlight" active-text="开启" inactive-text="关闭" />
              <span style="margin-left: 12px; font-size: 12px; color: #64748b">开启后弹窗标题与顶部「公告」入口以红色强调</span>
            </el-form-item>
            <el-form-item label="启用">
              <el-switch v-model="annForm.isActive" active-text="对用户展示" inactive-text="仅保存" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="annDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="saveAnnouncement">保存</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <el-tab-pane label="操作日志" name="logs">
        <el-table :data="logs" stripe>
          <el-table-column prop="action" label="操作" width="120" />
          <el-table-column prop="targetType" label="目标类型" width="100" />
          <el-table-column prop="targetId" label="目标 ID" width="80" />
          <el-table-column prop="ipAddress" label="IP 地址" width="140" />
          <el-table-column label="时间" width="160">
            <template #default="{ row }">{{ row.createdAt ? new Date(row.createdAt).toLocaleString() : '' }}</template>
          </el-table-column>
        </el-table>
        <div style="display: flex; justify-content: flex-end; padding: 12px">
          <el-pagination v-model:current-page="logPage" :page-size="20" :total="logTotal" layout="prev, pager, next" @current-change="loadLogs" />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.md-editor {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}
.md-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 10px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}
.md-panes {
  display: grid;
  grid-template-columns: 1fr 1fr;
}
.md-panes.no-preview {
  grid-template-columns: 1fr;
}
.md-panes :deep(.el-textarea__inner) {
  border: 0;
  border-radius: 0;
  box-shadow: none;
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 13px;
  line-height: 1.7;
}
.md-preview {
  border-left: 1px solid #e2e8f0;
  padding: 12px 16px;
  overflow-y: auto;
  max-height: 360px;
  font-size: 14px;
  color: #334155;
  line-height: 1.75;
  background: #fff;
}
.md-preview-empty {
  color: #cbd5e1;
  font-size: 13px;
}

/* markdown 渲染排版（与用户端弹窗一致） */
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 14px 0 8px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.4;
}
.markdown-body :deep(h1) { font-size: 19px; }
.markdown-body :deep(h2) { font-size: 17px; }
.markdown-body :deep(h3) { font-size: 15px; }
.markdown-body :deep(h4) { font-size: 14px; }
.markdown-body :deep(p) { margin: 8px 0; }
.markdown-body :deep(ul),
.markdown-body :deep(ol) { margin: 8px 0; padding-left: 22px; }
.markdown-body :deep(li) { margin: 4px 0; }
.markdown-body :deep(strong) { font-weight: 700; color: #0f172a; }
.markdown-body :deep(em) { font-style: italic; }
.markdown-body :deep(mark) {
  background: #fee2e2;
  color: #dc2626;
  padding: 0 3px;
  border-radius: 3px;
}
.markdown-body :deep(a) { color: #2563eb; text-decoration: underline; }
.markdown-body :deep(code) {
  background: #eef2f7;
  color: #db2777;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'SFMono-Regular', Consolas, monospace;
}
.markdown-body :deep(blockquote) {
  margin: 8px 0;
  padding: 4px 14px;
  border-left: 3px solid #cbd5e1;
  color: #64748b;
  background: #f1f5f9;
  border-radius: 0 6px 6px 0;
}
.markdown-body :deep(hr) {
  margin: 14px 0;
  border: 0;
  border-top: 1px solid #e2e8f0;
}
.markdown-body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 8px 0;
}
</style>
