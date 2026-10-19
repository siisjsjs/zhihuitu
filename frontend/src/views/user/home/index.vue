<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div style="max-width: 1200px; margin: 0 auto; padding: 32px 24px; text-align: center">
    <div style="margin-bottom: 48px">
      <h1 style="font-size: 40px; font-weight: 800; color: #0f172a; margin-bottom: 12px">欢迎使用 智绘图</h1>
      <p style="font-size: 18px; color: #64748b; max-width: 500px; margin: 0 auto">AI 驱动的智能图表生成平台，选择模板，填写数据或对话 AI，一键生成专业图表</p>
    </div>
    <el-button type="primary" size="large" @click="router.push('/templates')" style="padding: 16px 48px; font-size: 18px">开始创建图表 🚀</el-button>
  </div>
</template>
