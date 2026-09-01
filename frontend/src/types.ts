export interface User {
  id: number
  email: string
  created_at: string
}

export interface Resume {
  id: number
  owner_id: number
  title: string
  content: string
  created_at: string
  updated_at: string
}

export interface Job {
  id: number
  owner_id: number
  title: string
  description: string
  created_at: string
  updated_at: string
}

export interface Analysis {
  id: number
  owner_id: number
  resume_id: number | null
  job_id: number | null
  match_score: number | null
  match_summary: string | null
  interview_questions: string | null // JSON 字符串
  created_at: string
}

// 投递状态：wishlist 想投递 / applied 已投递 / interview 面试中 / offer 已拿offer / rejected 已拒绝
export type ApplicationStatus =
  | 'wishlist'
  | 'applied'
  | 'interview'
  | 'offer'
  | 'rejected'

export interface Application {
  id: number
  owner_id: number
  resume_id: number | null
  job_id: number | null
  resume_title: string
  job_title: string
  status: ApplicationStatus
  applied_at: string | null
  notes: string
  created_at: string
  updated_at: string
}
