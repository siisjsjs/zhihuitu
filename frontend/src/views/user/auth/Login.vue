<script setup lang="ts">
import { onMounted } from 'vue'

// 登录页不再提供账号密码表单：账号由知识库门户统一管理，
// 用户通过门户点击「进入绘图工具」SSO 直达本平台。此页只做跳转。
onMounted(() => {
  setTimeout(() => {
    window.location.replace('https://kb.example.com')
  }, 2000)
})
</script>

<template>
  <div class="sso-page">
    <main class="card">
      <img src="/logo.svg" alt="" class="brand-mark" aria-hidden="true" />
      <h1 class="title">请从知识库门户进入绘图平台</h1>
      <p class="sub">账号与知识库互通，无需在此登录。正在跳转到知识库门户…</p>
      <a class="btn" href="https://kb.example.com" target="_blank" rel="noopener">前往知识库门户</a>
    </main>
  </div>
</template>

<style scoped lang="scss">
.sso-page {
  --primary: #2563eb;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  min-height: 100dvh;
  padding: 24px;
  background: linear-gradient(140deg, #1e3a8a 0%, #2563eb 55%, #60a5fa 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
               'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
}
.card {
  width: 100%;
  max-width: 420px;
  text-align: center;
  background: #fff;
  border-radius: 20px;
  padding: 48px 40px;
  box-shadow: 0 24px 60px -30px rgba(2, 6, 23, 0.5);
}
.brand-mark {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: rgba(37, 99, 235, 0.1);
  padding: 8px;
  margin-bottom: 24px;
}
.title {
  margin: 0 0 12px;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.3;
}
.sub {
  margin: 0 0 28px;
  font-size: 15px;
  line-height: 1.7;
  color: #64748b;
}
.btn {
  display: inline-block;
  padding: 12px 28px;
  border-radius: 12px;
  background: var(--primary);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  text-decoration: none;
  box-shadow: 0 8px 22px -10px rgba(37, 99, 235, 0.6);
  transition: background 0.18s ease, transform 0.18s ease;
}
.btn:hover {
  background: #1d4ed8;
  transform: translateY(-1px);
}
</style>
