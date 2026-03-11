<template>
  <el-container class="app-container">
    <el-aside width="240px" class="app-aside">
      <div class="logo">
        <el-icon><VideoCamera /></el-icon>
        <span>流媒体服务</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="app-menu"
        background-color="#001529"
        text-color="#fff"
        active-text-color="#1890ff"
      >
        <el-menu-item index="/">
          <el-icon><Odometer /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/media">
          <el-icon><VideoPlay /></el-icon>
          <span>媒体库</span>
        </el-menu-item>
        <el-menu-item index="/scan">
          <el-icon><Search /></el-icon>
          <span>扫描管理</span>
        </el-menu-item>
        <el-menu-item index="/recognition">
          <el-icon><Collection /></el-icon>
          <span>识别管理</span>
        </el-menu-item>
        <el-menu-item index="/organize">
          <el-icon><FolderOpened /></el-icon>
          <span>整理管理</span>
        </el-menu-item>
        <el-menu-item index="/system">
          <el-icon><Setting /></el-icon>
          <span>系统管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <div class="header-left">
          <el-button text @click="toggleAside">
            <el-icon size="20"><Fold /></el-icon>
          </el-button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRoute.name">{{ currentRoute.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-button text>
            <el-icon><Bell /></el-icon>
          </el-button>
          <el-dropdown>
            <el-button text>
              <el-icon><User /></el-icon>
              <span>管理员</span>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>个人中心</el-dropdown-item>
                <el-dropdown-item divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)
const currentRoute = computed(() => route)

const toggleAside = () => {
  // TODO: 实现侧边栏折叠
}
</script>

<style lang="scss" scoped>
.app-container {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.app-aside {
  background-color: #001529;
  overflow-x: hidden;

  .logo {
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 18px;
    font-weight: bold;

    .el-icon {
      font-size: 24px;
      margin-right: 8px;
    }
  }

  .app-menu {
    border-right: none;
    height: calc(100vh - 64px);
  }
}

.app-header {
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;

  .header-left,
  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }
}

.app-main {
  background: #f0f2f5;
  padding: 24px;
  overflow-y: auto;
}
</style>
