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
  if (password.value.length < 8) {
    ElMessage.warning('密码至少 8 位')
    return
  }
  loading.value = true
  try {
    await auth.register(email.value, password.value)
    ElMessage.success('注册成功，已自动登录')
    router.push('/resumes')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div style="display: flex; justify-content: center; margin-top: 80px">
    <el-card style="width: 420px">
      <h2 style="margin-top: 0">注册 CareerFlow AI</h2>
      <el-form @submit.prevent="submit">
        <el-form-item label="邮箱">
          <el-input v-model="email" placeholder="you@example.com" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" show-password placeholder="至少 8 位" />
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="submit" style="width: 100%">
          注册并登录
        </el-button>
      </el-form>
      <div style="margin-top: 12px; text-align: center">
        <router-link to="/login">已有账号？去登录</router-link>
      </div>
    </el-card>
  </div>
</template>
