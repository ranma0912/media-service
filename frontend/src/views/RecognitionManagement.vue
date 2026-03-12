<template>
  <div class="recognition-management">
    <!-- 统计卡片 -->
    <el-row :gutter="24">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #1890ff;">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total }}</div>
              <div class="stat-label">待识别文件</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #52c41a;">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.success }}</div>
              <div class="stat-label">识别成功</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #faad14;">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.processing }}</div>
              <div class="stat-label">识别中</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #ff4d4f;">
              <el-icon><CircleClose /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.failed }}</div>
              <div class="stat-label">识别失败</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 待识别文件列表 -->
    <el-card class="list-card">
      <template #header>
        <div class="card-header">
          <span class="title">待识别文件</span>
          <div class="actions">
            <el-button type="primary" :icon="VideoPlay" @click="handleBatchRecognize">批量识别</el-button>
            <el-button :icon="Refresh" @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="fileName" label="文件名" min-width="250" show-overflow-tooltip />
        <el-table-column prop="mediaType" label="类型" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.mediaType === 'movie'" type="success">电影</el-tag>
            <el-tag v-else-if="row.mediaType === 'tv'" type="primary">剧集</el-tag>
            <el-tag v-else-if="row.mediaType === 'anime'" type="warning">动漫</el-tag>
            <el-tag v-else type="info">未知</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="fileSize" label="大小" width="100">
          <template #default="{ row }">
            {{ formatSize(row.fileSize) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="识别状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'pending'" type="info">待识别</el-tag>
            <el-tag v-else-if="row.status === 'processing'" type="warning">识别中</el-tag>
            <el-tag v-else-if="row.status === 'success'" type="success">已识别</el-tag>
            <el-tag v-else-if="row.status === 'failed'" type="danger">失败</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="{ row }">
            <span v-if="row.confidence">{{ (row.confidence * 100).toFixed(1) }}%</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="扫描时间" width="160" />
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleRecognize(row)">识别</el-button>
            <el-button link type="primary" @click="handleManual(row)">手动指定</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- 手动识别对话框 -->
    <el-dialog v-model="manualDialogVisible" title="手动识别" width="600px">
      <el-form :model="manualForm" label-width="100px">
        <el-form-item label="文件名">
          <el-input v-model="manualForm.fileName" disabled />
        </el-form-item>
        <el-form-item label="媒体类型">
          <el-select v-model="manualForm.mediaType" placeholder="请选择">
            <el-option label="电影" value="movie" />
            <el-option label="剧集" value="tv" />
            <el-option label="动漫" value="anime" />
          </el-select>
        </el-form-item>
        <el-form-item label="搜索关键词">
          <el-input v-model="manualForm.keyword" placeholder="输入标题或关键词" />
        </el-form-item>
        <el-form-item label="TMDB ID">
          <el-input v-model="manualForm.tmdbId" placeholder="直接输入TMDB ID" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="manualDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, CircleCheck, Clock, CircleClose, VideoPlay, Refresh } from '@element-plus/icons-vue'

// 统计数据
const stats = ref({
  total: 0,
  success: 0,
  processing: 0,
  failed: 0
})

// 加载状态
const loading = ref(false)

// 加载统计数据
const loadStats = async () => {
  try {
    const { getRecognitionStats } = await import('@/api/statistics')
    const recognitionStats = await getRecognitionStats()

    stats.value.total = recognitionStats.total || 0
    stats.value.success = recognitionStats.success || 0
    stats.value.processing = recognitionStats.processing || 0
    stats.value.failed = recognitionStats.failed || 0
  } catch (error) {
    console.error('加载统计数据失败:', error)
    ElMessage.error('加载统计数据失败')
  }
}

// 表格数据
const tableData = ref([])
const selectedRows = ref([])

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 手动识别对话框
const manualDialogVisible = ref(false)
const manualForm = reactive({
  id: null,
  fileName: '',
  mediaType: '',
  keyword: '',
  tmdbId: ''
})

// 格式化文件大小
const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    // 加载统计数据
    await loadStats()

    // TODO: 调用实际API
    // const res = await request.get('/api/recognition/pending', {
    //   params: { ...pagination }
    // })
    // tableData.value = res.data.list
    // pagination.total = res.data.total

    // 模拟数据
    tableData.value = [
      {
        id: 1,
        fileName: 'Unknown.Movie.2024.1080p.mkv',
        mediaType: 'undefined',
        fileSize: 2147483648,
        status: 'pending',
        confidence: 0,
        createdAt: '2024-01-15 10:30:00'
      },
      {
        id: 2,
        fileName: '模糊文件.mkv',
        mediaType: 'undefined',
        fileSize: 1073741824,
        status: 'failed',
        confidence: 0,
        createdAt: '2024-01-15 11:00:00'
      }
    ]
    pagination.total = 2
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

// 选择变化
const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

// 批量识别
const handleBatchRecognize = () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要识别的文件')
    return
  }

  ElMessageBox.confirm(
    `确定要识别选中的 ${selectedRows.value.length} 个文件吗？`,
    '批量识别',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    }
  ).then(() => {
    ElMessage.success('批量识别任务已启动')
    loadData()
  }).catch(() => {})
}

// 单个识别
const handleRecognize = (row) => {
  ElMessage.info(`开始识别: ${row.fileName}`)
}

// 手动指定
const handleManual = (row) => {
  Object.assign(manualForm, {
    id: row.id,
    fileName: row.fileName,
    mediaType: row.mediaType,
    keyword: '',
    tmdbId: ''
  })
  manualDialogVisible.value = true
}

// 搜索
const handleSearch = () => {
  if (!manualForm.keyword && !manualForm.tmdbId) {
    ElMessage.warning('请输入搜索关键词或TMDB ID')
    return
  }

  ElMessage.info('搜索功能开发中')
  manualDialogVisible.value = false
}

// 删除
const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除这条记录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('删除成功')
    loadData()
  }).catch(() => {})
}

// 初始化
loadData()
</script>

<style lang="scss" scoped>
.recognition-management {
  .stat-card {
    margin-bottom: 16px;

    .stat-content {
      display: flex;
      align-items: center;

      .stat-icon {
        width: 60px;
        height: 60px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 16px;

        .el-icon {
          font-size: 32px;
          color: #fff;
        }
      }

      .stat-info {
        flex: 1;

        .stat-value {
          font-size: 24px;
          font-weight: bold;
          color: #333;
          margin-bottom: 8px;
        }

        .stat-label {
          font-size: 14px;
          color: #666;
        }
      }
    }
  }

  .list-card {
    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;

      .title {
        font-size: 16px;
        font-weight: 500;
      }

      .actions {
        display: flex;
        gap: 8px;
      }
    }

    .pagination {
      margin-top: 16px;
      display: flex;
      justify-content: flex-end;
    }
  }
}
</style>
