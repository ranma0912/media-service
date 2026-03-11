<template>
  <div class="organize-management">
    <!-- 统计卡片 -->
    <el-row :gutter="24">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #1890ff;">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.pending }}</div>
              <div class="stat-label">待整理文件</div>
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
              <div class="stat-label">整理成功</div>
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
              <div class="stat-label">整理中</div>
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
              <div class="stat-label">整理失败</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 待整理文件列表 -->
    <el-card class="list-card">
      <template #header>
        <div class="card-header">
          <span class="title">待整理文件</span>
          <div class="actions">
            <el-button type="primary" :icon="FolderOpened" @click="handleBatchOrganize">批量整理</el-button>
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
        <el-table-column prop="fileName" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="title" label="标题" min-width="150" show-overflow-tooltip />
        <el-table-column prop="sourcePath" label="源路径" min-width="200" show-overflow-tooltip />
        <el-table-column prop="targetPath" label="目标路径" min-width="200" show-overflow-tooltip />
        <el-table-column prop="actionType" label="操作类型" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.actionType === 'move'" type="primary">移动</el-tag>
            <el-tag v-else-if="row.actionType === 'copy'" type="success">复制</el-tag>
            <el-tag v-else-if="row.actionType === 'link'" type="warning">硬链接</el-tag>
            <el-tag v-else type="info">{{ row.actionType }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'pending'" type="info">待整理</el-tag>
            <el-tag v-else-if="row.status === 'processing'" type="warning">整理中</el-tag>
            <el-tag v-else-if="row.status === 'completed'" type="success">已完成</el-tag>
            <el-tag v-else-if="row.status === 'failed'" type="danger">失败</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handlePreview(row)">预览</el-button>
            <el-button link type="primary" @click="handleOrganize(row)">整理</el-button>
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

    <!-- 整理预览对话框 -->
    <el-dialog v-model="previewDialogVisible" title="整理预览" width="800px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="文件名">{{ previewData.fileName }}</el-descriptions-item>
        <el-descriptions-item label="标题">{{ previewData.title }}</el-descriptions-item>
        <el-descriptions-item label="源路径">{{ previewData.sourcePath }}</el-descriptions-item>
        <el-descriptions-item label="目标路径">{{ previewData.targetPath }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">{{ previewData.actionType }}</el-descriptions-item>
        <el-descriptions-item label="文件大小">{{ formatSize(previewData.fileSize) }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="previewDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmOrganize">确认整理</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, CircleCheck, Clock, CircleClose, FolderOpened, Refresh } from '@element-plus/icons-vue'

// 统计数据
const stats = ref({
  pending: 45,
  success: 1980,
  processing: 3,
  failed: 8
})

// 加载状态
const loading = ref(false)

// 表格数据
const tableData = ref([])
const selectedRows = ref([])

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 预览对话框
const previewDialogVisible = ref(false)
const previewData = reactive({
  id: null,
  fileName: '',
  title: '',
  sourcePath: '',
  targetPath: '',
  actionType: '',
  fileSize: 0
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
    // TODO: 调用实际API
    // const res = await request.get('/api/organize/pending', {
    //   params: { ...pagination }
    // })
    // tableData.value = res.data.list
    // pagination.total = res.data.total

    // 模拟数据
    tableData.value = [
      {
        id: 1,
        fileName: 'The.Matrix.1999.1080p.BluRay.x264-SPARKS.mkv',
        title: '黑客帝国',
        sourcePath: 'D:/Downloads/The.Matrix.1999.1080p.BluRay.x264-SPARKS.mkv',
        targetPath: 'D:/Media/电影/黑客帝国 (1999)/黑客帝国 (1999).mkv',
        actionType: 'move',
        status: 'pending',
        fileSize: 2147483648
      },
      {
        id: 2,
        fileName: 'Breaking.Bad.S01E01.1080p.BluRay.x264-SPARKS.mkv',
        title: '绝命毒师',
        sourcePath: 'D:/Downloads/Breaking.Bad.S01E01.1080p.BluRay.x264-SPARKS.mkv',
        targetPath: 'D:/Media/剧集/绝命毒师/Season 01/Breaking.Bad.S01E01.mkv',
        actionType: 'link',
        status: 'pending',
        fileSize: 1073741824
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

// 批量整理
const handleBatchOrganize = () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要整理的文件')
    return
  }

  ElMessageBox.confirm(
    `确定要整理选中的 ${selectedRows.value.length} 个文件吗？`,
    '批量整理',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    }
  ).then(() => {
    ElMessage.success('批量整理任务已启动')
    loadData()
  }).catch(() => {})
}

// 预览
const handlePreview = (row) => {
  Object.assign(previewData, row)
  previewDialogVisible.value = true
}

// 单个整理
const handleOrganize = (row) => {
  Object.assign(previewData, row)
  previewDialogVisible.value = true
}

// 确认整理
const handleConfirmOrganize = () => {
  ElMessage.success('整理任务已启动')
  previewDialogVisible.value = false
  loadData()
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
.organize-management {
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
