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
</script>

<template>
  <div style="max-width: 900px; margin: 0 auto">
    <div style="display: flex; justify-content: space-between; align-items: center">
      <h2>我的简历</h2>
      <el-button type="primary" @click="openCreate">+ 新建简历</el-button>
    </div>

    <el-table :data="resumes" v-loading="loading" empty-text="还没有简历，点右上角新建">
      <el-table-column prop="title" label="标题" />
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
  </div>
</template>
