<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '@/api/request'

const templates = ref<any[]>([])
const total = ref(0)
const totalUses = ref(0)
const search = ref('')
const page = ref(1)
const pageSize = 10

async function loadTemplates() {
  const data = await request.get('/admin/templates', { params: { page: page.value, pageSize, keyword: search.value } })
  templates.value = data.list || []
  total.value = data.total || 0
  totalUses.value = data.totalUses || 0
}

function onSearch() {
  page.value = 1
  loadTemplates()
}

async function toggleStatus(tpl: any) {
  const action = tpl.status === 'published' ? 'unpublish' : 'publish'
  await request.post(`/admin/templates/${tpl.id}/${action}`)
  loadTemplates()
}

onMounted(loadTemplates)
</script>

<template>
  <div style="padding: 28px">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px">
      <div>
        <h1 style="font-size: 22px; font-weight: 700; color: #0f172a; margin: 0">模板管理</h1>
        <p style="font-size: 13px; color: #94a3b8; margin-top: 2px">
          共 {{ total }} 个模板 · 累计使用
          <span style="font-variant-numeric: tabular-nums; font-weight: 600; color: #8b5cf6">{{ totalUses }}</span> 次
        </p>
      </div>
      <el-input v-model="search" placeholder="搜索模板..." clearable style="width: 260px" @clear="loadTemplates" @keyup.enter="onSearch">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
    </div>

    <el-card shadow="never" style="border: 1px solid #e2e8f0">
      <el-table :data="templates" style="width: 100%" stripe>
        <el-table-column prop="name" label="模板名称" min-width="160" />
        <el-table-column label="分类" width="100">
          <template #default="{ row }"><el-tag size="small">{{ row.category }}</el-tag></template>
        </el-table-column>
        <el-table-column label="引擎" width="110">
          <template #default="{ row }">{{ row.engine === 'vue-component' ? 'Vue 组件' : 'Matplotlib' }}</template>
        </el-table-column>
        <el-table-column prop="usesCount" label="使用次数" width="120" align="center" sortable>
          <template #default="{ row }">
            <span style="font-variant-numeric: tabular-nums; font-weight: 600; color: #0f172a">{{ row.usesCount ?? 0 }}</span>
            <span style="font-size: 12px; color: #94a3b8"> 次</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">{{ row.createdAt ? new Date(row.createdAt).toLocaleDateString() : '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">{{ row.status === 'published' ? '已上架' : '已下架' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="toggleStatus(row)">{{ row.status === 'published' ? '下架' : '上架' }}</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="display: flex; justify-content: flex-end; padding: 12px">
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="loadTemplates" />
      </div>
    </el-card>
  </div>
</template>
