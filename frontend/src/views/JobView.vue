<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as api from '../utils/api'
import type { Job } from '../types'

const jobs = ref<Job[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ title: '', description: '', salary_range: '' })
const viewVisible = ref(false)
const viewData = reactive({ title: '', content: '', salary_range: '' })
const jobFileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)

async function load() {
  loading.value = true
  try {
    jobs.value = await api.listJobs()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.title = ''
  form.description = ''
  form.salary_range = ''
  dialogVisible.value = true
}

function openEdit(j: Job) {
  editingId.value = j.id
  form.title = j.title
  form.description = j.description
  form.salary_range = j.salary_range ?? ''
  dialogVisible.value = true
}

function openView(j: Job) {
  viewData.title = j.title
  viewData.content = j.description
  viewData.salary_range = j.salary_range ?? ''
  viewVisible.value = true
}

async function save() {
  try {
    if (editingId.value) {
      await api.updateJob(editingId.value, form.title, form.description, form.salary_range)
      ElMessage.success('已更新')
    } else {
      await api.createJob(form.title, form.description, form.salary_range)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

async function remove(j: Job) {
  await ElMessageBox.confirm(`确定删除 JD「${j.title}」？`, '提示', { type: 'warning' })
  try {
    await api.deleteJob(j.id)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(load)

async function onJobFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  uploading.value = true
  try {
    const j = await api.uploadJob(file)
    ElMessage.success(`已解析并创建 JD：「${j.title}」`)
    await load()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '解析失败')
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div style="max-width: 960px; margin: 0 auto">
    <div class="cf-page-head">
      <div>
        <h1 class="cf-page-title">职位 JD</h1>
        <div class="cf-page-sub">归档你心仪岗位的职位描述，作为 AI 匹配的基准</div>
      </div>
      <el-button type="primary" @click="openCreate">+ 新建 JD</el-button>
      <el-button @click="jobFileInput?.click()">📎 上传文件</el-button>
      <input
        ref="jobFileInput"
        type="file"
        accept=".txt,.md,.pdf,.docx"
        style="display: none"
        @change="onJobFile"
      />
    </div>

    <el-table :data="jobs" v-loading="loading" empty-text="还没有 JD，点右上角新建">
      <el-table-column prop="title" label="岗位" min-width="220" />
      <el-table-column label="更新时间" width="200">
        <template #default="{ row }">{{ new Date(row.updated_at).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" align="right">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="openView(row)">查看</el-button>
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑 JD' : '新建 JD'" width="600px">
      <el-form label-width="72px">
        <el-form-item label="岗位">
          <el-input v-model="form.title" placeholder="如：XX公司 后端开发工程师" />
        </el-form-item>
        <el-form-item label="薪资范围">
          <el-input v-model="form.salary_range" placeholder="如：12k-18k / 面议" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="10"
            placeholder="粘贴职位描述全文"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="viewVisible" :title="viewData.title" width="640px">
      <div style="font-size: 13px; color: #6b7280; margin-bottom: 8px">
        薪资范围：{{ viewData.salary_range || '（未填写）' }}
      </div>
      <div class="cf-preview">{{ viewData.content || '（无内容）' }}</div>
    </el-dialog>
  </div>
</template>
