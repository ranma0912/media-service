<template>
  <div class="media-library">
    <!-- 搜索栏 -->
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="输入文件名或标题" clearable />
        </el-form-item>
        <el-form-item label="媒体类型">
          <el-select v-model="searchForm.mediaType" placeholder="全部" clearable style="width: 120px;">
            <el-option label="电影" value="movie" />
            <el-option label="剧集" value="tv" />
            <el-option label="动漫" value="anime" />
          </el-select>
        </el-form-item>
        <el-form-item label="识别状态">
          <el-select v-model="searchForm.status" placeholder="全部" clearable style="width: 120px;">
            <el-option label="已识别" value="recognized" />
            <el-option label="未识别" value="unrecognized" />
            <el-option label="识别失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 媒体文件列表 -->
    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span class="title">媒体文件列表</span>
          <div class="actions">
            <el-button type="primary" :icon="Plus" @click="handleAdd">添加文件</el-button>
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
        <el-table-column prop="mediaType" label="类型" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.mediaType === 'movie'" type="success">电影</el-tag>
            <el-tag v-else-if="row.mediaType === 'tv'" type="primary">剧集</el-tag>
            <el-tag v-else-if="row.mediaType === 'anime'" type="warning">动漫</el-tag>
            <el-tag v-else type="info">未知</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="year" label="年份" width="80" />
        <el-table-column prop="fileSize" label="大小" width="100">
          <template #default="{ row }">
            {{ formatSize(row.fileSize) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="识别状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'recognized'" type="success">已识别</el-tag>
            <el-tag v-else-if="row.status === 'unrecognized'" type="warning">未识别</el-tag>
            <el-tag v-else-if="row.status === 'failed'" type="danger">识别失败</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="扫描时间" width="160" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">查看</el-button>
            <el-button link type="primary" @click="handleRecognize(row)">识别</el-button>
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
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus } from '@element-plus/icons-vue'

// 搜索表单
const searchForm = reactive({
  keyword: '',
  mediaType: '',
  status: ''
})

// 表格数据
const loading = ref(false)
const tableData = ref([])
const selectedRows = ref([])

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 格式化文件大小
const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  loadData()
}

// 重置
const handleReset = () => {
  Object.assign(searchForm, {
    keyword: '',
    mediaType: '',
    status: ''
  })
  pagination.page = 1
  loadData()
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    // 调用实际API
    const { getMediaFiles } = await import('@/api/media')
    const res = await getMediaFiles({
      page: pagination.page,
      page_size: pagination.size,
      media_type: searchForm.mediaType,
      search: searchForm.keyword
    })

    // 转换数据格式以匹配前端需求
    tableData.value = res.items.map(item => ({
      id: item.id,
      fileName: item.file_name,
      title: item.title || '',
      mediaType: item.media_type || 'undefined',
      year: item.year || 0,
      fileSize: item.file_size || 0,
      status: item.status || 'unrecognized',
      createdAt: item.scanned_at || ''
    }))
    pagination.total = res.total
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

// 选择变化
const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

// 添加文件
const handleAdd = () => {
  ElMessage.info('添加文件功能开发中')
}

// 查看详情
const handleView = (row) => {
  ElMessage.info(`查看详情: ${row.fileName}`)
}

// 识别
const handleRecognize = (row) => {
  ElMessage.info(`识别文件: ${row.fileName}`)
}

// 删除
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这条记录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    // 调用实际API
    const { deleteMediaFile } = await import('@/api/media')
    await deleteMediaFile(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 初始化
loadData()
</script>

<style lang="scss" scoped>
.media-library {
  .search-card {
    margin-bottom: 16px;
  }

  .table-card {
    .card-header {
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
