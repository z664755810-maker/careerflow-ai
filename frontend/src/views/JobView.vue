<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as api from '../utils/api'
import type { Job } from '../types'

const jobs = ref<Job[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ title: '', description: '' })

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
  dialogVisible.value = true
}

function openEdit(j: Job) {
  editingId.value = j.id
  form.title = j.title
  form.description = j.description
  dialogVisible.value = true
}

async function save() {
  try {
    if (editingId.value) {
      await api.updateJob(editingId.value, form.title, form.description)
      ElMessage.success('已更新')
    } else {
      await api.createJob(form.title, form.description)
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
</script>

<template>
  <div style="max-width: 900px; margin: 0 auto">
    <div style="display: flex; justify-content: space-between; align-items: center">
      <h2>职位描述 (JD)</h2>
      <el-button type="primary" @click="openCreate">+ 新建 JD</el-button>
    </div>

    <el-table :data="jobs" v-loading="loading" empty-text="还没有 JD，点右上角新建">
      <el-table-column prop="title" label="岗位" />
      <el-table-column label="更新时间" width="200">
        <template #default="{ row }">{{ new Date(row.updated_at).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑 JD' : '新建 JD'" width="600px">
      <el-form label-width="60px">
        <el-form-item label="岗位">
          <el-input v-model="form.title" placeholder="如：XX公司 后端开发工程师" />
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
  </div>
</template>
