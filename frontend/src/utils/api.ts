import axios from 'axios'
import type { Analysis, Application, ApplicationStatus, Job, Resume, User } from '../types'

// API 基地址：默认走同源 /api（开发由 Vite 代理，生产由 Vercel 重写）
const base = import.meta.env.VITE_API_BASE || '/api'

export const api = axios.create({ baseURL: base })

// 请求拦截：自动附带 JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cf_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：401 清除登录态并跳登录
api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('cf_token')
      localStorage.removeItem('cf_user')
      if (location.pathname !== '/login') {
        location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

// ---------- 鉴权 ----------
export async function register(email: string, password: string): Promise<User> {
  const { data } = await api.post<User>('/auth/register', { email, password })
  return data
}

export async function login(email: string, password: string): Promise<string> {
  // OAuth2PasswordRequestForm 要求 x-www-form-urlencoded
  const body = new URLSearchParams({ username: email, password })
  const { data } = await api.post<{ access_token: string }>('/auth/login', body)
  return data.access_token
}

export async function me(): Promise<User> {
  const { data } = await api.get<User>('/auth/me')
  return data
}

// ---------- 简历 ----------
export async function listResumes(): Promise<Resume[]> {
  const { data } = await api.get<Resume[]>('/resumes')
  return data
}
export async function createResume(title: string, content: string): Promise<Resume> {
  const { data } = await api.post<Resume>('/resumes', { title, content })
  return data
}
export async function updateResume(
  id: number,
  title: string,
  content: string,
): Promise<Resume> {
  const { data } = await api.put<Resume>(`/resumes/${id}`, { title, content })
  return data
}
export async function deleteResume(id: number): Promise<void> {
  await api.delete(`/resumes/${id}`)
}

// ---------- JD ----------
export async function listJobs(): Promise<Job[]> {
  const { data } = await api.get<Job[]>('/jobs')
  return data
}
export async function createJob(title: string, description: string): Promise<Job> {
  const { data } = await api.post<Job>('/jobs', { title, description })
  return data
}
export async function updateJob(
  id: number,
  title: string,
  description: string,
): Promise<Job> {
  const { data } = await api.put<Job>(`/jobs/${id}`, { title, description })
  return data
}
export async function deleteJob(id: number): Promise<void> {
  await api.delete(`/jobs/${id}`)
}

// ---------- 文件上传解析 ----------
export async function uploadResume(file: File, title?: string): Promise<Resume> {
  const fd = new FormData()
  fd.append('file', file)
  if (title) fd.append('title', title)
  const { data } = await api.post<Resume>('/resumes/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function uploadJob(file: File, title?: string): Promise<Job> {
  const fd = new FormData()
  fd.append('file', file)
  if (title) fd.append('title', title)
  const { data } = await api.post<Job>('/jobs/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// ---------- 投递管理 ----------
export async function listApplications(status?: ApplicationStatus): Promise<Application[]> {
  const { data } = await api.get<Application[]>('/applications', {
    params: status ? { status } : {},
  })
  return data
}
export async function createApplication(
  resume_id: number,
  job_id: number,
  status: ApplicationStatus = 'wishlist',
  notes = '',
): Promise<Application> {
  const { data } = await api.post<Application>('/applications', {
    resume_id,
    job_id,
    status,
    notes,
  })
  return data
}
export async function updateApplication(
  id: number,
  payload: Partial<{ status: ApplicationStatus; applied_at: string | null; notes: string }>,
): Promise<Application> {
  const { data } = await api.put<Application>(`/applications/${id}`, payload)
  return data
}
export async function deleteApplication(id: number): Promise<void> {
  await api.delete(`/applications/${id}`)
}

// ---------- AI 分析 ----------
export async function createAnalysis(
  resume_id: number,
  job_id: number,
): Promise<Analysis> {
  const { data } = await api.post<Analysis>('/analysis', { resume_id, job_id })
  return data
}
export async function listAnalyses(): Promise<Analysis[]> {
  const { data } = await api.get<Analysis[]>('/analysis')
  return data
}
export async function deleteAnalysis(id: number): Promise<void> {
  await api.delete(`/analysis/${id}`)
}
