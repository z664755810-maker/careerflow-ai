<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const step = ref<1 | 2>(1)
const email = ref('')
const code = ref('')
const password = ref('')
const loading = ref(false)
const devCode = ref<string | null>(null)
const cooldown = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

const canSend = computed(() => cooldown.value === 0)

function isValidEmail(v: string): boolean {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)
}

function startCooldown() {
  cooldown.value = 60
  timer = setInterval(() => {
    cooldown.value -= 1
    if (cooldown.value <= 0 && timer) {
      clearInterval(timer)
      timer = null
    }
  }, 1000)
}

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

async function sendCode() {
  if (cooldown.value > 0) return
  if (!isValidEmail(email.value)) {
    ElMessage.warning('请输入有效邮箱')
    return
  }
  loading.value = true
  try {
    devCode.value = await auth.requestCode(email.value)
    step.value = 2
    ElMessage.success('验证码已发送')
    startCooldown()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '发送失败')
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (password.value.length < 8) {
    ElMessage.warning('密码至少 8 位')
    return
  }
  loading.value = true
  try {
    await auth.register(email.value, code.value, password.value)
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
          <el-input v-model="email" :disabled="step === 2" placeholder="you@example.com" />
        </el-form-item>

        <template v-if="step === 1">
          <el-button
            type="primary"
            :loading="loading"
            :disabled="!canSend"
            @click="sendCode"
            style="width: 100%"
          >
            {{ cooldown > 0 ? `重新发送(${cooldown}s)` : '发送验证码' }}
          </el-button>
        </template>

        <template v-else>
          <el-alert
            v-if="devCode"
            type="info"
            :closable="false"
            style="margin-bottom: 12px"
            :title="`演示模式验证码：${devCode}`"
            description="未配置 SMTP，验证码直接显示。生产环境将通过邮件发送。"
          />
          <el-form-item label="验证码">
            <el-input v-model="code" placeholder="6 位数字" maxlength="6" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="password" type="password" show-password placeholder="至少 8 位" />
          </el-form-item>
          <el-button type="primary" :loading="loading" @click="submit" style="width: 100%">
            注册并登录
          </el-button>
        </template>
      </el-form>

      <div style="margin-top: 12px; text-align: center">
        <router-link to="/login">已有账号？去登录</router-link>
      </div>
    </el-card>
  </div>
</template>
