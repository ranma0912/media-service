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
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="任务ID" width="100" />
        <el-table-column prop="targetPath" label="扫描路径" min-width="200" show-overflow-tooltip />
        <el-table-column prop="scanType" label="扫描类型" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.scanType === 'full'" type="primary">全量</el-tag>
            <el-tag v-else-if="row.scanType === 'incremental'" type="success">增量</el-tag>
            <el-tag v-else-if="row.scanType === 'rescan'" type="warning">重新扫描</el-tag>
            <el-tag v-else type="info">{{ row.scanType }}</el-tag>
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
        <el-table-column prop="totalFiles" label="文件总数" width="100">
          <template #default="{ row }">
            {{ row.totalFiles || row.total_files || 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="newFiles" label="新增文件" width="100">
          <template #default="{ row }">
            {{ row.newFiles || row.new_files || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="进度" width="150">
          <template #default="{ row }">
            <el-progress
              v-if="row.status === 'running'"
              :percentage="row.progress || 0"
              :status="row.progress >= 100 ? 'success' : ''"
            />
            <span v-else-if="row.status === 'completed'">已完成</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时" width="100">
          <template #default="{ row }">
            {{ formatDuration(row.duration) }}
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="开始时间" width="160" />
        <el-table-column label="当前文件" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.currentFile || row.current_file || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">查看</el-button>
            <el-button v-if="row.status === 'running'" link type="danger" @click="handleStop(row)">停止</el-button>
            <el-button v-else-if="row.status === 'failed'" link type="primary" @click="handleRetry(row)">重试</el-button>
            <el-button v-if="row.status === 'completed'" link type="success" @click="handleRescan(row)">重新扫描</el-button>
            <el-button v-if="row.status !== 'running'" link type="danger" @click="handleDelete(row)">删除</el-button>
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
import { ref, reactive, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoCamera, FolderOpened, Setting, Refresh, Plus, Folder } from '@element-plus/icons-vue'
import WebSocketClient from '@/utils/websocket'

// 加载状态
const loading = ref(false)

// 扫描任务列表
const taskList = ref([])

// WebSocket连接
const wsConnections = new Map() // task_id -> WebSocketClient

const scanProgress = new Map() // task_id -> progress data

// 扫描路径列表
const pathList = ref([])

// 选中的任务
const selectedTasks = ref([])

// 加载路径列表
const loadPaths = async () => {
  try {
    const { getScanPaths } = await import('@/api/scan')
    const paths = await getScanPaths()
    pathList.value = paths.map(p => ({
      id: p.id,
      path: p.path,
      recursive: p.recursive,
      enabled: p.enabled,
      lastScanAt: p.last_scan_at
    }))
  } catch (error) {
    console.error('加载扫描路径失败:', error)
  }
}

// 路径对话框
const pathDialogVisible = ref(false)
const editingPathId = ref(null)
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
    // 调用实际API
    const { getScanHistory } = await import('@/api/scan')
    const res = await getScanHistory({
      limit: 20,
      offset: 0
    })

    // 转换数据格式以匹配前端需求
    taskList.value = res.items.map(item => ({
      id: item.id,
      targetPath: item.target_path,
      scanType: item.scan_type,
      status: item.completed_at ? 'completed' : 'running',
      totalFiles: item.total_files,
      newFiles: item.new_files,
      duration: item.duration_seconds,
      createdAt: item.started_at,
      completedAt: item.completed_at,
      errorMessage: item.error_message
    }))
  } catch (error) {
    console.error('加载扫描任务失败:', error)
    ElMessage.error('加载扫描任务失败')
  } finally {
    loading.value = false
  }
}

// 立即扫描
const handleScan = async () => {
  try {
    // 获取第一个启用的路径
    const enabledPath = pathList.value.find(p => p.enabled)
    if (!enabledPath) {
      ElMessage.warning('没有可用的扫描路径，请先添加扫描路径')
      return
    }

    await ElMessageBox.confirm(`确定要立即扫描路径 ${enabledPath.path} 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    })

    // 调用实际API创建扫描任务
    const { createScanTask } = await import('@/api/scan')
    const result = await createScanTask({
      path_id: enabledPath.id,
      scan_type: 'incremental',
      recursive: enabledPath.recursive
    })

    // 连接WebSocket监听进度
    connectScanProgress(result.task_id)

    ElMessage.success('扫描任务已启动')
    loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('启动扫描失败:', error)
      ElMessage.error('启动扫描失败')
    }
  }
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
const handleView = async (row) => {
  try {
    const { getScanTask } = await import('@/api/scan')
    const detail = await getScanTask(row.id)
    
    ElMessageBox.alert(
      `<div style="text-align: left;">
        <p><strong>任务ID:</strong> ${detail.id}</p>
        <p><strong>批次ID:</strong> ${detail.batch_id}</p>
        <p><strong>扫描路径:</strong> ${detail.target_path}</p>
        <p><strong>扫描类型:</strong> ${detail.scan_type === 'full' ? '全量' : '增量'}</p>
        <p><strong>递归扫描:</strong> ${detail.recursive ? '是' : '否'}</p>
        <p><strong>文件总数:</strong> ${detail.total_files}</p>
        <p><strong>新增文件:</strong> ${detail.new_files}</p>
        <p><strong>更新文件:</strong> ${detail.updated_files}</p>
        <p><strong>跳过文件:</strong> ${detail.skipped_files}</p>
        <p><strong>失败文件:</strong> ${detail.failed_files}</p>
        <p><strong>耗时:</strong> ${detail.duration_seconds}秒</p>
        <p><strong>开始时间:</strong> ${detail.started_at}</p>
        <p><strong>完成时间:</strong> ${detail.completed_at || '进行中'}</p>
        ${detail.error_message ? `<p><strong>错误信息:</strong> ${detail.error_message}</p>` : ''}
      </div>`,
      '任务详情',
      {
        dangerouslyUseHTMLString: true,
        confirmButtonText: '关闭'
      }
    )
  } catch (error) {
    console.error('获取任务详情失败:', error)
    ElMessage.error('获取任务详情失败')
  }
}

// 停止扫描
const handleStop = async (row) => {
  try {
    await ElMessageBox.confirm('确定要停止这个扫描任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    // 调用实际API停止扫描任务
    const { stopScanTask } = await import('@/api/scan')
    await stopScanTask(row.id)

    ElMessage.success('扫描任务已停止')
    loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('停止扫描失败:', error)
      ElMessage.error('停止扫描失败')
    }
  }
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedTasks.value = selection
}

// 删除扫描任务
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这个扫描任务吗？此操作不可恢复！', '警告', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const { deleteScanTask } = await import('@/api/scan')
    await deleteScanTask(row.id)

    ElMessage.success('扫描任务已删除')
    loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除扫描任务失败:', error)
      ElMessage.error('删除扫描任务失败')
    }
  }
}

// 重新扫描
const handleRescan = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要重新扫描路径 ${row.targetPath} 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    })

    const { retryScanTask } = await import('@/api/scan')
    const result = await retryScanTask(row.id)

    // 连接WebSocket监听进度
    connectScanProgress(result.task_id)

    ElMessage.success('重新扫描任务已启动')
    loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重新扫描失败:', error)
      const errorMessage = error.response?.data?.detail || error.message || '重新扫描失败'
      ElMessage.error(errorMessage)
    }
  }
}

// 重试扫描
const handleRetry = async (row) => {
  try {
    await ElMessageBox.confirm('确定要重试这个扫描任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    })

    // 调用实际API重试扫描任务
    const { retryScanTask } = await import('@/api/scan')
    await retryScanTask(row.id)

    ElMessage.success('扫描任务已重新创建')
    loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重试扫描失败:', error)
      ElMessage.error('重试扫描失败')
    }
  }
}

// 添加路径
const handleAddPath = () => {
  editingPathId.value = null
  Object.assign(pathForm, {
    path: '',
    recursive: true,
    enabled: true
  })
  pathDialogVisible.value = true
}

// 编辑路径
const handleEditPath = (row) => {
  editingPathId.value = row.id
  Object.assign(pathForm, {
    path: row.path,
    recursive: row.recursive,
    enabled: row.enabled
  })
  pathDialogVisible.value = true
}

// 删除路径
const handleDeletePath = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这个扫描路径吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(async () => {
      // 调用实际API删除路径
      const { deleteScanPath } = await import('@/api/scan')
      await deleteScanPath(row.id)

      // 从列表中移除
      const index = pathList.value.findIndex(item => item.id === row.id)
      if (index > -1) {
        pathList.value.splice(index, 1)
        ElMessage.success('删除成功')
      }
    }).catch(() => {})
  } catch (error) {
    console.error('删除路径失败:', error)
    ElMessage.error('删除路径失败')
  }
}

// 浏览路径
const handleBrowsePath = () => {
  ElMessage.info('路径浏览功能开发中')
}

// 保存路径
const handleSavePath = async () => {
  if (!pathForm.path) {
    ElMessage.warning('请输入扫描路径')
    return
  }

  try {
    const { addScanPath, updateScanPath, getScanPaths } = await import('@/api/scan')
    
    // 检查是新增还是编辑
    if (editingPathId.value) {
      // 更新现有路径
      await updateScanPath(editingPathId.value, {
        path: pathForm.path,
        recursive: pathForm.recursive,
        enabled: pathForm.enabled
      })
      ElMessage.success('更新成功')
    } else {
      // 添加新路径
      await addScanPath({
        path: pathForm.path,
        recursive: pathForm.recursive,
        enabled: pathForm.enabled
      })
      ElMessage.success('添加成功')
    }
    
    // 重新加载路径列表
    const paths = await getScanPaths()
    pathList.value = paths.map(p => ({
      id: p.id,
      path: p.path,
      recursive: p.recursive,
      enabled: p.enabled,
      lastScanAt: p.last_scan_at
    }))
    
    pathDialogVisible.value = false
  } catch (error) {
    console.error('保存路径失败:', error)
    ElMessage.error(error.response?.data?.detail || '保存路径失败')
  }
}

// 连接WebSocket监听扫描进度
const connectScanProgress = (taskId) => {
  // 如果已存在连接，先关闭
  if (wsConnections.has(taskId)) {
    wsConnections.get(taskId).close()
  }

  // 创建新的WebSocket连接
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/ws/scan/${taskId}`
  const ws = new WebSocketClient(wsUrl)

  // 监听消息
  ws.on('message', (data) => {
    console.log('收到扫描进度:', data)
    scanProgress.set(taskId, data)

    // 更新任务列表中的进度
    const task = taskList.value.find(t => t.id === taskId)
    if (task) {
      task.progress = data.progress
      task.scannedFiles = data.scanned_files
      task.totalFiles = data.total_files
      task.currentFile = data.current_file
      task.status = data.status
    }
  })

  // 监听连接状态
  ws.on('connected', () => {
    console.log(`扫描任务 ${taskId} WebSocket连接成功`)
  })

  ws.on('disconnected', () => {
    console.log(`扫描任务 ${taskId} WebSocket断开连接`)
  })

  // 存储连接
  wsConnections.set(taskId, ws)
}

// 断开WebSocket连接
const disconnectScanProgress = (taskId) => {
  if (wsConnections.has(taskId)) {
    wsConnections.get(taskId).close()
    wsConnections.delete(taskId)
  }
  if (scanProgress.has(taskId)) {
    scanProgress.delete(taskId)
  }
}

// 初始化
loadTasks()
loadPaths()

// 定时刷新任务列表（每5秒）
const refreshInterval = setInterval(() => {
  loadTasks()
}, 5000)

// 组件卸载时清理
onUnmounted(() => {
  clearInterval(refreshInterval)
  wsConnections.forEach(ws => ws.close())
  wsConnections.clear()
  scanProgress.clear()
})
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
