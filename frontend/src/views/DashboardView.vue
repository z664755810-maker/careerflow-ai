<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as api from '../utils/api'
import type { Analysis, Application, Job, Resume } from '../types'

const router = useRouter()
const resumes = ref<Resume[]>([])
const jobs = ref<Job[]>([])
const analyses = ref<Analysis[]>([])
const applications = ref<Application[]>([])
const loading = ref(false)

const resumeMap = computed<Record<number, string>>(() =>
  Object.fromEntries(resumes.value.map((r) => [r.id, r.title])),
)
const jobMap = computed<Record<number, string>>(() =>
  Object.fromEntries(jobs.value.map((j) => [j.id, j.title])),
)

const scored = computed(() => analyses.value.map((a) => a.match_score).filter((s): s is number => s != null))
const avgScore = computed(() =>
  scored.value.length ? Math.round(scored.value.reduce((a, b) => a + b, 0) / scored.value.length) : 0,
)
const recent = computed(() => analyses.value.slice(0, 5))

function scoreTag(score: number | null) {
  if (score == null) return 'info'
  return score >= 70 ? 'success' : score >= 50 ? 'warning' : 'danger'
}

async function loadAll() {
  loading.value = true
  try {
    ;[resumes.value, jobs.value, analyses.value, applications.value] = await Promise.all([
      api.listResumes(),
      api.listJobs(),
      api.listAnalyses(),
      api.listApplications(),
    ])
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<template>
  <div v-loading="loading">
    <div class="cf-page-head">
      <div>
        <h1 class="cf-page-title">概览</h1>
        <div class="cf-page-sub">你的求职材料与 AI 分析全景一览</div>
      </div>
      <el-button type="primary" @click="router.push('/analysis')">+ 新建 AI 分析</el-button>
    </div>

    <div class="cf-stat-grid">
      <el-card class="cf-stat-card" shadow="hover">
        <div class="cf-stat-ico">📄</div>
        <div class="cf-stat-label">简历数量</div>
        <div class="cf-stat-value">{{ resumes.length }}</div>
      </el-card>
      <el-card class="cf-stat-card" shadow="hover">
        <div class="cf-stat-ico">💼</div>
        <div class="cf-stat-label">职位 JD</div>
        <div class="cf-stat-value">{{ jobs.length }}</div>
      </el-card>
      <el-card class="cf-stat-card" shadow="hover">
        <div class="cf-stat-ico">📮</div>
        <div class="cf-stat-label">投递记录</div>
        <div class="cf-stat-value">{{ applications.length }}</div>
      </el-card>
      <el-card class="cf-stat-card" shadow="hover">
        <div class="cf-stat-ico">🤖</div>
        <div class="cf-stat-label">历史分析</div>
        <div class="cf-stat-value">{{ analyses.length }}</div>
      </el-card>
      <el-card class="cf-stat-card" shadow="hover">
        <div class="cf-stat-ico">🎯</div>
        <div class="cf-stat-label">平均匹配分</div>
        <div class="cf-stat-value">{{ avgScore }}</div>
      </el-card>
    </div>

    <el-card shadow="never">
      <div class="cf-page-head" style="margin-bottom: 12px">
        <h3 style="margin: 0">最近分析</h3>
        <el-button link type="primary" @click="router.push('/analysis')">查看全部</el-button>
      </div>
      <el-table :data="recent" empty-text="还没有分析记录，去「AI 分析」生成第一条吧">
        <el-table-column label="简历" min-width="160">
          <template #default="{ row }">{{ resumeMap[row.resume_id] ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="职位 JD" min-width="160">
          <template #default="{ row }">{{ jobMap[row.job_id] ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="匹配分" width="110">
          <template #default="{ row }">
            <el-tag :type="scoreTag(row.match_score)">{{ row.match_score ?? '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" min-width="170">
          <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
