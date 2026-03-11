<template>
  <div class="scan-management">
    <!-- 快捷操作 -->
    <el-card class="action-card">
      <div class="actions">
        <el-button type="primary" :icon="VideoCamera" @click="handleScan">
          立即扫描
        </el-button>
        <el-button :icon="FolderOpened" @click="handleSelectPath">
          选择扫描路径
        </el-button>
        <el-button :icon="Setting" @click="handleConfig">
          扫描配置
        </el-button>
      </div>
    </el-card>

    <!-- 扫描任务列表 -->
    <el-card class="task-card">
      <template #header>
        <div class="card-header">
          <span class="title">扫描任务</span>
          <el-button :icon="Refresh" @click="loadTasks">刷新</el-button>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="taskList"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="任务ID" width="100" />
        <el-table-column prop="targetPath" label="扫描路径" min-width="200" show-overflow-tooltip />
        <el-table-column prop="scanType" label="扫描类型" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.scanType === 'full'" type="primary">全量</el-tag>
            <el-tag v-else type="success">增量</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'running'" type="warning">扫描中</el-tag>
            <el-tag v-else-if="row.status === 'completed'" type="success">已完成</el-tag>
            <el-tag v-else-if="row.status === 'failed'" type="danger">失败</el-tag>
            <el-tag v-else type="info">等待中</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="totalFiles" label="文件总数" width="100" />
        <el-table-column prop="newFiles" label="新增文件" width="100" />
        <el-table-column prop="duration" label="耗时" width="100">
          <template #default="{ row }">
            {{ formatDuration(row.duration) }}
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="开始时间" width="160" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">查看</el-button>
            <el-button v-if="row.status === 'running'" link type="danger" @click="handleStop(row)">停止</el-button>
            <el-button v-else-if="row.status === 'failed'" link type="primary" @click="handleRetry(row)">重试</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 扫描路径配置 -->
    <el-card class="path-card">
      <template #header>
        <div class="card-header">
          <span class="title">监控路径</span>
          <el-button type="primary" :icon="Plus" @click="handleAddPath">添加路径</el-button>
        </div>
      </template>

      <el-table :data="pathList" stripe style="width: 100%">
        <el-table-column prop="path" label="路径" min-width="200" show-overflow-tooltip />
        <el-table-column prop="recursive" label="递归" width="80">
          <template #default="{ row }">
            <el-tag :type="row.recursive ? 'success' : 'info'">
              {{ row.recursive ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'">
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEditPath(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDeletePath(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 扫描路径选择对话框 -->
    <el-dialog v-model="pathDialogVisible" title="选择扫描路径" width="600px">
      <el-form :model="pathForm" label-width="100px">
        <el-form-item label="扫描路径">
          <el-input v-model="pathForm.path" placeholder="输入或选择路径">
            <template #append>
              <el-button :icon="Folder" @click="handleBrowsePath">浏览</el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="递归扫描">
          <el-switch v-model="pathForm.recursive" />
        </el-form-item>
        <el-form-item label="启用监控">
          <el-switch v-model="pathForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pathDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSavePath">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoCamera, FolderOpened, Setting, Refresh, Plus, Folder } from '@element-plus/icons-vue'

// 加载状态
const loading = ref(false)

// 扫描任务列表
const taskList = ref([])

// 扫描路径列表
const pathList = ref([
  {
    id: 1,
    path: 'D:/Downloads',
    recursive: true,
    enabled: true
  },
  {
    id: 2,
    path: 'E:/Media/Inbox',
    recursive: false,
    enabled: true
  }
])

// 路径对话框
const pathDialogVisible = ref(false)
const pathForm = reactive({
  path: '',
  recursive: true,
  enabled: true
})

// 格式化时长
const formatDuration = (seconds) => {
  if (!seconds) return '-'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) {
    return `${h}时${m}分${s}秒`
  } else if (m > 0) {
    return `${m}分${s}秒`
  } else {
    return `${s}秒`
  }
}

// 加载扫描任务
const loadTasks = async () => {
  loading.value = true
  try {
    // TODO: 调用实际API
    // const res = await request.get('/api/scan/tasks')
    // taskList.value = res.data

    // 模拟数据
    taskList.value = [
      {
        id: 1,
        targetPath: 'D:/Downloads',
        scanType: 'incremental',
        status: 'completed',
        totalFiles: 150,
        newFiles: 10,
        duration: 45,
        createdAt: '2024-01-15 10:30:00'
      },
      {
        id: 2,
        targetPath: 'E:/Media/Inbox',
        scanType: 'full',
        status: 'running',
        totalFiles: 0,
        newFiles: 0,
        duration: 0,
        createdAt: '2024-01-15 11:00:00'
      }
    ]
  } catch (error) {
    ElMessage.error('加载扫描任务失败')
  } finally {
    loading.value = false
  }
}

// 立即扫描
const handleScan = () => {
  ElMessageBox.confirm('确定要立即开始扫描吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'info'
  }).then(() => {
    ElMessage.success('扫描任务已启动')
    loadTasks()
  }).catch(() => {})
}

// 选择扫描路径
const handleSelectPath = () => {
  pathDialogVisible.value = true
}

// 扫描配置
const handleConfig = () => {
  ElMessage.info('扫描配置功能开发中')
}

// 查看任务详情
const handleView = (row) => {
  ElMessage.info(`查看任务: ${row.id}`)
}

// 停止扫描
const handleStop = (row) => {
  ElMessageBox.confirm('确定要停止这个扫描任务吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('扫描任务已停止')
    loadTasks()
  }).catch(() => {})
}

// 重试扫描
const handleRetry = (row) => {
  ElMessage.info(`重试任务: ${row.id}`)
}

// 添加路径
const handleAddPath = () => {
  Object.assign(pathForm, {
    path: '',
    recursive: true,
    enabled: true
  })
  pathDialogVisible.value = true
}

// 编辑路径
const handleEditPath = (row) => {
  Object.assign(pathForm, {
    path: row.path,
    recursive: row.recursive,
    enabled: row.enabled
  })
  pathDialogVisible.value = true
}

// 删除路径
const handleDeletePath = (row) => {
  ElMessageBox.confirm('确定要删除这个扫描路径吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    const index = pathList.value.findIndex(item => item.id === row.id)
    if (index > -1) {
      pathList.value.splice(index, 1)
      ElMessage.success('删除成功')
    }
  }).catch(() => {})
}

// 浏览路径
const handleBrowsePath = () => {
  ElMessage.info('路径浏览功能开发中')
}

// 保存路径
const handleSavePath = () => {
  if (!pathForm.path) {
    ElMessage.warning('请输入扫描路径')
    return
  }

  // TODO: 调用实际API保存路径配置
  ElMessage.success('保存成功')
  pathDialogVisible.value = false
}

// 初始化
loadTasks()
</script>

<style lang="scss" scoped>
.scan-management {
  .action-card {
    margin-bottom: 16px;

    .actions {
      display: flex;
      gap: 12px;
    }
  }

  .task-card,
  .path-card {
    margin-bottom: 16px;

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;

      .title {
        font-size: 16px;
        font-weight: 500;
      }
    }
  }
}
</style>
