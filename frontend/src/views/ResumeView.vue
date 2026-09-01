<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as api from '../utils/api'
import type { Resume } from '../types'

const resumes = ref<Resume[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ title: '', content: '' })
const viewVisible = ref(false)
const viewData = reactive({ title: '', content: '' })
const resumeFileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)

async function load() {
  loading.value = true
  try {
    resumes.value = await api.listResumes()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.title = ''
  form.content = ''
  dialogVisible.value = true
}

function openEdit(r: Resume) {
  editingId.value = r.id
  form.title = r.title
  form.content = r.content
  dialogVisible.value = true
}

function openView(r: Resume) {
  viewData.title = r.title
  viewData.content = r.content
  viewVisible.value = true
}

async function save() {
  try {
    if (editingId.value) {
      await api.updateResume(editingId.value, form.title, form.content)
      ElMessage.success('已更新')
    } else {
      await api.createResume(form.title, form.content)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

async function remove(r: Resume) {
  await ElMessageBox.confirm(`确定删除简历「${r.title}」？`, '提示', { type: 'warning' })
  try {
    await api.deleteResume(r.id)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(load)

async function onResumeFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // 允许重复选择同一文件
  if (!file) return
  uploading.value = true
  try {
    const r = await api.uploadResume(file)
    ElMessage.success(`已解析并创建简历：「${r.title}」`)
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
        <h1 class="cf-page-title">我的简历</h1>
        <div class="cf-page-sub">管理你的多份简历，AI 分析时会调用这里的全文</div>
      </div>
      <el-button type="primary" @click="openCreate">+ 新建简历</el-button>
      <el-button @click="resumeFileInput?.click()">📎 上传文件</el-button>
      <input
        ref="resumeFileInput"
        type="file"
        accept=".txt,.md,.pdf,.docx"
        style="display: none"
        @change="onResumeFile"
      />
    </div>

    <el-table :data="resumes" v-loading="loading" empty-text="还没有简历，点右上角新建">
      <el-table-column prop="title" label="标题" min-width="220" />
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

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑简历' : '新建简历'"
      width="600px"
    >
      <el-form label-width="60px">
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="如：校招后端简历 v1" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="10"
            placeholder="粘贴或填写简历全文，AI 分析时会用到"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="viewVisible" :title="viewData.title" width="640px">
      <div class="cf-preview">{{ viewData.content || '（无内容）' }}</div>
    </el-dialog>
  </div>
</template>
