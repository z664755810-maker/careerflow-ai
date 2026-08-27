<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const loggedIn = computed(() => !!auth.token)
const active = computed(() => route.path)

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container style="min-height: 100vh">
    <el-header v-if="loggedIn" style="display: flex; align-items: center; background: #409eff; color: #fff">
      <strong style="font-size: 18px; margin-right: 24px">CareerFlow AI</strong>
      <el-menu mode="horizontal" :default-active="active" :router="true" background-color="#409eff" text-color="#fff" active-text-color="#ffd04b" style="flex: 1">
        <el-menu-item index="/resumes">简历</el-menu-item>
        <el-menu-item index="/jobs">职位 JD</el-menu-item>
        <el-menu-item index="/analysis">AI 分析</el-menu-item>
      </el-menu>
      <span style="margin-right: 12px">{{ auth.user?.email }}</span>
      <el-button size="small" @click="logout">退出</el-button>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>
