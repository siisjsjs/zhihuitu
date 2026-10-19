<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '@/api/request'

const users = ref<any[]>([])
const total = ref(0)
const search = ref('')
const page = ref(1)
const pageSize = 10
const detail = ref<any>(null)
const detailVisible = ref(false)

async function loadUsers() {
  const data = await request.get('/admin/users', { params: { page: page.value, pageSize, keyword: search.value } })
  users.value = data.list || []
  total.value = data.total || 0
}

function onSearch() {
  page.value = 1
  loadUsers()
}

async function toggleBan(user: any) {
  const action = user.status === 'active' ? 'ban' : 'unban'
  await request.post(`/admin/users/${user.id}/${action}`)
  loadUsers()
}

function showDetail(user: any) {
  detail.value = user
  detailVisible.value = true
}

onMounted(loadUsers)
</script>

<template>
  <div style="padding: 28px">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px">
      <div>
        <h1 style="font-size: 22px; font-weight: 700; color: #0f172a; margin: 0">用户管理</h1>
        <p style="font-size: 13px; color: #94a3b8; margin-top: 2px">共 {{ total }} 位注册用户</p>
      </div>
      <el-input v-model="search" placeholder="搜索用户..." clearable style="width: 260px" @clear="loadUsers" @keyup.enter="onSearch">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
    </div>

    <el-card shadow="never" style="border: 1px solid #e2e8f0">
      <el-table :data="users" style="width: 100%" stripe>
        <el-table-column label="用户" min-width="150">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 10px">
              <div style="width: 32px; height: 32px; border-radius: 50%; background: #dbeafe; display: flex; align-items: center; justify-content: center; color: #3b82f6; font-size: 13px; font-weight: 600">
                {{ row.username?.[0] || '?' }}
              </div>
              <span style="font-weight: 500">{{ row.username }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column prop="chartsCount" label="图表数" width="110" align="center" sortable>
          <template #default="{ row }">
            <span style="font-variant-numeric: tabular-nums; font-weight: 600; color: #0f172a">{{ row.chartsCount ?? 0 }}</span>
            <span style="font-size: 12px; color: #94a3b8"> 个</span>
          </template>
        </el-table-column>
        <el-table-column label="最近活跃" width="170" sortable :sort-method="(a, b) => new Date(a.lastActive || 0).getTime() - new Date(b.lastActive || 0).getTime()">
          <template #default="{ row }">
            <span style="font-size: 13px; color: #64748b">{{ row.lastActive ? new Date(row.lastActive).toLocaleString('zh-CN', { hour12: false }) : '从未创建' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status === 'active' ? '正常' : '已封禁' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="showDetail(row)">详情</el-button>
            <el-button text size="small" :type="row.status === 'active' ? 'danger' : 'success'" @click="toggleBan(row)">
              {{ row.status === 'active' ? '封禁' : '解封' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="display: flex; justify-content: flex-end; padding: 12px">
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="loadUsers" />
      </div>
    </el-card>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailVisible" title="用户详情" width="440px">
      <template v-if="detail">
        <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #f1f5f9">
          <div style="width: 56px; height: 56px; border-radius: 50%; background: #dbeafe; display: flex; align-items: center; justify-content: center; color: #3b82f6; font-size: 22px; font-weight: 700">
            {{ detail.username?.[0] || '?' }}
          </div>
          <div>
            <div style="font-size: 18px; font-weight: 600">{{ detail.username }}</div>
            <div style="font-size: 13px; color: #94a3b8">{{ detail.email }}</div>
          </div>
        </div>
        <div v-for="r in [
          { l: '状态', v: detail.status === 'active' ? '正常' : '已封禁' },
          { l: '创建图表数', v: detail.chartsCount + ' 个' },
          { l: '最近活跃', v: detail.lastActive ? new Date(detail.lastActive).toLocaleString() : '-' },
        ]" :key="r.l" style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f8fafc; font-size: 13px">
          <span style="color: #94a3b8">{{ r.l }}</span>
          <span style="color: #0f172a; font-weight: 500">{{ r.v }}</span>
        </div>
      </template>
    </el-dialog>
  </div>
</template>
