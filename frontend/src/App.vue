<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const loggedIn = computed(() => !!auth.token)
const active = computed(() => route.path)

const navs = [
  { path: '/dashboard', label: '概览', icon: '📊' },
  { path: '/resumes', label: '我的简历', icon: '📄' },
  { path: '/jobs', label: '职位 JD', icon: '💼' },
  { path: '/analysis', label: 'AI 分析', icon: '🤖' },
]

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container v-if="loggedIn" class="cf-layout">
    <el-aside width="232px" class="cf-sidebar">
      <div class="cf-brand">
        <span class="cf-logo">CF</span>
        <div>
          <div class="cf-brand-name">CareerFlow</div>
          <div class="cf-brand-sub">AI 求职助手</div>
        </div>
      </div>
      <el-menu
        :default-active="active"
        :router="true"
        class="cf-side-menu"
        background-color="transparent"
        text-color="#cbd5e1"
        active-text-color="#ffffff"
      >
        <el-menu-item v-for="n in navs" :key="n.path" :index="n.path">
          <span class="cf-nav-icon">{{ n.icon }}</span>
          <span>{{ n.label }}</span>
        </el-menu-item>
      </el-menu>
      <div class="cf-side-footer">
        <div class="cf-user-box">
          <div class="cf-avatar">{{ (auth.user?.email || '?').charAt(0).toUpperCase() }}</div>
          <div>
            <div class="cf-user-email">{{ auth.user?.email }}</div>
            <el-button link class="cf-logout" @click="logout">退出登录</el-button>
          </div>
        </div>
      </div>
    </el-aside>
    <el-main class="cf-main">
      <router-view />
    </el-main>
  </el-container>
  <router-view v-else />
</template>
