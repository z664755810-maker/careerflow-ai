import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
  {
    path: '/register',
    name: 'register',
    component: () => import('../views/RegisterView.vue'),
  },
  {
    path: '/resumes',
    name: 'resumes',
    component: () => import('../views/ResumeView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/jobs',
    name: 'jobs',
    component: () => import('../views/JobView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/analysis',
    name: 'analysis',
    component: () => import('../views/AnalysisView.vue'),
    meta: { requiresAuth: true },
  },
  { path: '/', redirect: '/resumes' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.token) {
    return { name: 'login' }
  }
  if ((to.name === 'login' || to.name === 'register') && auth.token) {
    return { name: 'resumes' }
  }
})

export default router
