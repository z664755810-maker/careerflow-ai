<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const email = ref('')
const password = ref('')
const loading = ref(false)

async function submit() {
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-banner">
      <div class="banner-inner">
        <div class="banner-logo">CF</div>
        <h1>CareerFlow AI</h1>
        <p class="banner-desc">用 AI 读懂你的简历与岗位，<br />让每一次投递都更有把握。</p>
        <ul class="banner-points">
          <li><span>📄</span> 多份简历集中管理</li>
          <li><span>💼</span> 职位 JD 智能归档</li>
          <li><span>🤖</span> 匹配度评分 + 模拟面试</li>
        </ul>
      </div>
    </div>

    <div class="login-pane">
      <el-card class="login-card" shadow="never">
        <h2 style="margin: 0 0 4px">欢迎回来</h2>
        <p style="color: #64748b; margin: 0 0 22px; font-size: 14px">登录以继续使用 CareerFlow</p>
        <el-form @submit.prevent="submit">
          <el-form-item label="邮箱">
            <el-input v-model="email" placeholder="you@example.com" size="large" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="password" type="password" show-password size="large" />
          </el-form-item>
          <el-button type="primary" size="large" :loading="loading" @click="submit" style="width: 100%">
            登录
          </el-button>
        </el-form>
        <div style="margin-top: 14px; text-align: center; font-size: 14px">
          <router-link to="/register">还没有账号？去注册</router-link>
        </div>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-top: 16px"
          title="演示账号（体验用）"
          description="demo@careerflow.app / CareerFlow2026 —— 登录即可看到 4 份示例简历、4 份示例 JD 与历史分析记录"
        />
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  display: flex;
  min-height: 100vh;
}
.login-banner {
  flex: 1;
  background: linear-gradient(150deg, #1e1b4b 0%, #4338ca 55%, #7c3aed 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
.banner-inner {
  max-width: 360px;
}
.banner-logo {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.16);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 24px;
  letter-spacing: 1px;
  margin-bottom: 22px;
}
.banner-inner h1 {
  font-size: 30px;
  margin: 0 0 12px;
}
.banner-desc {
  color: #c7d2fe;
  line-height: 1.7;
  margin: 0 0 26px;
}
.banner-points {
  list-style: none;
  padding: 0;
  margin: 0;
}
.banner-points li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  color: #e0e7ff;
}
.banner-points span {
  font-size: 18px;
}
.login-pane {
  width: 460px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
}
.login-card {
  width: 360px;
  border: none !important;
  box-shadow: none !important;
}
@media (max-width: 768px) {
  .login-banner {
    display: none;
  }
  .login-pane {
    width: 100%;
  }
}
</style>
