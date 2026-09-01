<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as api from '../utils/api'
import type { Analysis, Job, Resume } from '../types'

const resumes = ref<Resume[]>([])
const jobs = ref<Job[]>([])
const analyses = ref<Analysis[]>([])
const resumeId = ref<number>()
const jobId = ref<number>()
const loading = ref(false)
const result = ref<Analysis | null>(null)

const questions = computed<string[]>(() => {
  if (!result.value?.interview_questions) return []
  try {
    return JSON.parse(result.value.interview_questions)
  } catch {
    return []
  }
})

// 把分析记录里的 resume_id / job_id 映射成标题，让历史更直观
const resumeMap = computed<Record<number, string>>(() =>
  Object.fromEntries(resumes.value.map((r) => [r.id, r.title])),
)
const jobMap = computed<Record<number, string>>(() =>
  Object.fromEntries(jobs.value.map((j) => [j.id, j.title])),
)

async function loadAll() {
  ;[resumes.value, jobs.value, analyses.value] = await Promise.all([
    api.listResumes(),
    api.listJobs(),
    api.listAnalyses(),
  ])
}

async function analyze() {
  if (!resumeId.value || !jobId.value) {
    ElMessage.warning('请先选择一份简历和一个 JD')
    return
  }
  loading.value = true
  result.value = null
  try {
    const a = await api.createAnalysis(resumeId.value, jobId.value)
    result.value = a
    await loadAll()
    ElMessage.success('分析完成')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '分析失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<template>
  <div style="max-width: 900px; margin: 0 auto">
    <h2>AI 匹配分析</h2>

    <el-card>
      <el-form inline>
        <el-form-item label="简历">
          <el-select v-model="resumeId" placeholder="选择简历" style="width: 240px">
            <el-option v-for="r in resumes" :key="r.id" :label="r.title" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="JD">
          <el-select v-model="jobId" placeholder="选择 JD" style="width: 240px">
            <el-option v-for="j in jobs" :key="j.id" :label="j.title" :value="j.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="analyze">开始分析</el-button>
        </el-form-item>
      </el-form>
      <el-alert
        v-if="resumes.length === 0 || jobs.length === 0"
        type="info"
        :closable="false"
        title="请先在「简历」和「职位 JD」页各创建至少一条数据，才能进行分析。"
      />
    </el-card>

    <el-card v-if="result" style="margin-top: 16px">
      <h3>匹配度评分</h3>
      <el-progress
        type="dashboard"
        :percentage="result.match_score ?? 0"
        :color="(result.match_score ?? 0) >= 70 ? '#67c23a' : '#e6a23c'"
      />
      <h3>分析建议</h3>
      <el-alert :closable="false" type="success">{{ result.match_summary }}</el-alert>
      <h3>模拟面试问题</h3>
      <ol>
        <li v-for="(q, i) in questions" :key="i" style="margin-bottom: 6px">{{ q }}</li>
      </ol>
    </el-card>

    <el-card style="margin-top: 16px">
      <h3>历史分析</h3>
      <el-table :data="analyses" empty-text="暂无历史">
        <el-table-column label="简历" min-width="180">
          <template #default="{ row }">{{ resumeMap[row.resume_id] ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="JD" min-width="180">
          <template #default="{ row }">{{ jobMap[row.job_id] ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="评分" width="90">
          <template #default="{ row }">
            <el-tag :type="(row.match_score ?? 0) >= 70 ? 'success' : 'warning'">
              {{ row.match_score ?? '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="建议摘要" min-width="260">
          <template #default="{ row }">
            <span style="color: #909399; font-size: 13px">{{ row.match_summary }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
