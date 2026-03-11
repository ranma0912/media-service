import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '仪表盘' }
  },
  {
    path: '/media',
    name: 'MediaLibrary',
    component: () => import('@/views/MediaLibrary.vue'),
    meta: { title: '媒体库' }
  },
  {
    path: '/scan',
    name: 'ScanManagement',
    component: () => import('@/views/ScanManagement.vue'),
    meta: { title: '扫描管理' }
  },
  {
    path: '/recognition',
    name: 'RecognitionManagement',
    component: () => import('@/views/RecognitionManagement.vue'),
    meta: { title: '识别管理' }
  },
  {
    path: '/organize',
    name: 'OrganizeManagement',
    component: () => import('@/views/OrganizeManagement.vue'),
    meta: { title: '整理管理' }
  },
  {
    path: '/system',
    name: 'SystemManagement',
    component: () => import('@/views/SystemManagement.vue'),
    meta: { title: '系统管理' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
