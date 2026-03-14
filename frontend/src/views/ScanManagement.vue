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

    <!-- 标签页切换 -->
    <el-tabs v-model="activeTab" class="scan-tabs">
      <!-- 已扫描文件标签页 -->
      <el-tab-pane label="已扫描文件" name="fileTasks">
        <el-card class="file-task-card">
          <template #header>
            <div class="card-header">
              <span class="title">已扫描文件</span>
              <div class="header-actions">
                <el-select v-model="fileTaskStatusFilter" placeholder="状态筛选" style="width: 120px; margin-right: 12px;">
                  <el-option label="全部" value="" />
                  <el-option label="扫描中" value="scanning" />
                  <el-option label="已完成" value="scanned" />
                  <el-option label="失败" value="failed" />
                </el-select>
                <el-button 
                  type="primary" 
                  :disabled="selectedFileTasks.length === 0"
                  @click="handleBatchRescanFiles"
                >
                  批量重新扫描 ({{ selectedFileTasks.length }})
                </el-button>
                <el-button 
                  type="warning" 
                  :disabled="selectedFileTasks.length === 0"
                  @click="handleBatchStopFileScans"
                >
                  批量停止 ({{ selectedFileTasks.length }})
                </el-button>
                <el-button 
                  type="danger" 
                  :disabled="selectedFileTasks.length === 0"
                  @click="handleBatchDeleteFileScanResults"
                >
                  批量删除 ({{ selectedFileTasks.length }})
                </el-button>
                <el-button :icon="Refresh" @click="loadFileTasks">刷新</el-button>
              </div>
            </div>
          </template>

          <el-table
            v-loading="loading"
            :data="fileTaskList"
            stripe
            style="width: 100%"
            @selection-change="handleFileTaskSelectionChange"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="id" label="任务ID" width="80" />
            <el-table-column prop="file_name" label="文件名" min-width="150" show-overflow-tooltip />
            <el-table-column prop="target_path" label="路径" min-width="150" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.status === 'pending'" type="info">等待中</el-tag>
                <el-tag v-else-if="row.status === 'scanning'" type="warning">扫描中</el-tag>
                <el-tag v-else-if="row.status === 'scanned'" type="success">已完成</el-tag>
                <el-tag v-else-if="row.status === 'failed'" type="danger">失败</el-tag>
                <el-tag v-else type="info">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="进度" width="120">
              <template #default="{ row }">
                <el-progress
                  v-if="row.status === 'scanning'"
                  :percentage="row.scan_progress || 0"
                  :status="(row.scan_progress || 0) >= 100 ? 'success' : ''"
                />
                <span v-else-if="row.status === 'scanned'">已完成</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="scan_started_at" label="开始时间" width="160" />
            <el-table-column prop="scan_completed_at" label="完成时间" width="160" />
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="handleViewFileTask(row)">查看结果</el-button>
                <el-button v-if="row.status === 'scanned'" link type="success" @click="handleRescanFile(row)">重新扫描</el-button>
                <el-button v-if="row.status === 'scanning'" link type="danger" @click="handleStopFileScan(row)">停止</el-button>
                <el-button v-if="row.status === 'scanned'" link type="danger" @click="handleDeleteFileScanResult(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

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
        <el-table-column prop="skip_strategy" label="跳过策略" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.skip_strategy === 'keyword'" type="warning">关键词</el-tag>
            <el-tag v-else-if="row.skip_strategy === 'record'" type="danger">关键词+记录</el-tag>
            <el-tag v-else type="info">不跳过</el-tag>
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
      <el-form :model="pathForm" label-width="150px">
        <el-form-item label="路径名称" required>
          <el-input 
            v-model="pathForm.path_name" 
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
        <el-form-item label="扫描类型" required>
          <el-radio-group v-model="pathForm.scan_type">
            <el-radio label="full">全量</el-radio>
            <el-radio label="incremental">增量</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="递归扫描">
          <el-switch v-model="pathForm.recursive" />
        </el-form-item>
        <el-form-item label="文件跳过策略">
          <el-radio-group v-model="pathForm.skip_strategy">
            <el-radio label="keyword">仅跳过关键词库文件</el-radio>
            <el-radio label="record">跳过关键词库和已扫描文件</el-radio>
            <el-radio label="none">不跳过任何文件</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="是否扫描子目录">
          <el-switch v-model="pathForm.scan_subdirectories" />
        </el-form-item>
        <el-form-item label="监控防抖时间(秒)">
          <el-input-number v-model="pathForm.scan_debounce_time" :min="30" :max="300" />
        </el-form-item>
        <el-form-item label="启用文件监控">
          <el-switch v-model="pathForm.monitoring_enabled" />
        </el-form-item>
        <el-form-item label="监控模式">
          <el-select v-model="pathForm.monitoring_mode" placeholder="选择监控模式" style="width: 100%">
            <el-option label="Watchdog" value="watchdog" />
            <el-option label="Polling" value="polling" />
          </el-select>
        </el-form-item>
        <el-form-item label="监控防抖(秒)">
          <el-input-number v-model="pathForm.monitoring_debounce" :min="1" :max="60" />
        </el-form-item>
        <el-form-item label="自动识别">
          <el-switch v-model="pathForm.auto_recognize" />
        </el-form-item>
        <el-form-item label="自动整理">
          <el-switch v-model="pathForm.auto_organize" />
        </el-form-item>
        <el-form-item label="启用路径">
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
          <el-radio-group v-model="scanForm.scan_type">
            <el-radio label="path">使用已配置路径</el-radio>
            <el-radio label="custom">自定义路径</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="scanForm.scan_type === 'path'" label="选择路径">
          <el-select v-model="scanForm.selected_path_id" placeholder="请选择扫描路径" style="width: 100%">
            <el-option
              v-for="path in pathList.filter(p => p.enabled)"
              :key="path.id"
              :label="`${path.path_name || path.path} (${path.scan_type === 'full' ? '全量' : '增量'})`"
              :value="path.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item v-if="scanForm.scan_type === 'custom'" label="扫描路径">
          <el-input v-model="scanForm.path" placeholder="输入或选择路径">
            <template #append>
              <el-button :icon="Folder" @click="handleBrowseCustomPath">浏览</el-button>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item v-if="scanForm.scan_type === 'custom'" label="使用默认策略">
          <el-switch v-model="scanForm.use_default_strategy" />
        </el-form-item>

        <template v-if="scanForm.scan_type === 'custom' && !scanForm.use_default_strategy">
          <el-form-item label="扫描类型">
            <el-radio-group v-model="scanForm.scan_type_value">
              <el-radio label="full">全量</el-radio>
              <el-radio label="incremental">增量</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="递归扫描">
            <el-switch v-model="scanForm.recursive" />
          </el-form-item>

          <el-form-item label="文件跳过策略">
            <el-radio-group v-model="scanForm.skip_strategy">
              <el-radio label="keyword">仅跳过关键词库文件</el-radio>
              <el-radio label="record">跳过关键词库和已扫描文件</el-radio>
              <el-radio label="none">不跳过任何文件</el-radio>
            </el-radio-group>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="scanDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="executeScan">执行扫描</el-button>
      </template>
    </el-dialog>

    <!-- 扫描配置对话框 -->
    <el-dialog v-model="configDialogVisible" title="默认扫描策略配置" width="700px">
      <el-form :model="configForm" label-width="200px">
        <el-form-item label="默认扫描类型">
          <el-radio-group v-model="configForm.default_scan_type">
            <el-radio label="full">全量扫描</el-radio>
            <el-radio label="incremental">增量扫描</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="默认递归扫描">
          <el-switch v-model="configForm.default_recursive" />
        </el-form-item>
        
        <el-form-item label="默认文件跳过策略">
          <el-radio-group v-model="configForm.default_skip_strategy">
            <el-radio label="keyword">仅跳过关键词库文件</el-radio>
            <el-radio label="record">跳过关键词库和已扫描文件</el-radio>
            <el-radio label="none">不跳过任何文件</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="默认扫描子目录">
          <el-switch v-model="configForm.scan_subdirectories" />
        </el-form-item>
        
        <el-form-item label="默认监控防抖时间(秒)">
          <el-input-number 
            v-model="configForm.default_monitor_debounce_time" 
            :min="30" 
            :max="300"
            style="width: 200px;"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button @click="resetConfig">恢复默认</el-button>
        <el-button type="primary" @click="saveConfig">保存配置</el-button>
      </template>
    </el-dialog>

    <!-- 文件扫描结果详情对话框 -->
    <el-dialog v-model="scanResultDialogVisible" title="文件扫描结果详情" width="800px">
      <div v-if="scanResultDetail" class="scan-result-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="文件名">{{ scanResultDetail.file_name }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">{{ formatFileSize(scanResultDetail.file_size) }}</el-descriptions-item>
          <el-descriptions-item label="文件类型">{{ scanResultDetail.file_type }}</el-descriptions-item>
          <el-descriptions-item label="文件路径">{{ scanResultDetail.file_path }}</el-descriptions-item>
          <el-descriptions-item label="扫描开始时间">{{ scanResultDetail.scan_started_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="扫描完成时间">{{ scanResultDetail.scan_completed_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="文件编码格式">{{ scanResultDetail.file_encoding_format || '-' }}</el-descriptions-item>
          <el-descriptions-item label="文件哈希值">
            <el-text truncated :title="scanResultDetail.file_hash">{{ scanResultDetail.file_hash || '-' }}</el-text>
          </el-descriptions-item>
          <el-descriptions-item label="视频轨道数">{{ scanResultDetail.video_tracks }}</el-descriptions-item>
          <el-descriptions-item label="音频轨道数">{{ scanResultDetail.audio_tracks }}</el-descriptions-item>
          <el-descriptions-item label="字幕轨道数">{{ scanResultDetail.subtitle_tracks }}</el-descriptions-item>
          <el-descriptions-item label="扫描任务ID">{{ scanResultDetail.scan_task_id }}</el-descriptions-item>
          <el-descriptions-item label="视频编码">{{ scanResultDetail.video_codec || '-' }}</el-descriptions-item>
          <el-descriptions-item label="音频编码">{{ scanResultDetail.audio_codec || '-' }}</el-descriptions-item>
          <el-descriptions-item label="外挂字幕" :span="2">
            <div v-if="scanResultDetail.has_external_subtitle">
              <el-tag type="success">有外挂字幕</el-tag>
              <el-text style="margin-left: 8px;">{{ scanResultDetail.external_subtitle_name || '-' }}</el-text>
            </div>
            <el-tag v-else type="info">无外挂字幕</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="扫描结果" :span="2">
            <el-text>{{ scanResultDetail.scan_result || '-' }}</el-text>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="scanResultDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 目录浏览对话框 -->
    <el-dialog v-model="browseDialogVisible" title="选择目录" width="800px">
      <div class="directory-browser">
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
import { VideoCamera, FolderOpened, Setting, Refresh, Plus, Folder, QuestionFilled } from '@element-plus/icons-vue'
import {
  createScanTask,
  getScanPaths,
  addScanPath,
  updateScanPath,
  deleteScanPath,
  browseDirectory,
  getDefaultScanConfig,
  updateDefaultScanConfig,
  resetDefaultScanConfig,
  getFileTasks,
  getScanResult,
  batchRescanMediaFiles,
  batchStopMediaFileScans,
  batchDeleteMediaFileScanResults
} from '@/api/scan'

// 加载状态
const loading = ref(false)

// 活动标签页
const activeTab = ref('fileTasks')

// 文件任务列表
const fileTaskList = ref([])

// 文件任务状态筛选
const fileTaskStatusFilter = ref('')

// 选中的文件任务
const selectedFileTasks = ref([])

// 扫描路径列表
const pathList = ref([])

// 扫描结果详情
const scanResultDetail = ref(null)
const scanResultDialogVisible = ref(false)

// 扫描配置对话框
const configDialogVisible = ref(false)
const configForm = reactive({
  default_scan_type: 'incremental',
  default_recursive: true,
  default_skip_strategy: 'keyword',
  scan_subdirectories: true,
  default_monitor_debounce_time: 30
})

// 路径对话框
const pathDialogVisible = ref(false)
const editingPathId = ref(null)
const pathForm = reactive({
  path_name: '',
  path: '',
  scan_type: 'incremental',
  recursive: true,
  skip_strategy: 'keyword',
  scan_subdirectories: true,
  scan_debounce_time: 30,
  monitoring_enabled: false,
  monitoring_mode: 'watchdog',
  monitoring_debounce: 5,
  auto_recognize: false,
  auto_organize: false,
  enabled: true
})

// 扫描选择对话框
const scanDialogVisible = ref(false)
const scanForm = reactive({
  scan_type: 'path', // path: 使用已配置路径, custom: 自定义路径
  selected_path_id: null,
  path: '',
  use_default_strategy: true,
  scan_type_value: 'incremental',
  recursive: true,
  skip_strategy: 'keyword'
})

// 目录浏览相关
const browseDialogVisible = ref(false)
const currentBrowsePath = ref('')
const directoryItems = ref([])
const browseTarget = ref('') // 'path' 或 'custom'

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

// 计算进度
const calculateProgress = (task) => {
  if (!task.total_files || task.total_files === 0) return 0
  const processed = (task.new_files || 0) + (task.updated_files || 0) + (task.skipped_files || 0) + (task.failed_files || 0)
  return Math.round((processed / task.total_files) * 100)
}

// 加载文件任务
const loadFileTasks = async () => {
  loading.value = true
  try {
    const params = { limit: 50, offset: 0 }
    if (fileTaskStatusFilter.value) {
      params.status = fileTaskStatusFilter.value
    }
    const tasks = await getFileTasks(params)
    fileTaskList.value = tasks || []
  } catch (error) {
    console.error('加载文件任务失败:', error)
    ElMessage.error('加载文件任务失败')
  } finally {
    loading.value = false
  }
}

// 加载路径列表
const loadPaths = async () => {
  try {
    const paths = await getScanPaths()
    pathList.value = paths || []
  } catch (error) {
    console.error('加载扫描路径失败:', error)
  }
}

// 文件任务选择变化
const handleFileTaskSelectionChange = (selection) => {
  selectedFileTasks.value = selection
}

// 立即扫描
const handleScan = async () => {
  if (pathList.value.length === 0) {
    ElMessage.info('尚未配置扫描路径，请先添加扫描路径')
    handleAddPath()
    return
  }

  const enabledPaths = pathList.value.filter(p => p.enabled)
  if (enabledPaths.length === 0) {
    ElMessage.warning('没有启用的扫描路径，请先启用扫描路径或添加新路径')
    handleAddPath()
    return
  }

  scanDialogVisible.value = true
  const enabledPath = pathList.value.find(p => p.enabled)
  if (enabledPath) {
    scanForm.selected_path_id = enabledPath.id
    scanForm.scan_type = 'path'
  }
}

// 执行扫描
const executeScan = async () => {
  try {
    let scanData = {}

    if (scanForm.scan_type === 'path' && scanForm.selected_path_id) {
      const selectedPath = pathList.value.find(p => p.id === scanForm.selected_path_id)
      if (!selectedPath) {
        ElMessage.warning('请选择扫描路径')
        return
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

      // 使用路径配置的扫描策略
      scanData = {
        path: selectedPath.path,
        use_default_strategy: true
      }
    } else if (scanForm.scan_type === 'custom' && scanForm.path) {
      await ElMessageBox.confirm(
        `确定要扫描自定义路径 "${scanForm.path}" 吗？\n\n` +
        `扫描类型: ${scanForm.scan_type_value === 'full' ? '全量' : '增量'}\n` +
        `递归扫描: ${scanForm.scan_type_value === 'full' ? '是' : '否'}`,
        '自定义扫描确认',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'info'
        }
      )

      scanData = {
        path: scanForm.path,
        use_default_strategy: scanForm.use_default_strategy,
        scan_type: scanForm.scan_type_value,
        recursive: scanForm.recursive,
        skip_strategy: scanForm.skip_strategy
      }
    } else {
      ElMessage.warning('请选择扫描路径或输入自定义路径')
      return
    }

    const result = await createScanTask(scanData)
    ElMessage.success('扫描任务已启动')
    loadFileTasks()
    scanDialogVisible.value = false
  } catch (error) {
    if (error !== 'cancel') {
      console.error('启动扫描失败:', error)
      ElMessage.error('启动扫描失败')
    }
  }
}

// 查看文件任务详情
const handleViewFileTask = async (row) => {
  try {
    const detail = await getScanResult(row.id)
    scanResultDetail.value = detail
    scanResultDialogVisible.value = true
  } catch (error) {
    console.error('获取文件扫描结果失败:', error)
    ElMessage.error('获取文件扫描结果失败')
  }
}

// 重新扫描文件
const handleRescanFile = async (row) => {
  try {
    await ElMessageBox.confirm('确定要重新扫描这个文件吗？\n系统将自动删除该文件的所有扫描记录并重新建立扫描任务。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await rescanFile(row.id)
    ElMessage.success('重新扫描任务已创建')
    loadFileTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重新扫描失败:', error)
      ElMessage.error('重新扫描失败')
    }
  }
}

// 停止文件扫描
const handleStopFileScan = async (row) => {
  try {
    await ElMessageBox.confirm('确定要停止这个文件的扫描吗？\n停止后将自动删除该文件的所有扫描记录。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await stopFileScan(row.id)
    ElMessage.success('文件扫描已停止')
    loadFileTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('停止文件扫描失败:', error)
      ElMessage.error('停止文件扫描失败')
    }
  }
}

// 删除文件扫描结果
const handleDeleteFileScanResult = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这个文件的扫描结果吗？此操作不可恢复！', '警告', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteScanResult(row.id)
    ElMessage.success('扫描结果已删除')
    loadFileTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除扫描结果失败:', error)
      ElMessage.error('删除扫描结果失败')
    }
  }
}

// 批量重新扫描文件
const handleBatchRescanFiles = async () => {
  if (selectedFileTasks.value.length === 0) {
    ElMessage.warning('请先选择要重新扫描的文件')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要重新扫描选中的 ${selectedFileTasks.value.length} 个文件吗？\n系统将自动删除这些文件的所有扫描记录并重新建立扫描任务。`,
      '批量重新扫描确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 提取media_file_id
    const mediaFileIds = selectedFileTasks.value
      .map(t => t.media_file_id)
      .filter(id => id !== undefined && id !== null && !isNaN(id))
      .map(id => parseInt(id, 10))

    console.log('选中的文件任务:', selectedFileTasks.value)
    console.log('提取的media_file_ids:', mediaFileIds)
    
    if (mediaFileIds.length === 0) {
      ElMessage.error('没有有效的文件ID，无法执行批量重新扫描')
      return
    }

    console.log('发送批量重新扫描请求...')
    const result = await batchRescanMediaFiles(mediaFileIds)
    console.log('批量重新扫描结果:', result)
    
    ElMessage.success(`批量重新扫描完成：成功 ${result.success} 个，失败 ${result.failed} 个`)
    selectedFileTasks.value = []
    loadFileTasks()
  } catch (error) {
    if (error !== 'cancel') {
    console.error('批量重新扫描失败:', error)
    console.error('错误响应:', error.response)
    console.error('错误数据:', error.response?.data)
    console.error('Detail内容:', error.response?.data?.detail)
    
    // 尝试解析详细错误信息
    let errorMsg = '批量重新扫描失败'
    if (error.response?.data) {
      if (error.response.data.detail) {
        // detail可能是数组或字符串
        if (Array.isArray(error.response.data.detail)) {
          // 如果是数组，提取第一条错误信息
          const firstError = error.response.data.detail[0]
          if (typeof firstError === 'string') {
            errorMsg += `: ${firstError}`
          } else if (firstError && firstError.msg) {
            errorMsg += `: ${firstError.msg}`
          } else {
            errorMsg += `: ${JSON.stringify(error.response.data.detail)}`
          }
        } else {
          errorMsg += `: ${error.response.data.detail}`
        }
      } else {
        errorMsg += `: ${JSON.stringify(error.response.data)}`
      }
    } else if (error.message) {
      errorMsg += `: ${error.message}`
    }
    
    ElMessage.error(errorMsg)
    }
  }
}

// 批量停止文件扫描
const handleBatchStopFileScans = async () => {
  if (selectedFileTasks.value.length === 0) {
    ElMessage.warning('请先选择要停止的文件')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要停止选中的 ${selectedFileTasks.value.length} 个文件的扫描吗？\n停止后将自动删除这些文件的所有扫描记录。`,
      '批量停止确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 提取media_file_id
    const mediaFileIds = selectedFileTasks.value
      .map(t => t.media_file_id)
      .filter(id => id !== undefined && id !== null && !isNaN(id))
      .map(id => parseInt(id, 10))

    if (mediaFileIds.length === 0) {
      ElMessage.error('没有有效的文件ID')
      return
    }

    const result = await batchStopMediaFileScans(mediaFileIds)
    ElMessage.success(`批量停止完成：成功 ${result.success} 个，失败 ${result.failed} 个`)
    selectedFileTasks.value = []
    loadFileTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量停止失败:', error)
      ElMessage.error('批量停止失败')
    }
  }
}

// 批量删除扫描结果
const handleBatchDeleteFileScanResults = async () => {
  if (selectedFileTasks.value.length === 0) {
    ElMessage.warning('请先选择要删除的文件')
    return
  }

  // 检查是否有未完成的文件
  const uncompletedTasks = selectedFileTasks.value.filter(t => t.status !== 'scanned')
  if (uncompletedTasks.length > 0) {
    ElMessage.warning('选中的文件中有未完成扫描的文件，无法删除')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedFileTasks.value.length} 个文件的扫描结果吗？此操作不可恢复！`,
      '批量删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 提取media_file_id
    const mediaFileIds = selectedFileTasks.value
      .map(t => t.media_file_id)
      .filter(id => id !== undefined && id !== null && !isNaN(id))
      .map(id => parseInt(id, 10))

    if (mediaFileIds.length === 0) {
      ElMessage.error('没有有效的文件ID')
      return
    }

    const result = await batchDeleteMediaFileScanResults(mediaFileIds)
    ElMessage.success(`批量删除完成：成功 ${result.success} 个，失败 ${result.failed} 个`)
    selectedFileTasks.value = []
    loadFileTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败')
    }
  }
}

// 扫描路径相关
const handleSelectPath = () => {
  pathDialogVisible.value = true
}

const handleAddPath = () => {
  editingPathId.value = null
  Object.assign(pathForm, {
    path_name: '',
    path: '',
    scan_type: 'incremental',
    recursive: true,
    skip_strategy: 'keyword',
    scan_subdirectories: true,
    scan_debounce_time: 30,
    monitoring_enabled: false,
    monitoring_mode: 'watchdog',
    monitoring_debounce: 5,
    auto_recognize: false,
    auto_organize: false,
    enabled: true
  })
  pathDialogVisible.value = true
}

const handleEditPath = (row) => {
  editingPathId.value = row.id
  Object.assign(pathForm, {
    path_name: row.path_name || '',
    path: row.path,
    scan_type: row.scan_type || 'incremental',
    recursive: row.recursive,
    skip_strategy: row.skip_strategy || 'keyword',
    scan_subdirectories: row.scan_subdirectories !== undefined ? row.scan_subdirectories : true,
    scan_debounce_time: row.scan_debounce_time || 30,
    monitoring_enabled: row.monitoring_enabled,
    monitoring_mode: row.monitoring_mode,
    monitoring_debounce: row.monitoring_debounce,
    auto_recognize: row.auto_recognize,
    auto_organize: row.auto_organize,
    enabled: row.enabled
  })
  pathDialogVisible.value = true
}

const handleDeletePath = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这个扫描路径吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteScanPath(row.id)
    ElMessage.success('删除成功')
    loadPaths()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除路径失败:', error)
      ElMessage.error('删除路径失败')
    }
  }
}

const handleSavePath = async () => {
  if (!pathForm.path_name || pathForm.path_name.trim() === '') {
    ElMessage.error('路径名称不能为空')
    return
  }

  if (pathForm.path_name.length > 100) {
    ElMessage.error('路径名称不能超过100个字符')
    return
  }

  if (!pathForm.path || pathForm.path.trim() === '') {
    ElMessage.error('路径不能为空')
    return
  }

  if (pathForm.path.length > 260) {
    ElMessage.error('路径长度不能超过260个字符')
    return
  }

  try {
    if (editingPathId.value) {
      await updateScanPath(editingPathId.value, pathForm)
      ElMessage.success('更新成功')
    } else {
      await addScanPath(pathForm)
      ElMessage.success('添加成功')
    }
    loadPaths()
    pathDialogVisible.value = false
  } catch (error) {
    console.error('保存路径失败:', error)
    ElMessage.error(error.response?.data?.detail || '保存路径失败')
  }
}

// 扫描配置相关
const handleConfig = async () => {
  try {
    const config = await getDefaultScanConfig()
    Object.assign(configForm, config)
    configDialogVisible.value = true
  } catch (error) {
    console.error('加载扫描配置失败:', error)
    ElMessage.error('加载扫描配置失败')
  }
}

const saveConfig = async () => {
  try {
    await updateDefaultScanConfig(configForm)
    ElMessage.success('扫描配置已保存')
    configDialogVisible.value = false
  } catch (error) {
    console.error('保存扫描配置失败:', error)
    ElMessage.error('保存扫描配置失败')
  }
}

const resetConfig = async () => {
  try {
    await resetDefaultScanConfig()
    Object.assign(configForm, {
      default_scan_type: 'incremental',
      default_recursive: true,
      default_skip_strategy: 'keyword',
      scan_subdirectories: true,
      default_monitor_debounce_time: 30
    })
    ElMessage.info('扫描配置已重置为默认值')
  } catch (error) {
    console.error('重置扫描配置失败:', error)
    ElMessage.error('重置扫描配置失败')
  }
}

// 目录浏览相关
const handleBrowsePath = () => {
  browseTarget.value = 'path'
  currentBrowsePath.value = ''
  browseDialogVisible.value = true
  loadDirectory('')
}

const handleBrowseCustomPath = () => {
  browseTarget.value = 'custom'
  currentBrowsePath.value = ''
  browseDialogVisible.value = true
  loadDirectory('')
}

const loadDirectory = async (path) => {
  try {
    const items = await browseDirectory(path)
    directoryItems.value = items || []
    currentBrowsePath.value = path
  } catch (error) {
    console.error('加载目录失败:', error)
    ElMessage.error(error.response?.data?.detail || '加载目录失败')
  }
}

const enterDirectory = (item) => {
  if (item.is_dir) {
    loadDirectory(item.path)
  }
}

const handleRowDblClick = (row) => {
  if (row.is_dir) {
    enterDirectory(row)
  } else {
    selectPath(row.path)
  }
}

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

const refreshDirectory = () => {
  loadDirectory(currentBrowsePath.value)
}

const selectPath = (path) => {
  if (browseTarget.value === 'path') {
    pathForm.path = path
  } else if (browseTarget.value === 'custom') {
    scanForm.path = path
  }
  browseDialogVisible.value = false
}

const selectCurrentPath = () => {
  if (currentBrowsePath.value) {
    selectPath(currentBrowsePath.value)
  } else {
    ElMessage.warning('请先选择一个目录')
  }
}

const pathSegments = computed(() => {
  if (!currentBrowsePath.value) return []
  const path = currentBrowsePath.value
  const separator = path.includes('\\') ? '\\' : '/'
  const parts = path.split(separator)
  const segments = [parts[0]]
  for (let i = 1; i < parts.length; i++) {
    segments.push(parts[i])
  }
  return segments
})

const navigateToPath = (path) => {
  loadDirectory(path)
}

const getPathUpTo = (index) => {
  const path = currentBrowsePath.value
  const separator = path.includes('\\') ? '\\' : '/'
  const parts = path.split(separator)
  return parts.slice(0, index + 1).join(separator)
}

// 初始化
loadPaths()
loadFileTasks()

// 定时刷新
const refreshInterval = setInterval(() => {
  if (activeTab.value === 'fileTasks') {
    // 只有当有正在扫描或等待中的任务时才自动刷新
    const hasActiveTasks = fileTaskList.value.some(
      task => task.status === 'scanning' || task.status === 'pending'
    )
    if (hasActiveTasks) {
      loadFileTasks()
    }
  }
}, 5000)

// 组件卸载时清理
onUnmounted(() => {
  clearInterval(refreshInterval)
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

  .scan-tabs {
    margin-bottom: 16px;
  }

  .task-card,
  .file-task-card,
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

  .scan-result-detail {
    .el-descriptions {
      margin-top: 20px;
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