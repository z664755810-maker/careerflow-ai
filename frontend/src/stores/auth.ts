import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '../utils/api'
import type { User } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('cf_token') || '')
  const user = ref<User | null>(
    JSON.parse(localStorage.getItem('cf_user') || 'null'),
  )

  async function login(email: string, password: string) {
    const t = await api.login(email, password)
    token.value = t
    localStorage.setItem('cf_token', t)
    user.value = await api.me()
    localStorage.setItem('cf_user', JSON.stringify(user.value))
  }

  async function register(email: string, password: string) {
    await api.register(email, password)
    await login(email, password)
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('cf_token')
    localStorage.removeItem('cf_user')
  }

  return { token, user, login, register, logout }
})
