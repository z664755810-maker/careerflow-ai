<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import * as api from '../utils/api'
import type { Analysis, InterviewMessage, InterviewSession } from '../types'

const route = useRoute()

const analyses = ref<Analysis[]>([])
const sessions = ref<InterviewSession[]>([])
const activeId = ref<number | null>(null)
const active = ref<InterviewSession | null>(null)
const answerText = ref('')
const sending = ref(false)
const starting = ref(false)
const dialogVisible = ref(false)
const pickAnalysisId = ref<number>()

const messages = computed<InterviewMessage[]>(() => {
  if (!active.value) return []
  try {
    const arr = JSON.parse(active.value.messages)
    return Array.isArray(arr) ? (arr as InterviewMessage[]) : []
  } catch {
    return []
  }
})

const inProgress = computed(() => active.value?.status === 'in_progress')
const isCompleted = computed(() => active.value?.status === 'completed')

const scoredSessions = computed(() =>
  sessions.value.map((s) => s.current_score).filter((s): s is number => s != null),
)
const avgScore = computed(() =>
  scoredSessions.value.length
    ? Math.round(scoredSessions.value.reduce((a, b) => a + b, 0) / scoredSessions.value.length)
    : 0,
)
const inProgressCount = computed(
  () => sessions.value.filter((s) => s.status === 'in_progress').length,
)
const completedCount = computed(
  () => sessions.value.filter((s) => s.status === 'completed').length,
)

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

const chatBox = ref<HTMLElement | null>(null)
function scrollToBottom() {
  nextTick(() => {
    const el = chatBox.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function loadAll() {
  ;[analyses.value, sessions.value] = await Promise.all([
    api.listAnalyses(),
    api.listInterviews(),
  ])
}

function selectSession(s: InterviewSession) {
  active.value = s
  activeId.value = s.id
  answerText.value = ''
  scrollToBottom()
}

async function openNew() {
  if (analyses.value.length === 0) {
    ElMessage.warning('请先在「AI 分析」页生成至少一次分析，才能开启模拟面试。')
    return
  }
  pickAnalysisId.value = analyses.value[0]?.id
  dialogVisible.value = true
}

async function start() {
  if (!pickAnalysisId.value) {
    ElMessage.warning('请选择一个分析记录')
    return
  }
  starting.value = true
  try {
    const s = await api.startInterview(pickAnalysisId.value)
    dialogVisible.value = false
    await loadAll()
    selectSession(s)
    ElMessage.success('面试已开始，来看看第一题吧')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '开启失败')
  } finally {
    starting.value = false
  }
}

async function send() {
  if (!active.value || !inProgress.value) return
  const text = answerText.value.trim()
  if (!text) {
    ElMessage.warning('请输入你的回答')
    return
  }
  sending.value = true
  try {
    const s = await api.answerInterview(active.value.id, text)
    answerText.value = ''
    active.value = s
    const idx = sessions.value.findIndex((x) => x.id === s.id)
    if (idx >= 0) sessions.value[idx] = s
    scrollToBottom()
    if (s.status === 'completed') {
      ElMessage.success(`面试结束，本轮累计均分 ${s.current_score ?? '-'}`)
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '提交失败')
  } finally {
    sending.value = false
  }
}

async function remove(s: InterviewSession) {
  await ElMessageBox.confirm('确定删除这场面试会话？此操作不可恢复。', '删除确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  try {
    await api.deleteInterview(s.id)
    if (activeId.value === s.id) {
      active.value = null
      activeId.value = null
    }
    await loadAll()
    ElMessage.success('已删除')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(async () => {
  await loadAll()
  // 从「AI 分析」详情一键进入：自动开启对应该分析的面试（已存在则直接打开）
  const q = route.query.analysis_id
  if (q != null && String(q).trim() !== '') {
    const aid = Number(q)
    if (aid) {
      const existing = sessions.value.find((s) => s.analysis_id === aid)
      if (existing) {
        selectSession(existing)
      } else if (analyses.value.some((a) => a.id === aid)) {
        starting.value = true
        try {
          const s = await api.startInterview(aid)
          await loadAll()
          selectSession(s)
        } catch (e: any) {
          ElMessage.error(e.response?.data?.detail || '开启面试失败')
        } finally {
          starting.value = false
        }
      } else {
        ElMessage.warning('未找到对应分析记录，请重新从分析页进入')
      }
    }
  }
})
</script>

<template>
  <div>
    <div class="cf-page-head">
      <div>
        <h1 class="cf-page-title">模拟面试</h1>
        <div class="cf-page-sub">
          基于某次 AI 匹配分析，开启一轮多轮面试：AI 出题、逐轮点评打分、实时累计均分
        </div>
      </div>
      <el-button type="primary" @click="openNew">🎤 开启新面试</el-button>
    </div>

    <div class="cf-stat-grid">
      <el-card class="cf-stat-card" shadow="hover">
        <div class="cf-stat-ico">💬</div>
        <div class="cf-stat-label">面试会话</div>
        <div class="cf-stat-value">{{ sessions.length }}</div>
      </el-card>
      <el-card class="cf-stat-card" shadow="hover">
        <div class="cf-stat-ico">⏳</div>
        <div class="cf-stat-label">进行中</div>
        <div class="cf-stat-value">{{ inProgressCount }}</div>
      </el-card>
      <el-card class="cf-stat-card" shadow="hover">
        <div class="cf-stat-ico">🏁</div>
        <div class="cf-stat-label">已结束</div>
        <div class="cf-stat-value">{{ completedCount }}</div>
      </el-card>
      <el-card class="cf-stat-card" shadow="hover">
        <div class="cf-stat-ico">📈</div>
        <div class="cf-stat-label">平均得分</div>
        <div class="cf-stat-value">{{ avgScore }}</div>
      </el-card>
    </div>

    <el-row :gutter="16">
      <el-col :span="8">
        <el-card shadow="never" class="cf-session-card">
          <div class="cf-page-head" style="margin-bottom: 10px">
            <h3 style="margin: 0">历史会话</h3>
          </div>
          <el-empty v-if="sessions.length === 0" description="还没有面试会话" :image-size="80" />
          <div v-else class="cf-session-list">
            <div
              v-for="s in sessions"
              :key="s.id"
              class="cf-session-item"
              :class="{ active: s.id === activeId }"
              @click="selectSession(s)"
            >
              <div class="cf-session-title">{{ s.analysis_title }}</div>
              <div class="cf-session-meta">
                <el-tag size="small" :type="scoreTag(s.current_score)">{{ s.current_score ?? '-' }}</el-tag>
                <el-tag size="small" :type="s.status === 'completed' ? 'success' : 'warning'">
                  {{ s.status === 'completed' ? '已结束' : '进行中' }}
                </el-tag>
                <span class="cf-session-time">{{ new Date(s.updated_at).toLocaleString() }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card shadow="never" class="cf-chat-card">
          <template v-if="active">
            <div class="cf-chat-head">
              <div>
                <div class="cf-chat-title">{{ active.analysis_title }}</div>
                <div class="cf-chat-sub">
                  <span>状态：</span>
                  <el-tag size="small" :type="active.status === 'completed' ? 'success' : 'warning'">
                    {{ active.status === 'completed' ? '已结束' : '进行中' }}
                  </el-tag>
                  <span class="cf-chat-score">
                    累计均分：<b :style="{ color: scoreColor(active.current_score) }">{{ active.current_score ?? '-' }}</b>
                  </span>
                </div>
              </div>
              <el-button size="small" link type="danger" @click="remove(active)">删除会话</el-button>
            </div>

            <el-alert
              v-if="isCompleted"
              type="success"
              :closable="false"
              style="margin-bottom: 12px"
              :title="`面试已结束，本轮累计均分 ${active.current_score ?? '-'}`"
            />

            <div ref="chatBox" class="cf-chat-box">
              <div v-for="(m, i) in messages" :key="i" class="cf-msg" :class="m.role">
                <div class="cf-msg-role">{{ m.role === 'interviewer' ? '面试官' : '我' }}</div>
                <div class="cf-msg-bubble">{{ m.content }}</div>
                <div
                  v-if="m.role === 'interviewer' && m.score != null"
                  class="cf-msg-score"
                  :style="{ color: scoreColor(m.score) }"
                >
                  本问评分 {{ m.score }}
                </div>
              </div>
            </div>

            <div class="cf-chat-input">
              <el-input
                v-model="answerText"
                type="textarea"
                :rows="3"
                placeholder="在这里输入你的回答…"
                :disabled="!inProgress || sending"
                @keydown.ctrl.enter="send"
              />
              <el-button type="primary" :loading="sending" :disabled="!inProgress" @click="send">
                {{ inProgress ? '提交回答' : '面试已结束' }}
              </el-button>
            </div>
            <div v-if="inProgress" class="cf-chat-hint">提示：Ctrl + Enter 快捷提交</div>
          </template>
          <el-empty v-else description="从左侧选择一场会话，或点击右上角「开启新面试」" />
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="dialogVisible" title="开启模拟面试" width="480px">
      <el-form label-width="80px">
        <el-form-item label="选择分析">
          <el-select v-model="pickAnalysisId" placeholder="选择一次匹配分析" style="width: 100%">
            <el-option
              v-for="a in analyses"
              :key="a.id"
              :label="`#${a.id} 匹配分 ${a.match_score ?? '-'}`"
              :value="a.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="starting" @click="start">开始面试</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.cf-session-card,
.cf-chat-card {
  height: calc(100vh - 220px);
  display: flex;
  flex-direction: column;
}
.cf-session-list {
  overflow: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cf-session-item {
  border: 1px solid #eef0f6;
  border-radius: 12px;
  padding: 12px 14px;
  cursor: pointer;
  background: #fff;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.1s ease;
}
.cf-session-item:hover {
  border-color: #c7c9f7;
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.1);
}
.cf-session-item.active {
  border-color: var(--cf-primary);
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.22);
  background: #f5f5ff;
}
.cf-session-title {
  font-weight: 600;
  font-size: 14px;
  color: #1f2937;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cf-session-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.cf-session-time {
  font-size: 11px;
  color: #94a3b8;
  margin-left: auto;
}

.cf-chat-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f1f6;
  margin-bottom: 12px;
}
.cf-chat-title {
  font-weight: 700;
  font-size: 15px;
  color: #1f2937;
}
.cf-chat-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  font-size: 13px;
  color: #6b7280;
}
.cf-chat-score {
  margin-left: 4px;
}

.cf-chat-box {
  flex: 1;
  overflow: auto;
  padding: 4px 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: #fafbff;
  border-radius: 12px;
}
.cf-msg {
  display: flex;
  flex-direction: column;
  max-width: 82%;
}
.cf-msg.interviewer {
  align-self: flex-start;
  align-items: flex-start;
}
.cf-msg.candidate {
  align-self: flex-end;
  align-items: flex-end;
}
.cf-msg-role {
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 4px;
}
.cf-msg-bubble {
  padding: 10px 14px;
  border-radius: 14px;
  line-height: 1.7;
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
}
.cf-msg.interviewer .cf-msg-bubble {
  background: #fff;
  border: 1px solid #eef0f6;
  border-top-left-radius: 4px;
  color: #1f2937;
}
.cf-msg.candidate .cf-msg-bubble {
  background: linear-gradient(135deg, var(--cf-primary), var(--cf-violet));
  color: #fff;
  border-top-right-radius: 4px;
}
.cf-msg-score {
  margin-top: 4px;
  font-size: 12px;
  font-weight: 700;
}

.cf-chat-input {
  display: flex;
  gap: 12px;
  margin-top: 12px;
  align-items: flex-end;
}
.cf-chat-input .el-input {
  flex: 1;
}
.cf-chat-hint {
  margin-top: 6px;
  font-size: 12px;
  color: #94a3b8;
  text-align: right;
}
</style>
