<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '@/api/request'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const store = useUserStore()
const username = ref('')
const email = ref('')
const phone = ref('')
const oldPw = ref('')
const newPw = ref('')
const confirmPw = ref('')
const saving = ref(false)
const pwSaving = ref(false)
const saved = ref(false)
const pwSaved = ref(false)

onMounted(async () => {
  const data = await request.get('/users/me')
  username.value = data.username
  email.value = data.email
  store.userInfo = data
})

async function saveProfile() {
  saving.value = true
  try {
    await request.put('/users/me', { username: username.value })
    saved.value = true
    setTimeout(() => saved.value = false, 2000)
  } catch (e: any) {
    ElMessage.error(e.message)
  }
  saving.value = false
}

async function savePw() {
  if (!oldPw.value || !newPw.value || newPw.value !== confirmPw.value) {
    ElMessage.warning('请正确填写密码')
    return
  }
  pwSaving.value = true
  try {
    await request.put('/users/me/password', { oldPassword: oldPw.value, newPassword: newPw.value })
    pwSaved.value = true
    oldPw.value = ''
    newPw.value = ''
    confirmPw.value = ''
    setTimeout(() => pwSaved.value = false, 2000)
  } catch (e: any) {
    ElMessage.error(e.message || '修改密码失败')
  }
  pwSaving.value = false
}
</script>

<template>
  <div style="max-width: 680px; margin: 0 auto; padding: 32px 24px">
    <h1 style="font-size: 24px; font-weight: 700; color: #0f172a; margin-bottom: 24px">个人信息</h1>

    <!-- Basic Info Card -->
    <div style="background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 28px; margin-bottom: 20px">
      <!-- Avatar Section -->
      <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 28px; padding-bottom: 20px; border-bottom: 1px solid #f1f5f9">
        <div style="position: relative">
          <div style="width: 80px; height: 80px; border-radius: 50%; background: linear-gradient(135deg, #60a5fa, #2563eb); display: flex; align-items: center; justify-content: center; color: #fff; font-size: 32px; font-weight: 700">
            {{ username?.[0]?.toUpperCase() || 'U' }}
          </div>
          <button style="position: absolute; bottom: 0; right: 0; width: 28px; height: 28px; border-radius: 50%; background: #2563eb; border: 2px solid #fff; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #fff; font-size: 12px">
            📷
          </button>
        </div>
        <div>
          <div style="font-size: 18px; font-weight: 600; color: #1e293b">{{ username }}</div>
          <div style="font-size: 13px; color: #94a3b8; margin-top: 2px">{{ email }}</div>
          <div style="font-size: 12px; color: #94a3b8; margin-top: 4px; display: flex; align-items: center; gap: 4px">🕐 注册于 {{ store.userInfo?.createdAt ? new Date(store.userInfo.createdAt).toLocaleDateString() : '-' }}</div>
        </div>
      </div>

      <div style="font-size: 15px; font-weight: 600; color: #1e293b; margin-bottom: 16px">基本信息</div>

      <div style="margin-bottom: 16px">
        <label style="display: block; font-size: 13px; font-weight: 500; color: #475569; margin-bottom: 6px">昵称</label>
        <el-input v-model="username" placeholder="昵称" style="max-width: 400px" />
      </div>

      <div style="margin-bottom: 16px">
        <label style="display: block; font-size: 13px; font-weight: 500; color: #475569; margin-bottom: 6px">邮箱</label>
        <div style="padding: 10px 16px; background: #f8fafc; border-radius: 8px; font-size: 14px; color: #64748b; max-width: 400px; border: 1px solid #e2e8f0">{{ email }}</div>
      </div>

      <div style="margin-bottom: 16px">
        <label style="display: block; font-size: 13px; font-weight: 500; color: #475569; margin-bottom: 6px">手机号</label>
        <el-input v-model="phone" placeholder="手机号" style="max-width: 400px" />
      </div>

      <div style="display: flex; gap: 8px; align-items: center">
        <el-button type="primary" :loading="saving" @click="saveProfile">💾 保存修改</el-button>
        <span v-if="saved" style="display: inline-flex; padding: 2px 10px; font-size: 12px; font-weight: 500; border-radius: 100px; background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0">已保存</span>
      </div>
    </div>

    <!-- Password Card -->
    <div style="background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 28px">
      <div style="font-size: 15px; font-weight: 600; color: #1e293b; margin-bottom: 16px; display: flex; align-items: center; gap: 8px">🔒 修改密码</div>

      <div style="margin-bottom: 16px">
        <label style="display: block; font-size: 13px; font-weight: 500; color: #475569; margin-bottom: 6px">当前密码</label>
        <el-input v-model="oldPw" type="password" placeholder="当前密码" style="max-width: 400px" show-password />
      </div>

      <div style="margin-bottom: 16px">
        <label style="display: block; font-size: 13px; font-weight: 500; color: #475569; margin-bottom: 6px">新密码</label>
        <el-input v-model="newPw" type="password" placeholder="新密码" style="max-width: 400px" show-password />
      </div>

      <div style="margin-bottom: 16px">
        <label style="display: block; font-size: 13px; font-weight: 500; color: #475569; margin-bottom: 6px">确认新密码</label>
        <el-input v-model="confirmPw" type="password" placeholder="确认新密码" style="max-width: 400px" show-password />
      </div>

      <div style="display: flex; gap: 8px; align-items: center">
        <el-button type="primary" :loading="pwSaving" @click="savePw">✓ 更新密码</el-button>
        <span v-if="pwSaved" style="display: inline-flex; padding: 2px 10px; font-size: 12px; font-weight: 500; border-radius: 100px; background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0">密码已更新</span>
      </div>
    </div>
  </div>
</template>
