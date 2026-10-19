<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import request from '@/api/request'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const username = ref('')
const email = ref('')
const password = ref('')

async function doRegister() {
  try {
    const data = await request.post('/auth/register', { username: username.value, email: email.value, password: password.value })
    userStore.setToken(data.token)
    userStore.userInfo = data.user
    ElMessage.success('注册成功')
    router.push('/templates')
  } catch (e: any) {
    ElMessage.error(e.message || '注册失败')
  }
}
</script>

<template>
  <div style="min-height: 100vh; display: flex; background: #f8fafc">
    <div style="flex: 1; background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #60a5fa 100%); display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 64px; text-align: center">
      <div style="width: 72px; height: 72px; border-radius: 20px; background: rgba(255,255,255,0.15); display: flex; align-items: center; justify-content: center; margin: 0 auto 32px; border: 1px solid rgba(255,255,255,0.2); font-size: 36px">📊</div>
      <h1 style="font-size: 36px; font-weight: 800; color: #fff; margin-bottom: 16px">智绘图</h1>
      <p style="font-size: 17px; color: rgba(255,255,255,0.75); line-height: 1.7">AI 驱动的智能图表生成平台</p>
    </div>
    <div style="width: 480px; display: flex; flex-direction: column; justify-content: center; padding: 48px 56px; background: #fff">
      <h2 style="font-size: 26px; font-weight: 700; color: #0f172a; margin-bottom: 8px">创建账号</h2>
      <p style="font-size: 14px; color: #94a3b8; margin-bottom: 36px">注册一个新的智绘图账号</p>
      <el-form @submit.prevent="doRegister">
        <el-form-item label="用户名"><el-input v-model="username" placeholder="输入用户名" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="email" placeholder="your@email.com" type="email" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="password" type="password" placeholder="输入密码" /></el-form-item>
        <el-form-item><el-button type="primary" style="width: 100%" @click="doRegister">注 册</el-button></el-form-item>
      </el-form>
      <div style="text-align: center; font-size: 14px; color: #94a3b8">
        已有账号？<router-link to="/login" style="color: #2563eb; font-weight: 500">去登录</router-link>
      </div>
    </div>
  </div>
</template>
