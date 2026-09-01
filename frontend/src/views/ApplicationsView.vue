<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as api from '../utils/api'
import type { Application, ApplicationStatus, Job, Resume } from '../types'

const resumes = ref<Resume[]>([])
const jobs = ref<Job[]>([])
const applications = ref<Application[]>([])
const loading = ref(false)

const STATUS_ORDER: ApplicationStatus[] = ['wishlist', 'applied', 'interview', 'offer', 'rejected']
const STATUS_META: Record<ApplicationStatus, { label: string; color: string }> = {
  wishlist: { label: '想投递', color: '#909399' },
  applied: { label: '已投递', color: '#409eff' },
  interview: { label: '面试中', color: '#e6a23c' },
  offer: { label: '已拿Offer', color: '#67c23a' },
  rejected: { label: '已拒绝', color: '#f56c6c' },
}
const statusLabel = (s: ApplicationStatus) => STATUS_META[s].label

const stats = computed(() => {
  const total = applications.value.length
  const active = applications.value.filter((a) => a.status === 'applied' || a.status === 'interview').length
  const offers = applications.value.filter((a) => a.status === 'offer').length
  return { total, active, offers }
})

const columns = computed(() =>
  STATUS_ORDER.map((st) => ({
    status: st,
    label: STATUS_META[st].label,
    color: STATUS_META[st].color,
    items: applications.value.filter((a) => a.status === st),
  })),
)

async function loadAll() {
  loading.value = true
  try {
    ;[resumes.value, jobs.value, applications.value] = await Promise.all([
      api.listResumes(),
      api.listJobs(),
      api.listApplications(),
    ])
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

// ---- 新建投递 ----
const createVisible = ref(false)
const createForm = reactive({ resume_id: undefined as number | undefined, job_id: undefined as number | undefined, status: 'wishlist' as ApplicationStatus, notes: '' })

function openCreate() {
  if (resumes.value.length === 0 || jobs.value.length === 0) {
    ElMessage.warning('请先在「我的简历」和「职位 JD」各创建至少一条数据')
    return
  }
  createForm.resume_id = undefined
  createForm.job_id = undefined
  createForm.status = 'wishlist'
  createForm.notes = ''
  createVisible.value = true
}

async function submitCreate() {
  if (!createForm.resume_id || !createForm.job_id) {
    ElMessage.warning('请选择简历和职位')
    return
  }
  try {
    await api.createApplication(createForm.resume_id, createForm.job_id, createForm.status, createForm.notes)
    ElMessage.success('已创建投递')
    createVisible.value = false
    await loadAll()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  }
}

// ---- 卡片内快速改状态 ----
async function changeStatus(app: Application, st: ApplicationStatus) {
  try {
    await api.updateApplication(app.id, { status: st })
    app.status = st
    ElMessage.success(`已移至「${statusLabel(st)}」`)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '更新失败')
  }
}

// ---- 编辑弹窗 ----
const editVisible = ref(false)
const editRow = ref<Application | null>(null)
const editForm = reactive({ status: 'wishlist' as ApplicationStatus, applied_at: '' as string, notes: '' })

function openEdit(app: Application) {
  editRow.value = app
  editForm.status = app.status
  editForm.applied_at = app.applied_at ? app.applied_at.slice(0, 19) : ''
  editForm.notes = app.notes
  editVisible.value = true
}

async function submitEdit() {
  if (!editRow.value) return
  try {
    await api.updateApplication(editRow.value.id, {
      status: editForm.status,
      applied_at: editForm.applied_at ? new Date(editForm.applied_at).toISOString() : null,
      notes: editForm.notes,
    })
    ElMessage.success('已保存')
    editVisible.value = false
    await loadAll()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

// ---- 删除 ----
async function remove(app: Application) {
  await ElMessageBox.confirm(`确定删除投递「${app.resume_title} × ${app.job_title}」？`, '删除确认', {
    type: 'warning',
  })
  try {
    await api.deleteApplication(app.id)
    ElMessage.success('已删除')
    await loadAll()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

const fmtDate = (s: string | null) =>
  s ? new Date(s).toLocaleDateString('zh-CN') : '未投递'

onMounted(loadAll)
</script>

<template>
  <div v-loading="loading">
    <div class="cf-page-head">
      <div>
        <h1 class="cf-page-title">投递管理</h1>
        <div class="cf-page-sub">把简历与 JD 关联成投递，跟踪从「想投递」到「拿 Offer」的全流程</div>
      </div>
      <el-button type="primary" @click="openCreate">+ 新建投递</el-button>
    </div>

    <div class="cf-stat-grid">
      <el-card class="cf-stat-card" shadow="hover">
        <div class="cf-stat-ico">📮</div>
        <div class="cf-stat-label">投递总数</div>
        <div class="cf-stat-value">{{ stats.total }}</div>
      </el-card>
      <el-card class="cf-stat-card" shadow="hover">
        <div class="cf-stat-ico">⏳</div>
        <div class="cf-stat-label">进行中</div>
        <div class="cf-stat-value">{{ stats.active }}</div>
      </el-card>
      <el-card class="cf-stat-card" shadow="hover">
        <div class="cf-stat-ico">🎉</div>
        <div class="cf-stat-label">已拿 Offer</div>
        <div class="cf-stat-value">{{ stats.offers }}</div>
      </el-card>
    </div>

    <div class="cf-board">
      <div v-for="col in columns" :key="col.status" class="cf-col">
        <div class="cf-col-head" :style="{ borderTopColor: col.color }">
          <span class="cf-dot" :style="{ background: col.color }"></span>
          <span class="cf-col-title">{{ col.label }}</span>
          <span class="cf-col-count">{{ col.items.length }}</span>
        </div>
        <div class="cf-col-body">
          <el-empty v-if="col.items.length === 0" description="暂无" :image-size="48" />
          <div v-for="app in col.items" :key="app.id" class="cf-card">
            <div class="cf-card-title">{{ app.resume_title }}</div>
            <div class="cf-card-sub">× {{ app.job_title }}</div>
            <div class="cf-card-meta">
              <span class="cf-meta-date">📅 {{ fmtDate(app.applied_at) }}</span>
            </div>
            <div v-if="app.notes" class="cf-card-notes">{{ app.notes }}</div>
            <el-select
              :model-value="app.status"
              size="small"
              class="cf-card-select"
              @change="(v: ApplicationStatus) => changeStatus(app, v)"
            >
              <el-option v-for="s in STATUS_ORDER" :key="s" :label="statusLabel(s)" :value="s" />
            </el-select>
            <div class="cf-card-actions">
              <el-button size="small" link type="primary" @click="openEdit(app)">编辑</el-button>
              <el-button size="small" link type="danger" @click="remove(app)">删除</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建投递 -->
    <el-dialog v-model="createVisible" title="新建投递" width="520px">
      <el-form label-width="72px">
        <el-form-item label="简历">
          <el-select v-model="createForm.resume_id" placeholder="选择简历" style="width: 100%">
            <el-option v-for="r in resumes" :key="r.id" :label="r.title" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="职位">
          <el-select v-model="createForm.job_id" placeholder="选择 JD" style="width: 100%">
            <el-option v-for="j in jobs" :key="j.id" :label="j.title" :value="j.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="createForm.status" style="width: 100%">
            <el-option v-for="s in STATUS_ORDER" :key="s" :label="statusLabel(s)" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="createForm.notes" type="textarea" :rows="3" placeholder="投递渠道、进度、待办等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑投递 -->
    <el-dialog v-model="editVisible" title="编辑投递" width="520px">
      <el-form label-width="72px" v-if="editRow">
        <el-form-item label="投递">
          <div class="cf-edit-pair">{{ editRow.resume_title }} × {{ editRow.job_title }}</div>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" style="width: 100%">
            <el-option v-for="s in STATUS_ORDER" :key="s" :label="statusLabel(s)" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="投递日期">
          <el-date-picker
            v-model="editForm.applied_at"
            type="datetime"
            placeholder="选择投递时间"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.notes" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.cf-board {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding-bottom: 8px;
}
.cf-col {
  flex: 1 1 0;
  min-width: 220px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 4px 20px rgba(30, 27, 75, 0.06);
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 280px);
}
.cf-col-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px;
  border-top: 3px solid var(--cf-primary);
  border-radius: 14px 14px 0 0;
  font-weight: 700;
}
.cf-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}
.cf-col-title {
  font-size: 14px;
}
.cf-col-count {
  margin-left: auto;
  background: #f1f0fd;
  color: var(--cf-primary);
  border-radius: 20px;
  padding: 1px 10px;
  font-size: 12px;
  font-weight: 700;
}
.cf-col-body {
  padding: 12px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.cf-card {
  background: #fafafe;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 12px;
  transition: box-shadow 0.2s, transform 0.2s;
}
.cf-card:hover {
  box-shadow: 0 6px 18px rgba(30, 27, 75, 0.1);
  transform: translateY(-2px);
}
.cf-card-title {
  font-weight: 700;
  font-size: 14px;
  color: #1f2937;
}
.cf-card-sub {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
  margin-bottom: 6px;
}
.cf-card-meta {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 6px;
}
.cf-card-notes {
  font-size: 12px;
  color: #4b5563;
  background: #fff;
  border-radius: 8px;
  padding: 6px 8px;
  margin-bottom: 8px;
  white-space: pre-wrap;
  word-break: break-word;
}
.cf-card-select {
  width: 100%;
  margin-bottom: 8px;
}
.cf-card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}
.cf-edit-pair {
  font-size: 13px;
  color: #374151;
}
</style>
