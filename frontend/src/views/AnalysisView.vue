<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as api from '../utils/api'
import RadarChart from '../components/RadarChart.vue'
import type { Analysis, Job, Resume } from '../types'

const router = useRouter()
const resumes = ref<Resume[]>([])
const jobs = ref<Job[]>([])
const analyses = ref<Analysis[]>([])
const resumeId = ref<number>()
const jobId = ref<number>()
const loading = ref(false)
const result = ref<Analysis | null>(null)

const resumeMap = computed<Record<number, string>>(() =>
  Object.fromEntries(resumes.value.map((r) => [r.id, r.title])),
)
const jobMap = computed<Record<number, string>>(() =>
  Object.fromEntries(jobs.value.map((j) => [j.id, j.title])),
)
// 薪资依据映射：让雷达/详情里能直接看到评分依据（期望薪资 vs 岗位薪资范围）
const resumeSalaryMap = computed<Record<number, string>>(() =>
  Object.fromEntries(resumes.value.map((r) => [r.id, r.expected_salary || ''])),
)
const jobSalaryMap = computed<Record<number, string>>(() =>
  Object.fromEntries(jobs.value.map((j) => [j.id, j.salary_range || ''])),
)

function salaryContext(a: Analysis | null | undefined) {
  const rid = a?.resume_id ?? null
  const jid = a?.job_id ?? null
  const exp = rid != null ? resumeSalaryMap.value[rid] || '未填写' : '未填写'
  const ran = jid != null ? jobSalaryMap.value[jid] || '未填写' : '未填写'
  return { exp, ran }
}

// 从分析详情一键进入模拟面试（带 analysis_id，面试页会自动开聊）
function goInterview(a: Analysis) {
  if (!a.id) return
  router.push({ path: '/interview', query: { analysis_id: String(a.id) } })
}

const scored = computed(() => analyses.value.map((a) => a.match_score).filter((s): s is number => s != null))
const avgScore = computed(() => (scored.value.length ? Math.round(scored.value.reduce((a, b) => a + b, 0) / scored.value.length) : 0))
const bestScore = computed(() => (scored.value.length ? Math.max(...scored.value) : 0))

function parseQuestions(raw: string | null): string[] {
  if (!raw) return []
  try {
    const v = JSON.parse(raw)
    return Array.isArray(v) ? v.map(String) : []
  } catch {
    return []
  }
}
const questions = computed(() => parseQuestions(result.value?.interview_questions ?? null))

// 详情弹窗
const detailVisible = ref(false)
const detailRow = ref<Analysis | null>(null)
const detailQuestions = computed(() => parseQuestions(detailRow.value?.interview_questions ?? null))

function openDetail(row: Analysis) {
  detailRow.value = row
  detailVisible.value = true
}

async function loadAll() {
  ;[resumes.value, jobs.value, analyses.value] = await Promise.all([
    api.listResumes(),
    api.listJobs(),
    api.listAnalyses(),
  ])
}

async function analyze(force = false) {
  if (!resumeId.value || !jobId.value) {
    ElMessage.warning('请先选择一份简历和一个 JD')
    return
  }
  loading.value = true
  result.value = null
  try {
    // 调接口前先记下该「简历×JD」组合是否已有记录，用于区分「命中缓存」还是「新生成」
    const before = analyses.value.find(
      (a) => a.resume_id === resumeId.value && a.job_id === jobId.value,
    )
    const a = await api.createAnalysis(resumeId.value, jobId.value, force)
    result.value = a
    await loadAll()
    if (!force && before && before.id === a.id) {
      // 后端命中缓存：直接返回旧记录，未重复调用 LLM
      ElMessage.info('已命中缓存（该简历×JD 之前分析过，未重复调用 AI，点「重新分析」可强制刷新）')
    } else {
      ElMessage.success(force ? '已重新分析并生成新结果' : '分析完成')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '分析失败')
  } finally {
    loading.value = false
  }
}

async function remove(row: Analysis) {
  await ElMessageBox.confirm(`确定删除这条分析记录？此操作不可恢复。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  try {
    await api.deleteAnalysis(row.id)
    ElMessage.success('已删除')
    if (result.value?.id === row.id) result.value = null
    await loadAll()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

function scoreTag(score: number | null) {
  if (score == null) return 'info'
  return score >= 70 ? 'success' : score >= 50 ? 'warning' : 'danger'
}

function scoreColor(score: number | null): string {
  const s = score ?? 0
  if (s >= 70) return '#67c23a'
  if (s >= 50) return '#e6a23c'
  return '#f56c6c'
}

// 四维匹配子分：统一定义显示名称与展示顺序
const DIM_LABELS: Record<string, string> = {
  skill_match: '技能',
  exp_match: '经验',
  education_match: '学历',
  salary_fit: '薪资',
}
const DIM_KEYS = ['skill_match', 'exp_match', 'education_match', 'salary_fit'] as const

function dimsOf(a: Analysis | null | undefined): { name: string; value: number | null }[] {
  if (!a) return []
  return DIM_KEYS.map((k) => ({ name: DIM_LABELS[k], value: (a[k] as number | null) ?? null }))
}
function hasDims(a: Analysis | null | undefined): boolean {
  return dimsOf(a).some((d) => d.value != null)
}
function dimColor(v: number | null): string {
  return scoreColor(v)
}

onMounted(loadAll)
</script>

<template>
  <div>
    <div class="cf-page-head">
      <div>
        <h1 class="cf-page-title">AI 匹配分析</h1>
        <div class="cf-page-sub">选择一份简历与一个职位，让 AI 评估匹配度并生成模拟面试问题</div>
      </div>
    </div>

    <div class="cf-stat-grid">
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
      <el-card class="cf-stat-card" shadow="hover">
        <div class="cf-stat-ico">🏆</div>
        <div class="cf-stat-label">最高匹配分</div>
        <div class="cf-stat-value">{{ bestScore }}</div>
      </el-card>
    </div>

    <el-card shadow="never" style="margin-bottom: 18px">
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
          <el-button type="primary" :loading="loading" @click="analyze(false)">开始分析</el-button>
          <el-button :loading="loading" @click="analyze(true)" style="margin-left: 8px">
            重新分析（调 AI）
          </el-button>
        </el-form-item>
      </el-form>
      <el-alert
        v-if="resumes.length === 0 || jobs.length === 0"
        type="info"
        :closable="false"
        title="请先在「我的简历」和「职位 JD」页各创建至少一条数据，才能进行分析。"
      />
    </el-card>

    <el-card v-if="result" shadow="never" style="margin-bottom: 18px">
      <div class="cf-page-head" style="margin-bottom: 8px">
        <h3 style="margin: 0">本次分析结果</h3>
        <el-button size="small" type="primary" @click="goInterview(result)">
          🎤 用本次分析开始模拟面试
        </el-button>
      </div>
      <div v-if="salaryContext(result)" style="font-size: 12px; color: #64748b; margin-bottom: 10px">
        评分依据 · 期望薪资：{{ salaryContext(result).exp }} ｜ 岗位薪资范围：{{ salaryContext(result).ran }}
      </div>
      <div style="display: flex; gap: 28px; flex-wrap: wrap; align-items: center">
        <el-progress
          type="dashboard"
          :percentage="result.match_score ?? 0"
          :color="scoreColor(result.match_score)"
        />
        <div style="flex: 1; min-width: 280px">
          <div style="font-weight: 600; margin-bottom: 6px">分析建议</div>
          <el-alert :closable="false" type="success">{{ result.match_summary }}</el-alert>
        </div>
      </div>
      <div style="margin-top: 16px">
        <div style="font-weight: 600; margin-bottom: 8px">模拟面试问题</div>
        <ol style="margin: 0; padding-left: 20px">
          <li v-for="(q, i) in questions" :key="i" style="margin-bottom: 8px; line-height: 1.6">{{ q }}</li>
        </ol>
      </div>
      <div v-if="hasDims(result)" style="margin-top: 16px; display: flex; gap: 18px; align-items: center; flex-wrap: wrap">
        <RadarChart :dimensions="dimsOf(result)" :size="200" />
        <div style="flex: 1; min-width: 220px">
          <div style="font-weight: 600; margin-bottom: 8px">四维匹配</div>
          <div
            v-for="d in dimsOf(result)"
            :key="d.name"
            style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px"
          >
            <span style="width: 36px; color: #64748b">{{ d.name }}</span>
            <span style="flex: 1"><el-progress :percentage="d.value ?? 0" :color="dimColor(d.value)" :show-text="false" /></span>
            <span style="width: 34px; text-align: right; font-weight: 600">{{ d.value ?? '-' }}</span>
          </div>
        </div>
      </div>
    </el-card>

    <el-card shadow="never">
      <div class="cf-page-head" style="margin-bottom: 12px">
        <h3 style="margin: 0">历史分析</h3>
      </div>
      <el-table :data="analyses" empty-text="暂无历史，生成一条分析即可看到记录">
        <el-table-column label="简历" min-width="170">
          <template #default="{ row }">{{ resumeMap[(row as Analysis).resume_id as number] ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="职位 JD" min-width="170">
          <template #default="{ row }">{{ jobMap[(row as Analysis).job_id as number] ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="匹配分" width="100">
          <template #default="{ row }">
            <el-tag :type="scoreTag((row as Analysis).match_score)">{{ (row as Analysis).match_score ?? '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="四维" min-width="170">
          <template #default="{ row }">
            <span v-if="hasDims(row as Analysis)" style="display: flex; gap: 4px; flex-wrap: wrap">
              <span
                v-for="d in dimsOf(row as Analysis)"
                :key="d.name"
                class="dim-chip"
                :style="{ borderColor: dimColor(d.value), color: dimColor(d.value) }"
              >{{ d.name }} {{ d.value }}</span>
            </span>
            <span v-else style="color: #94a3b8">—</span>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ new Date((row as Analysis).created_at).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="openDetail(row as Analysis)">查看</el-button>
            <el-button size="small" link type="danger" @click="remove(row as Analysis)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="detailVisible" title="分析详情" width="640px">
      <template v-if="detailRow">
        <div style="display: flex; gap: 16px; align-items: center; margin-bottom: 12px">
          <el-progress
            type="dashboard"
            :width="90"
            :percentage="detailRow.match_score ?? 0"
            :color="scoreColor(detailRow.match_score)"
          />
          <div>
            <div style="font-size: 13px; color: #6b7280">
              {{ resumeMap[detailRow.resume_id ?? -1] ?? '-' }} ×
              {{ jobMap[detailRow.job_id ?? -1] ?? '-' }}
            </div>
            <div style="font-weight: 700; margin-top: 4px">
              匹配度 {{ detailRow.match_score ?? '-' }}
            </div>
          </div>
          <el-button size="small" type="primary" @click="goInterview(detailRow); detailVisible = false">
            🎤 用本次分析开始模拟面试
          </el-button>
        </div>
        <div v-if="salaryContext(detailRow)" style="font-size: 12px; color: #64748b; margin: 6px 0 2px">
          评分依据 · 期望薪资：{{ salaryContext(detailRow).exp }} ｜ 岗位薪资范围：{{ salaryContext(detailRow).ran }}
        </div>
        <div style="font-weight: 600; margin: 10px 0 6px">分析建议</div>
        <el-alert :closable="false" type="success">{{ detailRow.match_summary }}</el-alert>
        <div style="font-weight: 600; margin: 14px 0 6px">模拟面试问题</div>
        <ol style="margin: 0; padding-left: 20px">
          <li v-for="(q, i) in detailQuestions" :key="i" style="margin-bottom: 8px; line-height: 1.6">{{ q }}</li>
        </ol>
        <div v-if="hasDims(detailRow)" style="margin-top: 16px">
          <div style="font-weight: 600; margin-bottom: 8px">四维匹配雷达</div>
          <div style="display: flex; gap: 18px; align-items: center; flex-wrap: wrap">
            <RadarChart :dimensions="dimsOf(detailRow)" :size="200" />
            <div style="flex: 1; min-width: 220px">
              <div
                v-for="d in dimsOf(detailRow)"
                :key="d.name"
                style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px"
              >
                <span style="width: 36px; color: #64748b">{{ d.name }}</span>
                <span style="flex: 1"><el-progress :percentage="d.value ?? 0" :color="dimColor(d.value)" :show-text="false" /></span>
                <span style="width: 34px; text-align: right; font-weight: 600">{{ d.value ?? '-' }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.dim-chip {
  display: inline-block;
  padding: 1px 7px;
  border: 1px solid;
  border-radius: 10px;
  font-size: 12px;
  line-height: 18px;
  white-space: nowrap;
}
</style>
