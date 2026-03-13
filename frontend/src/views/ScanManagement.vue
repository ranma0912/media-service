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
          <div class="header-actions">
            <el-button 
              type="danger" 
              :disabled="selectedTasks.length === 0"
              @click="handleBatchStop"
            >
              批量停止 ({{ selectedTasks.length }})
            </el-button>
            <el-button 
              type="danger" 
              :disabled="selectedTasks.length === 0"
              @click="handleBatchDelete"
            >
              批量删除 ({{ selectedTasks.length }})
            </el-button>
            <el-button :icon="Refresh" @click="loadTasks">刷新</el-button>
          </div>
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
        <el-table-column prop="path_name" label="名称" width="120" show-overflow-tooltip />
        <el-table-column prop="path" label="路径" min-width="200" show-overflow-tooltip />
        <el-table-column prop="scan_type" label="扫描类型" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.scan_type === 'full'" type="primary">全量</el-tag>
            <el-tag v-else-if="row.scan_type === 'incremental'" type="success">增量</el-tag>
            <el-tag v-else type="info">{{ row.scan_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="recursive" label="递归" width="80">
          <template #default="{ row }">
            <el-tag :type="row.recursive ? 'success' : 'info'">
              {{ row.recursive ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="monitoring_enabled" label="监控" width="80">
          <template #default="{ row }">
            <el-tag :type="row.monitoring_enabled ? 'success' : 'info'">
              {{ row.monitoring_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_scans" label="扫描次数" width="100" />
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

    <!-- 扫描路径配置对话框 -->
    <el-dialog v-model="pathDialogVisible" title="扫描路径配置" width="700px">
      <el-form :model="pathForm" label-width="120px">
        <el-form-item label="路径名称" required>
          <el-input 
            v-model="pathForm.pathName" 
            placeholder="输入路径名称（1-100字符）"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="扫描路径" required>
          <el-input 
            v-model="pathForm.path" 
            placeholder="输入或选择路径（最大260字符）"
            maxlength="260"
            show-word-limit
          >
            <template #append>
              <el-button :icon="Folder" @click="handleBrowsePath">浏览</el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <template #label>
            <span>扫描类型</span>
            <el-tooltip content="全量扫描：扫描所有文件；增量扫描：只扫描新增或修改的文件" placement="top">
              <el-icon class="ml-2"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-radio-group v-model="pathForm.scanType">
            <el-radio label="full">全量</el-radio>
            <el-radio label="incremental">增量</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <template #label>
            <span>递归扫描</span>
            <el-tooltip content="是否递归扫描子目录" placement="top">
              <el-icon class="ml-2"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-switch v-model="pathForm.recursive" />
        </el-form-item>
        <el-form-item>
          <template #label>
            <span>启用监控</span>
            <el-tooltip content="是否启用文件系统实时监控" placement="top">
              <el-icon class="ml-2"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-switch v-model="pathForm.monitoringEnabled" />
        </el-form-item>
        <el-form-item>
          <template #label>
            <span>监控防抖(秒)</span>
            <el-tooltip content="文件变化后等待多少秒再触发扫描" placement="top">
              <el-icon class="ml-2"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input-number v-model="pathForm.monitoringDebounce" :min="1" :max="60" />
        </el-form-item>
        <el-form-item>
          <template #label>
            <span>忽略模式</span>
            <el-tooltip content="选择预设的忽略模式或自定义忽略规则" placement="top">
              <el-icon class="ml-2"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-select v-model="pathForm.ignoreMode" placeholder="选择忽略模式" style="width: 100%">
            <el-option label="不忽略任何文件" value="none" />
            <el-option label="忽略临时文件" value="temp" />
            <el-option label="忽略系统文件" value="system" />
            <el-option label="忽略临时和系统文件" value="both" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="pathForm.ignoreMode === 'custom'">
          <template #label>
            <span>自定义忽略规则</span>
            <el-tooltip content="每行一个文件名模式，匹配的文件将被忽略" placement="top">
              <el-icon class="ml-2"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input 
            v-model="pathForm.ignorePatterns" 
            type="textarea" 
            :rows="3" 
            placeholder="例如：*.tmp&#10;*.part&#10;thumbs.db"
          />
        </el-form-item>
        <el-form-item>
          <template #label>
            <span>自动扫描间隔</span>
            <el-tooltip content="自动扫描的时间间隔（分钟），0表示不自动扫描" placement="top">
              <el-icon class="ml-2"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input-number 
            v-model="pathForm.scanInterval" 
            :min="0" 
            :max="1440"
            :step="5"
          />
          <span style="margin-left: 8px; color: #999;">分钟（0表示不自动扫描）</span>
        </el-form-item>
        <el-form-item>
          <template #label>
            <span>启用路径</span>
            <el-tooltip content="是否启用该扫描路径" placement="top">
              <el-icon class="ml-2"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-switch v-model="pathForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pathDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSavePath">确定</el-button>
      </template>
    </el-dialog>

    <!-- 扫描选择对话框 -->
    <el-dialog v-model="scanDialogVisible" title="执行扫描" width="700px">
      <el-form :model="scanForm" label-width="120px">
        <el-form-item label="扫描方式">
          <el-radio-group v-model="scanForm.scanType">
            <el-radio label="path">使用已配置路径</el-radio>
            <el-radio label="custom">自定义路径</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="scanForm.scanType === 'path'" label="选择路径">
          <el-select v-model="scanForm.selectedPathId" placeholder="请选择扫描路径">
            <el-option
              v-for="path in pathList.filter(p => p.enabled)"
              :key="path.id"
              :label="`${path.path_name || path.path} (${path.scan_type === 'full' ? '全量' : '增量'})`"
              :value="path.id"
            >
              <template #default>
                <div>
                  <div>{{ path.path_name || path.path }}</div>
                  <div style="font-size: 12px; color: #999;">
                    <el-tag size="small" :type="path.scan_type === 'full' ? 'primary' : 'success'">
                      {{ path.scan_type === 'full' ? '全量' : '增量' }}
                    </el-tag>
                    <el-tag size="small" :type="path.monitoring_enabled ? 'success' : 'info'">
                      {{ path.monitoring_enabled ? '监控' : '不监控' }}
                    </el-tag>
                  </div>
                </div>
              </template>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item v-if="scanForm.scanType === 'custom'" label="扫描路径">
          <el-input v-model="scanForm.customPath" placeholder="输入或选择路径">
            <template #append>
              <el-button :icon="Folder" @click="handleBrowseCustomPath">浏览</el-button>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item v-if="scanForm.scanType === 'custom'" label="扫描类型">
          <el-radio-group v-model="scanForm.customScanType">
            <el-radio label="full">全量</el-radio>
            <el-radio label="incremental">增量</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="scanForm.scanType === 'custom'" label="递归扫描">
          <el-switch v-model="scanForm.customRecursive" />
        </el-form-item>

        <el-form-item v-if="scanForm.scanType === 'custom'" label="文件跳过方式">
          <el-radio-group v-model="scanForm.skipMode">
            <el-radio label="keyword">仅跳过关键词库文件</el-radio>
            <el-radio label="record">跳过关键词库和已扫描文件</el-radio>
            <el-radio label="none">不跳过任何文件</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="scanForm.scanType === 'custom' && scanForm.skipMode !== 'none'" label="跳过说明">
          <div style="font-size: 12px; color: #666; line-height: 1.6;">
            <div v-if="scanForm.skipMode === 'keyword'">
              <el-icon><QuestionFilled /></el-icon>
              仅跳过关键词库文件（如：keywords.txt、rules_xxx.txt等）
            </div>
            <div v-if="scanForm.skipMode === 'record'">
              <el-icon><QuestionFilled /></el-icon>
              跳过关键词库文件和数据库中已存在的文件（基于文件路径判断）
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scanDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="executeScan">执行扫描</el-button>
      </template>
    </el-dialog>

    <!-- 目录浏览对话框 -->
    <el-dialog v-model="browseDialogVisible" title="选择目录" width="800px">
      <div class="directory-browser">
        <!-- 路径导航栏 -->
        <div class="path-navigation">
          <el-button 
            v-for="(segment, index) in pathSegments" 
            :key="index"
            link 
            @click="navigateToPath(getPathUpTo(index))"
          >
            {{ segment }}
          </el-button>
        </div>

        <!-- 目录内容列表 -->
        <el-table
          :data="directoryItems"
          height="400"
          @row-dblclick="handleRowDblClick"
          style="width: 100%"
        >
          <el-table-column prop="name" label="名称" min-width="200">
            <template #default="{ row }">
              <el-icon v-if="row.is_dir" class="folder-icon"><Folder /></el-icon>
              <span>{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="modified_time" label="修改时间" width="180">
            <template #default="{ row }">
              {{ row.modified_time || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="size" label="大小" width="120">
            <template #default="{ row }">
              {{ row.is_dir ? '-' : formatFileSize(row.size) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button v-if="row.is_dir" link type="primary" @click="enterDirectory(row)">
                进入
              </el-button>
              <el-button v-else link type="primary" @click="selectPath(row.path)">
                选择
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 操作按钮 -->
        <div class="browser-actions">
          <el-button @click="goUp">上级目录</el-button>
          <el-button @click="refreshDirectory">刷新</el-button>
          <el-button @click="selectCurrentPath">选择当前目录</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onUnmounted, computed } from 'vue'
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
  pathName: '',
  path: '',
  scanType: 'incremental',
  recursive: true,
  monitoringEnabled: true,
  monitoringDebounce:5,
  scanInterval: 0, // 自动扫描间隔（分钟），0表示不自动扫描
  ignoreMode: 'none', // none, temp, system, both, custom
  ignorePatterns: '',
  enabled: true
})

// 路径验证函数
const validatePath = (path) => {
  if (!path || path.trim() === '') {
    return '路径不能为空'
  }

  // 检查路径长度（Windows最大路径长度为260字符）
  if (path.length > 260) {
    return '路径长度不能超过260个字符'
  }

  // 检查非法字符（排除驱动器盘符后的冒号）
  const illegalChars = /[<>:"|?*]/
  // 检查路径中是否存在非法字符，但排除驱动器盘符后的冒号（如 F:）
  const pathWithoutDrive = path.replace(/^[A-Za-z]:/, '')
  if (illegalChars.test(pathWithoutDrive)) {
    return '路径包含非法字符：< > : " | ? *'
  }

  // 检查是否包含保留的设备名称
  const reservedNames = /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/i
  const parts = path.split(/[\/]/)
  for (const part of parts) {
    if (reservedNames.test(part)) {
      return `路径包含保留的设备名称: ${part}`
    }
  }

  return null
}

// 路径名称验证函数
const validatePathName = (name) => {
  if (!name || name.trim() === '') {
    return '路径名称不能为空'
  }

  if (name.length > 100) {
    return '路径名称不能超过100个字符'
  }

  // 检查非法字符
  const illegalChars = /[<>:"|?*\/]/i
  if (illegalChars.test(name)) {
    return '路径名称包含非法字符：< > : " | ? * / \\'
  }

  return null
}

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
    // 检查是否有配置的扫描路径
    if (pathList.value.length === 0) {
      // 没有配置任何扫描路径，自动打开配置窗口
      ElMessage.info('尚未配置扫描路径，请先添加扫描路径')
      handleAddPath()
      return
    }

    // 检查是否有可用的扫描路径
    const enabledPaths = pathList.value.filter(p => p.enabled)

    if (enabledPaths.length === 0) {
      // 有配置的路径但没有启用的，提示用户
      ElMessage.warning('没有启用的扫描路径，请先启用扫描路径或添加新路径')
      handleAddPath()
      return
    }

    // 显示扫描选择对话框
    await showScanDialog()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('启动扫描失败:', error)
      ElMessage.error('启动扫描失败')
    }
  }
}

// 显示扫描选择对话框
const scanDialogVisible = ref(false)
const scanForm = reactive({
  scanType: 'path', // path: 使用已配置路径, custom: 自定义路径
  selectedPathId: null,
  customPath: '',
  customRecursive: true,
  customScanType: 'incremental',
  skipMode: 'keyword' // keyword: 仅跳过关键词库, record: 跳过关键词库和已扫描, none: 不跳过任何文件
})

// 目录浏览相关
const browseDialogVisible = ref(false)
const currentBrowsePath = ref('')
const directoryItems = ref([])
const browseTarget = ref('') // 'path' 或 'custom'，标识是为主路径还是自定义路径浏览

const showScanDialog = async () => {
  scanDialogVisible.value = true
  // 默认选择第一个启用的路径
  const enabledPath = pathList.value.find(p => p.enabled)
  if (enabledPath) {
    scanForm.selectedPathId = enabledPath.id
    scanForm.scanType = 'path'
  }
}

// 执行扫描
const executeScan = async () => {
  try {
    let scanData = {}

    if (scanForm.scanType === 'path' && scanForm.selectedPathId) {
      // 使用已配置的扫描路径
      const selectedPath = pathList.value.find(p => p.id === scanForm.selectedPathId)
      if (!selectedPath) {
        ElMessage.warning('请选择扫描路径')
        return
      }

      scanData = {
        path_id: selectedPath.id,
        // 使用路径的独立配置，不覆盖
        // scan_type: 'incremental', // 使用路径配置的扫描类型
        // recursive: selectedPath.recursive // 使用路径配置的递归设置
      }

      await ElMessageBox.confirm(
        `确定要扫描路径 "${selectedPath.path_name || selectedPath.path}" 吗？\n\n` +
        `扫描类型: ${selectedPath.scan_type === 'full' ? '全量' : '增量'}\n` +
        `递归扫描: ${selectedPath.recursive ? '是' : '否'}\n` +
        `监控: ${selectedPath.monitoring_enabled ? '启用' : '禁用'}`,
        '扫描配置确认',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'info'
        }
      )
    } else if (scanForm.scanType === 'custom' && scanForm.customPath) {
      // 使用自定义路径
      scanData = {
        path: scanForm.customPath,
        recursive: scanForm.customRecursive,
        scan_type: scanForm.customScanType
      }

      await ElMessageBox.confirm(
        `确定要扫描自定义路径 "${scanForm.customPath}" 吗？\n\n` +
        `扫描类型: ${scanForm.customScanType === 'full' ? '全量' : '增量'}\n` +
        `递归扫描: ${scanForm.customRecursive ? '是' : '否'}`,
        '自定义扫描确认',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'info'
        }
      )
    } else {
      ElMessage.warning('请选择扫描路径或输入自定义路径')
      return
    }

    // 调用API创建扫描任务
    const { createScanTask } = await import('@/api/scan')
    const result = await createScanTask(scanData)

    // 连接WebSocket监听进度
    connectScanProgress(result.task_id)

    ElMessage.success('扫描任务已启动')
    loadTasks()

    // 关闭对话框
    scanDialogVisible.value = false
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

// 批量停止任务
const handleBatchStop = async () => {
  if (selectedTasks.value.length === 0) {
    ElMessage.warning('请先选择要停止的任务')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要停止选中的 ${selectedTasks.value.length} 个扫描任务吗？`,
      '批量停止确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const { batchStopTasks } = await import('@/api/scan')
    const result = await batchStopTasks(selectedTasks.value.map(t => t.id))

    ElMessage.success(
      `批量停止完成：成功 ${result.success} 个，失败 ${result.failed} 个`
    )
    
    // 清空选择
    selectedTasks.value = []
    loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量停止任务失败:', error)
      ElMessage.error('批量停止任务失败')
    }
  }
}

// 批量删除任务
const handleBatchDelete = async () => {
  if (selectedTasks.value.length === 0) {
    ElMessage.warning('请先选择要删除的任务')
    return
  }

  // 检查是否有正在运行的任务
  const runningTasks = selectedTasks.value.filter(t => t.status === 'running')
  if (runningTasks.length > 0) {
    ElMessage.warning('选中的任务中有正在运行的任务，无法删除')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedTasks.value.length} 个扫描任务吗？此操作不可恢复！`,
      '批量删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const { batchDeleteTasks } = await import('@/api/scan')
    const result = await batchDeleteTasks(selectedTasks.value.map(t => t.id))

    ElMessage.success(
      `批量删除完成：成功 ${result.success} 个，失败 ${result.failed} 个`
    )
    
    // 清空选择
    selectedTasks.value = []
    loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除任务失败:', error)
      ElMessage.error('批量删除任务失败')
    }
  }
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
      // 提供更详细的错误信息
      const errorMsg = error.response?.data?.detail || error.message || '重试扫描失败'
      ElMessage.error(errorMsg)
    }
  }
}

// 添加路径
const handleAddPath = () => {
  editingPathId.value = null
  Object.assign(pathForm, {
    pathName: '',
    path: '',
    scanType: 'incremental',
    recursive: true,
    monitoringEnabled: true,
    monitoringDebounce: 5,
    ignorePatterns: '',
    enabled: true
  })
  pathDialogVisible.value = true
}

// 编辑路径
const handleEditPath = (row) => {
  editingPathId.value = row.id
  Object.assign(pathForm, {
    pathName: row.path_name || '',
    path: row.path,
    scanType: row.scan_type || 'incremental',
    recursive: row.recursive,
    monitoringEnabled: row.monitoring_enabled,
    monitoringDebounce: row.monitoring_debounce || 5,
    ignorePatterns: Array.isArray(row.ignore_patterns) ? row.ignore_patterns.join('\n') : '',
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
  browseTarget.value = 'path'
  currentBrowsePath.value = ''
  browseDialogVisible.value = true
  loadDirectory('')
}

// 浏览自定义路径
const handleBrowseCustomPath = () => {
  browseTarget.value = 'custom'
  currentBrowsePath.value = ''
  browseDialogVisible.value = true
  loadDirectory('')
}

// 加载目录内容
const loadDirectory = async (path) => {
  try {
    const { browseDirectory } = await import('@/api/scan')
    const items = await browseDirectory(path)
    directoryItems.value = items
    currentBrowsePath.value = path
  } catch (error) {
    console.error('加载目录失败:', error)
    ElMessage.error(error.response?.data?.detail || '加载目录失败')
  }
}

// 进入目录
const enterDirectory = (item) => {
  if (item.is_dir) {
    loadDirectory(item.path)
  }
}

// 双击行处理
const handleRowDblClick = (row) => {
  if (row.is_dir) {
    enterDirectory(row)
  } else {
    selectPath(row.path)
  }
}

// 返回上级目录
const goUp = () => {
  if (!currentBrowsePath.value) return

  const path = currentBrowsePath.value
  const separator = path.includes('\\') ? '\\' : '/'
  const parts = path.split(separator)

  if (parts.length > 1) {
    parts.pop()
    const parentPath = parts.join(separator)
    loadDirectory(parentPath)
  } else {
    loadDirectory('')
  }
}

// 刷新目录
const refreshDirectory = () => {
  loadDirectory(currentBrowsePath.value)
}

// 选择路径
const selectPath = (path) => {
  if (browseTarget.value === 'path') {
    pathForm.path = path
  } else if (browseTarget.value === 'custom') {
    scanForm.customPath = path
  }
  browseDialogVisible.value = false
}

// 选择当前目录
const selectCurrentPath = () => {
  if (currentBrowsePath.value) {
    selectPath(currentBrowsePath.value)
  } else {
    ElMessage.warning('请先选择一个目录')
  }
}

// 获取路径分段
const pathSegments = computed(() => {
  if (!currentBrowsePath.value) return []

  const path = currentBrowsePath.value
  const separator = path.includes('\\') ? '\\' : '/'
  const parts = path.split(separator)

  // 添加根目录
  const segments = [parts[0]]

  // 添加其他分段
  for (let i = 1; i < parts.length; i++) {
    segments.push(parts[i])
  }

  return segments
})

// 导航到指定路径
const navigateToPath = (path) => {
  loadDirectory(path)
}

// 获取到指定索引的路径
const getPathUpTo = (index) => {
  const path = currentBrowsePath.value
  const separator = path.includes('\\') ? '\\' : '/'
  const parts = path.split(separator)
  return parts.slice(0, index + 1).join(separator)
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'

  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

// 保存路径
const handleSavePath = async () => {
  // 验证路径名称
  const nameError = validatePathName(pathForm.pathName)
  if (nameError) {
    ElMessage.error(nameError)
    return
  }

  // 验证路径
  const pathError = validatePath(pathForm.path)
  if (pathError) {
    ElMessage.error(pathError)
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

  .directory-browser {
    .path-navigation {
      margin-bottom: 16px;
      padding: 12px;
      background: #f5f7fa;
      border-radius: 4px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;

      .el-button {
        padding: 4px 8px;
        font-size: 14px;
      }
    }

    .folder-icon {
      margin-right: 8px;
      color: #409eff;
    }

    .browser-actions {
      margin-top: 16px;
      display: flex;
      gap: 12px;
      justify-content: flex-end;
    }
  }
}
</style>


