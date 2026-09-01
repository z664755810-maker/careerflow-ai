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
// 演示账号提示：作品集演示用，方便 recruiters 一键体验
const showDemo = ref(true)

async function submit() {
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    ElMessage.success('登录成功')
    router.push('/resumes')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div style="display: flex; justify-content: center; margin-top: 80px">
    <el-card style="width: 420px">
      <h2 style="margin-top: 0">登录 CareerFlow AI</h2>
      <el-form @submit.prevent="submit">
        <el-form-item label="邮箱">
          <el-input v-model="email" placeholder="you@example.com" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" show-password />
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="submit" style="width: 100%">
          登录
        </el-button>
      </el-form>
      <div style="margin-top: 12px; text-align: center">
        <router-link to="/register">还没有账号？去注册</router-link>
      </div>
      <el-alert
        v-if="showDemo"
        type="info"
        :closable="false"
        show-icon
        style="margin-top: 14px"
        title="演示账号（体验用）"
        description="demo@careerflow.app / CareerFlow2026 —— 登录即可看到 4 份示例简历、4 份示例 JD 与历史分析记录"
      />
    </el-card>
  </div>
</template>
